# HULP AI Evaluation & Model Improvement Loop

A model-agnostic evaluation pipeline: run cached-replay/live model calls
against fulfilment-timeline cases, validate JSON output, grade it, and
produce case-level + aggregate results -- so a prompt or model change can be
proven safe/worthwhile before it ships.

## 1. Setup

```bash
cd hulp-eval
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then paste your real OpenRouter key into .env
```

Get an API key from https://openrouter.ai (use a fresh, assignment-only
account). Add credit (up to the $15 / INR 1500 reimbursement cap) and keep
the receipt + an Activity page screenshot for submission.

**Running with $0 balance:** OpenRouter lets you call models whose id ends
in `:free` with no credit added at all. As of this project's setup, the
free lineup was: `nvidia/nemotron-3.5-lightning:free`,
`poolside/laguna-s-2.1:free`, `liquid/lfm-2.5-2.6b:free`,
`dots-studio/dots-3-note-preview:free` -- check openrouter.ai/models
yourself since this rotates. Free models are capped at ~20 requests/minute
and 50/day (rises to 1,000/day once you've ever added $10+ credit). Any
model WITHOUT `:free` in its id requires a positive balance -- calling one
with $0 balance fails with a payment-required error, it does not silently
downgrade to free.

## 2. Repo layout

```
prompts/            prompt_v0.txt (supplied), prompt_v1.txt, prompt_v2.txt, prompt_notes.md
cases/               starter_all.jsonl (supplied 12), pii_cases.jsonl (supplied 4),
                      additional_tuning_cases.jsonl, additional_holdout_cases.jsonl,
                      split_cases.py -> generates tuning_cases.jsonl / holdout_cases.jsonl (8+8, locked)
src/
  model_adapter.py    thin OpenRouter wrapper -- explicit model_id, no auto-router
  context_builder.py  build_model_context(): PII field policy (keep/generalise/tokenise/exclude)
  schema.py            frozen output contract
  graders/
    schema_grader.py       deterministic: valid JSON + required fields
    deterministic_grader.py deterministic: state match, must_not_do, blocker recall, false-completion
    llm_judge.py            narrow LLM grader, client_update faithfulness ONLY
  runner.py            runs one case through one prompt+model, logs artifacts/runs.jsonl
  aggregator.py         grades all logged runs, computes aggregate metrics
  cli.py                entrypoint: split / run / grade
tests/                pytest -- includes the PII no-leak assertions
artifacts/
  runs.jsonl            full audit log of every run (submission requirement)
  cached_outputs/        one JSON file per run
  summary.json           produced by `grade`
REPORT.md              fill in after running (v0->v2 evidence, PII deltas, model qualification)
LOCAL_MODEL_PLAN.md    already drafted
```

## 3. Commands

```bash
# 1) materialise the locked tuning/holdout split (already run once; safe to re-run, deterministic)
python -m src.cli split

# 2) baseline: prompt_v0 on the primary model, both sets
python -m src.cli run --cases tuning  --prompt prompt_v0 --model nvidia/nemotron-3.5-lightning:free
python -m src.cli run --cases holdout --prompt prompt_v0 --model nvidia/nemotron-3.5-lightning:free

# 3) after editing prompts/prompt_v1.txt, prompts/prompt_v2.txt (see prompt_notes.md for the hypothesis behind each edit)
python -m src.cli run --cases tuning --prompt prompt_v1 --model nvidia/nemotron-3.5-lightning:free
python -m src.cli run --cases tuning --prompt prompt_v2 --model nvidia/nemotron-3.5-lightning:free
python -m src.cli run --cases holdout --prompt prompt_v2 --model nvidia/nemotron-3.5-lightning:free   # final check only, once

# 4) PII: full vs minimised context comparison (part 3)
python -m src.cli run --cases pii --prompt prompt_v2 --model nvidia/nemotron-3.5-lightning:free --context minimised
python -m src.cli run --cases pii --prompt prompt_v2 --model nvidia/nemotron-3.5-lightning:free --context full

# 5) model qualification: freeze prompt_v2, run the SAME holdout set on a second model family
python -m src.cli run --cases holdout --prompt prompt_v2 --model poolside/laguna-s-2.1:free

# 6) grade everything logged so far and print aggregate metrics
python -m src.cli grade
```

Every `run` call appends to `artifacts/runs.jsonl` -- never deletes prior
runs, so your full history stays intact for the submission.

Try the whole pipeline without spending any API credit first:

```bash
python -m src.cli run --cases tuning --prompt prompt_v0 --model nvidia/nemotron-3.5-lightning:free --dry-run
python -m src.cli grade
```

## 4. Tests

```bash
pytest -q
```

Includes the leak-proofing tests (`tests/test_context_builder.py`) that
assert no field marked `exclude` in `src/context_builder.py` ever appears in
the payload sent to a model.

## 5. Submission checklist

- [ ] This repo (prompts, cases, src, tests, artifacts/runs.jsonl, cached_outputs)
- [ ] `REPORT.md` filled in with real numbers, not TODOs
- [ ] `LOCAL_MODEL_PLAN.md` (already drafted, revise if your approach changes)
- [ ] OpenRouter credit-purchase receipt
- [ ] OpenRouter Activity page screenshot/export
- [ ] 6-minute walkthrough video
- [ ] `.env` NOT committed (check `.gitignore`)
