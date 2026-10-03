# Day 2 Instructor Map

A reference for running Day 2 on top of the existing Day 1 project. It
records what the code actually does today, so Day 2 tests can be written
against real IDs, fields, and status codes. Every value below was checked
against `app/`, `data/`, and a live `TestClient` run on 2026-09-27.

## 1. Project context (unchanged from Day 1)

| Item | Value |
| --- | --- |
| Project folder | `ai-qa-orchestration/` |
| Git branch | `main` (tracks `origin/main`) |
| Virtual environment | `.venv/` (Python 3.12.10; project allows `>=3.11,<3.13`) |
| Installed test deps | pytest 8.4.2, fastapi 0.141.1, httpx 0.28.1, jsonschema 4.26.0 |
| Test config | `pyproject.toml` → `pythonpath = ["."]`, `testpaths = ["tests"]` |
| Shared fixture | `client` in `tests/conftest.py` (a FastAPI `TestClient`) |
| Secrets | None needed. `.env.example` only holds `APP_ENV=development` |

## 2. Day 1 test files

These are the Day 1 files. Do not move or rename them.

| File | Tests |
| --- | --- |
| `tests/test_employees.py` | `test_get_my_profile_returns_known_employee` |
| `tests/test_service_status.py` | `test_health_check_returns_ok`, `test_vpn_status_has_defined_status_and_update_time` |
| `tests/test_tickets.py` | `test_get_own_ticket_returns_200`, `test_get_other_employees_ticket_returns_403`, `test_ticket_matches_schema`, `test_missing_ticket_returns_404` |

Supporting file: `tests/conftest.py` (fixture only, no tests).

`test_missing_ticket_returns_404` was added in class on Day 1 and is not
committed yet (see section 8).

## 3. Run only the Day 1 tests

Activate `.venv` first, then run this from the project root. It is the
same command on Windows PowerShell and macOS:

```bash
python -m pytest -v tests/test_employees.py tests/test_service_status.py tests/test_tickets.py
```

Activate the environment:

- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- macOS: `source .venv/bin/activate`

**Verified results (2026-09-27):**

- Before any Day 2 files existed: `7 passed, 1 warning in 0.27s`.
- After adding the Day 2 fixtures topic: `7 passed, 1 warning in 0.19s`.
  Day 1 behaviour is unchanged.

Do not use a bare `python -m pytest` to mean "Day 1 only". Because
`testpaths = ["tests"]`, it also collects everything in `tests/day2/` once
Day 2 files exist.

To run Day 2 only (once files exist): `python -m pytest -v tests/day2`

## 4. Identity mechanism

- Identity comes only from the request header **`X-Demo-Employee-ID`**
  (BR01). This is a demo header, not real authentication: no tokens,
  no passwords.
- It is resolved in `get_current_employee` in `app/main.py` and applies to
  `/employees/me` and `/tickets/{ticket_id}`.
- The match is exact and case-sensitive: `emp001` is rejected with 400.
- The identity check runs **before** the ticket lookup. A missing or
  unknown header therefore returns 400 even when the ticket does not
  exist.

## 5. Sample data

### Employees (`data/employees.json`)

| employee_id | full_name | department |
| --- | --- | --- |
| EMP001 | Dana Whitfield | Finance |
| EMP002 | Marcus Lee | Sales |
| EMP003 | Priya Nair | Engineering |
| EMP004 | Oliver Grant | Human Resources |

Each employee record also has an `email` field (`@northstar.example`, all
synthetic).

### Tickets and who owns them (`data/tickets.json`)

| ticket_id | Owner | status | subject |
| --- | --- | --- | --- |
| TCK-1001 | EMP001 | open | VPN client fails to connect from home network |
| TCK-1002 | EMP002 | resolved | VPN password reset needed |
| TCK-1003 | EMP003 | in_progress | VPN disconnects every 10 minutes |
| TCK-1004 | EMP004 | open | Need VPN access for new laptop |
| TCK-1005 | EMP001 | in_progress | VPN slow during video calls |
| TCK-1006 | EMP002 | resolved | VPN certificate expired |

Tickets per employee: EMP001 and EMP002 have two each; EMP003 and EMP004
have one each. `TCK-9999` does not exist and is the ID the Day 1 tests use
for "not found".

### VPN status (`data/service_status.json`)

`status: "operational"`, `updated_at: "2026-09-25T08:00:00Z"`.

