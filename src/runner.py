"""
Runs one or many cases through one prompt version + one model, via the
model adapter, and appends a full audit record to artifacts/runs.jsonl for
every single call -- this is the file the assignment asks you to submit
(case ID, prompt version, model ID, provider, settings, input, raw output,
tokens, cost, latency, timestamp).

Also writes a cached copy of each raw response under
artifacts/cached_outputs/<prompt_version>__<model_slug>__<case_id>.json so
a rerun of the aggregator never needs to re-call the API.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from src.context_builder import build_model_context
from src.model_adapter import call_model, ModelResponse

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
RUNS_LOG = ARTIFACTS_DIR / "runs.jsonl"
CACHE_DIR = ARTIFACTS_DIR / "cached_outputs"


def _slug(model_id: str) -> str:
    return model_id.replace("/", "__").replace(":", "--")


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_prompt(prompt_version: str) -> str:
    path = REPO_ROOT / "prompts" / f"{prompt_version}.txt"
    return path.read_text().strip()


def run_case(
    case: dict,
    prompt_version: str,
    model_id: str,
    caller: Callable[..., ModelResponse] = call_model,
    use_pii_minimised_context: bool = True,
) -> dict:
    """
    Runs a single case and appends the full record to runs.jsonl.
    Returns the record dict (includes both the raw model response and the
    reference answer key, if present, for convenience when grading).
    """
    system_prompt = load_prompt(prompt_version)

    if use_pii_minimised_context:
        built = build_model_context(case)
        model_payload = built["model_payload"]
        field_manifest = built["field_manifest"]
    else:
        # Only used deliberately in the part-3 "full vs minimised" comparison.
        model_payload = {k: v for k, v in case.items() if k != "reference"}
        field_manifest = {}

    user_content = json.dumps(model_payload, indent=2)
    response = caller(model_id=model_id, system_prompt=system_prompt, user_content=user_content)

    record = {
        "case_id": case.get("case_id"),
        "prompt_version": prompt_version,
        "model_id": response.model_id,
        "provider": response.provider,
        "settings": response.settings,
        "context_mode": "minimised" if use_pii_minimised_context else "full",
        "field_manifest": field_manifest,
        "model_input": model_payload,
        "raw_output": response.raw_text,
        "parsed_output": response.parsed_json,
        "json_valid": response.json_valid,
        "prompt_tokens": response.prompt_tokens,
        "completion_tokens": response.completion_tokens,
        "total_tokens": response.total_tokens,
        "estimated_cost_usd": response.estimated_cost_usd,
        "latency_seconds": response.latency_seconds,
        "timestamp": response.timestamp,
        "error": response.error,
        "reference": case.get("reference"),
    }

    ARTIFACTS_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)
    with open(RUNS_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")

    cache_name = f"{prompt_version}__{_slug(model_id)}__{case.get('case_id')}.json"
    with open(CACHE_DIR / cache_name, "w") as f:
        json.dump(record, f, indent=2)

    return record


def run_case_set(
    cases_path: Path,
    prompt_version: str,
    model_id: str,
    caller: Callable[..., ModelResponse] = call_model,
    use_pii_minimised_context: bool = True,
) -> list[dict]:
    cases = load_jsonl(cases_path)
    return [
        run_case(c, prompt_version, model_id, caller=caller, use_pii_minimised_context=use_pii_minimised_context)
        for c in cases
    ]
