"""Deterministic check #1: is the output valid JSON matching the required contract?"""
from jsonschema import validate, ValidationError

from src.schema import OUTPUT_SCHEMA


def grade_schema(parsed_json: dict | None) -> dict:
    if parsed_json is None:
        return {"schema_valid": False, "schema_errors": ["output was not valid JSON"]}
    try:
        validate(instance=parsed_json, schema=OUTPUT_SCHEMA)
        return {"schema_valid": True, "schema_errors": []}
    except ValidationError as exc:
        return {"schema_valid": False, "schema_errors": [exc.message]}
