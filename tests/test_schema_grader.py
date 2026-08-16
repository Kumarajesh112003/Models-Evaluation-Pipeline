from src.graders.schema_grader import grade_schema

VALID = {
    "state": "blocked",
    "verified_facts": [],
    "commitments": [],
    "blockers": ["x"],
    "contradictions_or_changes": [],
    "next_action": "do the thing",
    "client_update": "hi",
    "approval_required": True,
    "escalation": {"required": False},
    "risk_flags": [],
    "confidence": 0.8,
}


def test_valid_output_passes():
    result = grade_schema(VALID)
    assert result["schema_valid"] is True
    assert result["schema_errors"] == []


def test_missing_field_fails():
    broken = dict(VALID)
    del broken["next_action"]
    result = grade_schema(broken)
    assert result["schema_valid"] is False
    assert result["schema_errors"]


def test_none_input_fails():
    result = grade_schema(None)
    assert result["schema_valid"] is False