## 6. Endpoints, response fields, status codes

The API only has `GET` routes. Any other method returns `405`.

| Endpoint | Header needed | Success fields (200) |
| --- | --- | --- |
| `GET /health` | No | `status` (`"ok"`), `service` (`"northstar-it-service-desk"`) |
| `GET /services/vpn/status` | No | `service`, `status`, `updated_at`, `message` |
| `GET /employees/me` | Yes | `employee_id`, `full_name`, `department`, `email` |
| `GET /tickets/{ticket_id}` | Yes | `ticket_id`, `employee_id`, `subject`, `description`, `status`, `created_at`, `updated_at` |

Ticket responses must match `schemas/ticket.schema.json`: all 7 fields are
required, extra fields are not allowed, and `status` must be one of
`open`, `in_progress`, or `resolved`. The allowed VPN `status` values are
`operational`, `degraded`, and `outage` (BR04).

Every error body has the form `{"detail": "<message>"}`.

### Observed status codes

| Request | Code | `detail` |
| --- | --- | --- |
| `GET /tickets/TCK-1001`, header `EMP001` (owner) | 200 | — |
| `GET /tickets/TCK-1001`, header `EMP002` (not owner) | 403 | `You may not view another employee's ticket.` |
| `GET /tickets/TCK-9999`, header `EMP001` | 404 | `Ticket not found: TCK-9999` |
| `GET /employees/me`, no header | 400 | `Missing required header: X-Demo-Employee-ID` |
| `GET /employees/me`, header `EMP999` | 400 | `Unknown demo employee id: EMP999` |
| `GET /employees/me`, header `emp001` | 400 | `Unknown demo employee id: emp001` |
| `GET /tickets/TCK-1001`, no header | 400 | `Missing required header: X-Demo-Employee-ID` |
| `GET /tickets/TCK-9999`, header `EMP999` | 400 | `Unknown demo employee id: EMP999` (identity is checked first) |
| `POST /tickets/TCK-1001` | 405 | `Method Not Allowed` |

Codes the Day 1 tests already assert: 200 (health, VPN status, profile,
own ticket), 403, and 404. The 400 cases and the 405 case are not
asserted by any Day 1 test yet.

## 7. Is a running server needed?

**No server is needed for the tests.** They use FastAPI's `TestClient`
(`tests/conftest.py`), which calls the app in-process without any
network.

To start the server for manual exploration (Swagger UI, curl), activate
`.venv` and run this from the project root:

- Windows PowerShell: `uvicorn app.main:app --reload --port 8000`
- macOS: `uvicorn app.main:app --reload --port 8000`

If `uvicorn` is not found, use `python -m uvicorn app.main:app --reload
--port 8000`. The server runs at `http://127.0.0.1:8000`, and the docs page
is at `/docs`. This was verified on 2026-09-27: `/health` returned 200, and
`EMP002` requesting `TCK-1001` returned 403.

## 8. Baseline and blockers

**Baseline:** 7 of 7 Day 1 tests pass. There are no blockers.

Things to know:

1. **Uncommitted Day 1 work.** `tests/test_tickets.py` has an uncommitted
   change that adds `test_missing_ticket_returns_404`. Also,
   `practice_day1.py` in the project root is untracked and empty. Neither
   is collected as a Day 2 test. Decide whether students should commit
   these before Day 2 starts.
2. **Name clashes in `tests/day2/`.** `tests/` has no `__init__.py`. If a
   Day 2 file reuses a Day 1 file name (for example
   `tests/day2/test_tickets.py`), pytest stops with an
   "import file mismatch" error. Give Day 2 files unique names (for
   example `test_day2_*.py`), or add `__init__.py` files.
3. **Shared fixture.** The `client` fixture in `tests/conftest.py` is
   available to `tests/day2/` automatically, so Day 2 does not redefine
   it. `tests/day2/conftest.py` only adds fixtures Day 2 needs on top of
   it (see section 9).
4. **Harmless warning.** Starlette prints a `StarletteDeprecationWarning`
   about `httpx` in `TestClient`. It does not affect any result.
5. **Python version.** The README says to use Python 3.11. This `.venv`
   runs 3.12.10, which the project allows.

## 9. Day 2 progress

### Topic 1: fixtures

New files:

