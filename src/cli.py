"""
Single entrypoint tying everything together.

Examples:
  python -m src.cli split
  python -m src.cli run --cases tuning --prompt prompt_v0 --model openai/gpt-4o-mini
  python -m src.cli run --cases holdout --prompt prompt_v2 --model qwen/qwen-2.5-72b-instruct
  python -m src.cli run --cases pii --prompt prompt_v2 --model openai/gpt-4o-mini --context full
  python -m src.cli grade
  python -m src.cli run --cases tuning --prompt prompt_v0 --model openai/gpt-4o-mini --dry-run
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.model_adapter import DryRunAdapter, call_model
from src.runner import run_case_set

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = REPO_ROOT / "cases"

CASE_FILES = {
    "tuning": CASES_DIR / "tuning_cases.jsonl",
    "holdout": CASES_DIR / "holdout_cases.jsonl",
    "pii": CASES_DIR / "pii_cases.jsonl",
}


def cmd_split(_: argparse.Namespace) -> None:
    import runpy
    runpy.run_path(str(CASES_DIR / "split_cases.py"), run_name="__main__")


def cmd_run(args: argparse.Namespace) -> None:
    cases_path = CASE_FILES[args.cases]
    caller = DryRunAdapter() if args.dry_run else call_model
    use_minimised = args.context != "full"

    records = run_case_set(
        cases_path=cases_path,
        prompt_version=args.prompt,
        model_id=args.model,
        caller=caller,
        use_pii_minimised_context=use_minimised,
    )
    print(f"Ran {len(records)} case(s) from {args.cases} with {args.prompt} on {args.model} "
          f"(context={'minimised' if use_minimised else 'full'}, dry_run={args.dry_run})")
    for r in records:
        status = "OK" if r["json_valid"] else f"INVALID JSON ({r['error']})"
        print(f"  {r['case_id']}: {status}, {r['total_tokens']} tokens, {r['latency_seconds']}s")


def cmd_grade(args: argparse.Namespace) -> None:
    from src import aggregator
    aggregator.run(args.out)


def main() -> None:
    parser = argparse.ArgumentParser(description="HULP AI evaluation loop CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("split", help="Split starter cases into tuning/holdout sets").set_defaults(func=cmd_split)

    run_p = sub.add_parser("run", help="Run a case set through a prompt+model")
    run_p.add_argument("--cases", choices=list(CASE_FILES), required=True)
    run_p.add_argument("--prompt", required=True, help="prompt file name without .txt, e.g. prompt_v0")
    run_p.add_argument("--model", required=True, help="explicit OpenRouter model id, e.g. openai/gpt-4o-mini")
    run_p.add_argument("--context", choices=["minimised", "full"], default="minimised")
    run_p.add_argument("--dry-run", action="store_true", help="Use a canned response instead of calling OpenRouter")
    run_p.set_defaults(func=cmd_run)

    grade_p = sub.add_parser("grade", help="Grade all logged runs and print aggregate metrics")
    grade_p.add_argument("--out", default=str(REPO_ROOT / "artifacts" / "summary.json"))
    grade_p.set_defaults(func=cmd_grade)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
