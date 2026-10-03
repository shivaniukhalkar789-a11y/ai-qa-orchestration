# Week 1 API Case Matrix

This matrix lists each distinct API scenario covered by the Week 1 and
Day 2 tests. It is the single list to check against when asking "is this
behaviour tested?"

**Scenario** means one distinct request plus one distinct expected result.
Each row below is one scenario.

Not counted as scenarios:

- Repeated teaching demonstrations (for example, the same request shown
  again with a different assertion style).
- Single assertions inside a test.
- Standalone validator examples on hand-written dictionaries
  (`test_example_*` in `tests/day2/test_04_schema.py`).
- Fault-injected reruns (`--day2-fault=...`). These show that tests can
  fail. They do not add coverage.

## Categories

| Category | Meaning |
| --- | --- |
| positive | The request should succeed (200) and return the right data. |
| negative | The request is malformed or unknown and should be rejected (400, 404, 405). |
| ownership | The request asks for another employee's data and should be denied (403). |
| schema | The response body must match a JSON Schema in `schemas/`. |

Schema checks appear as a second assertion inside a positive, ownership,
or negative row. They are listed in the matrix's **Schema** column rather
than as separate scenarios.

## Scenario matrix

Requirement codes: **BR01** identity from header, **BR02** ownership,
**BR03** missing ticket is 404, **BR04** VPN status format. "Contract"
means the schema file or response shape in `schemas/` or `app/main.py`.