| File | Purpose |
| --- | --- |
| `tests/day2/conftest.py` | Four extra fixtures for Day 2 (listed below) |
| `tests/day2/test_01_fixtures.py` | Two tests: each employee views their own ticket |

The two tests use four fixtures from `tests/day2/conftest.py`, plus the
`client` fixture from Day 1:

| Fixture | Defined in | What it gives the test |
| --- | --- | --- |
| `client` | `tests/conftest.py` (Day 1, reused) | A `TestClient` that calls the app in-process |
| `employee_a` | `tests/day2/conftest.py` | `{"employee_id": "EMP001", "own_ticket_id": "TCK-1001"}` |
| `employee_b` | `tests/day2/conftest.py` | `{"employee_id": "EMP002", "own_ticket_id": "TCK-1002"}` |
| `employee_a_headers` | `tests/day2/conftest.py` | `{"X-Demo-Employee-ID": "EMP001"}`. Built from `employee_a` |
| `employee_b_headers` | `tests/day2/conftest.py` | `{"X-Demo-Employee-ID": "EMP002"}`. Built from `employee_b` |

- **Header name:** the header fixtures import `DEMO_HEADER_NAME` from
  `app/main.py` instead of retyping the header name. The project has no
  other auth helper to reuse.
- **Expected values:** the expected ticket ID and owner come from the
  fixtures, which are copied by hand from `data/tickets.json`. They are
  never read from the response being tested.
- **Assertions:** each test checks the status code (200), `ticket_id`, and
  `employee_id` (the owner).
- **Scope:** all fixtures use the default function scope, so each test
  gets fresh copies.

Run it:

```bash
python -m pytest -v tests/day2/test_01_fixtures.py
```

See which fixture each test used and where it came from:

```bash
python -m pytest --fixtures-per-test tests/day2/test_01_fixtures.py
```

**Results (2026-09-27):**

| Run | Result |
| --- | --- |
| `tests/day2/test_01_fixtures.py` | `2 passed, 1 warning in 0.05s` |
| Day 1 files (section 3 command) | `7 passed, 1 warning in 0.19s` |
| Full suite (`python -m pytest -q`) | `9 passed, 1 warning in 0.18s` |

The two `conftest.py` files (`tests/` and `tests/day2/`) load together
without conflict. The only warning is the Starlette `httpx` deprecation
warning noted in section 8.

### Topic 2: parameterised tests

New file: `tests/day2/test_02_parameterized.py`. It holds one test
function, `test_get_ticket`, which runs once per row of a `CASES` table.
It reuses the Day 1 `client` fixture and `DEMO_HEADER_NAME` from
`app/main.py`.

| Case ID | Caller | Ticket | Expected status | Expected content | Overlap |
| --- | --- | --- | --- | --- | --- |
| `employee_a_views_own_ticket` | EMP001 | TCK-1001 | 200 | `ticket_id` = TCK-1001, `employee_id` = EMP001 | **Overlap:** Topic 1 and Day 1 `test_get_own_ticket_returns_200` |
| `employee_b_views_own_ticket` | EMP002 | TCK-1002 | 200 | `ticket_id` = TCK-1002, `employee_id` = EMP002 | **Overlap:** Topic 1 |
| `employee_a_denied_employee_b_ticket` | EMP001 | TCK-1002 | 403 | body exactly `{"detail": "You may not view another employee's ticket."}` | **New** |
| `employee_b_denied_employee_a_ticket` | EMP002 | TCK-1001 | 403 | same exact body as above | **Overlap:** Day 1 `test_get_other_employees_ticket_returns_403` (status only there) |
| `valid_employee_missing_ticket` | EMP001 | TCK-9999 | 404 | body exactly `{"detail": "Ticket not found: TCK-9999"}` | **Overlap:** Day 1 `test_missing_ticket_returns_404` (status only there) |

- **Exact status only:** each case accepts one exact status code. No
  alternatives are allowed.
- **No data leak:** for 403 and 404, the whole body must equal the error
  message exactly. That proves no ticket fields (such as `subject`,
  `description`, or `employee_id`) leak in a denied response.
- **What overlap means here:** the overlapping cases send the same
  requests as earlier tests but check more. The 403 and 404 cases now
  check the body, where Day 1 only checked the status. This makes the
  existing cases stronger, but they still count once toward the case
  total.

Run it:

```bash
python -m pytest -v tests/day2/test_02_parameterized.py
```

