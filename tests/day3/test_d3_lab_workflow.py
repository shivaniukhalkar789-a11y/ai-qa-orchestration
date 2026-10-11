"""Verdicts, runs, reviews, providers and the clinic (all offline)."""

import json

import pytest

from day3_lab import fixtures, report, runstore, verdict
from day3_lab.providers import LiveProvider, MockProvider, ProviderError
from day3_lab.runner import evaluate_item


def _record(**overrides):
    base = {"provider_error": None, "structural_findings": [], "response_hash": "h1",
            "review_history": []}
    base.update(overrides)
    return base


def _review(scores, critical=False, response_hash="h1"):
    names = ["correctness", "relevance", "completeness", "safety"]
    return {"scores": dict(zip(names, scores)), "critical": critical, "response_hash": response_hash}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---- decision rule --------------------------------------------------------

def test_provider_failure_is_error():
    assert verdict.decide(_record(provider_error={"type": "timeout"}))["status"] == "ERROR"


def test_structural_failure_is_fail_even_with_a_review():
    rec = _record(structural_findings=[{"kind": "schema_error"}], review_history=[_review([2, 2, 2, 2])])
    assert verdict.decide(rec)["status"] == "FAIL"


def test_unreviewed_valid_response_is_review_pending_never_pass():
    assert verdict.decide(_record())["status"] == "REVIEW_PENDING"


@pytest.mark.parametrize(
    "scores, critical, expected",
    [
        ([2, 2, 2, 2], False, "PASS"),
        ([2, 1, 1, 2], False, "PASS"),
        ([2, 2, 2, 2], True, "FAIL"),   # critical overrides perfect scores
        ([1, 2, 2, 2], False, "FAIL"),
        ([2, 2, 2, 1], False, "FAIL"),
        ([2, 0, 2, 2], False, "FAIL"),
        ([2, 2, 0, 2], False, "FAIL"),
    ],
)
def test_rubric_thresholds_without_averaging(scores, critical, expected):
    rec = _record(review_history=[_review(scores, critical)])
    assert verdict.decide(rec)["status"] == expected


def test_review_of_different_output_is_ignored():
    rec = _record(review_history=[_review([2, 2, 2, 2], response_hash="old")])
    assert verdict.decide(rec)["status"] == "REVIEW_PENDING"


@pytest.mark.parametrize("scores", [[3, 2, 2, 2], [-1, 2, 2, 2], [2, 2, 2], [2.0, 2, 2, 2], [True, 2, 2, 2]])
def test_invalid_scores_rejected(scores):
    assert verdict.validate_scores(scores)


# ---- CLI: validate / run --------------------------------------------------

def test_validate_data_reports_ten_cases(run_cli):
    code, out, _ = run_cli("validate-data")
    assert code == 0 and "10 cases" in out


def test_mock_run_saves_evidence_and_labels_mock(mock_run):
    run = read_json(mock_run)
    assert run["mode"] == "mock" and run["label"] == "MOCK" and run["model"] is None
    for key in ("run_id", "timestamp", "commit", "dirty", "prompt_hash", "dataset_hash", "rubric_version"):
        assert key in run
    rec = run["records"][0]
    assert rec["raw_response"] and rec["parsed_response"] and rec["response_hash"]
    assert rec["token_usage"] is None  # never invented for mock
    assert rec["human_assessment"]["status"] == "PENDING"
    assert rec["verdict"]["status"] == "REVIEW_PENDING"
    html = (mock_run.parent / "run.html").read_text(encoding="utf-8")
    assert "MOCK" in html and "not a production release decision" in html


def test_full_mock_run_covers_all_cases_and_none_pass(run_cli, tmp_path):
    code, _, _ = run_cli("run", "--mode", "mock", "--out", tmp_path / "all")
    assert code == 0
    run = read_json(tmp_path / "all" / "run.json")
    assert len(run["records"]) == 10
    assert {r["verdict"]["status"] for r in run["records"]} == {"REVIEW_PENDING"}


def test_run_refuses_to_overwrite(run_cli, mock_run):
    code, _, err = run_cli("run", "--mode", "mock", "--case", "D3-02", "--out", mock_run.parent)
    assert code == 2 and "new --out" in err
    assert read_json(mock_run)["records"][0]["case_id"] == "D3-01"


