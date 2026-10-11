"""Static HTML report. Every value from the run is HTML-escaped."""

import json
from html import escape as esc

STYLE = """
body{font-family:system-ui,Segoe UI,sans-serif;margin:0 auto;max-width:60rem;padding:1rem 1rem 3rem;
color:#1b1f23;background:#fff;line-height:1.45}
.banner{background:#fff3cd;border:1px solid #d4a72c;padding:.6rem .9rem;border-radius:6px;margin:.6rem 0}
.live{background:#e7f1ff;border-color:#4a8be0}
table{border-collapse:collapse;width:100%;margin:.4rem 0}
th,td{border:1px solid #d0d7de;padding:.3rem .5rem;text-align:left;vertical-align:top;font-size:.9rem}
th{background:#f6f8fa;width:12rem}
pre{background:#f6f8fa;border:1px solid #d0d7de;padding:.6rem;overflow-x:auto;white-space:pre-wrap}
section{border-top:2px solid #d0d7de;margin-top:1.4rem;padding-top:.6rem}
.v{font-weight:700;padding:.1rem .5rem;border-radius:4px;border:1px solid}
.PASS{color:#116329;background:#dafbe1}.FAIL,.ERROR{color:#82071e;background:#ffebe9}
.REVIEW_PENDING{color:#7d4e00;background:#fff8c5}
code{background:#f6f8fa;padding:0 .2rem}
@media(prefers-color-scheme:dark){body{background:#0d1117;color:#e6edf3}
th{background:#161b22}pre,code{background:#161b22}th,td,pre,section{border-color:#30363d}
.banner{background:#3a2e05;border-color:#9e6a03}.live{background:#0c2d6b;border-color:#1f6feb}
.PASS{color:#7ee787;background:#0f2d17}.FAIL,.ERROR{color:#ffa198;background:#3d0f0f}
.REVIEW_PENDING{color:#f2cc60;background:#3a2e05}}
"""


def _rows(pairs) -> str:
    return "<table>" + "".join(
        f"<tr><th>{esc(str(k))}</th><td>{v}</td></tr>" for k, v in pairs
    ) + "</table>"