**Results (2026-09-27):**

| Run | Result |
| --- | --- |
| `tests/day2/test_02_parameterized.py` | `5 passed in 0.07s` (5 case IDs listed in the report) |
| Day 1 files (section 3 command) | `7 passed, 1 warning in 0.34s` |
| All Day 2 (`python -m pytest -q tests/day2`) | `7 passed, 1 warning in 0.07s` |
| Full suite (`python -m pytest -q`) | `14 passed, 1 warning in 0.21s` |

**Check that the tests can fail (2026-09-27).** A throwaway pytest plugin,
kept outside the project, replaced `rules.employee_owns_ticket` in memory
so it always returned `True`. With that change,
`employee_a_denied_employee_b_ticket` and
`employee_b_denied_employee_a_ticket` failed, and the other 3 cases
passed. No project files were changed for this check.

### Topic 3: ownership and fault injection

New file: `tests/day2/test_03_ownership.py`. Two tests use the Topic 1
fixtures (`employee_a_headers`, `employee_b`, and so on):

| Test | Request | Expected |
| --- | --- | --- |
| `test_employee_a_cannot_view_employee_b_ticket` | EMP001 asks for TCK-1002 | 403, body exactly `{"detail": "You may not view another employee's ticket."}`, and none of TCK-1002's protected text in the response |
| `test_employee_b_cannot_view_employee_a_ticket` | EMP002 asks for TCK-1001 | the same checks, for TCK-1001's protected text |

"Protected text" is the foreign ticket's ID, owner ID, subject,
description, and `created_at`. These are copied by hand from
`data/tickets.json`, and the test checks that none of them appear anywhere
in the raw response.

**Overlap:** both requests are the same as the two 403 cases in Topic 2
(unique cases 6 and 9 in section 10). This file adds explicit checks that
no protected text leaks, so it adds **no new unique case**.

#### Where ownership is enforced

- `app/rules.py` → `employee_owns_ticket(ticket, employee_id)` returns
  `True` only when `ticket["employee_id"]` equals the caller's ID.
- `app/main.py` → `get_ticket()` first returns 404 if the ticket does not
  exist. Then it calls `rules.employee_owns_ticket(...)`. If the answer is
  `False`, it returns 403.

#### The TEST-ONLY fault: `--day2-fault=ownership`

Defined in `tests/day2/conftest.py`:

- **`pytest_addoption`** registers the option. It accepts only the value
  `ownership`, and any other value is rejected.
- **`pytest_report_header`** prints
  `day2-fault: ownership (TEST-ONLY fault injection is ACTIVE)` at the top
  of the run, so nobody mistakes a faulted run for a normal one.
- **`day2_fault`** is an autouse fixture that runs for every test in
  `tests/day2/`.
  - With the option on, it uses pytest's `monkeypatch` to replace
    `rules.employee_owns_ticket` in memory with a version that always
    returns `True`.
  - `monkeypatch` restores the real function automatically after each
    test.

This is isolated because `app/main.py` looks up
`rules.employee_owns_ticket` each time a request arrives. Replacing it in
memory therefore changes the behaviour of the real endpoint, reached
through the real `TestClient`. The fault leaves everything else untouched:

- Identity checks still run.
- `data/` is not touched.
- `app/` is not edited.
- The application has no setting for this fault, so a normal `uvicorn`
  run can never switch it on.

**Isolation checks (2026-09-27):**

| Command | Result |
| --- | --- |
| `pytest tests/test_tickets.py --day2-fault=ownership` | Rejected: `unrecognized arguments` (exit 4). The option only exists when a `tests/day2` path is given. |
| `pytest --day2-fault=ownership` (no path) | Rejected: `unrecognized arguments` (exit 4) |
| `pytest tests/day2 --day2-fault=bogus` | Rejected: `invalid choice: 'bogus'` (exit 4) |
| `git status` / `git diff -- app data schemas` | No changes to `app/`, `data/`, or `schemas/` |

#### Verification (2026-09-27)

| Step | Command | Result |
| --- | --- | --- |
| 1. Normal | `python -m pytest -v tests/day2/test_03_ownership.py` | `2 passed` |
| 2a. Fault on | `python -m pytest -v tests/day2/test_03_ownership.py --day2-fault=ownership` | `2 failed`: `assert 200 == 403` |
| 2b. Fault on, wider run | `python -m pytest -v tests/day2 tests/test_tickets.py --day2-fault=ownership` | `4 failed, 9 passed` (details below) |
| 3. Normal again | `tests/day2/test_03_ownership.py` / Day 1 files / `tests/day2` / full suite | `2 passed` / `7 passed` / `9 passed` / `16 passed` |

