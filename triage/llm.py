"""Thin Anthropic wrapper: forced tool use for structured output, retries for malformed output."""
import threading
from collections import defaultdict
import anthropic
from pydantic import BaseModel

from . import config

class LLMOutputError(RuntimeError):
    pass


class LLM:
    def __init__(self, client=None):
        # The SDK retries 429 and 5xx responses with exponential backoff.
        self.client = client or anthropic.Anthropic(max_retries=5)
        self.usage = defaultdict(lambda: defaultdict(int))
        self._lock = threading.Lock()

    def _track(self, model, resp):
        u = resp.usage
        with self._lock:
            d = self.usage[model]
            d["input"] += u.input_tokens
            d["output"] += u.output_tokens
            d["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
            d["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0

    def cost_usd(self) -> float:
        total = 0.0
        for model, d in self.usage.items():
            p = config.PRICES.get(model)
            if p:
                total += (d["input"] * p[0] + d["output"] * p[1] + d["cache_read"] * p[2] + d["cache_write"] * p[3]) / 1e6
        return total

    @staticmethod
    def _system(text: str) -> list[dict]:
        return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]

    def structured(self, model: str, schema: type[BaseModel], system: str, user: str, max_tokens: int = 800):
        name = f"record_{schema.__name__.lower()}"
        tool = {"name": name, "description": f"Record the {schema.__name__} result.",
                "input_schema": schema.model_json_schema()}
        content, last_error = user, None
        for _ in range(2):  # one retry with the validation error fed back
            resp = self.client.messages.create(
                model=model, max_tokens=max_tokens,
                system=self._system(system), tools=[tool],
                tool_choice={"type": "tool", "name": name},
                messages=[{"role": "user", "content": content}],
            )
            self._track(model, resp)
            block = next((b for b in resp.content if b.type == "tool_use"), None)
            try:
                if block is None:
                    raise ValueError("model returned no tool call")
                return schema.model_validate(block.input)
            except ValueError as e:  # pydantic.ValidationError subclasses ValueError
                last_error = e
                content = f"{user}\n\nYour previous output was invalid ({e}). Call the tool again with valid values."
        raise LLMOutputError(f"invalid structured output after retry: {last_error}")

    def text(self, model: str, system: str, user: str, max_tokens: int = 700) -> str:
        resp = self.client.messages.create(
            model=model, max_tokens=max_tokens,
            system=self._system(system), messages=[{"role": "user", "content": user}],
        )
        self._track(model, resp)
        return "".join(b.text for b in resp.content if b.type == "text").strip()
