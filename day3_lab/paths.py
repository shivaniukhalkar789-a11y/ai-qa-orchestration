"""Project file locations used by the Day 3 lab."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CASES_PATH = ROOT / "datasets" / "day3" / "cases.json"
RUBRIC_PATH = ROOT / "rubrics" / "day3" / "rubric.json"
PROMPT_PATH = ROOT / "prompts" / "day3" / "response_v1.txt"
