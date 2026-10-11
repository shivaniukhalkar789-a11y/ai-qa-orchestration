"""Run metadata, hashing, saving and human reviews."""

import getpass
import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from day3_lab import report, verdict
from day3_lab.data import DIMENSIONS
from day3_lab.paths import ROOT
from day3_lab.runner import sha256_text


class StoreError(Exception):
    """A user-correctable problem (existing output, stale review, ...)."""


def file_hash(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_info() -> tuple:
    """(commit or 'unavailable', dirty flag or None)."""

    def run(args):
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10, check=True
        ).stdout

    try:
        commit = run(["rev-parse", "HEAD"]).strip()
        dirty = bool(run(["status", "--porcelain"]).strip())
        return commit, dirty
    except Exception:
        return "unavailable", None


def build_run(*, mode, model, records, prompt_path, cases_path, rubric, rubric_path,
              elapsed, extra=None) -> dict:
    commit, dirty = git_info()
    run = {
        "run_id": f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}",
        "timestamp": utc_now(),
        "commit": commit,
        "dirty": dirty,
        "mode": mode,
        "label": "MOCK" if mode == "mock" else "LIVE",
        "model": model if mode != "mock" else None,
        "prompt_file": Path(prompt_path).name,
        "prompt_hash": file_hash(prompt_path),
        "dataset_hash": file_hash(cases_path),
        "rubric_version": rubric["version"],
        "rubric_hash": file_hash(rubric_path),
        "total_elapsed_seconds": round(elapsed, 4),
        "caveats": [
            "Schema validity is structural only. It does not prove factual accuracy "
            "or safety.",
            "Human assessment starts PENDING. No human scores are generated automatically.",
        ],
        "records": records,
    }
    if mode == "mock":
        run["caveats"].insert(
            0,
            "MOCK: fixed reviewed responses. Success validates the workflow, not live "
            "model quality. Editing the prompt does not change mock responses.",
        )
    run.update(extra or {})
    return run


def refresh_verdicts(run: dict) -> None:
    for record in run["records"]:
        record["verdict"] = verdict.decide(record)


def write_run(run: dict, out_dir, *, new: bool) -> None:
    """Write run.json and run.html. With new=True, refuse existing output."""
    out = Path(out_dir)
    if new and ((out / "run.json").exists() or (out / "run.html").exists()):
        raise StoreError(f"{out} already contains a run; choose a new --out directory")
    out.mkdir(parents=True, exist_ok=True)
    refresh_verdicts(run)
    (out / "run.json").write_text(
        json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out / "run.html").write_text(report.render_html(run), encoding="utf-8")


def load_run(path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StoreError(f"cannot read run file {path}: {exc}") from exc


def add_review(run_path, record_id, scores, critical, note, reviewer=None,
               expected_hash=None) -> dict:
    """Append a human review bound to the record's response hash."""
    problems = verdict.validate_scores(scores)
    if problems:
        raise StoreError("; ".join(problems))
    if not isinstance(note, str) or not note.strip():
        raise StoreError("a nonempty --note is required")
    if critical not in ("yes", "no"):
        raise StoreError("--critical must be yes or no")

    run = load_run(run_path)
    record = next((r for r in run["records"] if r["record_id"] == record_id), None)
    if record is None:
        known = ", ".join(r["record_id"] for r in run["records"])
        raise StoreError(f"no record {record_id!r} in this run (have: {known})")
    if record.get("provider_error") or record.get("structural_findings") or not record.get("raw_response"):
        raise StoreError(
            "this record has no structurally valid response to assess "
            "(provider error or structural failure)"
        )
    actual = sha256_text(record["raw_response"])
    if actual != record.get("response_hash"):
        raise StoreError("stale review refused: raw_response no longer matches the stored response hash")
    if expected_hash and expected_hash != actual:
        raise StoreError("stale review refused: --response-hash does not match the current response")

    review = {
        "reviewer": reviewer or getpass.getuser() or "unknown",
        "timestamp": utc_now(),
        "scores": dict(zip(DIMENSIONS, scores)),
        "critical": critical == "yes",
        "note": note.strip(),
        "response_hash": actual,
    }
    record["review_history"].append(review)
    record["human_assessment"] = {"status": "REVIEWED", **review}
    write_run(run, Path(run_path).parent, new=False)
    return record["verdict"] if "verdict" in record else verdict.decide(record)
