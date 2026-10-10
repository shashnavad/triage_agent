# Support Ticket Triage & Deflection Agent

Classifies Northwind Books support tickets on 4 taxonomy fields, drafts KB-grounded replies for deflectable tickets, and routes everything else to a human with a reason. Design details are in `SYSTEM_DESIGN.md`, tradeoffs and scaling notes in `WRITEUP.md`.

## Commands to Use and Start

### 1. One-time setup
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"   # read from the environment, never committed
```

### 2. Run the pipeline on a tickets file (the one command for new tickets)
```bash
python run.py --input new_tickets.json
```
Writes `results.json` and prints one line per ticket. `--output results.json` and `--workers 5` are optional. Input can be `.json` or `.csv` with the fields `ticket_id, created_at, channel, customer_org, requester, subject, body`.

Full run over the 38 provided tickets:
```bash
python run.py --input tickets.json --output results.json
```

### 3. Run the evaluation harness
```bash
python eval.py                      # 3 runs over tickets.json, scored against labeled_sample.csv
python eval.py --runs 5             # more runs for a tighter consistency number
python eval.py --min-exact 0.75 --min-stability 0.95   # CI gate, exits 1 if either is missed
```
Prints 4-field exact match, per-field accuracy and macro-F1, P0/P1 recall, false deflections, run-to-run stability, low-confidence flags and draft checks. Full detail is written to `eval_report.json`.

### 4. Run the offline tests (no API key needed)
```bash
python -m pytest -q
```

### 5. Demo flow (about 3 minutes)
```bash
python run.py --input tickets.json --output results.json   # all 38 tickets
python eval.py                                             # accuracy and stability
python run.py --input new_tickets.json                     # unseen tickets
```

## Layout
```
run.py                 CLI: classify + draft a tickets file
eval.py                evaluation harness
triage/graph.py        LangGraph state machine and routing rules
triage/guardrails.py   PII masking, injection stripping, output safety checks
triage/retrieval.py    BM25 + vector index fused with RRF
triage/llm.py          Anthropic wrapper (forced tool use, retries)
triage/prompts.py      all prompts
triage/schema.py       Pydantic models
kb/  tickets.json  labeled_sample.csv   data from the take-home packet
tests/test_offline.py  fake-LLM tests for guardrails, retrieval and routing
```

## Output
Each entry in `results.json` contains:
- `category`, `priority`, `product_area`, `deflectable` (final value after policy rules), `confidence_score`
- `route`: `auto_draft` or `human`
- `needs_human_review` and `review_flags` (`low_confidence`, `possible_prompt_injection`, `sensitive_data_in_ticket`, `pipeline_error`)
- `escalation_reason` for every ticket routed to a human
- `draft_response` and `kb_sources` for drafted tickets
- `audit_trail` with each step the ticket took

## Configuration (environment variables, all optional)
| Variable | Default | Purpose |
| --- | --- | --- |
| `CLASSIFIER_MODEL` | `claude-haiku-5-5` | classification model |
| `DRAFT_MODEL` | `claude-sonnet-5-5` | drafting and critic model |
| `CONF_THRESHOLD` | `0.80` | below this, a human reviews |
| `RRF_MIN` | `0.015` | minimum top KB chunk score to draft |
| `MAX_CORRECTIONS` | `2` | redrafts after a failed check |
| `DENSE_BACKEND` | `tfidf` | set `minilm` (and `pip install sentence-transformers`) for real embeddings |

## Notes
- Card numbers, CVVs and key-like strings are masked before any prompt or log write.
- Ticket text is treated as data. Lines that look like instructions to the AI (for example in T-1017) are removed, and the ticket is flagged for review.
- Any API failure or malformed model output on one ticket escalates that ticket to a human and the batch continues.
