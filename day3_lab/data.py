"""Load and validate the Day 3 dataset and rubric."""

import json

from day3_lab.contract import SERVICE_STATUSES
from day3_lab.paths import CASES_PATH, RUBRIC_PATH

EXPECTED_CASE_COUNT = 10
CASE_KEYS = {
    "case_id",
    "category",
    "question",
    "approved_context",
    "expected_behaviour",
    "prohibited_behaviour",
    "evaluation_method",
    "requirement_ids",
}
CONTEXT_KEYS = {"device", "service_status", "recovery_time", "guidance"}
DIMENSIONS = ["correctness", "relevance", "completeness", "safety"]


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_dataset(path=CASES_PATH) -> dict:
    return load_json(path)


def load_rubric(path=RUBRIC_PATH) -> dict:
    return load_json(path)


def _is_str_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) and v for v in value)


def validate_dataset(dataset) -> list:
    """Return a list of problem strings (empty means structurally valid)."""
    problems = []
    if not isinstance(dataset, dict):
        return ["dataset is not an object"]
    if dataset.get("dataset_version") != "day3-v1":
        problems.append("dataset_version must be 'day3-v1'")
    if dataset.get("synthetic") is not True:
        problems.append("synthetic must be true")
    cases = dataset.get("cases")
    if not isinstance(cases, list):
        return problems + ["cases must be a list"]
    if len(cases) != EXPECTED_CASE_COUNT:
        problems.append(f"expected {EXPECTED_CASE_COUNT} cases, found {len(cases)}")

    ids = [c.get("case_id") if isinstance(c, dict) else None for c in cases]
    if len(set(ids)) != len(ids):
        problems.append("case_id values are not unique")

    for case in cases:
        if not isinstance(case, dict):
            problems.append("a case is not an object")
            continue
        cid = case.get("case_id")
        if set(case) != CASE_KEYS:
            problems.append(f"{cid}: keys differ by {sorted(set(case) ^ CASE_KEYS)}")
            continue
        for key in ("case_id", "category", "question"):
            if not isinstance(case[key], str) or not case[key].strip():
                problems.append(f"{cid}: {key} must be a nonempty string")
        ctx = case["approved_context"]
        if not isinstance(ctx, dict) or set(ctx) != CONTEXT_KEYS:
            problems.append(f"{cid}: approved_context must have keys {sorted(CONTEXT_KEYS)}")
            continue
        if ctx["device"] is not None and not isinstance(ctx["device"], str):
            problems.append(f"{cid}: device must be string or null")
        if ctx["service_status"] not in SERVICE_STATUSES:
            problems.append(f"{cid}: invalid service_status {ctx['service_status']!r}")
        if ctx["recovery_time"] is not None and not isinstance(ctx["recovery_time"], str):
            problems.append(f"{cid}: recovery_time must be string or null")
        if not isinstance(ctx["guidance"], str) or not ctx["guidance"].strip():
            problems.append(f"{cid}: guidance must be a nonempty string")
        for key in ("expected_behaviour", "prohibited_behaviour", "requirement_ids"):
            if not _is_str_list(case[key]) or not case[key]:
                problems.append(f"{cid}: {key} must be a nonempty list of strings")
        if case["evaluation_method"] != ["schema", "human_rubric"]:
            problems.append(f"{cid}: evaluation_method must be ['schema', 'human_rubric']")
    return problems


def validate_rubric(rubric, dataset=None) -> list:
    problems = []
    if not isinstance(rubric, dict):
        return ["rubric is not an object"]
    if rubric.get("dimension_order") != DIMENSIONS:
        problems.append(f"dimension_order must be {DIMENSIONS}")
    scales = rubric.get("scales")
    if not isinstance(scales, dict) or list(scales) != DIMENSIONS:
        problems.append("scales must define exactly the four dimensions in order")
    else:
        for name, scale in scales.items():
            if not isinstance(scale, dict) or sorted(scale) != ["0", "1", "2"]:
                problems.append(f"scale {name} must define 0, 1 and 2")
    for key in ("critical_examples", "decision_rule", "review_scope"):
        if not rubric.get(key):
            problems.append(f"{key} is missing")
    if dataset is not None and rubric.get("version") != dataset.get("dataset_version"):
        problems.append("rubric version does not match dataset_version")
    return problems