def test_unknown_case_is_an_error(run_cli, tmp_path):
    code, _, err = run_cli("run", "--mode", "mock", "--case", "D3-99", "--out", tmp_path / "x")
    assert code == 2 and "unknown case" in err


def test_prompt_change_does_not_change_mock_responses(dataset, prompt_text):
    provider = MockProvider(fixtures.MOCK_RESPONSES)
    item = {"record_id": "D3-01", "case": dataset["cases"][0]}
    a = evaluate_item(provider, item, prompt_text)
    b = evaluate_item(provider, item, prompt_text + "\nANSWER IN FRENCH")
    assert a["response_hash"] == b["response_hash"]


def test_open_command_uses_standard_browser(run_cli, mock_run, monkeypatch):
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    code, _, _ = run_cli("open", mock_run.parent / "run.html")
    assert code == 0 and opened and opened[0].startswith("file:")
    assert run_cli("open", mock_run.parent / "nope.html")[0] == 2


# ---- reviews ----------------------------------------------------------------

def _review_args(path, *extra, scores=("2", "2", "2", "2"), critical="no", note="Supported by supplied context."):
    return ["review", "--report", path, "--case", "D3-01", "--scores", *scores,
            "--critical", critical, "--note", note, *extra]


def test_review_passes_and_keeps_history_and_regenerates_html(run_cli, mock_run):
    code, out, _ = run_cli(*_review_args(mock_run, "--reviewer", "tester"))
    assert code == 0 and "PASS" in out
    rec = read_json(mock_run)["records"][0]
    assert rec["verdict"]["status"] == "PASS"
    assert rec["review_history"][0]["reviewer"] == "tester"
    assert rec["review_history"][0]["response_hash"] == rec["response_hash"]
    run_cli(*_review_args(mock_run, scores=("2", "2", "2", "1"), note="Second look."))
    rec = read_json(mock_run)["records"][0]
    assert len(rec["review_history"]) == 2 and rec["verdict"]["status"] == "FAIL"
    assert "tester" in (mock_run.parent / "run.html").read_text(encoding="utf-8")


def test_review_critical_yes_fails(run_cli, mock_run):
    run_cli(*_review_args(mock_run, critical="yes"))
    assert read_json(mock_run)["records"][0]["verdict"]["status"] == "FAIL"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"scores": ("3", "2", "2", "2")},
        {"scores": ("2", "2", "-1", "2")},
        {"note": "   "},
    ],
)
def test_review_rejects_invalid_input(run_cli, mock_run, kwargs):
    code, _, err = run_cli(*_review_args(mock_run, **kwargs))
    assert code == 2 and err
    assert read_json(mock_run)["records"][0]["review_history"] == []


def test_review_rejects_stale_and_tampered_output(run_cli, mock_run):
    code, _, err = run_cli(*_review_args(mock_run, "--response-hash", "deadbeef"))
    assert code == 2 and "stale" in err
    run = read_json(mock_run)
    run["records"][0]["raw_response"] = run["records"][0]["raw_response"].replace("outage", "fine")
    mock_run.write_text(json.dumps(run), encoding="utf-8")
    code, _, err = run_cli(*_review_args(mock_run))
    assert code == 2 and "stale" in err


def test_review_unknown_record_and_unreviewable_record(run_cli, mock_run):
    args = _review_args(mock_run)
    args[args.index("D3-01")] = "D3-77"
    assert run_cli(*args)[0] == 2
    run = read_json(mock_run)
    run["records"][0]["structural_findings"] = [{"kind": "schema_error", "path": "", "message": "x"}]
    mock_run.write_text(json.dumps(run), encoding="utf-8")
    assert run_cli(*_review_args(mock_run))[0] == 2


# ---- providers --------------------------------------------------------------

class FailingProvider:
    model = None

    def __init__(self, exc):
        self.exc = exc

    def generate(self, item, prompt):
        raise self.exc


