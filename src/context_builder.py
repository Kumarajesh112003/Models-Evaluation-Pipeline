"""
build_model_context(case) -> {model_payload, field_manifest}

Treats context selection as part of model accuracy (assignment part 3).
For every field that might appear in a case's `available_context`, we
decide in ONE place -- this file -- whether the reasoning model needs it:

    keep       -> sent to the model as-is (not sensitive, needed for reasoning)
    generalise -> sent to the model as a non-identifying alias/summary
    tokenise   -> sent to the model as an opaque reference id (not personal data,
                  but not meant to be human-readable either)
    exclude    -> NEVER sent to the model; only trusted execution code may use
                  the real value later (e.g. to actually message a real vendor)

Unknown/unlisted fields default to "exclude" -- the safe default -- so a new
sensitive field added later can't silently leak just because nobody wrote a
rule for it yet.
"""
from __future__ import annotations

import copy
from typing import Any

EXCLUDE = "exclude"
GENERALISE = "generalise"
TOKENISE = "tokenise"
KEEP = "keep"

# field_name -> (action, generalised_value_or_None, purpose, downstream_attachment)
FIELD_POLICY: dict[str, tuple[str, str | None, str, str]] = {
    # --- S-PII01: physio / medical ---
    "family_id": (TOKENISE, None, "links records without revealing identity", "n/a, safe to keep as opaque id"),
    "patient_full_name": (GENERALISE, "the client's family member", "model needs a referent, not the real name", "execution layer resolves to real name when messaging the approved channel"),
    "patient_phone": (EXCLUDE, None, "not needed to reason about status", "execution layer only, via approved channel"),
    "home_address": (EXCLUDE, None, "not needed to reason about status", "execution layer only, if a vendor visit is scheduled"),
    "medical_report": (EXCLUDE, None, "full report was not authorised for disclosure", "never attached unless client gives explicit fresh consent"),
    "task_relevant_condition": (KEEP, None, "the one clinical fact the client explicitly authorised sharing", "n/a"),
    "approved_vendor_channel": (KEEP, None, "needed to check if vendor is using an approved channel", "n/a"),
    "vendor_personal_whatsapp": (EXCLUDE, None, "raw number not needed; only the fact that an unapproved channel was requested matters", "execution layer only, and only if channel is later approved"),

    # --- S-PII02: payment ---
    "client_full_name": (GENERALISE, "the client", "model needs a referent, not the real name", "execution layer resolves for receipts"),
    "client_pan": (EXCLUDE, None, "financial identity document, never needed for state reasoning", "never leaves trusted execution/finance systems"),
    "bank_account": (EXCLUDE, None, "payment secret, never needed for state reasoning", "trusted payment execution code only"),
    "card_last_four": (EXCLUDE, None, "still a payment identifier; reasoning only needs amount + outcome", "trusted payment execution code only"),
    "payment_token": (EXCLUDE, None, "live secret credential, must never reach a model prompt/log/cache", "trusted payment execution code only"),
    "payment_reference": (TOKENISE, None, "opaque id needed to reconcile the specific payment attempt", "execution layer uses it to query the provider"),
    "approved_amount_inr": (KEEP, None, "needed to check the outcome matches the approved amount", "n/a"),
    "provider_status_url": (EXCLUDE, None, "an authenticated action URL, not a reasoning fact", "trusted execution code only, never shown to a model"),

    # --- S-PII03: child pickup ---
    "child_full_name": (GENERALISE, "the child", "model needs a referent, not the real name", "execution layer resolves for the driver/school"),
    "child_date_of_birth": (EXCLUDE, None, "not needed to reason about a pickup-time status", "execution layer only, if age verification is ever required"),
    "school_name": (GENERALISE, "the school", "model needs a referent, not the real name", "execution layer resolves for routing"),
    "school_address": (EXCLUDE, None, "exact location not needed for status reasoning", "execution layer only, for the authorised driver"),
    "parent_phone": (EXCLUDE, None, "not needed to reason about status", "execution layer only, for direct contact"),
    "emergency_contact": (EXCLUDE, None, "not needed to reason about status", "execution layer only, in a genuine emergency"),
    "school_pass_id": (EXCLUDE, None, "credential, not a reasoning fact -- only whether a pass is required matters", "execution layer supplies to the authorised driver only"),
    "driver_vendor_id": (EXCLUDE, None, "operational id, not needed for state reasoning", "execution layer only, to actually dispatch"),

    # --- S-PII04: candidate vetting ---
    "candidate_full_name": (GENERALISE, "the candidate", "case text already refers to 'Candidate R'; no need for real name in reasoning", "execution layer resolves for internal records"),
    "aadhaar_number": (EXCLUDE, None, "government identity document, never needed for state reasoning", "never leaves trusted verification systems"),
    "driving_licence_number": (EXCLUDE, None, "identity document, never needed for state reasoning", "never leaves trusted verification systems"),
    "background_report": (EXCLUDE, None, "raw report is not needed; only the pass/fail status matters", "trusted HR/vetting systems only"),
    "candidate_phone": (EXCLUDE, None, "not needed to reason about verification status", "execution layer only"),
    "licence_verified": (KEEP, None, "verification outcome the client explicitly asked to hear", "n/a"),
    "background_check_status": (KEEP, None, "verification outcome the client explicitly asked to hear", "n/a"),
    "availability": (KEEP, None, "operationally needed to schedule", "n/a"),
    "skill_tags": (KEEP, None, "operationally relevant, not personal data", "n/a"),
}

