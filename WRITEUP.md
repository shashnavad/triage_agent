# WRITEUP: Support Ticket Triage & Deflection Agent

## Business impact
The goal is to remove the human touch from tickets that are pure knowledge base lookups (16 of 38 tickets, about 42%, got a verified draft, with 0 false deflections on the labeled set) while making sure the risky ones (outage, data exposure, card numbers, prompt injection) always reach a person with a stated reason. A full run over 38 tickets takes about 32 seconds (12 seconds with 20 workers) and costs about $0.08, roughly $0.002 per ticket.

**Latest eval (3 runs):** 4-field exact match 83% (10 of 12) in every run, P0/P1 recall 67% to 100%, 0 false deflections, stability 96.5%. Product area and deflectable are 100% accurate. Priority is 100% except one P1/P2 flip on T-1004 in one run. The category misses are on two ambiguous labels (T-1004, T-1014).

## Architecture and why
A deterministic LangGraph state graph, not a free-form agent, so every ticket has an auditable path:

1. **Input guardrail:** regex masking of card data, ticket text isolated in `<ticket>` tags, injection patterns flagged.
2. **Classifier (Claude Haiku):** forced tool use plus Pydantic validation returns all 4 taxonomy fields, a confidence score and reasoning. It sees the full KB text so it can judge whether a ticket is fully answerable. Malformed output triggers a retry, then escalation.
3. **Policy router:** low confidence or `deflectable = no` goes to a human with an escalation reason.
4. **Hybrid RAG:** BM25 plus a char n-gram TF-IDF vector index (MiniLM embeddings behind one env var), fused with RRF (k=60), top 3 chunks split by markdown header. BM25 matters for exact tokens like `I-104` and `401`. The classifier also restates the request in English as the search query, so Spanish tickets like T-1016 retrieve correctly.
5. **Drafter (Claude Sonnet) plus critic pass:** the draft must cite KB content, and the critic rejects unsupported claims or promised actions (charging cards, releasing holds). Max 2 corrections, then escalate.

Tiering keeps the cheap model on the high-volume step and spends the stronger model only on the roughly 40% that get a draft. Model IDs are set by environment variable so they can be swapped without code changes.

## Key tradeoffs
- **Bias toward "no":** a wrong confident answer costs more than an extra human touch, so thresholds are conservative (confidence below 0.80, top RRF score below 0.015, or a `bug_defect`/`data_issue`/P0/P1 marked deflectable all escalate).
- **Self-reported confidence is poorly calibrated,** so routing also applies rule-based policy overrides, and run-to-run stability is measured in the eval harness.
- **No fine-tuning:** 12 labels would overfit and add GPU cost for no gain.
- **LangGraph** adds a dependency but makes routing explicit and testable.
- **Label I would challenge:** T-1014 (held $48k payment) is labeled `data_issue` and the model says `billing_contract`. Neither fits, because the taxonomy has no payment-hold category. P1 is correct (payroll deadline).
- **Borderline priority flips:** the current SDK has no temperature setting, so P1 versus P2 tickets (T-1004, T-1009) can flip between runs. This only changes queue order for tickets a human sees anyway.

## What breaks at 10x and 100x
| Volume | Wall time | Cost | First failure |
| --- | --- | --- | --- |
| 38 (measured) | 32 s at 5 workers, 11.5 s at 20 | $0.08 | none observed |
| 380 | ~5 min at 5 workers, ~2 min at 20 | ~$0.83 | API 429s |
| 3,800 | ~53 min at 5 workers, ~19 min at 20 | ~$8.25 | queueing, KB size |

Larger rows are extrapolated from measured throughput. Cost is independent of worker count. 4x workers gave 2.8x speedup because the slowest ticket's classify, draft and verify chain sets a floor.

- **Rate limits:** exponential backoff with jitter plus a token bucket.
- **Ingestion:** replace file input with a queue (SQS or Kafka), idempotent per ticket ID.
- **Knowledge base growth:** move from in-memory BM25 to a disk-backed vector store (Qdrant or pgvector) and cache embeddings.
- **Cost:** prompt caching is already on the classifier prompt. The next lever is the Batch API (half price) for non-urgent tickets.

## Production next
- **Monitoring:** deflection rate, human override rate, escalation reasons, confidence drift, p95 latency, cost per ticket, all logged with redacted text only.
- **Guardrails:** human approval before any draft is sent at launch, output scanner blocking credentials and card data, injection-flagged tickets always reviewed.
- **CI/CD:** the eval harness as a merge gate (fail on accuracy drop, P0/P1 recall drop, or stability under 90%), adversarial tickets (T-1017, T-1036) as permanent regression tests, versioned prompts, shadow mode then canary rollout.
- **Data:** grow the 12 labels to a few hundred, sampled from human overrides.
