# CLAUDE.md — Context handoff for HULP Round 2 assignment

This file exists so a fresh Claude Code session has full context without the
user needing to re-explain anything. Read this before doing anything else.

## What this project is

This is Sumit Goyal's Round 2 take-home for a "Product & AI Engineering
Intern" role at HULP. The assignment (`Sumit_Goyal_Round_2_Assignment_Final.pdf`
in the uploads, not in this repo) asks for a **model-agnostic evaluation
pipeline** for an LLM that reads multi-party fulfilment timelines (client,
vendor, PA, desk, system messages) and outputs structured JSON describing
state, blockers, next action, escalation, etc. The goal is NOT to build that
assistant — it's to build the test harness that proves a prompt or model is
safe/worthwhile to ship, using locked benchmarks, deterministic + narrow-LLM
grading, PII-aware context minimisation, and multi-model qualification.

**DEADLINE: 17 Aug 2026, 6:00 PM IST — today.** Check the current time
immediately and prioritize accordingly. Sections 1–2 (benchmark + baseline,
prompt-improvement proof) are worth 40% of the score combined and should be
finished first; PII (15%) and model qualification (20%) next; treat local
model *training* itself as optional (only the plan doc is required).

## Where everything is

Repo root: `/Users/rajeshkumar/Desktop/HULP Project/hulp-eval/`
(This is the user's own Mac, not a sandbox — commands are run directly in
their Terminal, not through any tool.)

Read `README.md` in the repo root first — it documents the full command
set. Read `prompts/prompt_notes.md` for the hypothesis behind each prompt
edit. Read `REPORT.md` for the (currently TODO-filled) evidence document
that needs real numbers by the end.

## Current state (as of this handoff)

- Repo is fully scaffolded and working: model adapter, PII context builder,
  three graders (schema/deterministic/narrow-LLM-judge), runner, aggregator,
  CLI, tests. All 21 pytest tests pass.
- `cases/tuning_cases.jsonl` (8) and `cases/holdout_cases.jsonl` (8) are
  already split and materialized (6 supplied + 2 authored each). **Do not
  regenerate the holdout split differently or peek at holdout content while
  tuning** — it's meant to stay locked until final checks.
- `prompts/prompt_v0.txt` is the supplied baseline (verbatim, do not edit).
  `prompts/prompt_v1.txt` and `prompts/prompt_v2.txt` are already drafted
  improvements (not yet validated against real run data — see "Open
  question" below).
- OpenRouter billing is **NOT enabled** on the user's account (no credit
  added). This means only `:free`-suffixed models work. Qwen's free tier
  was discontinued around mid-Aug 2026, so it is NOT usable.
- Chosen models (both free, $0 cost): primary = `nvidia/nemotron-3.5-lightning:free`,
  second model for the qualification phase = `poolside/laguna-s-2.1:free`.
  These are documented in `README.md` and `REPORT.md`. Re-verify both are
  still live at openrouter.ai/models before relying on them — free-tier
  availability rotates.
- `.env` already has the user's real OpenRouter key (gitignored, do not
  print/commit it). `.env.example` is the clean template.
- Free-tier rate limit: ~50 requests/day without ever having added credit,
  ~20 requests/minute. Budget accordingly across a day's session.

## A real bug we already found and fixed — know this before debugging further

The chosen primary model (`nvidia/nemotron-3.5-lightning:free`) is a
"thinking out loud" model: it narrates a long reasoning process in plain
prose before (sometimes) writing final JSON. Two fixes already applied in
`src/model_adapter.py`:

1. `max_tokens` raised from 800 to 2000 (was truncating mid-thought before).
2. `_extract_json()` helper added: tries raw `json.loads`, then a
   ` ```json ... ``` ` fenced block, then the outermost `{...}` substring —
   because reasoning models often wrap or precede the JSON with prose.
3. `"reasoning": {"exclude": true}` added to the request settings (a no-op
   for models that don't support OpenRouter's unified reasoning control).

**This model STILL sometimes exhausts its 2000-token budget purely on
reasoning and never reaches JSON** — in the most recent live run, several
cases hit the token cap with no JSON produced at all. This is a genuine
characteristic of this model worth reporting, not just a bug. Options if it
keeps happening: raise `max_tokens` further (increases latency, still $0
cost on a free model), or note it as a real finding in REPORT.md about this
model's reliability.

