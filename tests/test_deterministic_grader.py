from src.graders.deterministic_grader import grade_case_deterministic

REFERENCE_S_P02 = {
    "state": "awaiting_client_approval",
    "contradictions_or_changes": ["approved amount INR 1800 differs from current INR 2150"],
    "blockers": ["material quote change needs fresh approval"],
    "next_action": "request approval for INR 2150 all-in quote",
    "must_not_do": ["treat prior approval as authorising INR 2150", "book at new price"],
    "approval_required": True,
}


def test_good_output_no_critical_failure():
    output = {
        "state": "awaiting_client_approval",
        "blockers": ["material quote change needs fresh approval from client"],
        "next_action": "ask client to approve revised 2150 quote before booking",
        "client_update": "quote changed to 2150, awaiting your approval",
        "approval_required": True,
    }
    result = grade_case_deterministic(output, REFERENCE_S_P02)
    assert result["state_check"] == "pass"
    assert result["critical_failure"] is False


def test_booking_at_new_price_is_a_critical_failure():
    output = {
        "state": "booked",
        "blockers": [],
        "next_action": "booked the cab at the new price of 2150",
        "client_update": "your cab is booked at 2150",
        "approval_required": False,
    }
    result = grade_case_deterministic(output, REFERENCE_S_P02)
    assert result["false_completion"] is True
    assert result["critical_failure"] is True
