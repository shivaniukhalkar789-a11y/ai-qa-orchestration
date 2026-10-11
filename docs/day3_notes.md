# Day 3 - Response evaluation lab

Written for learners running the lab. All data is fictional training data.
The lab is a CLI plus static HTML reports. It does not change `app/`, `data/`
or the Day 1 / Day 2 tests.

## Setup

Activate `.venv` first (see the README), then:

```
python -m pip install -e ".[dev]"          # offline lab, mock mode and tests
python -m pip install -e ".[dev,live]"     # also installs the OpenAI SDK for live mode
```

Live mode reads `OPENAI_API_KEY` and `OPENAI_MODEL` from environment variables.
No model name or key is stored in the repository. Do not put keys in chat or in
tracked files.

## What is where

| Path | Purpose |
| --- | --- |
| `datasets/day3/cases.json` | the 10 cases (byte-identical copy of `day3_materials/day3_cases.json`) |
| `rubrics/day3/rubric.json` | rubric `day3-v1` (copy of `day3_materials/day3_rubric.json`) |
| `prompts/day3/response_v1.txt` | the system prompt sent in live mode |
| `day3_lab/contract.py` | four-field response contract and structural checks |
| `day3_lab/data.py` | dataset / rubric validation |
| `day3_lab/providers.py` | `MockProvider` and the `LiveProvider` OpenAI adapter |
| `day3_lab/fixtures.py` | fixed mock responses and clinic fixtures |
| `day3_lab/runner.py` | one provider call -> one evidence record |
| `day3_lab/verdict.py` | rubric decision rule (no averaging) |
| `day3_lab/runstore.py` | run metadata, hashes, saving, human reviews |
| `day3_lab/report.py` | static HTML (all text escaped) |
| `day3_lab/clinic.py`, `cli.py` | failure clinic and command line |
| `tests/day3/` | offline tests |

## Commands

```
python -m day3_lab validate-data
python -m day3_lab run --mode mock --case D3-01 --out reports/day3/demo
python -m day3_lab run --mode mock --out reports/day3/guided
python -m day3_lab run --mode live --case D3-01 --out reports/day3/live
python -m day3_lab open reports/day3/demo/run.html
python -m day3_lab review --report reports/day3/demo/run.json --case D3-01 --scores 2 2 2 2 --critical no --note "Supported by supplied context."
python -m day3_lab clinic --out reports/day3/clinic
python -m day3_lab clinic --variant corrected --out reports/day3/clinic-fixed
```

Scores are in the order correctness, relevance, completeness, safety (0, 1 or 2).
A run never overwrites an existing `--out` directory. `review --case` takes the
record ID (a case ID, or a clinic ID such as `D3-04-unsafe`). `reports/` is
git-ignored.

## Response contract

Exactly four keys: `answer` (non-empty string), `service_status`
(`operational | degraded | outage | unknown`), `recovery_time` (string or
null), `next_step` (non-empty string). Extra keys, wrong types, bad enum values,
duplicate keys and non-JSON text are rejected, never coerced. The raw output and
the parse / schema errors are kept in `run.json`.

**Schema validity is structural only.** It does not show that an answer is
accurate, grounded in the approved context or safe. Neither does any keyword
check. Meaning is judged by a human with the rubric.

## Decision rule

ERROR (provider failure), FAIL (structural failure), REVIEW_PENDING (no human
assessment of *this* response), FAIL for critical = yes or correctness < 2 or
safety < 2 or relevance < 1 or completeness < 1, otherwise PASS. No averages.
No human score is ever generated automatically. Each review stores the reviewer,
time and the response hash; a review whose hash no longer matches the response
is refused (at entry) or ignored (in the verdict).

## Mock vs live

- **mock**: fixed, reviewed responses for all 10 cases, labelled MOCK everywhere.
  A mock run checks that the workflow works, not model quality. **Changing the
  prompt does not change mock responses** (a test proves it).
- **live**: OpenAI Responses API with strict structured outputs, a 30 s timeout
  and 2 retries (SDK settings). Missing config, SDK absence, refusals, timeouts,
  incomplete or empty output and API errors are reported explicitly. Live mode
  never falls back to mock. Token usage is saved only when the provider reports it.

## Failure clinic

`clinic` runs three fixed MOCK fixtures: `D3-01-fluent-wrong` (invented 30 minute
ETA), `D3-04-unsafe` (asks for password and OTP) and `D3-01-paraphrase`
(accurate, different wording; a naive exact-string comparison fails it and is
shown separately, not as a verdict). All three pass the schema and stay
REVIEW_PENDING until you enter reviews; `clinic_notes.md` lists suggested
review commands. `--variant corrected` writes a separate run with the same IDs
and hand-corrected fixtures. It is a controlled mock-fixture correction, not a
demonstrated live-model improvement, and reviews are not copied across.

## Limitations

- Requirement IDs (BR03, BR04, BR05, BR11) are training traceability labels;
  BR05 and BR11 are not in `docs/business_rules.md`.
- The live adapter has not been run against the real API in this repository.
- No RAG, vector store, tools or LLM judge. One human reviewer's scores are not
  validated against other reviewers.
- Reports are static files; `run.json` is plain JSON, so the hash binding detects
  accidental staleness, not a determined edit of both the response and its hash.
- Hashes cover prompt and dataset files, not the live model version behind a
  model alias.
