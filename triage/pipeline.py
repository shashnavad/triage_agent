import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config
from .graph import build_graph
from .llm import LLM
from .retrieval import HybridRetriever

TICKET_FIELDS = ["ticket_id", "created_at", "channel", "customer_org", "requester", "subject", "body"]


def load_tickets(path) -> list[dict]:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    else:
        rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("tickets file must contain a list of tickets")
    tickets = []
    for i, r in enumerate(rows):
        if not r.get("ticket_id"):
            raise ValueError(f"ticket at index {i} has no ticket_id")
        tickets.append({k: str(r.get(k) or "") for k in TICKET_FIELDS})
    return tickets


def make_graph(llm=None):
    return build_graph(llm or LLM(), HybridRetriever())


def to_record(ticket: dict, s: dict) -> dict:
    route = s["route"]
    conf = s.get("confidence_score", 0.0)
    flags = []
    if conf < config.CONF_THRESHOLD:
        flags.append("low_confidence")
    if s.get("injection_flagged"):
        flags.append("possible_prompt_injection")
    if s.get("sensitive_flagged"):
        flags.append("sensitive_data_in_ticket")
    return {
        "ticket_id": ticket["ticket_id"],
        "subject": ticket["subject"],
        "category": s.get("category", "other"),
        "priority": s.get("priority", "P2"),
        "product_area": s.get("product_area", "general"),
        "deflectable": "yes" if route == "auto_draft" else "no",
        "model_deflectable": s.get("model_deflectable", "no"),
        "confidence_score": conf,
        "route": route,
        "needs_human_review": route == "human" or bool(flags),
        "review_flags": flags,
        "escalation_reason": "; ".join(s.get("escalation_reasons", [])) or None,
        "draft_response": s.get("draft_response") if route == "auto_draft" else None,
        "kb_sources": [c["id"] for c in s.get("retrieved_chunks", [])] if route == "auto_draft" else [],
        "drafts_attempted": s.get("retry_count", 0),
        "reasoning": s.get("classification_reasoning", ""),
        "audit_trail": s.get("audit_trail", []),
    }


def error_record(ticket: dict, err: Exception) -> dict:
    return {"ticket_id": ticket["ticket_id"], "subject": ticket["subject"], "category": "other", "priority": "P2",
            "product_area": "general", "deflectable": "no", "model_deflectable": "no", "confidence_score": 0.0,
            "route": "human", "needs_human_review": True, "review_flags": ["pipeline_error"],
            "escalation_reason": f"pipeline error: {type(err).__name__}: {err}", "draft_response": None,
            "kb_sources": [], "drafts_attempted": 0, "reasoning": "", "audit_trail": ["error"]}


def run_tickets(graph, tickets: list[dict], workers: int = config.WORKERS) -> list[dict]:
    """Runs every ticket through the graph. One bad ticket never stops the batch."""
    def one(t):
        try:
            return to_record(t, graph.invoke({"ticket_id": t["ticket_id"], "raw_ticket": t}))
        except Exception as e:
            return error_record(t, e)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(one, tickets))
