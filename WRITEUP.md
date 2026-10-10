# WRITEUP: Support Ticket Triage & Deflection Agent

## Business impact
The goal is to remove the human touch from tickets that are pure knowledge base lookups (5 of the 12 labeled tickets, about 40%) while making sure the risky ones (outage, data exposure, card numbers, prompt injection) always reach a person with a stated reason. A full run over 38 tickets costs about $0.02, roughly $0.0005 per ticket.

**Latest eval (paste from `python eval.py`):** 4-field exact match [ ]/12, P0/P1 recall [ ], 3-run stability [ ]%.

## Architecture and why
A deterministic LangGraph state graph, not a free-form agent, so every ticket has an auditable path:

1. **Input guardrail:** regex masking of card data, ticket text isolated in `<ticket_body>` tags, injection patterns flagged.
2. **Classifier (Claude Haiku):** forced tool use plus Pydantic validation returns all 4 taxonomy fields, a confidence score and reasoning. Malformed output triggers a retry, then escalation.
3. **Policy router:** low confidence or `deflectable = no` goes to a human with an escalation reason.
4. **Hybrid RAG:** BM25 plus a char n-gram TF-IDF vector index (MiniLM embeddings behind one env var), fused with RRF (k=60), top 3 chunks split by markdown header. BM25 matters for exact tokens like `I-104` and `401`. The classifier also restates the request in English as the search query, so Spanish tickets like T-1016 retrieve correctly.
5. **Drafter (Claude Sonnet) plus critic pass:** the draft must cite KB content, and the critic rejects unsupported claims or promised actions (charging cards, releasing holds). Max 2 corrections, then escalate.

Tiering keeps the cheap model on the high-volume step and spends the stronger model only on the roughly 40% that get a draft. Model IDs are set by environment variable so they can be swapped without code changes.

## Key tradeoffs
- **Bias toward "no":** a wrong confident answer costs more than an extra human touch, so thresholds are conservative (confidence below 0.80, top RRF score below 0.015, or a `bug_defect`/`data_issue`/P0/P1 marked deflectable all escalate).
- **Self-reported confidence is poorly calibrated,** so it is combined with rule checks and disagreement across repeated runs.
- **No fine-tuning:** 12 labels would overfit and add GPU cost for no gain.
- **LangGraph** adds a dependency but makes routing explicit and testable.
- **Label I would challenge:** T-1014 (held $48k payment) is labeled `data_issue`. Nothing is wrong with the data; it is a Risk team review, so `other` or a payments-hold category fits better. P1 is correct (payroll deadline).

## What breaks at 10x and 100x
| Volume | Latency | Cost | First failure |
| --- | --- | --- | --- |
| 38 (baseline) | ~25 s sequential | ~$0.02 | none |
| 380 | ~18 s with 10 async workers | ~$0.20 | API 429s |
| 3,800 | ~2.5 min with worker pool | ~$2.00 | queueing, KB size |

- **Rate limits:** exponential backoff with jitter plus a token bucket.
- **Ingestion:** replace file input with a queue (SQS or Kafka), idempotent per ticket ID.
- **Knowledge base growth:** move from in-memory BM25 to a disk-backed vector store (Qdrant or pgvector) and cache embeddings.
- **Cost:** use prompt caching on the static taxonomy prompt.

## Production next
- **Monitoring:** deflection rate, human override rate, escalation reasons, confidence drift, p95 latency, cost per ticket, all logged with redacted text only.
- **Guardrails:** human approval before any draft is sent at launch, output scanner blocking credentials and card data, injection-flagged tickets always reviewed.
- **CI/CD:** the eval harness as a merge gate (fail on accuracy drop, P0/P1 recall drop, or stability under 95%), adversarial tickets (T-1017, T-1036) as permanent regression tests, versioned prompts, shadow mode then canary rollout.
- **Data:** grow the 12 labels to a few hundred, sampled from human overrides.
