"""
Extra pytest fixtures for the Day 2 tests.

The `client` fixture is NOT defined here. It lives in tests/conftest.py,
and pytest shares it with every test below tests/, including this folder.
This file only adds what Day 2 needs on top of it: two known employees,
the demo identity header for each of them, a reusable JSON Schema check,
and the TEST-ONLY --day2-fault option.

The employee and ticket IDs below are copied from data/employees.json and
data/tickets.json. They are written out by hand on purpose, so a test's
expected answer never comes from the API response it is checking.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from app import data, rules

# Reuse the header name the app itself uses, instead of retyping it.
from app.main import DEMO_HEADER_NAME

# The project's contract files live in schemas/ at the project root.
SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"

DAY2_FAULTS = ["ownership", "missing-status", "wrong-status-type"]


def pytest_addoption(parser):
    """Register the TEST-ONLY --day2-fault option.

    This option exists only inside pytest. The application itself has no
    such setting, so a normal `uvicorn app.main:app` run can never have
    the fault switched on.
    """
    parser.addoption(
        "--day2-fault",
        action="store",
        default=None,
        choices=DAY2_FAULTS,
        help="TEST-ONLY: inject a fault into Day 2 test runs. "
        "ownership = skip the ticket ownership check; "
        "missing-status = drop 'status' from the VPN status response; "
        "wrong-status-type = make the VPN 'status' a number.",
    )


def pytest_report_header(config):
    """Print a warning line at the top of the run when a fault is active."""
    fault = config.getoption("--day2-fault")
    if fault:
        return f"day2-fault: {fault} (TEST-ONLY fault injection is ACTIVE)"
    return None


@pytest.fixture(autouse=True)
def day2_fault(request, monkeypatch):
    """Apply the fault chosen with --day2-fault, for Day 2 tests only.

    autouse=True means every test in tests/day2/ gets this fixture without
    asking for it. With no --day2-fault option, it does nothing.

    Each fault swaps one app function for a broken version. The swap only
    lives in memory, for one test at a time: monkeypatch puts the real
    function back automatically when the test finishes. No files under
    app/ or data/ are changed.

    - ownership: rules.employee_owns_ticket always says "yes, this
      employee owns the ticket".
    - missing-status / wrong-status-type: data.load_service_status still
      reads data/service_status.json, then breaks the "status" field in
      its in-memory copy. The real endpoint and FastAPI then build the
      HTTP response from that broken data, exactly as they would from a
      broken data file.
    """
    fault = request.config.getoption("--day2-fault")

    if fault == "ownership":
        monkeypatch.setattr(
            rules, "employee_owns_ticket", lambda ticket, employee_id: True
        )

    elif fault in ("missing-status", "wrong-status-type"):
        real_load_service_status = data.load_service_status

        def broken_load_service_status() -> dict:
            service_status = dict(real_load_service_status())
            if fault == "missing-status":
                del service_status["status"]
            else:
                service_status["status"] = 123  # a number, not a string
            return service_status

        monkeypatch.setattr(data, "load_service_status", broken_load_service_status)


def load_schema(schema_file: str) -> dict:
    """Read one schema from schemas/ and make sure the schema itself is valid."""
    with open(SCHEMAS_DIR / schema_file, "r", encoding="utf-8") as file:
        schema = json.load(file)
    Draft7Validator.check_schema(schema)
    return schema


@pytest.fixture()
def assert_matches_schema():
    """A reusable check: does this JSON data match a schema in schemas/?

    The fixture gives the test a function. Call it like this:

        assert_matches_schema(response.json(), "ticket.schema.json")

    It collects EVERY problem jsonschema finds (not just the first) and
    fails the test with one readable line per problem, for example:

        status: 123 is not of type 'string'
    """

    def check(instance, schema_file: str) -> None:
        validator = Draft7Validator(load_schema(schema_file))
        problems = [
            f"{'/'.join(str(part) for part in error.path) or '(top level)'}: {error.message}"
            for error in sorted(validator.iter_errors(instance), key=str)
        ]
        assert not problems, f"{schema_file} does not match:\n" + "\n".join(problems)

    return check


@pytest.fixture()
def employee_a() -> dict:
    """Employee A: Dana Whitfield (EMP001), who owns ticket TCK-1001."""
    return {"employee_id": "EMP001", "own_ticket_id": "TCK-1001"}


@pytest.fixture()
def employee_b() -> dict:
    """Employee B: Marcus Lee (EMP002), who owns ticket TCK-1002."""
    return {"employee_id": "EMP002", "own_ticket_id": "TCK-1002"}


@pytest.fixture()
def employee_a_headers(employee_a) -> dict:
    """Request headers that identify the caller as Employee A.

    This fixture asks for another fixture (employee_a) by naming it as a
    parameter. pytest builds employee_a first and passes it in.
    """
    return {DEMO_HEADER_NAME: employee_a["employee_id"]}


@pytest.fixture()
def employee_b_headers(employee_b) -> dict:
    """Request headers that identify the caller as Employee B."""
    return {DEMO_HEADER_NAME: employee_b["employee_id"]}
