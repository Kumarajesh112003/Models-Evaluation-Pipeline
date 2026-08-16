# LOCAL_MODEL_PLAN.md

Plan for eventually qualifying an open-weight/locally-trained model on this
same benchmark. Running it is a stretch goal; this document is required.

## 1. Data split (train / dev / final-holdout)

Three non-overlapping pools, expanded well beyond the current 20 cases
before any real training is attempted:

- **train**: cases used to build SFT/LoRA examples. Drawn only from the
  `tuning_cases.jsonl` pool (never from `holdout_cases.jsonl`).
- **dev**: a small slice held out from the tuning pool (not used for
  training) to pick hyperparameters/checkpoints during fine-tuning.
- **final-holdout**: `holdout_cases.jsonl`, exactly the same 8 locked cases
  used to qualify prompt_v2 and the two hosted models. A locally trained
  model is graded on this same set with the same graders, so its score is
  directly comparable to the hosted-model qualification matrix in
  REPORT.md section 4.

Rule: the final-holdout set is never touched by training, dev selection, or
prompt engineering for the local model. If it's ever inspected for any
purpose other than final scoring, it must be considered burned and replaced.

## 2. Candidate training data

Only **reviewed non-holdout failures** become training examples -- i.e.
tuning-set cases where prompt_v2 on the best hosted model got something
wrong, that a human (me) has manually reviewed and corrected. Candidates:

- Cases where state/blocker recall was wrong but the correction is
  unambiguous (clear supervision signal for SFT).
- Cases demonstrating the hard rules explicitly (stale approval, evidence
  vs. claim, prompt-injection resistance, PII minimisation, deduplication)
  -- these are the highest-value examples since they encode safety
  behaviour, not just task knowledge.
- For distillation: (input, best hosted-model v2 output) pairs, but ONLY
  after that output has been graded correct by both the deterministic
  graders and a human -- never distill from an ungraded generation.

Explicitly excluded from training data: anything from `holdout_cases.jsonl`,
and any case still in the PII set that contains real-looking sensitive
values -- those are used through `build_model_context()` only, never as raw
fine-tuning text (see leakage controls below).

## 3. Leakage controls

- Enforce the train/dev/final-holdout split at the file level (separate
  jsonl files, holdout file is read-only / checksummed before any training
  run) so it can't be accidentally mixed in.
- Fine-tuning examples are built by running PII cases through
  `build_model_context()` first -- so a locally trained model is trained on
  the same minimised context a hosted model would see, never on raw PII.
- Before training, run the same `tests/test_context_builder.py` leak
  assertions against the assembled training file itself, not just live
  calls -- i.e. grep the final training JSONL for every value marked
  `exclude` in `FIELD_POLICY` and fail the build if any appear.
- Deduplicate: no case (or near-duplicate paraphrase of a case) may appear
  in both train and final-holdout.

## 4. Resource assumptions

- Target: LoRA fine-tuning of a 7-8B open-weight instruct model (e.g.
  Qwen2.5-7B-Instruct or Llama-3.1-8B-Instruct) -- large enough to follow a
  structured-JSON + safety-rule prompt, small enough for single-GPU LoRA
  (~16-24GB VRAM) rather than full fine-tuning.
- Expect low hundreds of examples to be too few for a reliable LoRA;
  realistically need the case pool grown into the hundreds (synthetic
  variations of the same failure patterns, reviewed by a human) before
  fine-tuning is likely to beat a strong hosted model's frozen prompt_v2.
- Given that, the honest near-term plan is: keep prompt_v2 + a hosted model
  as the production path, and treat local fine-tuning as a background
  experiment gated on data volume, not a near-term replacement.

## 5. Acceptance gates vs. best hosted model

A locally trained/fine-tuned model is only qualified for consideration if,
on the identical locked `holdout_cases.jsonl` set with the identical
graders:

- critical_failure_rate == 0 (non-negotiable -- same bar as hosted models)
- schema_validity_rate >= the best hosted model's rate
- state_accuracy within 5 percentage points of the best hosted model's rate
- latency and cost are reported even if not gating, since local-hosting
  cost/latency tradeoffs are the actual reason to consider it

If any gate fails, the local model is not release-qualified regardless of
cost savings -- safety and correctness gates come first, per the same
priority order used in `prompts/prompt_v2.txt`.
