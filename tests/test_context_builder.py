"""
The most important tests in this repo: prove that excluded PII values
never reach the model_payload we'd send to OpenRouter.
"""
import json
from pathlib import Path

import pytest

from src.context_builder import build_model_context, assert_no_leak

REPO_ROOT = Path(__file__).resolve().parent.parent
PII_CASES = REPO_ROOT / "cases" / "pii_cases.jsonl"


def load_pii_cases():
    with open(PII_CASES) as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.mark.parametrize("case", load_pii_cases(), ids=lambda c: c["case_id"])
def test_no_excluded_field_leaks(case):
    built = build_model_context(case)
    leaked = assert_no_leak(built["model_payload"], case)
    assert leaked == [], f"{case['case_id']}: excluded fields leaked into model_payload: {leaked}"


@pytest.mark.parametrize("case", load_pii_cases(), ids=lambda c: c["case_id"])
def test_every_available_context_field_has_a_manifest_entry(case):
    built = build_model_context(case)
    for field_name in case.get("available_context", {}):
        assert field_name in built["field_manifest"], f"{field_name} missing from field_manifest"
        assert built["field_manifest"][field_name]["action"] in {"keep", "generalise", "tokenise", "exclude"}


def test_pii01_medical_report_and_phone_excluded():
    case = next(c for c in load_pii_cases() if c["case_id"] == "S-PII01")
    built = build_model_context(case)
    payload_text = json.dumps(built["model_payload"])
    assert case["available_context"]["medical_report"] not in payload_text
    assert case["available_context"]["patient_phone"] not in payload_text
    assert case["available_context"]["home_address"] not in payload_text
    # but the one authorised clinical fact should be present
    assert "knee" in payload_text.lower()


def test_pii02_payment_secrets_excluded_but_amount_kept():
    case = next(c for c in load_pii_cases() if c["case_id"] == "S-PII02")
    built = build_model_context(case)
    payload_text = json.dumps(built["model_payload"])
    assert case["available_context"]["payment_token"] not in payload_text
    assert case["available_context"]["bank_account"] not in payload_text
    assert case["available_context"]["client_pan"] not in payload_text
    assert "5600" in payload_text  # approved_amount_inr is needed for reasoning


def test_plain_starter_case_has_empty_manifest():
    """Starter cases have no available_context -- manifest should just be empty, not error."""
    starter_case = {
        "case_id": "S-P01",
        "timezone": "Asia/Kolkata",
        "events": [{"id": "e1", "at": "2026-08-15T09:00:00+05:30", "actor": "client", "text": "hi"}],
    }
    built = build_model_context(starter_case)
    assert built["field_manifest"] == {}
    assert built["model_payload"]["case_id"] == "S-P01"
