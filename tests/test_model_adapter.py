from src.model_adapter import _extract_json

VALID_JSON_TEXT = '{"state": "blocked", "confidence": 0.5}'


def test_plain_json_parses():
    assert _extract_json(VALID_JSON_TEXT) == {"state": "blocked", "confidence": 0.5}


def test_json_in_markdown_fence_parses():
    text = f"Sure, here you go:\n```json\n{VALID_JSON_TEXT}\n```\nLet me know if you need more."
    assert _extract_json(text) == {"state": "blocked", "confidence": 0.5}


def test_json_after_reasoning_prose_parses():
    text = (
        "Here's a thinking process:\n1. Analyze the events...\n2. Extract facts...\n"
        f"Final answer: {VALID_JSON_TEXT}"
    )
    assert _extract_json(text) == {"state": "blocked", "confidence": 0.5}


def test_truncated_response_with_no_json_returns_none():
    # Mirrors the real failure seen: reasoning cut off mid-thought, no JSON ever emitted.
    text = "Here's a thinking process:\n1. Analyze the events...\n2. Extract facts from"
    assert _extract_json(text) is None


def test_empty_text_returns_none():
    assert _extract_json("") is None