def _pre(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
    return f"<pre>{esc(text)}</pre>"


def _list(items) -> str:
    return "<ul>" + "".join(f"<li>{esc(str(i))}</li>" for i in items) + "</ul>"


def _record_html(record: dict, run_path_hint: str) -> str:
    v = record.get("verdict", {"status": "REVIEW_PENDING", "reasons": []})
    ctx = record["approved_context"]
    parts = [
        f'<section id="{esc(record["record_id"])}">',
        f'<h2>{esc(record["record_id"])} &middot; {esc(record["category"])} '
        f'<span class="v {esc(v["status"])}">{esc(v["status"])}</span></h2>',
    ]
    if record.get("note"):
        parts.append(f'<p><strong>Teaching note:</strong> {esc(record["note"])}</p>')
    parts.append(
        _rows(
            [
                ("Dataset case", esc(record["case_id"])),
                ("Requirement IDs (training labels)", esc(", ".join(record["requirement_ids"]))),
                ("Question", esc(record["question"])),
                ("Device", esc(str(ctx["device"]))),
                ("Service status (context)", esc(ctx["service_status"])),
                ("Recovery time (context)", esc(str(ctx["recovery_time"]))),
                ("Guidance (context)", esc(ctx["guidance"])),
                ("Expected behaviour", _list(record["expected_behaviour"])),
                ("Prohibited behaviour", _list(record["prohibited_behaviour"])),
            ]
        )
    )
    parts.append("<h3>Response</h3>")
    if record.get("provider_error"):
        parts.append(_rows([("Provider error", esc(json.dumps(record["provider_error"])))]))
    if record.get("raw_response") is not None:
        parts.append("<p>Raw response (evidence, unmodified):</p>" + _pre(record["raw_response"]))
    if record.get("parsed_response") is not None:
        parts.append("<p>Parsed response:</p>" + _pre(record["parsed_response"]))
    findings = record.get("structural_findings", [])
    parts.append(
        _rows(
            [
                ("Structural check", esc(record["structural_status"])),
                (
                    "Structural findings",
                    _list(f'{f["kind"]} {f["path"]}: {f["message"]}' for f in findings)
                    if findings
                    else "none",
                ),
                ("Response hash", esc(str(record["response_hash"]))),
                ("Elapsed seconds", esc(str(record["elapsed_seconds"]))),
                ("Token usage", esc(json.dumps(record["token_usage"])) if record["token_usage"] else "not reported"),
            ]
        )
    )
    parts.append(
        "<p><em>Structural PASS means the shape is valid. It is not evidence that the "
        "answer is accurate or safe.</em></p>"
    )
    naive = record.get("extra_checks", {}).get("naive_exact_match")
    if naive:
        parts.append(
            "<h3>Naive exact-string comparison (separate, not a verdict)</h3>"
            + _rows(
                [
                    ("Matched reference sentence", esc(str(naive["matched"]))),
                    ("Reference", esc(naive["reference_answer"])),
                    ("Warning", esc(naive["warning"])),
                ]
            )
        )
    parts.append(
        "<h3>Decision</h3>"
        + _rows(
            [
                ("Verdict", f'<span class="v {esc(v["status"])}">{esc(v["status"])}</span>'),
                ("Reasons", _list(v["reasons"])),
                ("Human assessment", esc(record["human_assessment"]["status"])),
            ]
        )
    )
    history = record.get("review_history", [])
    if history:
        rows = "".join(
            "<tr>"
            f"<td>{esc(r['reviewer'])}</td><td>{esc(r['timestamp'])}</td>"
            f"<td>{esc(json.dumps(r['scores']))}</td><td>{esc(str(r['critical']))}</td>"
            f"<td>{esc(r['note'])}</td><td>{esc(r['response_hash'][:12])}</td></tr>"
            for r in history
        )
        parts.append(
            "<h3>Review history</h3><table><tr><th>Reviewer</th><th>Time</th><th>Scores</th>"
            f"<th>Critical</th><th>Note</th><th>Bound hash</th></tr>{rows}</table>"
        )
    elif record.get("raw_response") is not None and not record.get("structural_findings"):
        parts.append(
            "<p>Enter a review: <code>"
            + esc(
                f'python -m day3_lab review --report {run_path_hint} --case '
                f'{record["record_id"]} --scores C R P S --critical no --note "..."'
            )
            + "</code> (scores: correctness relevance completeness safety).</p>"
        )
    parts.append("</section>")
    return "".join(parts)


def render_html(run: dict) -> str:
    banners = "".join(
        f'<div class="banner{" live" if run["mode"] == "live" else ""}">{esc(c)}</div>'
        for c in run["caveats"]
    )
    if run.get("label_note"):
        banners += f'<div class="banner">{esc(run["label_note"])}</div>'
    counts = {}
    for record in run["records"]:
        status = record.get("verdict", {}).get("status", "REVIEW_PENDING")
        counts[status] = counts.get(status, 0) + 1
    meta = [
        ("Run ID", run["run_id"]),
        ("Timestamp (UTC)", run["timestamp"]),
        ("Mode", f'{run["mode"]} ({run["label"]})'),
        ("Model", run["model"] if run["model"] else "null (no model; fixed mock responses)"),
        ("Commit", run["commit"]),
        ("Working tree dirty", run["dirty"]),
        ("Prompt hash", run["prompt_hash"]),
        ("Dataset hash", run["dataset_hash"]),
        ("Rubric version", run["rubric_version"]),
        ("Total elapsed seconds", run["total_elapsed_seconds"]),
        ("Verdict counts", json.dumps(counts, sort_keys=True)),
    ]
    hint = "run.json"
    body = "".join(_record_html(r, hint) for r in run["records"])
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Day 3 response evaluation - {esc(run['run_id'])}</title>"
        f"<style>{STYLE}</style></head><body>"
        f"<h1>Day 3 response evaluation {esc('[MOCK]' if run['mode'] == 'mock' else '[LIVE]')}</h1>"
        f"{banners}{_rows([(k, esc(str(v))) for k, v in meta])}{body}"
        "<p><small>Classroom response assessment only; not a production release decision. "
        "Fictional training data.</small></p></body></html>"
    )