Details for step 2b:

- **The 4 failures** are the two Topic 3 tests and the two Topic 2 cases
  `employee_a_denied_employee_b_ticket` and
  `employee_b_denied_employee_a_ticket`.
- **The own-ticket and missing-ticket cases still passed.** That is
  correct: the fault only affects ownership, not the 404 check.
- **Day 1 `test_get_other_employees_ticket_returns_403` also passed in
  the same session, right after the faulted Day 2 tests.** This proves
  the patch was undone after each Day 2 test and never reached outside
  `tests/day2/`.

The failures are real test failures, not `xfail`. Under the fault, the
endpoint returns 200 with the full foreign ticket, and the unchanged
assertions catch it.

#### In plain words for students

The ownership rule is one line in `app/rules.py`: "does this ticket's
owner match the person asking?" The `--day2-fault=ownership` option
secretly replaces that line with "always say yes", but only while the
tests run. Then Employee A can open Employee B's ticket and gets 200 and
the whole ticket instead of 403. Our tests expect 403 and a body with
nothing but the error message, so they fail loudly. That failure is the
point: it shows these tests would catch a real bug in the ownership rule.
When the option is left off, the real rule is used and the tests pass.

### Topic 4: JSON Schema validation

**Dependency:** `jsonschema>=4.21,<5.0` was already listed under
`[project] dependencies` in `pyproject.toml` (installed version: 4.26.0),
so `pyproject.toml` needed no edit. No new package was installed.

**Schemas.** All schemas live in `schemas/`, next to the Day 1 ticket
schema. They use the same draft-07 style.

| Schema file | Used for | Required fields and types |
| --- | --- | --- |
| `ticket.schema.json` (Day 1, unchanged) | `GET /tickets/{id}`, 200 | 7 string fields; `status` limited to `open`, `in_progress`, or `resolved` |
| `employee.schema.json` (new) | `GET /employees/me`, 200 | `employee_id` (pattern `^EMP[0-9]+$`), `full_name`, `department`, `email`: all strings |
| `service_status.schema.json` (new) | `GET /services/vpn/status`, 200 | `service` (the string `"vpn"`), `status` (a string limited to `operational`, `degraded`, or `outage`), `updated_at` (string); `message` is an optional string |
| `error.schema.json` (new) | 400, 403, or 404 bodies | `detail` (non-empty string), nothing else |

All four schemas set `"additionalProperties": false`, so any extra field
fails.

In `service_status.schema.json`, only `status` and `updated_at` are
required by BR04. `service` is also required because it names the
endpoint. `message` is always present in the data file today, but no rule
promises it, so it is optional.

`format` values (`date-time`, `email`) are labels only. jsonschema does not
check them unless you pass a `FormatChecker` and install extra packages,
and this project does neither.

**Reusable validator:** the `assert_matches_schema` fixture in
`tests/day2/conftest.py`.

- A test calls `assert_matches_schema(response.json(), "<file>.schema.json")`.
- The fixture first checks that the schema file itself is valid.
- It then collects every mismatch and fails with one readable line per
  problem, for example `status: 123 is not of type 'string'`.

**Tests** in `tests/day2/test_04_schema.py`. Each API test asserts the
status code first, then applies the schema for that status.

| Test | Request | Status, then schema | Overlap |
| --- | --- | --- | --- |
| `test_employee_profile_matches_schema` | `GET /employees/me` as EMP001 | 200 → `employee.schema.json` (also checks `employee_id` = EMP001) | **New unique case** |
| `test_ticket_matches_schema` | EMP002 → TCK-1002 | 200 → `ticket.schema.json` | **Overlap:** the ticket schema was already checked on Day 1 (on TCK-1001). This test uses a different ticket, but it is not counted as new. |
| `test_service_status_matches_schema` | `GET /services/vpn/status` | 200 → `service_status.schema.json` | **New unique case** (Day 1 only checked the `status` value and that `updated_at` exists) |
| `test_forbidden_ticket_error_matches_schema` | EMP001 → TCK-1002 | 403 → `error.schema.json` | **Overlap:** unique case 9; Topics 2 and 3 already check the exact body |
| `test_example_valid_dictionary_passes` | none (hand-written dict) | — | **Beginner example, not an API case** |
| `test_example_missing_required_field_fails` | none (hand-written dict) | — | **Beginner example, not an API case** |
| `test_example_wrong_type_fails` | none (hand-written dict) | — | **Beginner example, not an API case** |