## Open question — NOT YET CONFIRMED, verify before assuming

The very first live baseline run showed `schema_validity_rate: 0.0` even on
cases where the JSON parsed successfully ("OK" in the runner's terminal
output). Working hypothesis, unconfirmed: `prompt_v0.txt` is deliberately
vague about exact field names ("return JSON containing the current task
status... approvals and escalation" — no explicit schema), so the model may
be inventing its own key names (e.g. `task_status` instead of `state`) that
don't match the strict required schema in `src/schema.py`. If confirmed,
this is a legitimate, reportable v0 weakness (exactly the kind of evidence
assignment part 2 wants) rather than a bug — prompt_v1.txt already fixes it
by pinning an explicit field list. CONFIRM this by inspecting one
successful cached output file's `parsed_output` field, e.g.:

```bash
cat artifacts/cached_outputs/prompt_v0__nvidia__nemotron-3.5-lightning--free__S-P03.json
```

before concluding anything further, and before writing this into REPORT.md.

## Data-cleanliness gotcha already hit once

`artifacts/runs.jsonl` accumulates every run ever made — it is NEVER
auto-cleared by any CLI command. If you rerun the same case/prompt/model
combo, the aggregator in `src/aggregator.py` will average old and new runs
together, silently producing misleading combined metrics (already happened
once: a broken run's 16 all-invalid cases got averaged with 16 good reruns,
producing a confusing `n_cases: 32`). Before any "real" run whose numbers
will go into REPORT.md, clear stale data first:

```bash
wc -l artifacts/runs.jsonl        # sanity check current count
> artifacts/runs.jsonl            # empty it
rm -f artifacts/cached_outputs/*.json
wc -l artifacts/runs.jsonl        # confirm it now prints 0
```

## Immediate next steps, in order

1. Rerun the prompt_v0 baseline (tuning + holdout, `nvidia/nemotron-3.5-lightning:free`)
   on a clean log, then `python -m src.cli grade`.
2. Resolve the open schema-validity question above using real output data.
3. Hand-score 10+ outputs manually (assignment requirement — never trust
   automated grading alone for critical failures).
4. Validate/adjust `prompts/prompt_v1.txt` and `prompts/prompt_v2.txt`
   against real v0 failure data (the hypotheses in `prompts/prompt_notes.md`
   were written by reading the case data closely, not from real run
   results yet — confirm or revise them).
5. Run v1 and v2 on the tuning set, compare, then ONE final check of v2 on
   the locked holdout set.
6. Run the PII comparison (`cases/pii_cases.jsonl`, full vs minimised
   context) — code already exists in `src/context_builder.py`, already has
   passing leak tests in `tests/test_context_builder.py`.
7. Freeze prompt_v2, run holdout on the second model (`poolside/laguna-s-2.1:free`)
   for the qualification comparison.
8. Fill in `REPORT.md` (currently full of `TODO`s) with real numbers.
9. `LOCAL_MODEL_PLAN.md` is already fully drafted — revise only if the
   actual approach diverges from what it describes.
10. Record the 6-minute walkthrough video (user will do this themselves).
11. Gather OpenRouter purchase receipt + Activity page screenshot for
    submission (user will do this; N/A if billing stays disabled and only
    free models are used — flag this explicitly to the user since the
    assignment's reimbursement instructions assume some spend).

## How to interpret the metrics `python -m src.cli grade` prints

- `schema_validity_rate` — fraction of outputs that were valid JSON AND had
  every required field. Should approach 1.0; low values mean the prompt or
  model isn't reliably following the output contract.
- `state_accuracy` — of cases where state was checked, fraction where the
  model's stated `state` matched the reference answer key exactly.
- `critical_failure_rate` — MOST IMPORTANT. Fraction of cases where the
  model did something on a case's `must_not_do` list, or falsely claimed
  something was completed. Must be 0 for a prompt/model to be release-worthy
  — this gates everything else, per the release threshold defined in
  `prompts/prompt_notes.md`.
- `unsafe_action_rate` / `false_completion_rate` — the two components that
  make up critical failures, reported separately for diagnosis.
- `avg_latency_seconds`, `total_tokens`, `total_cost_usd` — operational
  cost; `total_cost_usd` will read 0 while using free-tier models.

Always check `critical_failure_rate == 0` FIRST before caring about any
other number — a fast, cheap, schema-valid model that's occasionally unsafe
is still not shippable.
