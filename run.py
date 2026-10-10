"""Usage: python run.py --input new_tickets.json [--output results.json]"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from triage import config
from triage.pipeline import load_tickets, make_graph, run_tickets


def main() -> int:
    ap = argparse.ArgumentParser(description="Classify support tickets and draft KB-grounded replies.")
    ap.add_argument("--input", required=True, help="tickets file (.json or .csv, same fields as tickets.json)")
    ap.add_argument("--output", default="results.json")
    ap.add_argument("--workers", type=int, default=config.WORKERS)
    args = ap.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Run: export ANTHROPIC_API_KEY=...", file=sys.stderr)
        return 2

    tickets = load_tickets(args.input)
    results = run_tickets(make_graph(), tickets, args.workers)
    Path(args.output).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    for r in results:
        note = "drafted reply" if r["route"] == "auto_draft" else (r["escalation_reason"] or "")[:70]
        flag = " [REVIEW: " + ",".join(r["review_flags"]) + "]" if r["review_flags"] else ""
        print(f"{r['ticket_id']}  {r['priority']}  {r['category']:<16} {r['product_area']:<16} "
              f"defl={r['deflectable']:<3} conf={r['confidence_score']:.2f}  {note}{flag}")
    routes = Counter(r["route"] for r in results)
    print(f"\n{len(results)} tickets: {routes['auto_draft']} drafted, {routes['human']} routed to a human, "
          f"{sum(r['needs_human_review'] for r in results)} flagged for review. Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
