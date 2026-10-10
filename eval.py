"""Usage: python eval.py [--input tickets.json] [--labels labeled_sample.csv] [--runs 3]

Runs the full pipeline N times, then reports accuracy vs the labeled sample, run-to-run consistency,
low-confidence flagging and draft safety. Exits 1 if --min-exact or --min-stability is not met (CI gate).
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

from sklearn.metrics import f1_score

from triage import config, guardrails
from triage.pipeline import load_tickets, make_graph, run_tickets
from triage.schema import FIELDS


def load_labels(path) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
        return {r["ticket_id"]: {k: r[k] for k in FIELDS} for r in csv.DictReader(f)}


def classification_metrics(records: list[dict], labels: dict) -> dict:
    rows = [(r, labels[r["ticket_id"]]) for r in records if r["ticket_id"] in labels]
    n = len(rows)
    exact = sum(all(p[f] == t[f] for f in FIELDS) for p, t in rows)
    per_field = {f: sum(p[f] == t[f] for p, t in rows) / n for f in FIELDS}
    f1 = {f: f1_score([t[f] for _, t in rows], [p[f] for p, _ in rows], average="macro", zero_division=0) for f in FIELDS}
    high = [(p, t) for p, t in rows if t["priority"] in ("P0", "P1")]
    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return {
        "n_labeled": n,
        "exact_match": exact / n,
        "per_field_accuracy": per_field,
        "per_field_macro_f1": f1,
        "p0_p1_recall": sum(p["priority"] in ("P0", "P1") for p, _ in high) / len(high) if high else None,
        "priority_downgrades": [p["ticket_id"] for p, t in rows if rank[p["priority"]] > rank[t["priority"]]],
        "false_deflections": [p["ticket_id"] for p, t in rows if p["deflectable"] == "yes" and t["deflectable"] == "no"],
        "mismatches": {p["ticket_id"]: {f: {"pred": p[f], "label": t[f]} for f in FIELDS if p[f] != t[f]}
                       for p, t in rows if any(p[f] != t[f] for f in FIELDS)},
    }


def consistency(runs: list[list[dict]]) -> dict:
    by_id: dict[str, list[tuple]] = {}
    for run in runs:
        for r in run:
            by_id.setdefault(r["ticket_id"], []).append(tuple(r[f] for f in FIELDS))
    agree = {tid: Counter(v).most_common(1)[0][1] / len(v) for tid, v in by_id.items()}
    unstable = {tid: [dict(zip(FIELDS, v)) for v in set(by_id[tid])] for tid, a in agree.items() if a < 1}
    return {"stability": sum(agree.values()) / len(agree), "fully_stable_tickets": sum(a == 1 for a in agree.values()),
            "n_tickets": len(agree), "unstable": unstable}


def review_and_draft_quality(records: list[dict], labels: dict, metrics: dict) -> dict:
    drafts = [r for r in records if r["route"] == "auto_draft"]
    labeled = [r for r in records if r["ticket_id"] in labels]
    flagged = [r for r in labeled if "low_confidence" in r["review_flags"]]
    right = lambda r: all(r[f] == labels[r["ticket_id"]][f] for f in FIELDS)
    return {
        "confidence_threshold": config.CONF_THRESHOLD,
        "low_confidence_tickets": [r["ticket_id"] for r in records if "low_confidence" in r["review_flags"]],
        "labeled_flagged_accuracy": sum(map(right, flagged)) / len(flagged) if flagged else None,
        "labeled_unflagged_accuracy": (lambda u: sum(map(right, u)) / len(u) if u else None)(
            [r for r in labeled if "low_confidence" not in r["review_flags"]]),
        "injection_flagged": [r["ticket_id"] for r in records if "possible_prompt_injection" in r["review_flags"]],
        "sensitive_data_flagged": [r["ticket_id"] for r in records if "sensitive_data_in_ticket" in r["review_flags"]],
        "drafts_produced": len(drafts),
        "drafts_needing_correction": sum(r["drafts_attempted"] > 1 for r in drafts),
        "drafts_failing_rule_check": [r["ticket_id"] for r in drafts if guardrails.check_output(r["draft_response"])],
        "false_deflections_on_labeled": metrics["false_deflections"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="tickets.json")
    ap.add_argument("--labels", default="labeled_sample.csv")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--output", default="eval_report.json")
    ap.add_argument("--min-exact", type=float, help="fail if 4-field exact match is below this")
    ap.add_argument("--min-stability", type=float, help="fail if run-to-run stability is below this")
    args = ap.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Run: export ANTHROPIC_API_KEY=...", file=sys.stderr)
        return 2

    tickets, labels, graph = load_tickets(args.input), load_labels(args.labels), make_graph()
    runs = []
    for i in range(args.runs):
        print(f"run {i + 1}/{args.runs} over {len(tickets)} tickets ...", flush=True)
        runs.append(run_tickets(graph, tickets))

    per_run = [classification_metrics(r, labels) for r in runs]
    metrics = per_run[0]
    stab = consistency(runs)
    quality = review_and_draft_quality(runs[0], labels, metrics)
    report = {"classification": metrics, "consistency": stab, "review_and_drafts": quality}
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nCLASSIFICATION vs labeled sample ({metrics['n_labeled']} tickets, run 1)")
    print(f"  4-field exact match : {metrics['exact_match']:.0%}")
    for f in FIELDS:
        print(f"  {f:<13} acc {metrics['per_field_accuracy'][f]:.0%}   macro-F1 {metrics['per_field_macro_f1'][f]:.2f}")
    print(f"  P0/P1 recall        : {metrics['p0_p1_recall']}   downgrades: {metrics['priority_downgrades'] or 'none'}")
    print(f"  false deflections   : {metrics['false_deflections'] or 'none'}")
    print(f"  per run exact match {[round(m['exact_match'], 2) for m in per_run]}, "
          f"P0/P1 recall {[round(m['p0_p1_recall'], 2) for m in per_run]}")
    for tid, diff in metrics["mismatches"].items():
        print(f"  mismatch {tid}: {diff}")
    print(f"\nCONSISTENCY over {args.runs} runs: stability {stab['stability']:.1%}, "
          f"{stab['fully_stable_tickets']}/{stab['n_tickets']} tickets identical every run")
    for tid, variants in stab["unstable"].items():
        print(f"  unstable {tid}: {variants}")
    print(f"\nREVIEW FLAGS (low confidence < {config.CONF_THRESHOLD}): {quality['low_confidence_tickets'] or 'none'}")
    print(f"  accuracy when flagged {quality['labeled_flagged_accuracy']}, when not flagged {quality['labeled_unflagged_accuracy']}")
    print(f"  injection flagged {quality['injection_flagged']}, sensitive data flagged {quality['sensitive_data_flagged']}")
    print(f"DRAFTS: {quality['drafts_produced']} produced, {quality['drafts_needing_correction']} needed correction, "
          f"rule violations {quality['drafts_failing_rule_check'] or 'none'}\nWrote {args.output}")

    failed = []
    if args.min_exact is not None and metrics["exact_match"] < args.min_exact:
        failed.append(f"exact match {metrics['exact_match']:.0%} < {args.min_exact:.0%}")
    if args.min_stability is not None and stab["stability"] < args.min_stability:
        failed.append(f"stability {stab['stability']:.1%} < {args.min_stability:.1%}")
    if failed:
        print("GATE FAILED: " + "; ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
