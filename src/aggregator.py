"""
Reads artifacts/runs.jsonl, grades every run (schema + deterministic, and
optionally the narrow LLM judge), and produces:
  - case-level results (one row per run)
  - aggregate metrics per (prompt_version, model_id)

This is what backs the tables in REPORT.md.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from src.graders.schema_grader import grade_schema
from src.graders.deterministic_grader import grade_case_deterministic

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_LOG = REPO_ROOT / "artifacts" / "runs.jsonl"


def load_runs(path: Path = RUNS_LOG) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def grade_run(run: dict) -> dict:
    graded = dict(run)
    graded.update(grade_schema(run.get("parsed_output")))
    if run.get("reference") and run.get("parsed_output"):
        graded.update(grade_case_deterministic(run["parsed_output"], run["reference"]))
    return graded


def aggregate(graded_runs: list[dict]) -> dict:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in graded_runs:
        groups[(r.get("prompt_version"), r.get("model_id"))].append(r)

    summary = {}
    for (prompt_version, model_id), rows in groups.items():
        n = len(rows)
        schema_valid = sum(1 for r in rows if r.get("schema_valid"))
        critical_failures = sum(1 for r in rows if r.get("critical_failure"))
        state_pass = sum(1 for r in rows if r.get("state_check") == "pass")
        state_checked = sum(1 for r in rows if r.get("state_check") in ("pass", "fail"))
        unsafe = sum(1 for r in rows if r.get("unsafe_action"))
        false_completion = sum(1 for r in rows if r.get("false_completion"))
        avg_latency = sum(r.get("latency_seconds", 0) or 0 for r in rows) / n if n else 0
        total_tokens = sum(r.get("total_tokens", 0) or 0 for r in rows)
        total_cost = sum(r.get("estimated_cost_usd", 0) or 0 for r in rows)

        summary[f"{prompt_version} | {model_id}"] = {
            "n_cases": n,
            "schema_validity_rate": round(schema_valid / n, 3) if n else None,
            "state_accuracy": round(state_pass / state_checked, 3) if state_checked else None,
            "critical_failure_rate": round(critical_failures / n, 3) if n else None,
            "unsafe_action_rate": round(unsafe / n, 3) if n else None,
            "false_completion_rate": round(false_completion / n, 3) if n else None,
            "avg_latency_seconds": round(avg_latency, 3),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
        }
    return summary


def run(out_path: str | None = None) -> dict:
    out_path = out_path or str(REPO_ROOT / "artifacts" / "summary.json")
    runs = load_runs()
    graded = [grade_run(r) for r in runs]
    summary = aggregate(graded)

    with open(out_path, "w") as f:
        json.dump({"per_case": graded, "aggregate": summary}, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"\nFull per-case grading written to {out_path}")
    return summary


def main() -> None:
    """Only used when running `python -m src.aggregator` directly."""
    parser = argparse.ArgumentParser(description="Grade and aggregate all logged runs.")
    parser.add_argument("--out", default=str(REPO_ROOT / "artifacts" / "summary.json"))
    args = parser.parse_args()
    run(args.out)


if __name__ == "__main__":
    main()