#### The schema words, in plain language

- **`object`:** the data must be a JSON object, meaning curly braces with
  named fields. In Python, that becomes a `dict`.
- **`string`:** the value must be text in quotes. `"operational"` is a
  string, and `123` is not, even though it looks fine when printed.
- **`properties`:** the list of fields the object may have, with the rules
  for each field's value (its type, allowed values, pattern).
- **`required`:** the fields that must be present. A field listed in
  `properties` but not in `required` is allowed to be missing.

#### New TEST-ONLY faults

The `--day2-fault` option now accepts `ownership`, `missing-status`, and
`wrong-status-type`.

| Fault | Where it is injected | Effect on the real response |
| --- | --- | --- |
| `missing-status` | `app.data.load_service_status`, the function `get_vpn_status()` calls to build its response | `status` key removed |
| `wrong-status-type` | the same function | `status` becomes the number `123` |

How the injection works:

- The broken function still reads `data/service_status.json`. It then
  changes its own in-memory copy, and the file on disk is never touched.
- The request still goes through the real route, FastAPI, and
  `TestClient`. No test edits a response.
- `monkeypatch` restores the real function after each test, the same way
  it does for the ownership fault.

**Does FastAPI catch these faults first? No.** `get_vpn_status()` is
declared as `-> dict`, so FastAPI only checks that the return value is a
dictionary. It does not check which keys are inside or what types they
have. Under both faults the client really received **HTTP 200**:

- `missing-status`: `{'service': 'vpn', 'updated_at': '2026-09-25T08:00:00Z', 'message': 'VPN service is running normally.'}`
- `wrong-status-type`: `{'service': 'vpn', 'status': 123, 'updated_at': '2026-09-25T08:00:00Z', 'message': 'VPN service is running normally.'}`

So in this project, the JSON Schema check is the only thing that catches
these faults. No framework validation was disabled.

#### Verification (2026-09-27)

| Step | Command | Result |
| --- | --- | --- |
| 1. Baseline | `python -m pytest -v tests/day2/test_04_schema.py` | `7 passed` |
| 2a. `missing-status` | `... --day2-fault=missing-status` | `1 failed, 6 passed`. Only `test_service_status_matches_schema` failed: `(top level): 'status' is a required property` |
| 2b. `wrong-status-type` | `... --day2-fault=wrong-status-type` | `1 failed, 6 passed`. Only `test_service_status_matches_schema` failed: `status: 123 is not of type 'string'` and `status: 123 is not one of ['operational', 'degraded', 'outage']` |
| 2c. `ownership` (existing fault) | `... --day2-fault=ownership` | `1 failed, 6 passed`. `test_forbidden_ticket_error_matches_schema` failed, because a 403 was expected and 200 came back |
| 3. Baseline again | this file / Day 1 files / `tests/day2` / full suite | `7 passed` / `7 passed` / `16 passed` / `23 passed` |

Reach check: `pytest tests/day2/test_04_schema.py tests/test_service_status.py --day2-fault=wrong-status-type`
gave `1 failed, 8 passed`. The Day 1 VPN status test passed in the same
session, so the fault never reached outside `tests/day2/`.

`git status` shows no changes to `app/`, `data/`, or `pyproject.toml`.

### Topic 5: Week 1 API coverage

New file: `tests/day2/test_05_week1_coverage.py`. It has 4 test functions,
and each one is parametrised, giving 15 test items. The full scenario list, with the
requirement behind each row, is in
[docs/week01-api-case-matrix.md](week01-api-case-matrix.md).

| Test function | Rows | What it covers |
| --- | --- | --- |
| `test_employee_profile_returns_own_record` | 3 | EMP002, EMP003, EMP004 each get their own profile (200, employee schema) |
| `test_employee_views_own_ticket` | 4 | TCK-1003 (EMP003), TCK-1004 (EMP004), TCK-1005 (EMP001's second ticket), TCK-1006 (EMP002's second ticket). Each checks the ticket schema and the status value. |
| `test_employee_denied_another_employees_ticket` | 2 | EMP004 → TCK-1003 and EMP003 → TCK-1005 are denied (403, exact body) |
| `test_error_response` | 6 | No header on profile; unknown `EMP999`; lowercase `emp001`; no header on ticket; unknown employee on a missing ticket (400, not 404); POST to a ticket (405) |

