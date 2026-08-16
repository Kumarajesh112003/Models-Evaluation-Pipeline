# REPORT.md

Fill in every `TODO` after you've actually run the pipeline. Numbers below
are placeholders showing the shape of the table, not real results -- do not
submit this file with placeholder numbers still in it.

## 0. Summary

- Primary model: `nvidia/nemotron-3.5-lightning:free`
- Second model (qualification): `poolside/laguna-s-2.1:free`
- Note: free-tier models used because billing was not enabled on OpenRouter. Free models are rate-limited (~50 requests/day without added credit) and their availability can change; note this as a caveat when interpreting results and re-verify these model IDs are still live at openrouter.ai/models before your final run.
- Total OpenRouter spend: TODO (attach receipt + Activity screenshot)
- Time actually spent: TODO
- AI tools used while building this: TODO (be specific and honest -- e.g.
  "used Claude to scaffold the repo structure, graders, and prompt drafts;
  I wrote/reviewed the grading rules, ran and read every output myself,
  and made all threshold/release decisions.")

## 1. Benchmark and baseline

- Tuning cases: 8 (`cases/tuning_cases.jsonl`) — 6 from the supplied set, 2 authored (`cases/additional_tuning_cases.jsonl`)
- Holdout cases: 8 (`cases/holdout_cases.jsonl`, LOCKED) — 6 from the supplied set, 2 authored (`cases/additional_holdout_cases.jsonl`)
- Baseline run: prompt_v0 on `nvidia/nemotron-3.5-lightning:free`, both sets, `context=minimised`.
- Raw/cached outputs: `artifacts/cached_outputs/prompt_v0__*`
- Hand-scored outputs: TODO — list which 10+ case/run combos you personally scored and where you disagreed with the automated graders.

| metric | value |
|---|---|
| schema_validity_rate | TODO |
| state_accuracy | TODO |
| critical_failure_rate | TODO |
| unsafe_action_rate | TODO |
| false_completion_rate | TODO |
| avg_latency_seconds | TODO |
| total_tokens | TODO |
| total_cost_usd | TODO |

Grader disagreements found during hand-scoring: TODO.

## 2. Prompt-improvement proof (v0 -> v1 -> v2)

See `prompts/prompt_notes.md` for the failure/hypothesis recorded before
each edit.

| case_id | v0 | v1 | v2 |
|---|---|---|---|
| S-P01 | TODO | TODO | TODO |
| S-P03 | TODO | TODO | TODO |
| ... | | | |

Aggregate movement (tuning set):

| version | schema_validity | state_accuracy | critical_failure_rate |
|---|---|---|---|
| v0 | TODO | TODO | TODO |
| v1 | TODO | TODO | TODO |
| v2 | TODO | TODO | TODO |

New regressions introduced by v1 or v2 (cases that got worse): TODO.

**Release threshold** (from `prompts/prompt_notes.md`): schema_validity >= 0.95,
critical_failure_rate == 0, state_accuracy >= 0.85, holdout-only.

**Does v2 pass it on the LOCKED holdout set?** TODO — yes/no with numbers.

## 3. PII-aware context optimisation

`src/context_builder.py` implements `build_model_context()`. Full field-by-
field keep/generalise/tokenise/exclude decisions are in `FIELD_POLICY`
inside that file, with a `purpose` and `downstream_attachment` note for each.

Leak tests: `tests/test_context_builder.py` — asserts every field marked
`exclude` never appears in the serialised `model_payload` sent to the model,
for all 4 PII cases (`pii_cases.jsonl`).

| case_id | full-context accuracy | minimised accuracy | full tokens | minimised tokens | critical failures (full) | critical failures (minimised) |
|---|---|---|---|---|---|---|
| S-PII01 | TODO | TODO | TODO | TODO | TODO | TODO |
| S-PII02 | TODO | TODO | TODO | TODO | TODO | TODO |
| S-PII03 | TODO | TODO | TODO | TODO | TODO | TODO |
| S-PII04 | TODO | TODO | TODO | TODO | TODO | TODO |

## 4. Model qualification

Frozen prompt: prompt_v2. Frozen output contract: `src/schema.py`.
Holdout set: `cases/holdout_cases.jsonl` (locked, 8 cases), same settings
(temperature=0, same max_tokens/seed) for both models.

| metric | nvidia/nemotron-3.5-lightning:free | poolside/laguna-s-2.1:free |
|---|---|---|
| accuracy (state_accuracy) | TODO | TODO |
| critical_failure_rate | TODO | TODO |
| schema_validity_rate | TODO | TODO |
| avg_latency_seconds | TODO | TODO |
| total_cost_usd | TODO | TODO |

Time/code changes needed to add the second model: TODO (should be ~0 code
changes beyond the `--model` CLI flag, since both go through
`src/model_adapter.py`; note any provider-specific quirk you hit).

**Release recommendation:** TODO.

## 5. Remaining known failures

TODO — list any case, in either set, that still fails under prompt_v2 on
the strongest model, and why it's hard.
