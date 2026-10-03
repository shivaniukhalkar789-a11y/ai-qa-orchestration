"""
Day 2 - Topic 5: Week 1 API coverage.

This file fills the gaps left by Day 1 and Topics 1-4. It covers the rest
of the employees and tickets in data/, the identity errors (BR01), the
ordering of checks, and one wrong HTTP method.

Each row in the tables below is one distinct API scenario. The full
matrix, with the requirement behind each row, is in
docs/week01-api-case-matrix.md.

Notes for beginners:

- Each test runs once per row, because of @pytest.mark.parametrize
  (explained in tests/day2/test_02_parameterized.py).
- Expected values are written out by hand from data/employees.json and
  data/tickets.json. They are never read from the response being checked.
- Every test checks the status code first, then the schema for that
  status, then the specific values.
"""

import pytest

from app.main import DEMO_HEADER_NAME

FORBIDDEN_DETAIL = "You may not view another employee's ticket."

# ---------------------------------------------------------------------------
# Positive: each employee sees their own profile (BR01).
# ---------------------------------------------------------------------------

PROFILE_CASES = [
    pytest.param("EMP002", "Marcus Lee", id="emp002_profile"),
    pytest.param("EMP003", "Priya Nair", id="emp003_profile"),
    pytest.param("EMP004", "Oliver Grant", id="emp004_profile"),
]


@pytest.mark.parametrize("employee_id, full_name", PROFILE_CASES)
def test_employee_profile_returns_own_record(client, assert_matches_schema, employee_id, full_name):
    # Arrange: identify the caller with the demo header.
    headers = {DEMO_HEADER_NAME: employee_id}

    # Act
    response = client.get("/employees/me", headers=headers)

    # Assert: status, then schema, then the values.
    assert response.status_code == 200
    body = response.json()
    assert_matches_schema(body, "employee.schema.json")
    assert body["employee_id"] == employee_id
    assert body["full_name"] == full_name


# ---------------------------------------------------------------------------
# Positive: each employee views their own tickets (BR02).
# ---------------------------------------------------------------------------

OWN_TICKET_CASES = [
    pytest.param("EMP003", "TCK-1003", "in_progress", id="emp003_own_tck1003"),
    pytest.param("EMP004", "TCK-1004", "open", id="emp004_own_tck1004"),
    # EMP001 owns two tickets. TCK-1005 is the second one.
    pytest.param("EMP001", "TCK-1005", "in_progress", id="emp001_second_ticket_tck1005"),
    pytest.param("EMP002", "TCK-1006", "resolved", id="emp002_second_ticket_tck1006"),
]


@pytest.mark.parametrize("caller_id, ticket_id, expected_status_value", OWN_TICKET_CASES)
def test_employee_views_own_ticket(client, assert_matches_schema, caller_id, ticket_id, expected_status_value):
    # Arrange: identify the caller with the demo header.
    headers = {DEMO_HEADER_NAME: caller_id}

    # Act
    response = client.get(f"/tickets/{ticket_id}", headers=headers)

    # Assert: status, then schema, then the values.
    assert response.status_code == 200
    body = response.json()
    assert_matches_schema(body, "ticket.schema.json")
    assert body["ticket_id"] == ticket_id
    assert body["employee_id"] == caller_id
    assert body["status"] == expected_status_value


# ---------------------------------------------------------------------------
# Ownership: an employee is denied a ticket that belongs to someone else (BR02).
# ---------------------------------------------------------------------------

CROSS_EMPLOYEE_CASES = [
    pytest.param("EMP004", "TCK-1003", id="emp004_denied_emp003_tck1003"),
    pytest.param("EMP003", "TCK-1005", id="emp003_denied_emp001_tck1005"),
]


@pytest.mark.parametrize("caller_id, ticket_id", CROSS_EMPLOYEE_CASES)
def test_employee_denied_another_employees_ticket(client, assert_matches_schema, caller_id, ticket_id):
    # Arrange: identify the caller with the demo header.
    headers = {DEMO_HEADER_NAME: caller_id}

    # Act
    response = client.get(f"/tickets/{ticket_id}", headers=headers)

    # Assert: status, then the error schema, then the exact message.
    assert response.status_code == 403
    body = response.json()
    assert_matches_schema(body, "error.schema.json")
    assert body == {"detail": FORBIDDEN_DETAIL}


# ---------------------------------------------------------------------------
# Negative: identity errors, ordering of checks, and an unsupported method.
#
# Each row: (method, path, header value or None for no header,
#            expected status, expected detail)
# ---------------------------------------------------------------------------

ERROR_CASES = [
    pytest.param(
        "GET", "/employees/me", None, 400,
        "Missing required header: X-Demo-Employee-ID",
        id="no_header_on_profile",
    ),
    pytest.param(
        "GET", "/employees/me", "EMP999", 400,
        "Unknown demo employee id: EMP999",
        id="unknown_employee_on_profile",
    ),
    # IDs are case-sensitive, so "emp001" does not match "EMP001".
    pytest.param(
        "GET", "/employees/me", "emp001", 400,
        "Unknown demo employee id: emp001",
        id="lowercase_id_is_unknown",
    ),
    pytest.param(
        "GET", "/tickets/TCK-1001", None, 400,
        "Missing required header: X-Demo-Employee-ID",
        id="no_header_on_ticket",
    ),
    # The identity check runs before the ticket lookup. TCK-9999 does not
    # exist, but the answer is 400 (bad identity), not 404 (missing ticket).
    pytest.param(
        "GET", "/tickets/TCK-9999", "EMP999", 400,
        "Unknown demo employee id: EMP999",
        id="identity_checked_before_missing_ticket",
    ),
    # Only GET is supported on /tickets/{id}. Other methods are rejected by
    # FastAPI itself, before any app code runs.
    pytest.param(
        "POST", "/tickets/TCK-1001", "EMP001", 405,
        "Method Not Allowed",
        id="post_to_ticket_not_allowed",
    ),
]


@pytest.mark.parametrize("method, path, caller_id, expected_status, expected_detail", ERROR_CASES)
def test_error_response(client, assert_matches_schema, method, path, caller_id, expected_status, expected_detail):
    # Arrange: send the header only when the row gives a caller ID.
    headers = {} if caller_id is None else {DEMO_HEADER_NAME: caller_id}

    # Act
    response = client.request(method, path, headers=headers)

    # Assert: status, then the error schema, then the exact message.
    assert response.status_code == expected_status
    body = response.json()
    assert_matches_schema(body, "error.schema.json")
    assert body == {"detail": expected_detail}
