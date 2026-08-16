"""
Model adapter: a single thin wrapper around OpenRouter's chat-completions API.

This hides provider differences (assignment part 4) behind ONE function.
To evaluate a different model, you only ever change the `model_id` string —
nothing else in the pipeline (runner, graders, aggregator) needs to know
which provider is behind it.

Uses explicit model IDs only (no auto-router), per the assignment's
instructions for reproducible, comparable runs.
"""
from __future__ import annotations

import os
import re
import time
import json
import dataclasses
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


def _extract_json(raw_text: str) -> dict | None:
    """
    Some models (especially 'reasoning'/'thinking' style models like several
    open-weight free-tier ones) ignore response_format=json_object and
    narrate their reasoning in plain prose, sometimes with the final JSON
    wrapped in a markdown code fence, sometimes just appended at the end.
    Try, in order: (1) the raw text as-is, (2) a ```json ... ``` fenced
    block, (3) the outermost {...} substring in the text. Returns None if
    nothing parses -- that's still a real, reportable schema failure.
    """
    if not raw_text:
        return None

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    fence_match = _FENCE_RE.search(raw_text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    first_brace = raw_text.find("{")
    last_brace = raw_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = raw_text[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


@dataclasses.dataclass
class ModelResponse:
    model_id: str
    provider: str
    raw_text: str
    parsed_json: dict | None
    json_valid: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    latency_seconds: float
    settings: dict
    timestamp: str
    error: str | None = None


def _extract_provider(model_id: str) -> str:
    # OpenRouter model ids look like "openai/gpt-4o-mini" or "qwen/qwen-2.5-72b-instruct"
    return model_id.split("/", 1)[0] if "/" in model_id else "unknown"


def call_model(
    model_id: str,
    system_prompt: str,
    user_content: str,
    temperature: float = 0.0,
    max_tokens: int = 2000,
    seed: int | None = 7,
    timeout: int = 120,
) -> ModelResponse:
    """
    Call one model via OpenRouter with a fixed, explicit model_id.

    Keep temperature/max_tokens/seed identical across models/prompt versions
    whenever you need a FAIR comparison (parts 2 and 4 of the assignment).

    max_tokens defaults to 2000 (not a tiny number) because some models
    -- especially free/open-weight "reasoning" models -- spend hundreds of
    tokens narrating their thought process before writing the final JSON
    answer. A too-low cap truncates them mid-thought and they never reach
    the answer at all, which looks like a formatting failure but is really
    a budget failure. `reasoning: {"exclude": true}` additionally asks
    OpenRouter to strip any reasoning trace from the response for models
    that support that unified control; it's a no-op for models that don't.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set. Copy .env.example to .env and add your key."
        )

    settings = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "seed": seed,
        "response_format": {"type": "json_object"},
        "reasoning": {"exclude": True},
    }

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        **settings,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional but recommended by OpenRouter for attribution/rate-limit tiers:
        "HTTP-Referer": "https://hulp-eval.local",
        "X-Title": os.environ.get("OPENROUTER_APP_NAME", "hulp-eval"),
    }

    start = time.time()
    error = None
    raw_text = ""
    usage = {}
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
    except Exception as exc:  # noqa: BLE001 - we want to record ANY failure, not crash the run
        error = str(exc)
    latency = time.time() - start

    parsed = _extract_json(raw_text)
    json_valid = parsed is not None

    return ModelResponse(
        model_id=model_id,
        provider=_extract_provider(model_id),
        raw_text=raw_text,
        parsed_json=parsed,
        json_valid=json_valid,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        estimated_cost_usd=usage.get("cost"),  # OpenRouter can return this if enabled on the key
        latency_seconds=round(latency, 3),
        settings=settings,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        error=error,
    )


class DryRunAdapter:
    """
    A fake adapter used by tests and --dry-run mode so the whole pipeline
    (runner -> graders -> aggregator) can be exercised WITHOUT spending
    API credit or needing a key. It echoes back a minimally valid answer
    shaped like the required schema.
    """

    def __init__(self, canned: dict[str, Any] | None = None):
        self.canned = canned

    def __call__(self, model_id: str, system_prompt: str, user_content: str, **kwargs) -> ModelResponse:
        payload = self.canned or {
            "state": "in_progress",
            "verified_facts": [],
            "commitments": [],
            "blockers": [],
            "contradictions_or_changes": [],
            "next_action": "dry-run placeholder action",
            "client_update": "dry-run placeholder update",
            "approval_required": False,
            "escalation": {"required": False},
            "risk_flags": [],
            "confidence": 0.5,
        }
        text = json.dumps(payload)
        return ModelResponse(
            model_id=model_id,
            provider="dryrun",
            raw_text=text,
            parsed_json=payload,
            json_valid=True,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
            latency_seconds=0.0,
            settings=kwargs,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
