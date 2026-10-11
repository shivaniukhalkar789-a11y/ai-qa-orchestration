"""Dataset, rubric and response-contract tests (offline)."""

import copy
import json

import pytest

from day3_lab import data, fixtures
from day3_lab.contract import check_response
from day3_lab.paths import ROOT


def test_dataset_is_valid_with_ten_unique_cases(dataset):
    assert data.validate_dataset(dataset) == []
    ids = [c["case_id"] for c in dataset["cases"]]
    assert len(ids) == 10 and len(set(ids)) == 10


def test_rubric_is_consistent_with_dataset(rubric, dataset):
    assert data.validate_rubric(rubric, dataset) == []
    assert rubric["version"] == "day3-v1"


def test_lab_inputs_are_unchanged_copies_of_supplied_materials():
    for supplied, copied in [
        ("day3_materials/day3_cases.json", "datasets/day3/cases.json"),
        ("day3_materials/day3_rubric.json", "rubrics/day3/rubric.json"),
    ]:
        assert (ROOT / supplied).read_bytes() == (ROOT / copied).read_bytes()


def test_every_case_has_a_mock_fixture(dataset):
    assert {c["case_id"] for c in dataset["cases"]} == set(fixtures.MOCK_RESPONSES)


def test_every_mock_fixture_is_structurally_valid():
    for case_id, response in fixtures.MOCK_RESPONSES.items():
        parsed, findings = check_response(json.dumps(response))
        assert findings == [] and parsed == response, case_id


def test_dataset_validation_catches_problems(dataset):
    broken = copy.deepcopy(dataset)
    broken["cases"][1]["case_id"] = broken["cases"][0]["case_id"]
    broken["cases"][2]["approved_context"]["service_status"] = "fine"
    del broken["cases"][3]["question"]
    problems = " | ".join(data.validate_dataset(broken))
    assert "not unique" in problems and "invalid service_status" in problems
    assert "keys differ" in problems


def test_rubric_validation_catches_problems(rubric, dataset):
    broken = copy.deepcopy(rubric)
    broken["version"] = "other"
    del broken["scales"]["safety"]["2"]
    assert len(data.validate_rubric(broken, dataset)) == 2


GOOD = {"answer": "a", "service_status": "outage", "recovery_time": None, "next_step": "n"}


def _with(**changes):
    value = dict(GOOD)
    value.update(changes)
    return json.dumps(value)


@pytest.mark.parametrize(
    "raw, kind",
    [
        ("not json", "parse_error"),
        ('{"answer": "a",', "parse_error"),
        ('{"answer": "a", "answer": "b", "service_status": "outage", '
         '"recovery_time": null, "next_step": "n"}', "parse_error"),
        (json.dumps({k: v for k, v in GOOD.items() if k != "next_step"}), "schema_error"),
        (_with(extra="x"), "schema_error"),
        (_with(answer=5), "schema_error"),
        (_with(answer=""), "schema_error"),
        (_with(answer="   "), "schema_error"),
        (_with(next_step=None), "schema_error"),
        (_with(service_status="down"), "schema_error"),
        (_with(service_status="OUTAGE"), "schema_error"),
        (_with(recovery_time=30), "schema_error"),
        (_with(recovery_time=False), "schema_error"),
        ("[]", "schema_error"),
        ("null", "schema_error"),
        (None, "parse_error"),
    ],
)
def test_invalid_output_is_rejected_not_coerced(raw, kind):
    parsed, findings = check_response(raw)
    assert parsed is None
    assert findings and findings[0]["kind"] == kind


@pytest.mark.parametrize("status", ["operational", "degraded", "outage", "unknown"])
def test_valid_enum_values_and_null_or_string_recovery_time(status):
    for recovery in (None, "about 45 minutes"):
        parsed, findings = check_response(_with(service_status=status, recovery_time=recovery))
        assert findings == [] and parsed["service_status"] == status
