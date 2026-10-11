"""Run work items through a provider and build one evidence record each."""

import hashlib
import time

from day3_lab.contract import check_response
from day3_lab.providers import ProviderError


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def case_items(cases: list) -> list:
    """Work items for a plain run: one per dataset case, record_id = case_id."""
    return [{"record_id": c["case_id"], "case": c} for c in cases]


def evaluate_item(provider, item: dict, prompt_text: str) -> dict:
    """Call the provider once and keep everything as evidence.

    Provider failures become a provider_error entry (verdict ERROR). Nothing
    is retried here, retried silently, or replaced by a mock answer.
    """
    case = item["case"]
    started = time.perf_counter()
    result, error = None, None
    try:
        result = provider.generate(item, prompt_text)
    except ProviderError as exc:
        error = {"type": exc.kind, "message": str(exc)}
    except Exception as exc:  # unexpected: still recorded, never hidden
        error = {"type": "unexpected", "message": f"{type(exc).__name__}: {exc}"}
    elapsed = round(time.perf_counter() - started, 4)

    record = {
        "record_id": item["record_id"],
        "case_id": case["case_id"],
        "category": case["category"],
        "question": case["question"],
        "approved_context": case["approved_context"],
        "expected_behaviour": case["expected_behaviour"],
        "prohibited_behaviour": case["prohibited_behaviour"],
        "requirement_ids": case["requirement_ids"],
        "note": item.get("note"),
        "extra_checks": item.get("extra_checks", {}),
        "elapsed_seconds": elapsed,
        "provider_error": error,
        "raw_response": None,
        "parsed_response": None,
        "structural_findings": [],
        "structural_status": "NOT_RUN",
        "response_hash": None,
        "token_usage": None,
        "human_assessment": {"status": "PENDING"},
        "review_history": [],
    }
    if result is not None:
        parsed, findings = check_response(result.raw_text)
        record.update(
            raw_response=result.raw_text,
            parsed_response=parsed,
            structural_findings=findings,
            structural_status="FAIL" if findings else "PASS",
            response_hash=sha256_text(result.raw_text),
            token_usage=result.token_usage,
        )
        if "naive_reference" in item:
            record["extra_checks"] = dict(record["extra_checks"])
            record["extra_checks"]["naive_exact_match"] = _naive_check(
                parsed, item["naive_reference"]
            )
    return record


def _naive_check(parsed, reference: str) -> dict:
    matched = bool(parsed) and parsed.get("answer") == reference
    return {
        "reference_answer": reference,
        "matched": matched,
        "warning": "Deliberately naive exact-string comparison. It is NOT a quality "
        "verdict: accurate answers can be worded differently.",
    }
