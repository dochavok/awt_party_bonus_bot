"""The coverage table, tests/COVERAGE.md (TF-3): complete and up to date (M1)."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.coverage import (
    current_text,
    generated_part,
    not_automated,
    partly_automated,
)
from tests.support.traceability import ROOT, requirements

pytestmark = pytest.mark.milestone("M1")

_ROW = re.compile(r"^\|\s*(\S+)\s*\|\s*([MSC])\s*\|\s*([^|]*)\|\s*(.*)\|\s*$")


def _generated_rows() -> dict[str, str]:
    """Requirement ID -> the Tests cell of the generated table."""
    rows = {}
    for line in generated_part(current_text()).splitlines():
        match = _ROW.match(line)
        if match:
            rows[match.group(1)] = match.group(4).strip()
    return rows


@pytest.mark.req("TF-3")
def test_the_generated_part_is_up_to_date(tmp_path: Path) -> None:
    fresh = tmp_path / "COVERAGE.md"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", f"--write-coverage={fresh}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert fresh.read_text(encoding="utf-8") == current_text(), (
        "tests/COVERAGE.md is out of date: run `uv run pytest --collect-only -q --write-coverage`"
    )


@pytest.mark.req("TF-3")
def test_every_requirement_is_in_the_table() -> None:
    assert set(_generated_rows()) == set(requirements())


@pytest.mark.req("TF-3")
def test_every_must_have_has_a_test_or_a_stated_reason() -> None:
    listed = not_automated(current_text())
    missing = [
        req_id
        for req_id, tests in _generated_rows().items()
        if requirements()[req_id].priority == "M"
        and tests == "*Not automated*"
        and req_id not in listed
    ]
    assert not missing, f"must-have requirements with no test and no stated reason: {missing}"


@pytest.mark.req("TF-3")
def test_the_not_automated_tables_name_real_requirements() -> None:
    unknown = not_automated(current_text()) - set(requirements())
    assert not unknown


@pytest.mark.req("TF-3")
def test_not_automated_rows_really_have_no_tests_unless_partly_automated() -> None:
    text = current_text()
    rows = _generated_rows()
    tested_but_listed = [
        req_id
        for req_id in not_automated(text) - partly_automated(text)
        if rows.get(req_id) != "*Not automated*"
    ]
    assert not tested_but_listed, f"listed as not automated but have tests: {tested_but_listed}"