**Results (2026-10-03):**

| Run | Result |
| --- | --- |
| `tests/day2/test_05_week1_coverage.py` | `15 passed` |
| Day 1 files (section 3 command) | `7 passed` (unchanged) |
| Full suite (`python -m pytest -q`) | **`38 passed`** |
| `--day2-fault=ownership` on Topic 5 | `2 failed, 13 passed`. The two failures are the ownership denials. |
| `--day2-fault=missing-status` on Topic 5 | `15 passed`. Expected: Topic 5 does not call the VPN status endpoint. |
| `--day2-fault=wrong-status-type` on Topic 5 | `15 passed`. Expected, for the same reason. |
| Full suite after the fault runs | `38 passed` |

Fault-injected reruns are checks that the tests can fail. They are not
counted as scenarios.

## 10. Unique-case count

pytest counts one "passed" line per test run. Some of those runs repeat a
request that an earlier test already made, so the pytest total is higher
than the number of distinct cases. Count each distinct combination of
request and expected outcome once:

| # | Unique case | First covered by | Also exercised by |
| --- | --- | --- | --- |
| 1 | `GET /health`: 200, `status` = ok | Day 1 | — |
| 2 | `GET /services/vpn/status`: 200, valid status and `updated_at` | Day 1 | — |
| 3 | `GET /employees/me` as EMP001: 200 | Day 1 | — |
| 4 | EMP001 views own TCK-1001: 200 | Day 1 | Topic 1, Topic 2 |
| 5 | Ticket response matches ticket schema (TCK-1001) | Day 1 | Topic 4 (TCK-1002) |
| 6 | EMP002 views TCK-1001: 403 | Day 1 | Topic 2 (adds exact body check), Topic 3 (adds protected-text check) |
| 7 | EMP001 views missing TCK-9999: 404 | Day 1 | Topic 2 (adds exact body check) |
| 8 | EMP002 views own TCK-1002: 200 | Topic 1 | Topic 2 |
| 9 | EMP001 views EMP002's TCK-1002: 403 | Topic 2 | Topic 3 (adds protected-text check), Topic 4 (adds error schema) |
| 10 | Employee profile matches employee schema | Topic 4 | — |
| 11 | VPN status matches service-status schema | Topic 4 | — |

- **pytest total:** 23 (7 Day 1, 2 Topic 1, 5 Topic 2, 2 Topic 3,
  7 Topic 4).
- **API tests within that total:** 20. The 3 Topic 4 beginner examples
  validate hand-written dictionaries and are **not** API cases.
- **Unique API cases:** 11 (7 from Day 1, 1 new in Topic 1, 1 new in
  Topic 2, 0 new in Topic 3, 2 new in Topic 4).
- **Fault-injection runs** (`--day2-fault=...`) are a check that the tests
  can fail. They are not extra cases and do not count here.

### Week 1 totals (after Topic 5, 2026-10-03)

The unique-case table above stops at 11 because it lists only the earlier
topics. The full Week 1 scenario list, with 26 rows (W1-01 to W1-26), is in
[docs/week01-api-case-matrix.md](week01-api-case-matrix.md).

| Measure | Count |
| --- | --- |
| **Unique API scenarios** (matrix rows) | **26** (11 from Day 1 and Topics 1–4, 15 new in Topic 5) |
| Full pytest count (`python -m pytest -q`) | **38 passed** |
| Pytest items that are standalone validator examples (not API scenarios) | 3 |
| Pytest items that are API tests | 35 |

Report the scenario count and the pytest count separately. The pytest count
is higher because some requests are repeated in more than one test file, and
the parametrised tests run once per row.

Submission evidence (run results, environment versions, limitations, and
unresolved issues) is in [docs/day2-run-evidence.md](day2-run-evidence.md).

Not covered (listed with reasons in the matrix): real authentication,
creating or changing tickets, list endpoints, VPN `degraded` and `outage`
states, real 500 errors, date and email format checks, most ownership
pairs, and concurrency or performance.
