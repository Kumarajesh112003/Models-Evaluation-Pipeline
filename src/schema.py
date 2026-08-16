"""
The required output contract every prompt version must produce.
Used by the schema grader and kept frozen across prompt_v0/v1/v2 and
across models (assignment part 4 requires the "output contract" to be frozen
once you start comparing models).
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "state",
        "verified_facts",
        "commitments",
        "blockers",
        "contradictions_or_changes",
        "next_action",
        "client_update",
        "approval_required",
        "escalation",
        "risk_flags",
        "confidence",
    ],
    "properties": {
        "state": {"type": "string"},
        "verified_facts": {"type": "array", "items": {"type": "string"}},
        "commitments": {"type": "array", "items": {"type": "string"}},
        "blockers": {"type": "array", "items": {"type": "string"}},
        "contradictions_or_changes": {"type": "array", "items": {"type": "string"}},
        "next_action": {"type": "string"},
        "client_update": {"type": "string"},
        "approval_required": {"type": "boolean"},
        "escalation": {"type": "object"},
        "risk_flags": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}
