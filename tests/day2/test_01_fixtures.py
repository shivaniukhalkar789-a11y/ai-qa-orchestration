"""
Day 2 - Topic 1: pytest fixtures.

Each test lists the fixtures it needs as function parameters. pytest finds
each fixture by name, builds it, and passes it in before the test runs:

- client              -> tests/conftest.py (Day 1)
- employee_a / _b     -> tests/day2/conftest.py
- employee_a_headers  -> tests/day2/conftest.py
- employee_b_headers  -> tests/day2/conftest.py
"""


def test_employee_a_can_view_own_ticket(client, employee_a, employee_a_headers):
    # Arrange: the ticket to request and its owner, both taken from the
    # prepared test data (never from the response we are about to check).
    ticket_id = employee_a["own_ticket_id"]
    expected_owner = employee_a["employee_id"]

    # Act: Employee A asks for their own ticket.
    response = client.get(f"/tickets/{ticket_id}", headers=employee_a_headers)

    # Assert: the request succeeded and returned the right ticket and owner.
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == ticket_id
    assert body["employee_id"] == expected_owner


def test_employee_b_can_view_own_ticket(client, employee_b, employee_b_headers):
    # Arrange: the ticket to request and its owner, both taken from the
    # prepared test data (never from the response we are about to check).
    ticket_id = employee_b["own_ticket_id"]
    expected_owner = employee_b["employee_id"]

    # Act: Employee B asks for their own ticket.
    response = client.get(f"/tickets/{ticket_id}", headers=employee_b_headers)

    # Assert: the request succeeded and returned the right ticket and owner.
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == ticket_id
    assert body["employee_id"] == expected_owner
