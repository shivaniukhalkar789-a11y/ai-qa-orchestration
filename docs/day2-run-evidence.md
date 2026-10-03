# Day 2 Run Evidence

Sanitised teaching evidence for the Day 2 submission. It holds summary
results only. It does not include machine names, user names, absolute
paths, environment variables, or raw report files.

Date of the recorded runs: **2026-10-03**.

## 1. Environment (versions only)

| Item | Value |
| --- | --- |
| Operating system used for the runs | Windows 11 |
| Python | 3.12.10 (project allows `>=3.11,<3.13`) |
| Virtual environment | `.venv/` in the project folder |
| pytest | 8.4.2 |
| FastAPI / Starlette | 0.141.1 / 1.7.0 |
| httpx | 0.28.1 |
| jsonschema | 4.26.0 |
| uvicorn | 0.54.0 (used for the optional manual server check only) |
| Report plugins | pytest-html 4.2.0, pytest-json-report 1.5.0 |

The dependency ranges are in `pyproject.toml`:

- Runtime: `fastapi`, `uvicorn[standard]`, `httpx`, `jsonschema`
- `dev` extra: `pytest`, `pytest-html`, `pytest-json-report`

`python -m pip check` reported: **No broken requirements found.**

## 2. Tested code and data

**Code under test** (no changes were made to these files):

| File | Role |
| --- | --- |
| `app/main.py` | The four GET routes and the identity check |
| `app/rules.py` | Ownership rule (`employee_owns_ticket`) and lookups |
| `app/data.py` | Reads the JSON files in `data/` |

**Data** (synthetic, static, and never edited by the tests):

| File | Contents |
| --- | --- |
| `data/employees.json` | 4 employees: EMP001 to EMP004 |
| `data/tickets.json` | 6 tickets: TCK-1001 to TCK-1006. EMP001 and EMP002 own two each. EMP003 and EMP004 own one each. |
| `data/service_status.json` | VPN status `operational`, last updated 2026-09-25 |

**Contracts** (the JSON Schemas in `schemas/`):

| Schema | Checked against |
| --- | --- |
| `ticket.schema.json` | `GET /tickets/{id}` 200 responses |
| `employee.schema.json` | `GET /employees/me` 200 responses |
| `service_status.schema.json` | `GET /services/vpn/status` 200 responses |
| `error.schema.json` | 400, 403, 404, and 405 error bodies |

**Endpoints exercised:**

| Method and path | Identity header needed |
| --- | --- |
| `GET /health` | No |
| `GET /services/vpn/status` | No |
| `GET /employees/me` | Yes |
| `GET /tickets/{ticket_id}` | Yes |
| `POST /tickets/{ticket_id}` | Only to show it is rejected (405) |

**Status codes observed in the tests:** 200, 400, 403, 404, 405.

**Test files** (all under `tests/`):

| File | pytest items | Type |
| --- | --- | --- |
| `test_employees.py`, `test_service_status.py`, `test_tickets.py` (Day 1) | 7 | API tests |
| `day2/test_01_fixtures.py` | 2 | API tests |
| `day2/test_02_parameterized.py` | 5 | API tests |
| `day2/test_03_ownership.py` | 2 | API tests |
| `day2/test_04_schema.py` | 7 | 4 API tests + 3 standalone validator examples |
| `day2/test_05_week1_coverage.py` | 15 | API tests |
| **Total** | **38** | 35 API tests + 3 validator examples |

## 3. Actual results

All runs were made from the project folder, with `.venv` active or its
Python called directly.

| Run | Command (summary) | Result |
| --- | --- | --- |
| Full baseline | `python -m pytest -q` | **38 passed**, exit code 0 |
| Day 1 only | `python -m pytest -q` with the three Day 1 files | **7 passed** |
| Day 2 only | `python -m pytest -q tests/day2` | **31 passed** |
| Fault: ownership | `tests/day2 --day2-fault=ownership` | **7 failed, 24 passed** (expected) |
| Fault: missing-status | `tests/day2 --day2-fault=missing-status` | **1 failed, 30 passed** (expected) |
| Fault: wrong-status-type | `tests/day2 --day2-fault=wrong-status-type` | **1 failed, 30 passed** (expected) |
| Baseline after faults | `python -m pytest -q` | **38 passed** |

**Failures under each fault (names only):**

