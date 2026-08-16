"""
Deterministic, one-time split of the 12 supplied starter cases into a
tuning set and a locked holdout set, then adds the hand-authored extra
cases so each set has at least 8 cases (assignment requirement).

Run once: `python cases/split_cases.py`
Do NOT edit holdout_cases.jsonl by hand afterwards -- treat it as locked.

Split logic: odd-position cases (S-P01, 03, 05, 07, 09, 11) go to tuning;
even-position cases (S-P02, 04, 06, 08, 10, 12) go to holdout. This was
chosen (not random) so both sets get a spread of failure types -- e.g.
tuning gets the prompt-injection-free cases while holdout still gets
S-P08 (prompt injection) and S-P12 (escalation), etc. See README for the
full tag breakdown.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]

def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

def main() -> None:
    starter = load_jsonl(HERE / "starter_all.jsonl")
    tuning = [c for i, c in enumerate(starter) if i % 2 == 0]   # S-P01,03,05,07,09,11
    holdout = [c for i, c in enumerate(starter) if i % 2 == 1]  # S-P02,04,06,08,10,12

    tuning += load_jsonl(HERE / "additional_tuning_cases.jsonl")
    holdout += load_jsonl(HERE / "additional_holdout_cases.jsonl")

    write_jsonl(HERE / "tuning_cases.jsonl", tuning)
    write_jsonl(HERE / "holdout_cases.jsonl", holdout)

    print(f"tuning_cases.jsonl: {len(tuning)} cases")
    print(f"holdout_cases.jsonl: {len(holdout)} cases (LOCKED -- do not tune against these)")

if __name__ == "__main__":
    main()
