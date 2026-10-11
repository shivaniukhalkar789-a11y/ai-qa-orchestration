"""The four-field response contract and its structural checks.

A response that passes these checks is *structurally valid* only. That says
nothing about whether it is factually accurate, grounded in the approved
context or safe. Those judgements need a human reviewer.
"""

import copy
import json

from jsonschema import Draft7Validator

SERVICE_STATUSES = ["operational", "degraded", "outage", "unknown"]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string", "minLength": 1},
        "service_status": {"type": "string", "enum": SERVICE_STATUSES},
        "recovery_time": {"type": ["string", "null"]},
        "next_step": {"type": "string", "minLength": 1},
    },
    "required": ["answer", "service_status", "recovery_time", "next_step"],
    "additionalProperties": False,
}


def openai_json_schema() -> dict:
    """The same contract without keywords strict structured outputs may not
    support (minLength). Local validation still enforces the full schema."""
    schema = copy.deepcopy(RESPONSE_SCHEMA)
    for prop in schema["properties"].values():
        prop.pop("minLength", None)
    return schema


def _reject_duplicate_keys(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen[key] = value
    return seen


def check_response(raw_text) -> tuple:
    """Return (parsed_response_or_None, findings).

    findings is a list of {"kind", "path", "message"} dicts. parsed is only
    returned when there are no findings; invalid output is never coerced.
    """
    if not isinstance(raw_text, str):
        return None, [
            {"kind": "parse_error", "path": "", "message": "raw output is not text"}
        ]
    try:
        parsed = json.loads(raw_text, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        return None, [{"kind": "parse_error", "path": "", "message": str(exc)}]

    findings = []
    validator = Draft7Validator(RESPONSE_SCHEMA)
    for error in sorted(validator.iter_errors(parsed), key=lambda e: str(e.path)):
        findings.append(
            {
                "kind": "schema_error",
                "path": "/".join(str(part) for part in error.path),
                "message": error.message,
            }
        )
    if not findings:
        for key in ("answer", "next_step"):
            if not parsed[key].strip():
                findings.append(
                    {
                        "kind": "schema_error",
                        "path": key,
                        "message": "must not be blank",
                    }
                )
    return (parsed if not findings else None), findings