| Case ID | Requirement / contract | Scenario | Employee context | Expected result | Category | Schema | Executable test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W1-01 | Health contract | Health check | No header needed | 200, `status` = `ok`, `service` = `northstar-it-service-desk` | positive | — | `tests/test_service_status.py::test_health_check_returns_ok` |
| W1-02 | BR04 | VPN status has a defined status and update time | No header needed | 200, `status` in `operational`/`degraded`/`outage`, `updated_at` present | positive | — | `tests/test_service_status.py::test_vpn_status_has_defined_status_and_update_time` |
| W1-03 | `service_status.schema.json` | VPN status matches its schema | No header needed | 200, body matches schema | schema | yes | `tests/day2/test_04_schema.py::test_service_status_matches_schema` |
| W1-04 | BR01 | EMP001 gets own profile | EMP001 (Dana Whitfield) | 200, `employee_id` = EMP001, `full_name` = Dana Whitfield | positive | — | `tests/test_employees.py::test_get_my_profile_returns_known_employee` |
| W1-05 | `employee.schema.json` | EMP001 profile matches its schema | EMP001 | 200, body matches schema | schema | yes | `tests/day2/test_04_schema.py::test_employee_profile_matches_schema` |
| W1-06 | BR02 | EMP001 views own TCK-1001 | EMP001 | 200, `ticket_id` = TCK-1001, `employee_id` = EMP001 | positive | — | `tests/test_tickets.py::test_get_own_ticket_returns_200` |
| W1-07 | `ticket.schema.json` | TCK-1001 matches its schema | EMP001 | 200, body matches schema | schema | yes | `tests/test_tickets.py::test_ticket_matches_schema` |
| W1-08 | BR02 | EMP002 denied TCK-1001 | EMP002 (Marcus Lee) | 403, `detail` = "You may not view another employee's ticket." | ownership | — | `tests/test_tickets.py::test_get_other_employees_ticket_returns_403` |
| W1-09 | BR03 | Missing ticket TCK-9999 | EMP001 | 404, `detail` = "Ticket not found: TCK-9999" | negative | — | `tests/test_tickets.py::test_missing_ticket_returns_404` |
| W1-10 | BR02 | EMP002 views own TCK-1002 | EMP002 | 200, `ticket_id` = TCK-1002, `employee_id` = EMP002 | positive | — | `tests/day2/test_01_fixtures.py::test_employee_b_can_view_own_ticket` |
| W1-11 | BR02 | EMP001 denied TCK-1002 | EMP001 | 403, exact error body | ownership | — | `tests/day2/test_02_parameterized.py::test_get_ticket[employee_a_denied_employee_b_ticket]` |
| W1-12 | BR01 | EMP002 gets own profile | EMP002 (Marcus Lee) | 200, `full_name` = Marcus Lee | positive | yes | `tests/day2/test_05_week1_coverage.py::test_employee_profile_returns_own_record[emp002_profile]` |
| W1-13 | BR01 | EMP003 gets own profile | EMP003 (Priya Nair) | 200, `full_name` = Priya Nair | positive | yes | `tests/day2/test_05_week1_coverage.py::test_employee_profile_returns_own_record[emp003_profile]` |
| W1-14 | BR01 | EMP004 gets own profile | EMP004 (Oliver Grant) | 200, `full_name` = Oliver Grant | positive | yes | `tests/day2/test_05_week1_coverage.py::test_employee_profile_returns_own_record[emp004_profile]` |
| W1-15 | BR01 | No header on profile | None | 400, `detail` = "Missing required header: X-Demo-Employee-ID" | negative | yes | `tests/day2/test_05_week1_coverage.py::test_error_response[no_header_on_profile]` |
| W1-16 | BR01 | Unknown employee on profile | EMP999 (not in data) | 400, `detail` = "Unknown demo employee id: EMP999" | negative | yes | `tests/day2/test_05_week1_coverage.py::test_error_response[unknown_employee_on_profile]` |
| W1-17 | BR01 | Lowercase ID is unknown | emp001 (exact match required) | 400, `detail` = "Unknown demo employee id: emp001" | negative | yes | `tests/day2/test_05_week1_coverage.py::test_error_response[lowercase_id_is_unknown]` |
| W1-18 | BR02 | EMP003 views own TCK-1003 (in progress) | EMP003 | 200, `status` = `in_progress`, owner EMP003 | positive | yes | `tests/day2/test_05_week1_coverage.py::test_employee_views_own_ticket[emp003_own_tck1003]` |
| W1-19 | BR02 | EMP004 views own TCK-1004 (open) | EMP004 | 200, `status` = `open`, owner EMP004 | positive | yes | `tests/day2/test_05_week1_coverage.py::test_employee_views_own_ticket[emp004_own_tck1004]` |
| W1-20 | BR02 | EMP001's second ticket TCK-1005 | EMP001 | 200, `status` = `in_progress`, owner EMP001 | positive | yes | `tests/day2/test_05_week1_coverage.py::test_employee_views_own_ticket[emp001_second_ticket_tck1005]` |
| W1-21 | BR02 | EMP002's second ticket TCK-1006 (resolved) | EMP002 | 200, `status` = `resolved`, owner EMP002 | positive | yes | `tests/day2/test_05_week1_coverage.py::test_employee_views_own_ticket[emp002_second_ticket_tck1006]` |
| W1-22 | BR02 | EMP004 denied EMP003's TCK-1003 | EMP004 (Oliver Grant) | 403, exact error body | ownership | yes | `tests/day2/test_05_week1_coverage.py::test_employee_denied_another_employees_ticket[emp004_denied_emp003_tck1003]` |
| W1-23 | BR02 | EMP003 denied EMP001's TCK-1005 | EMP003 (Priya Nair) | 403, exact error body | ownership | yes | `tests/day2/test_05_week1_coverage.py::test_employee_denied_another_employees_ticket[emp003_denied_emp001_tck1005]` |
| W1-24 | BR01 | No header on ticket | None | 400, `detail` = "Missing required header: X-Demo-Employee-ID" | negative | yes | `tests/day2/test_05_week1_coverage.py::test_error_response[no_header_on_ticket]` |
| W1-25 | BR01 before BR03 | Unknown employee asks for a missing ticket | EMP999 with TCK-9999 | 400 (not 404), `detail` = "Unknown demo employee id: EMP999" | negative | yes | `tests/day2/test_05_week1_coverage.py::test_error_response[identity_checked_before_missing_ticket]` |
| W1-26 | Supported methods | POST to a ticket is not allowed | EMP001 | 405, `detail` = "Method Not Allowed" | negative | yes | `tests/day2/test_05_week1_coverage.py::test_error_response[post_to_ticket_not_allowed]` |