def test_provider_error_is_recorded_as_error_not_hidden(dataset, prompt_text):
    item = {"record_id": "D3-01", "case": dataset["cases"][0]}
    rec = evaluate_item(FailingProvider(ProviderError("timeout", "slow")), item, prompt_text)
    assert rec["provider_error"] == {"type": "timeout", "message": "slow"}
    assert rec["raw_response"] is None and rec["response_hash"] is None
    assert verdict.decide(rec)["status"] == "ERROR"
    unexpected = evaluate_item(FailingProvider(RuntimeError("boom")), item, prompt_text)
    assert unexpected["provider_error"]["type"] == "unexpected"


def test_malformed_provider_output_keeps_raw_text_and_errors(dataset, prompt_text):
    item = {"record_id": "D3-01", "case": dataset["cases"][0]}
    rec = evaluate_item(MockProvider({"D3-01": "Sure! The VPN is down."}), item, prompt_text)
    assert rec["raw_response"] == "Sure! The VPN is down."
    assert rec["parsed_response"] is None and rec["structural_findings"]
    assert verdict.decide(rec)["status"] == "FAIL"


class FakeResponses:
    def __init__(self, response=None, exc=None):
        self.response, self.exc, self.calls = response, exc, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        return self.response


class FakeClient:
    def __init__(self, **kw):
        self.kw = kw
        self.responses = kw.pop("_responses", None) or FakeResponses()


class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


GOOD_TEXT = json.dumps(fixtures.MOCK_RESPONSES["D3-01"])


def _live(response=None, exc=None):
    client = FakeClient()
    client.responses = FakeResponses(response, exc)
    return LiveProvider("test-model", client), client


def _ok_response(**kw):
    base = dict(status="completed", output=[Obj(type="message", content=[Obj(type="output_text", text=GOOD_TEXT)])],
                output_text=GOOD_TEXT, usage=Obj(input_tokens=10, output_tokens=5, total_tokens=15))
    base.update(kw)
    return Obj(**base)


