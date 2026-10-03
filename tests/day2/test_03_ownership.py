"""
Day 2 - Topic 3: ticket ownership (BR02) and fault injection.

Where ownership is enforced:
    app/rules.py  -> employee_owns_ticket() decides who owns a ticket.
    app/main.py   -> get_ticket() calls it and returns 403 when it says no.

These tests check that an employee cannot read another employee's ticket,
in both directions, and that the denial response reveals nothing about
the foreign ticket.

To prove the tests really guard the rule, run them with the TEST-ONLY
fault switched on (see tests/day2/conftest.py). They should FAIL:

    python -m pytest -v tests/day2/test_03_ownership.py --day2-fault=ownership

Overlap: the two requests below are the same as the two 403 cases in
test_02_parameterized.py. This file adds explicit checks that no
protected ticket text appears in the response, so it adds no new
unique case.
"""

FORBIDDEN_DETAIL = "You may not view another employee's ticket."

# Text that belongs to each ticket and must never reach a non-owner.
# Copied by hand from data/tickets.json.
PROTECTED_TICKET_TEXT = {
    "TCK-1001": [
        "TCK-1001",
        "EMP001",
        "VPN client fails to connect from home network",
        "Getting a timeout error when connecting to VPN from home Wi-Fi.",
        "2026-09-20T09:15:00Z",
    ],
    "TCK-1002": [
        "TCK-1002",
        "EMP002",
        "VPN password reset needed",
        "Forgot VPN password after the recent policy change.",
        "2026-09-18T11:00:00Z",
    ],
}


def test_employee_a_cannot_view_employee_b_ticket(client, employee_a_headers, employee_b):
    # Arrange: Employee A will ask for a ticket that belongs to Employee B.
    foreign_ticket_id = employee_b["own_ticket_id"]

    # Act
    response = client.get(f"/tickets/{foreign_ticket_id}", headers=employee_a_headers)

    # Assert: denied with the documented message, and nothing else.
    assert response.status_code == 403
    assert response.json() == {"detail": FORBIDDEN_DETAIL}
    for protected_text in PROTECTED_TICKET_TEXT[foreign_ticket_id]:
        assert protected_text not in response.text


def test_employee_b_cannot_view_employee_a_ticket(client, employee_b_headers, employee_a):
    # Arrange: Employee B will ask for a ticket that belongs to Employee A.
    foreign_ticket_id = employee_a["own_ticket_id"]

    # Act
    response = client.get(f"/tickets/{foreign_ticket_id}", headers=employee_b_headers)

    # Assert: denied with the documented message, and nothing else.
    assert response.status_code == 403
    assert response.json() == {"detail": FORBIDDEN_DETAIL}
    for protected_text in PROTECTED_TICKET_TEXT[foreign_ticket_id]:
        assert protected_text not in response.text
