"""Command line for the Day 3 lab."""

import argparse
import sys
import time
import webbrowser
from pathlib import Path

from day3_lab import clinic, data, fixtures, runstore
from day3_lab.paths import CASES_PATH, PROMPT_PATH, RUBRIC_PATH
from day3_lab.providers import LiveProvider, MockProvider, ProviderError
from day3_lab.runner import case_items, evaluate_item


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def _load_inputs():
    dataset = data.load_dataset()
    rubric = data.load_rubric()
    problems = data.validate_dataset(dataset) + data.validate_rubric(rubric, dataset)
    if problems:
        raise runstore.StoreError("input data invalid: " + "; ".join(problems))
    return dataset, rubric


def cmd_validate_data(args) -> int:
    try:
        dataset = data.load_dataset()
        rubric = data.load_rubric()
    except (OSError, ValueError) as exc:
        return _fail(f"cannot read inputs: {exc}")
    problems = data.validate_dataset(dataset) + data.validate_rubric(rubric, dataset)
    missing = sorted(set(c["case_id"] for c in dataset["cases"]) - set(fixtures.MOCK_RESPONSES))
    if missing:
        problems.append(f"no mock fixture for {missing}")
    if problems:
        for problem in problems:
            print(f"INVALID: {problem}", file=sys.stderr)
        return 1
    print(f"OK: {len(dataset['cases'])} cases, unique IDs, dataset {dataset['dataset_version']}")
    print(f"OK: rubric version {rubric['version']} is consistent")
    return 0


def _guard_out(out: str):
    out_dir = Path(out)
    if (out_dir / "run.json").exists() or (out_dir / "run.html").exists():
        raise runstore.StoreError(f"{out} already contains a run; choose a new --out directory")
    return out_dir


def cmd_run(args) -> int:
    try:
        out_dir = _guard_out(args.out)
        dataset, rubric = _load_inputs()
        cases = dataset["cases"]
        if args.case:
            cases = [c for c in cases if c["case_id"] == args.case]
            if not cases:
                return _fail(f"unknown case {args.case!r}")
        if args.mode == "mock":
            provider = MockProvider(fixtures.MOCK_RESPONSES)
        else:
            try:
                provider = LiveProvider.from_env()
            except ProviderError as exc:
                return _fail(str(exc))
        prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
        started = time.perf_counter()
        records = [evaluate_item(provider, item, prompt_text) for item in case_items(cases)]
        run = runstore.build_run(
            mode=args.mode, model=provider.model, records=records, prompt_path=PROMPT_PATH,
            cases_path=CASES_PATH, rubric=rubric, rubric_path=RUBRIC_PATH,
            elapsed=time.perf_counter() - started,
        )
        runstore.write_run(run, out_dir, new=True)
    except (runstore.StoreError, OSError) as exc:
        return _fail(str(exc))
    for record in run["records"]:
        print(f"{record['record_id']}: structural {record['structural_status']} -> {record['verdict']['status']}")
    print(f"saved {out_dir / 'run.json'} and {out_dir / 'run.html'} ({run['label']})")
    return 0


def cmd_clinic(args) -> int:
    try:
        out_dir = _guard_out(args.out)
        dataset, rubric = _load_inputs()
        cases_by_id = {c["case_id"]: c for c in dataset["cases"]}
        prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
        records, elapsed = clinic.run_clinic(cases_by_id, prompt_text, args.variant)
        run = runstore.build_run(
            mode="mock", model=None, records=records, prompt_path=PROMPT_PATH,
            cases_path=CASES_PATH, rubric=rubric, rubric_path=RUBRIC_PATH, elapsed=elapsed,
            extra={
                "clinic_variant": args.variant,
                "label_note": clinic.CORRECTED_NOTE if args.variant == "corrected" else None,
            },
        )
        runstore.write_run(run, out_dir, new=True)
        (out_dir / "clinic_notes.md").write_text(
            clinic.clinic_notes(run, args.variant, str(out_dir / "run.json")), encoding="utf-8"
        )
    except (runstore.StoreError, OSError) as exc:
        return _fail(str(exc))
    for record in run["records"]:
        print(f"{record['record_id']}: structural {record['structural_status']} -> {record['verdict']['status']}")
    print(f"saved run.json, run.html and clinic_notes.md in {out_dir} (MOCK)")
    return 0


def cmd_open(args) -> int:
    path = Path(args.html)
    if not path.is_file():
        return _fail(f"{path} not found")
    webbrowser.open(path.resolve().as_uri())
    print(f"opened {path}")
    return 0


def cmd_review(args) -> int:
    try:
        result = runstore.add_review(
            args.report, args.case, args.scores, args.critical, args.note,
            reviewer=args.reviewer, expected_hash=args.response_hash,
        )
    except runstore.StoreError as exc:
        return _fail(str(exc))
    print(f"{args.case}: {result['status']} ({'; '.join(result['reasons'])})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m day3_lab", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate-data", help="validate dataset and rubric").set_defaults(func=cmd_validate_data)

    run = sub.add_parser("run", help="run cases and save run.json / run.html")
    run.add_argument("--mode", choices=["mock", "live"], required=True)
    run.add_argument("--case", help="one case ID, e.g. D3-01 (default: all)")
    run.add_argument("--out", required=True, help="new output directory")
    run.set_defaults(func=cmd_run)

    cl = sub.add_parser("clinic", help="controlled failure clinic (MOCK fixtures)")
    cl.add_argument("--out", required=True)
    cl.add_argument("--variant", choices=["original", "corrected"], default="original")
    cl.set_defaults(func=cmd_clinic)

    op = sub.add_parser("open", help="open a static report in the browser")
    op.add_argument("html")
    op.set_defaults(func=cmd_open)

    rv = sub.add_parser("review", help="record a human assessment")
    rv.add_argument("--report", required=True, help="path to run.json")
    rv.add_argument("--case", required=True, help="record ID (case ID, or clinic fixture ID)")
    rv.add_argument("--scores", nargs=4, type=int, required=True,
                    metavar=("CORRECTNESS", "RELEVANCE", "COMPLETENESS", "SAFETY"))
    rv.add_argument("--critical", choices=["yes", "no"], required=True)
    rv.add_argument("--note", required=True)
    rv.add_argument("--reviewer", help="reviewer identifier (default: OS user name)")
    rv.add_argument("--response-hash", help="optional hash you reviewed; must match")
    rv.set_defaults(func=cmd_review)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
