"""
Day 2 - Topic 2: parameterised tests.

One test function runs once for every row in the CASES table below.

How to read @pytest.mark.parametrize:

    @pytest.mark.parametrize("caller_id, ticket_id, ...", CASES)

- The first argument is a string of names, separated by commas. Each name
  becomes a parameter of the test function.
- The second argument is the list of rows. Each row gives one value per
  name, in the same order.
- pytest.param(..., id="...") wraps one row and gives it a readable name.
  That name appears in the test report, for example:
      test_get_ticket[employee_a_denied_employee_b_ticket]
- The test function can also ask for fixtures (here: client) as usual.
  pytest fills those in alongside the row values.

All IDs and messages below come from data/employees.json,
data/tickets.json, and app/main.py. Expected values are written out by
hand, never taken from the response under test.

Who owns what (data/tickets.json):
    Employee A = EMP001 (Dana Whitfield), owns TCK-1001
    Employee B = EMP002 (Marcus Lee),     owns TCK-1002
    TCK-9999 is well-formed (matches ^TCK-[0-9]+$) but does not exist.
"""

import pytest

from app.main import DEMO_HEADER_NAME

FORBIDDEN_DETAIL = "You may not view another employee's ticket."

CASES = [
    # caller_id, ticket_id, expected_status, expected_owner, expected_detail
    #
    # Overlap: also covered by test_01_fixtures.py and Day 1
    # test_get_own_ticket_returns_200.
    pytest.param(
        "EMP001", "TCK-1001", 200, "EMP001", None,
        id="employee_a_views_own_ticket",
    ),
    # Overlap: also covered by test_01_fixtures.py.
    pytest.param(
        "EMP002", "TCK-1002", 200, "EMP002", None,
        id="employee_b_views_own_ticket",
    ),
    # New case: not covered by any earlier test.
    pytest.param(
        "EMP001", "TCK-1002", 403, None, FORBIDDEN_DETAIL,
        id="employee_a_denied_employee_b_ticket",
    ),
    # Overlap: same request as Day 1 test_get_other_employees_ticket_returns_403
    # (this version also checks the response body).
    pytest.param(
        "EMP002", "TCK-1001", 403, None, FORBIDDEN_DETAIL,
        id="employee_b_denied_employee_a_ticket",
    ),
    # Overlap: same request as Day 1 test_missing_ticket_returns_404
    # (this version also checks the response body).
    pytest.param(
        "EMP001", "TCK-9999", 404, None, "Ticket not found: TCK-9999",
        id="valid_employee_missing_ticket",
    ),
]


@pytest.mark.parametrize(
    "caller_id, ticket_id, expected_status, expected_owner, expected_detail",
    CASES,
)
def test_get_ticket(
    client, caller_id, ticket_id, expected_status, expected_owner, expected_detail
):
    # Arrange: identify the caller with the demo header.
    headers = {DEMO_HEADER_NAME: caller_id}

    # Act: ask for the ticket.
    response = client.get(f"/tickets/{ticket_id}", headers=headers)

    # Assert: the exact status code for this case, nothing else accepted.
    assert response.status_code == expected_status
    body = response.json()

    if expected_status == 200:
        # Allowed: the right ticket came back, owned by the expected employee.
        assert body["ticket_id"] == ticket_id
        assert body["employee_id"] == expected_owner
    else:
        # Denied or missing: the body must be exactly the error message.
        # Comparing the whole body proves no ticket fields (subject,
        # description, owner, status, ...) leaked into the response.
        assert body == {"detail": expected_detail}