DEFAULT_POLICY = (EXCLUDE, None, "no explicit policy written for this field yet -- safe default is to exclude it", "add a rule to FIELD_POLICY before using this field")


def build_model_context(case: dict[str, Any]) -> dict[str, Any]:
    """
    case: one parsed line from a *_cases.jsonl file. Works for both plain
    starter cases (no available_context) and PII cases (with it).
    """
    case = copy.deepcopy(case)
    model_payload: dict[str, Any] = {
        "case_id": case.get("case_id"),
        "timezone": case.get("timezone"),
        "events": case.get("events", []),
    }
    field_manifest: dict[str, dict[str, str]] = {}

    available_context = case.get("available_context")
    if not available_context:
        return {"model_payload": model_payload, "field_manifest": field_manifest}

    safe_context: dict[str, Any] = {}
    for field_name, value in available_context.items():
        action, generalised_value, purpose, downstream = FIELD_POLICY.get(field_name, DEFAULT_POLICY)

        field_manifest[field_name] = {
            "action": action,
            "purpose": purpose,
            "downstream_attachment": downstream,
        }

        if action == KEEP:
            safe_context[field_name] = value
        elif action == GENERALISE:
            safe_context[field_name] = generalised_value
        elif action == TOKENISE:
            # Already-opaque ids (e.g. "pay-909", "fam-2207") are safe to keep as-is;
            # they carry no personal meaning by themselves.
            safe_context[field_name] = value
        elif action == EXCLUDE:
            pass  # deliberately omitted from model_payload
        else:  # pragma: no cover - guards against a typo'd action string
            raise ValueError(f"Unknown context action: {action}")

    model_payload["context"] = safe_context
    return {"model_payload": model_payload, "field_manifest": field_manifest}


def assert_no_leak(model_payload: dict[str, Any], case: dict[str, Any]) -> list[str]:
    """
    Test helper: confirms every value policed as EXCLUDE never appears
    anywhere in the serialised model_payload (belt-and-braces string search,
    in addition to the structural fact that we never copied it in).
    Returns a list of leaked field names (empty list = pass).
    """
    import json

    payload_text = json.dumps(model_payload)
    available_context = case.get("available_context", {})
    leaked = []
    for field_name, value in available_context.items():
        action, _, _, _ = FIELD_POLICY.get(field_name, DEFAULT_POLICY)
        if action == EXCLUDE and value is not None and str(value) in payload_text:
            leaked.append(field_name)
    return leaked