def test_live_missing_config_is_explicit_and_never_falls_back_to_mock(run_cli, tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    code, _, err = run_cli("run", "--mode", "live", "--case", "D3-01", "--out", tmp_path / "live")
    assert code == 2 and "OPENAI_API_KEY" in err and "no mock fallback" in err
    assert not (tmp_path / "live" / "run.json").exists()


def test_live_from_env_uses_bounded_timeout_and_retries_without_network():
    seen = {}

    def factory(**kw):
        seen.update(kw)
        return FakeClient()

    provider = LiveProvider.from_env({"OPENAI_API_KEY": "k", "OPENAI_MODEL": "m"}, factory)
    assert provider.model == "m" and seen["timeout"] > 0 and seen["max_retries"] >= 0


def test_live_success_uses_strict_structured_output_and_real_usage(dataset):
    provider, client = _live(_ok_response())
    result = provider.generate({"record_id": "D3-01", "case": dataset["cases"][0]}, "PROMPT")
    call = client.responses.calls[0]
    assert call["model"] == "test-model" and call["instructions"] == "PROMPT"
    fmt = call["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True
    assert fmt["schema"]["additionalProperties"] is False
    assert result.token_usage == {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}


def test_live_without_usage_reports_none_not_invented(dataset):
    provider, _ = _live(_ok_response(usage=None))
    assert provider.generate({"record_id": "x", "case": dataset["cases"][0]}, "P").token_usage is None


@pytest.mark.parametrize(
    "response, exc, kind",
    [
        (None, type("APITimeoutError", (Exception,), {})("timed out"), "timeout"),
        (None, RuntimeError("500"), "provider_error"),
        (_ok_response(output=[Obj(type="message", content=[Obj(type="refusal", refusal="no")])]), None, "refusal"),
        (_ok_response(status="incomplete", incomplete_details="max_output_tokens"), None, "incomplete"),
        (_ok_response(output_text=""), None, "empty_output"),
    ],
)
def test_live_failures_are_reported_explicitly(dataset, response, exc, kind):
    provider, _ = _live(response, exc)
    with pytest.raises(ProviderError) as info:
        provider.generate({"record_id": "x", "case": dataset["cases"][0]}, "P")
    assert info.value.kind == kind


# ---- report -----------------------------------------------------------------

def test_html_escapes_response_text(dataset, prompt_text, mock_run):
    evil = "<script>alert(1)</script>"
    item = {"record_id": "D3-01", "case": dataset["cases"][0], "note": evil}
    payload = dict(fixtures.MOCK_RESPONSES["D3-01"], answer=evil)
    rec = evaluate_item(MockProvider({"D3-01": payload}), item, prompt_text)
    run = read_json(mock_run)
    run["records"] = [rec]
    runstore.refresh_verdicts(run)
    html = report.render_html(run)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


# ---- clinic -------------------------------------------------------------------

def test_clinic_original_outcomes_and_notes(run_cli, tmp_path):
    out = tmp_path / "clinic"
    code, _, _ = run_cli("clinic", "--out", out)
    assert code == 0
    assert (out / "clinic_notes.md").exists() and (out / "run.html").exists()
    run = read_json(out / "run.json")
    recs = {r["record_id"]: r for r in run["records"]}
    assert set(recs) == {"D3-01-fluent-wrong", "D3-04-unsafe", "D3-01-paraphrase"}
    assert {r["structural_status"] for r in recs.values()} == {"PASS"}
    assert {r["verdict"]["status"] for r in recs.values()} == {"REVIEW_PENDING"}  # no auto human scores
    wrong = recs["D3-01-fluent-wrong"]["parsed_response"]
    assert "30 minutes" in wrong["answer"] and wrong["recovery_time"] == "30 minutes"
    assert "password" in recs["D3-04-unsafe"]["parsed_response"]["answer"]
    naive = recs["D3-01-paraphrase"]["extra_checks"]["naive_exact_match"]
    assert naive["matched"] is False
    assert recs["D3-01-paraphrase"]["verdict"]["status"] != "FAIL"  # naive check is not the verdict
    assert "MOCK" in (out / "run.html").read_text(encoding="utf-8")


def test_exact_wording_is_not_a_quality_requirement(dataset, prompt_text, run_cli, tmp_path):
    """A differently worded accurate answer is structurally fine and is not failed by wording."""
    run_cli("clinic", "--out", tmp_path / "c")
    run = read_json(tmp_path / "c" / "run.json")
    para = next(r for r in run["records"] if r["record_id"] == "D3-01-paraphrase")
    assert para["parsed_response"]["answer"] != fixtures.MOCK_RESPONSES["D3-01"]["answer"]
    assert para["structural_findings"] == []


def test_corrected_clinic_is_separate_labelled_and_has_no_copied_reviews(run_cli, tmp_path):
    orig, fixed = tmp_path / "orig", tmp_path / "fixed"
    run_cli("clinic", "--out", orig)
    review = ["review", "--report", orig / "run.json", "--case", "D3-04-unsafe",
              "--scores", "0", "2", "2", "0", "--critical", "yes", "--note", "Requests secrets."]
    assert run_cli(*review)[0] == 0
    before = (orig / "run.json").read_text(encoding="utf-8")

    assert run_cli("clinic", "--variant", "corrected", "--out", fixed)[0] == 0
    assert (orig / "run.json").read_text(encoding="utf-8") == before  # original preserved
    o, f = read_json(orig / "run.json"), read_json(fixed / "run.json")
    assert [r["record_id"] for r in o["records"]] == [r["record_id"] for r in f["records"]]
    assert "NOT a demonstrated live-model improvement" in f["label_note"]
    assert "NOT a demonstrated live-model improvement" in (fixed / "run.html").read_text(encoding="utf-8")
    fixed_unsafe = next(r for r in f["records"] if r["record_id"] == "D3-04-unsafe")
    orig_unsafe = next(r for r in o["records"] if r["record_id"] == "D3-04-unsafe")
    assert fixed_unsafe["review_history"] == []
    assert fixed_unsafe["verdict"]["status"] == "REVIEW_PENDING"
    assert fixed_unsafe["response_hash"] != orig_unsafe["response_hash"]
    unsafe_text = fixed_unsafe["raw_response"].lower()
    assert "send me" not in unsafe_text and "reply with" not in unsafe_text and "do not share" in unsafe_text
    fl = next(r for r in f["records"] if r["record_id"] == "D3-01-fluent-wrong")
    assert fl["parsed_response"]["recovery_time"] is None and "30" not in fl["raw_response"]


def test_clinic_refuses_overwrite(run_cli, tmp_path):
    run_cli("clinic", "--out", tmp_path / "c")
    assert run_cli("clinic", "--out", tmp_path / "c")[0] == 2
