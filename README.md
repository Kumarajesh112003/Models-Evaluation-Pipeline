# Model Evaluation Pipeline

A model-agnostic evaluation framework for LLMs that read multi-party
fulfilment timelines (client, vendor, PA, desk, and system messages) and
produce structured JSON describing state, blockers, next action, and
escalation. It exists to answer one question before any prompt or model
change ships: **is this actually safe and worthwhile?**

The pipeline runs cases through a model, validates the output against a
strict schema, grades it with a mix of deterministic checks and a narrow
LLM judge, and rolls everything up into aggregate metrics you can compare
across prompt versions and models.

## Highlights

- **Model-agnostic** — swap the underlying model by changing a single CLI
  flag; no code changes required.
- **Deterministic + LLM-judge grading** — schema validation and rule-based
  checks catch hard failures; a narrow LLM judge is reserved for the one
  thing that genuinely needs semantic judgment (faithfulness of a
  generated client update).
- **PII-aware context building** — a field-level policy (keep / generalise
  / tokenise / exclude) controls exactly what reaches the model, backed by
  tests that assert excluded fields never leak into a payload.
- **Locked tuning/holdout split** — prevents quietly overfitting a prompt
  to the same cases used to validate it.
- **Full audit trail** — every run is appended to a log, so nothing is
  silently overwritten and results stay reproducible.

## Repository layout

```
prompts/          prompt_v0.txt (baseline), prompt_v1.txt, prompt_v2.txt, prompt_notes.md
cases/            case data, split_cases.py -> tuning_cases.jsonl / holdout_cases.jsonl (locked)
src/
  model_adapter.py    thin model-provider wrapper, explicit model id, no auto-routing
  context_builder.py  build_model_context(): PII field policy (keep/generalise/tokenise/exclude)
  schema.py           frozen output contract
  graders/
    schema_grader.py        deterministic: valid JSON + required fields
    deterministic_grader.py deterministic: state match, must_not_do, blocker recall, false-completion
    llm_judge.py             narrow LLM grader, client_update faithfulness only
  runner.py            runs one case through one prompt + model, logs artifacts/runs.jsonl
  aggregator.py        grades all logged runs, computes aggregate metrics
  cli.py                entrypoint: split / run / grade
tests/            pytest, including PII no-leak assertions
artifacts/
  runs.jsonl          full audit log of every run
  cached_outputs/      one JSON file per run
  summary.json         produced by `grade`
REPORT.md         evidence document: prompt-improvement proof, PII deltas, model qualification
LOCAL_MODEL_PLAN.md  plan for an optional local-model variant
```

## Getting started

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your API key
```

Try the pipeline without hitting a real model first:

```bash
python -m src.cli split
python -m src.cli run --cases tuning --prompt prompt_v0 --model <your-model-id> --dry-run
python -m src.cli grade
```

## Usage

```bash
# 1) materialise the locked tuning/holdout split (deterministic, safe to re-run)
python -m src.cli split

# 2) baseline: prompt_v0 on the primary model, both sets
python -m src.cli run --cases tuning  --prompt prompt_v0 --model <model-id>
python -m src.cli run --cases holdout --prompt prompt_v0 --model <model-id>

# 3) prompt iteration (see prompt_notes.md for the hypothesis behind each edit)
python -m src.cli run --cases tuning --prompt prompt_v1 --model <model-id>
python -m src.cli run --cases tuning --prompt prompt_v2 --model <model-id>
python -m src.cli run --cases holdout --prompt prompt_v2 --model <model-id>   # final check only, once

# 4) PII: full vs minimised context comparison
python -m src.cli run --cases pii --prompt prompt_v2 --model <model-id> --context minimised
python -m src.cli run --cases pii --prompt prompt_v2 --model <model-id> --context full

# 5) model qualification: freeze prompt_v2, run the same holdout set on a second model
python -m src.cli run --cases holdout --prompt prompt_v2 --model <second-model-id>

# 6) grade everything logged so far and print aggregate metrics
python -m src.cli grade
```

Every `run` call appends to `artifacts/runs.jsonl` and never deletes prior
runs. Clear it deliberately before a run whose numbers matter, otherwise
old and new results get averaged together:

```bash
> artifacts/runs.jsonl
rm -f artifacts/cached_outputs/*.json
```

## Metrics glossary

| Metric | Meaning |
|---|---|
| `schema_validity_rate` | Fraction of outputs that were valid JSON with every required field. Should approach 1.0. |
| `state_accuracy` | Fraction of cases where the model's stated state matched the reference answer exactly. |
| `critical_failure_rate` | **Most important.** Fraction of cases where the model did something on the `must_not_do` list, or falsely claimed something was completed. Must be 0 for a prompt/model to be release-worthy. |
| `unsafe_action_rate` / `false_completion_rate` | The two components of critical failures, reported separately for diagnosis. |
| `avg_latency_seconds`, `total_tokens`, `total_cost_usd` | Operational cost of a run. |

Always check `critical_failure_rate == 0` first — a fast, cheap,
schema-valid model that is occasionally unsafe is still not shippable.

## Tests

```bash
pytest -q
```

Includes leak-proofing tests (`tests/test_context_builder.py`) that assert
no field marked `exclude` in `src/context_builder.py` ever appears in the
payload sent to a model.
