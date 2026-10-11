"""Fixtures for the Day 3 lab tests.

Nothing from tests/day2/conftest.py is needed here (it is not visible to this
folder anyway), and the Day 3 lab never calls the API under app/, so no shared
fixture had to be moved to tests/conftest.py. All tests here are offline.
"""

import pytest

from day3_lab import cli, data
from day3_lab.paths import PROMPT_PATH


@pytest.fixture(scope="session")
def dataset() -> dict:
    return data.load_dataset()


@pytest.fixture(scope="session")
def rubric() -> dict:
    return data.load_rubric()


@pytest.fixture()
def prompt_text() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@pytest.fixture()
def run_cli(capsys):
    """Run `python -m day3_lab ...` in-process; returns (exit_code, stdout, stderr)."""

    def call(*argv):
        code = cli.main([str(a) for a in argv])
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return call


@pytest.fixture()
def mock_run(run_cli, tmp_path):
    """A saved mock run of D3-01; returns the run.json path."""
    out = tmp_path / "demo"
    code, _, err = run_cli("run", "--mode", "mock", "--case", "D3-01", "--out", out)
    assert code == 0, err
    return out / "run.json"