Notes on the Schema column:

- "yes" means the test also checks the body against a schema. For 200
  responses this is `employee.schema.json` or `ticket.schema.json`. For
  400, 403, 404, and 405 responses it is `error.schema.json`.
- A "yes" in this column does not create a new scenario. A schema check
  added to an existing request does not count as a new row.

## Totals

| Measure | Count |
| --- | --- |
| Rows in this matrix (unique API scenarios) | **26** |
| Scenarios from Day 1 and Topics 1-4 (W1-01 to W1-11) | 11 |
| New scenarios in Topic 5 (W1-12 to W1-26) | 15 |
| Full pytest count (`python -m pytest -q`) | 38 |
| Pytest items that are not API scenarios (Topic 4 schema examples) | 3 |
| Pytest items that are API scenarios (38 - 3) | 35 |

The difference between the 35 API pytest items and the 26 unique
scenarios comes from the same request appearing in more than one test
file, from schema checks added to existing requests, and from the
parametrised tests that run once per row.

Target check: the requirement was at least 20 distinct API scenarios.
**26 meets it.**

## Unsupported coverage

These behaviours are **not** tested. Each one is listed here because the
project does not provide it, or because testing it would need an endpoint
or a data change that this project does not allow.

| Area | Why it is not covered |
| --- | --- |
| Real authentication (passwords, tokens, 401 responses) | Not implemented. Identity comes only from the demo header (BR01). Testing a 401 would mean inventing behaviour the app does not have. |
| Creating, editing, or closing tickets | No such endpoints exist. Only `GET /tickets/{id}` is available. |
| Listing all tickets or all employees | No list endpoints exist. |
| VPN status `degraded` and `outage` values | `data/service_status.json` only holds `operational`. Changing it would mean editing persistent data, which is not allowed. The schema and the test only check that the value is one of the three allowed values. |
| Real 500 server-error handling | No code path in the app produces one without fault injection, and injected faults are not counted as scenarios. |
| Date-time and email format checks | The schemas label these formats, but `jsonschema` does not enforce them unless a `FormatChecker` is added. The project does not add one. |
| Every ownership pair | There are 4 employees, so 12 possible ordered pairs. This matrix covers 4 of them, chosen to span different employees and tickets: EMP001↔EMP002 (Day 1, Topic 2), EMP004→EMP003 and EMP003→EMP001 (W1-22, W1-23). |
| Public VPN status ignoring the identity header | It has no identity check, so this is a property of the design rather than a rule. It is not counted as a scenario. |
| Non-GET methods on health, profile, and VPN status | Only one method check exists (W1-26, POST on a ticket). Other routes were not checked for method rejection. |
| Concurrency, performance, rate limits, pagination | None of these exist in the app. |

## How to run

Run all Week 1 and Day 2 tests:

```bash
python -m pytest -q
```

Expected: `38 passed`.

Run only the Topic 5 scenarios:

```bash
python -m pytest -v tests/day2/test_05_week1_coverage.py
```

Expected: `15 passed`.

Run only the Day 1 files (the Day 1 command from `docs/day2-instructor-map.md`):

```bash
python -m pytest -q tests/test_employees.py tests/test_service_status.py tests/test_tickets.py
```

Expected: `7 passed`.

## Verification results (2026-10-03)

| Run | Result |
| --- | --- |
| `tests/day2/test_05_week1_coverage.py` | 15 passed |
| Day 1 files | 7 passed (unchanged) |
| Full suite (baseline) | 38 passed |
| `--day2-fault=ownership` on Topic 5 | 2 failed, 13 passed. The two failures are the ownership denials (W1-22, W1-23). |
| `--day2-fault=missing-status` on Topic 5 | 15 passed. Expected: Topic 5 never calls the VPN status endpoint. |
| `--day2-fault=wrong-status-type` on Topic 5 | 15 passed. Expected, for the same reason. |
| Full suite again after the fault runs | 38 passed |

The two status faults only affect the VPN status endpoint, and Topic 5
does not test that endpoint. Their failures are caught by the Topic 4
schema tests, which are already in the baseline.
