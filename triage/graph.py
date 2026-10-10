"""LangGraph state machine: guard -> classify -> policy -> retrieve -> draft <-> verify -> finalize | escalate."""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from . import config, guardrails, prompts
from .schema import CriticVerdict, Taxonomy

HUMAN_ONLY_CATEGORIES = {"bug_defect", "data_issue", "security_privacy", "billing_contract", "feature_request"}


class AgentState(TypedDict, total=False):
    ticket_id: str
    raw_ticket: dict
    sanitized_text: str
    injection_flagged: bool
    sensitive_flagged: bool
    classification_failed: bool
    category: str
    priority: str
    product_area: str
    model_deflectable: str
    confidence_score: float
    classification_reasoning: str
    english_query: str
    retrieved_chunks: list
    draft_response: str | None
    retry_count: int
    validation_errors: list
    draft_verified: bool
    route: str
    escalation_reasons: Annotated[list, operator.add]
    audit_trail: Annotated[list, operator.add]


def policy_reasons(s: dict) -> list[str]:
    """Pure routing rules. Any reason returned sends the ticket to a human."""
    reasons = []
    if s.get("classification_failed"):
        return [s["classification_reasoning"]]
    if s["confidence_score"] < config.CONF_THRESHOLD:
        reasons.append(f"low confidence ({s['confidence_score']:.2f} < {config.CONF_THRESHOLD})")
    if s["model_deflectable"] == "no":
        reasons.append(f"not deflectable: {s['classification_reasoning']}")
    elif s["category"] in HUMAN_ONLY_CATEGORIES:
        reasons.append(f"policy override: {s['category']} always needs a human")
    elif s["priority"] in ("P0", "P1"):
        reasons.append(f"policy override: {s['priority']} always needs a human")
    return reasons


def build_graph(llm, retriever):
    classifier_system = prompts.classifier_system(retriever.index_text())

    def guard(state):
        t = state["raw_ticket"]
        g = guardrails.sanitize(f"Subject: {t.get('subject', '')}\n\n{t.get('body', '')}")
        trail = [f"guard: injection={g['injection_flagged']} sensitive={g['sensitive_flagged']}"]
        return {"sanitized_text": g["text"], "injection_flagged": g["injection_flagged"],
                "sensitive_flagged": g["sensitive_flagged"], "audit_trail": trail}

    def classify(state):
        user = prompts.ticket_block(state["raw_ticket"].get("channel", ""), state["sanitized_text"])
        try:
            r = llm.structured(config.CLASSIFIER_MODEL, Taxonomy, classifier_system, user)
        except Exception as e:  # API failure or malformed output after retry
            return {"classification_failed": True, "category": "other", "priority": "P2", "product_area": "general",
                    "model_deflectable": "no", "confidence_score": 0.0,
                    "classification_reasoning": f"classification error: {type(e).__name__}: {str(e)[:200]}",
                    "english_query": "", "audit_trail": [f"classify: failed ({type(e).__name__}: {str(e)[:200]})"]}
        return {"category": r.category, "priority": r.priority, "product_area": r.product_area,
                "model_deflectable": r.deflectable, "confidence_score": r.confidence_score,
                "classification_reasoning": r.reasoning, "english_query": r.english_query,
                "audit_trail": [f"classify: {r.category}/{r.priority}/{r.product_area}/{r.deflectable} @ {r.confidence_score:.2f}"]}

    def policy(state):
        reasons = policy_reasons(state)
        return {"escalation_reasons": reasons, "audit_trail": [f"policy: {'escalate' if reasons else 'pass'}"]}

    def retrieve(state):
        chunks = retriever.search(f"{state['english_query']}\n{state['sanitized_text']}")
        out = {"retrieved_chunks": chunks, "retry_count": 0, "validation_errors": [],
               "audit_trail": [f"retrieve: {[c['id'] for c in chunks]}"]}
        if not chunks or chunks[0]["score"] < config.RRF_MIN:
            out["escalation_reasons"] = ["knowledge base has no strong match for this ticket"]
        return out

    def draft(state):
        errors = state.get("validation_errors", [])
        try:
            text = llm.text(config.DRAFT_MODEL, prompts.DRAFT_SYSTEM,
                            prompts.draft_user(state["retrieved_chunks"], state["sanitized_text"],
                                               state.get("draft_response"), errors))
        except Exception as e:
            return {"escalation_reasons": [f"draft generation failed ({type(e).__name__})"],
                    "audit_trail": ["draft: error"]}
        if text.startswith("INSUFFICIENT_CONTEXT"):
            return {"escalation_reasons": ["KB excerpts do not fully answer the ticket"],
                    "audit_trail": ["draft: insufficient context"]}
        n = state.get("retry_count", 0) + 1
        return {"draft_response": text, "retry_count": n, "audit_trail": [f"draft: attempt {n}"]}

    def verify(state):
        issues = guardrails.check_output(state["draft_response"])
        if not issues:
            try:
                v = llm.structured(config.CLASSIFIER_MODEL, CriticVerdict, prompts.CRITIC_SYSTEM,
                                   prompts.critic_user(state["retrieved_chunks"], state["sanitized_text"], state["draft_response"]))
                if not (v.grounded and v.safe):
                    issues = v.issues or ["critic rejected the draft"]
            except Exception as e:
                return {"escalation_reasons": [f"draft verification failed ({type(e).__name__})"],
                        "audit_trail": ["verify: error"]}
        if not issues:
            return {"draft_verified": True, "validation_errors": [], "audit_trail": ["verify: pass"]}
        out = {"draft_verified": False, "validation_errors": issues, "audit_trail": [f"verify: fail {issues}"]}
        if state["retry_count"] > config.MAX_CORRECTIONS:
            out["escalation_reasons"] = ["draft failed verification: " + "; ".join(issues)]
        return out

    def finalize(state):
        return {"route": "auto_draft", "audit_trail": ["finalize: auto_draft"]}

    def escalate(state):
        return {"route": "human", "draft_response": None, "audit_trail": ["finalize: human"]}

    g = StateGraph(AgentState)
    for name, fn in [("guard", guard), ("classify", classify), ("policy", policy), ("retrieve", retrieve),
                     ("draft", draft), ("verify", verify), ("finalize", finalize), ("escalate", escalate)]:
        g.add_node(name, fn)
    has_reasons = lambda s: bool(s.get("escalation_reasons"))
    g.add_edge(START, "guard")
    g.add_edge("guard", "classify")
    g.add_edge("classify", "policy")
    g.add_conditional_edges("policy", lambda s: "escalate" if has_reasons(s) else "retrieve")
    g.add_conditional_edges("retrieve", lambda s: "escalate" if has_reasons(s) else "draft")
    g.add_conditional_edges("draft", lambda s: "escalate" if has_reasons(s) else "verify")
    g.add_conditional_edges("verify", lambda s: "finalize" if s.get("draft_verified") else ("escalate" if has_reasons(s) else "draft"))
    g.add_edge("finalize", END)
    g.add_edge("escalate", END)
    return g.compile()
