"""Controlled failure clinic: fixed MOCK fixtures, no live calls."""

import time

from day3_lab import fixtures
from day3_lab.providers import MockProvider
from day3_lab.runner import evaluate_item

CORRECTED_NOTE = (
    "CONTROLLED MOCK-FIXTURE CORRECTION: the fixtures were edited by hand to "
    "remove the invented ETA and the secret request. This is NOT a demonstrated "
    "live-model improvement. Human reviews of the original responses were not "
    "copied; every response here needs its own review."
)


def build_items(cases_by_id: dict, variant: str) -> tuple:
    table = fixtures.CLINIC_CORRECTED if variant == "corrected" else fixtures.CLINIC_ORIGINAL
    items, responses = [], {}
    for record_id, (case_id, note, response) in table.items():
        item = {"record_id": record_id, "case": cases_by_id[case_id], "note": note}
        if record_id == "D3-01-paraphrase":
            item["naive_reference"] = fixtures.NAIVE_REFERENCE_ANSWER
        items.append(item)
        responses[record_id] = response
    return items, responses


def run_clinic(cases_by_id: dict, prompt_text: str, variant: str) -> tuple:
    """Return (records, elapsed_seconds)."""
    items, responses = build_items(cases_by_id, variant)
    provider = MockProvider(responses)
    started = time.perf_counter()
    records = [evaluate_item(provider, item, prompt_text) for item in items]
    return records, time.perf_counter() - started


def clinic_notes(run: dict, variant: str, run_json: str) -> str:
    lines = [
        f"# Day 3 failure clinic ({variant}) - MOCK fixtures",
        "",
        f"Run ID: `{run['run_id']}`. All responses are fixed MOCK fixtures; no live model was called.",
        "",
    ]
    if variant == "corrected":
        lines += [f"> {CORRECTED_NOTE}", ""]
    lines += [
        "Structural validity is not accuracy or safety. Human assessment is PENDING "
        "for every record until you enter it with the `review` command.",
        "",
        "| Record | Structural check | Verdict now | Teaching expectation |",
        "| --- | --- | --- | --- |",
    ]
    for r in run["records"]:
        lines.append(
            f"| {r['record_id']} | {r['structural_status']} | {r['verdict']['status']} | {r['note']} |"
        )
    naive = next(
        (r["extra_checks"]["naive_exact_match"] for r in run["records"]
         if "naive_exact_match" in r.get("extra_checks", {})),
        None,
    )
    if naive:
        lines += [
            "",
            "## Naive exact-string comparison",
            f"On D3-01-paraphrase the naive comparison matched = **{naive['matched']}**. "
            "That only shows wording differs. It must not be read as a quality verdict; "
            "the paraphrase is judged by the human rubric.",
        ]
    lines += [
        "",
        "## Entering reviews (suggested examples; you decide the scores)",
        "```",
        f'python -m day3_lab review --report {run_json} --case D3-01-fluent-wrong --scores 0 2 2 2 --critical no --note "Invents a 30 minute ETA not in the context."',
        f'python -m day3_lab review --report {run_json} --case D3-04-unsafe --scores 0 2 2 0 --critical yes --note "Requests password and OTP."',
        f'python -m day3_lab review --report {run_json} --case D3-01-paraphrase --scores 2 2 2 2 --critical no --note "Accurate, unknown ETA, suitable next step."',
        "```",
        "",
        "Reviews are bound to each response's hash. Reviews of the original run do not apply to the corrected run.",
        "",
    ]
    return "\n".join(lines)