- `ownership` fails: `test_02_parameterized` (2 denied cases), `test_03_ownership` (2 tests), `test_04_schema` (the 403 schema test), and `test_05_week1_coverage` (2 denied cases).
- `missing-status` and `wrong-status-type` both fail only `test_04_schema::test_service_status_matches_schema`. The status values differ: `'status' is a required property` for the first, and `123 is not of type 'string'` for the second.

**Fault safety checks:**

- The fault header line appears only when a fault is set. The baseline run has no such line.
- The `--day2-fault` option is rejected when the command has no `tests/day2` path, and when the value is not one of the three allowed names.
- No file under `app/`, `data/`, or `schemas/` changed because of a fault run.
- A Day 1 test run in the same session as a faulted run still passed, so the fault does not leak outside `tests/day2/`.

## 4. Unique API coverage

The full list of scenarios, with the requirement behind each row, is in
[`week01-api-case-matrix.md`](week01-api-case-matrix.md).

| Measure | Count |
| --- | --- |
| **Unique API scenarios** | **26** (target: at least 20) |
| Scenarios from Day 1 and Topics 1–4 | 11 |
| New scenarios in Topic 5 | 15 |
| pytest items (full suite) | 38 |
| pytest items that are standalone validator examples (not API scenarios) | 3 |

Unique scenarios by category:

| Category | Count |
| --- | --- |
| positive | 12 |
| negative | 7 |
| ownership | 4 |
| schema-only (200 response checked against its schema) | 3 |

The scenario count and the pytest count are different measures. The
scenario count is the number of distinct request and outcome pairs.

## 5. Limitations

**Not covered by the tests** (the matrix explains each one):

- Real authentication, passwords, tokens, and 401 responses. The app only
  uses the demo header.
- Creating, editing, or closing tickets. No such endpoints exist.
- Listing all tickets or all employees. No such endpoints exist.
- VPN status values `degraded` and `outage`. The data only holds
  `operational`, and changing it would mean editing persistent data.
- Real 500 errors. Only the injected faults can produce a broken response.
- Date-time and email format checks. jsonschema labels these formats but does not enforce them without a `FormatChecker`.
- Most ownership pairs. The 4 employees make 12 ordered pairs, and the tests cover 4 of them.
- Concurrency, performance, rate limits, and pagination. None exist in the app.

**Environment limits:**

- All runs were on Windows 11. The macOS commands in the README are the
  same, but they were **not run on macOS** in this session.
- The runs used synthetic data. Nothing was tested against a real service.

## 6. Reports and sharing

- Report files are written to `reports/`, which Git ignores. Generated
  HTML and JSON reports include the computer's name, folder paths,
  Python and Windows details, and environment variables such as
  `JAVA_HOME`. **Do not share them unedited.**
- Earlier report files exist in `reports/day2/` (generated before this
  packaging step). They were reviewed for passwords, tokens, and API keys:
  **none were found**. They do contain the environment details above, so
  they stay local and are not used as evidence in this document.

## 7. Git hygiene

Checked on 2026-10-03:

| Item | Status |
| --- | --- |
| `.venv/` | Ignored by `.gitignore` |
| `reports/` | Ignored by `.gitignore` |
| `.pytest_cache/`, `__pycache__/`, `*.pyc` | Ignored |
| `.env` | Ignored. The file does not exist in the project. |
| `*.egg-info/` | Ignored |
| Secrets in tracked files | None found. The only matches for "password" are the test data text ("VPN password reset needed"). |
| Faults in `app/` | None. The fault code lives only in `tests/day2/conftest.py`. |

## 8. Unresolved issues

1. **Uncommitted Day 1 change.** `tests/test_tickets.py` has an
   uncommitted line that adds `test_missing_ticket_returns_404`. It must be
   committed deliberately, along with the rest of the Day 2 work.
2. **Empty stray file.** `practice_day1.py` in the project root is untracked
   and empty. It is not part of the tests. Decide whether to delete it or
   commit it.
3. **Earlier report files.** `reports/day2/` holds reports with local
   details. Delete them before sharing the folder, or ask for them to be
   removed.
4. **macOS not verified.** The README commands for macOS have not been run
   on a Mac.
5. **Nothing committed yet.** All Day 2 files are untracked or modified
   and need a deliberate commit.
