"""
Day 2 - Topic 4: JSON Schema validation.

A JSON Schema is a JSON file that describes the SHAPE a piece of JSON must
have. The project's schemas live in schemas/. The words you will see most:

- "type": "object"  -> the data must be a JSON object ({...}), which
                       becomes a dict in Python.
- "type": "string"  -> the value must be text ("..."). A number such as
                       123 is NOT a string, even though it can be printed.
- "properties"      -> describes each field the object may have, and what
                       type (and other rules) each field's value must follow.
- "required"        -> the list of fields that MUST be present. A field in
                       "properties" but not in "required" is optional.

Two more you will see: "additionalProperties": false means no extra
fields are allowed, and "enum" lists the only allowed values.

Every API test below first checks the HTTP status code, then validates
the body against the schema that belongs to that status code. The
checking itself is done by the reusable assert_matches_schema fixture in
tests/day2/conftest.py.

Faults (TEST-ONLY) that this file should catch:

    python -m pytest -v tests/day2/test_04_schema.py --day2-fault=missing-status
    python -m pytest -v tests/day2/test_04_schema.py --day2-fault=wrong-status-type
"""

import pytest


# ---------------------------------------------------------------------------
# API cases: each one calls the real endpoint through the client fixture.
# ---------------------------------------------------------------------------


def test_employee_profile_matches_schema(client, employee_a, employee_a_headers, assert_matches_schema):
    # Arrange: headers from the Topic 1 fixtures.

    # Act
    response = client.get("/employees/me", headers=employee_a_headers)

    # Assert: status first, then the success schema.
    assert response.status_code == 200
    assert_matches_schema(response.json(), "employee.schema.json")
    assert response.json()["employee_id"] == employee_a["employee_id"]


def test_ticket_matches_schema(client, employee_b, employee_b_headers, assert_matches_schema):
    # Arrange: Employee B's own ticket (TCK-1002, status "resolved").
    ticket_id = employee_b["own_ticket_id"]

    # Act
    response = client.get(f"/tickets/{ticket_id}", headers=employee_b_headers)

    # Assert: status first, then the success schema.
    assert response.status_code == 200
    assert_matches_schema(response.json(), "ticket.schema.json")


def test_service_status_matches_schema(client, assert_matches_schema):
    # Arrange: this endpoint needs no identity header.

    # Act
    response = client.get("/services/vpn/status")

    # Assert: status first, then the success schema.
    assert response.status_code == 200
    assert_matches_schema(response.json(), "service_status.schema.json")


def test_forbidden_ticket_error_matches_schema(client, employee_a_headers, employee_b, assert_matches_schema):
    # Arrange: Employee A asks for Employee B's ticket, which must be denied.
    foreign_ticket_id = employee_b["own_ticket_id"]

    # Act
    response = client.get(f"/tickets/{foreign_ticket_id}", headers=employee_a_headers)

    # Assert: status first. A 403 must use the ERROR schema, not the ticket
    # schema. Its "additionalProperties": false also rejects any ticket
    # field that leaks into the error body.
    assert response.status_code == 403
    assert_matches_schema(response.json(), "error.schema.json")


# ---------------------------------------------------------------------------
# Beginner validator examples: NOT API cases.
#
# These check small hand-written dictionaries, not API responses, so they
# do not count toward the API case total. They show what the validator
# says when "required" or "type" is broken.
# ---------------------------------------------------------------------------

VALID_STATUS_EXAMPLE = {
    "service": "vpn",
    "status": "operational",
    "updated_at": "2026-09-25T08:00:00Z",
}


def test_example_valid_dictionary_passes(assert_matches_schema):
    assert_matches_schema(VALID_STATUS_EXAMPLE, "service_status.schema.json")


def test_example_missing_required_field_fails(assert_matches_schema):
    example = {"service": "vpn", "updated_at": "2026-09-25T08:00:00Z"}

    with pytest.raises(AssertionError, match="'status' is a required property"):
        assert_matches_schema(example, "service_status.schema.json")


def test_example_wrong_type_fails(assert_matches_schema):
    example = {**VALID_STATUS_EXAMPLE, "status": 123}

    with pytest.raises(AssertionError, match="123 is not of type 'string'"):
        assert_matches_schema(example, "service_status.schema.json")
