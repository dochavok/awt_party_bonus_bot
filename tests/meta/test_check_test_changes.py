"""The TF-6 CI check (scripts/check_test_changes.py) (M1)."""

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.check_test_changes import REQUIREMENTS, main, violations

pytestmark = [pytest.mark.milestone("M1"), pytest.mark.req("TF-6", "TF-5")]


def test_adding_new_test_files_is_allowed() -> None:
    assert violations([("A", "tests/commands/test_new.py"), ("A", "tests/fixtures/new.yaml")]) == []


def test_modifying_a_test_without_the_requirements_is_refused() -> None:
    assert violations([("M", "tests/commands/test_output.py")]) == [
        "modified: tests/commands/test_output.py"
    ]


def test_deleting_a_test_without_the_requirements_is_refused() -> None:
    assert violations([("D", "tests/engine/test_properties.py")]) == [
        "deleted: tests/engine/test_properties.py"
    ]


@pytest.mark.parametrize(
    "path",
    [
        "tests/scenarios/engine-scenarios.yaml",
        "tests/fixtures/sample-game.yaml",
        "tests/conftest.py",
        "tests/support/fakes.py",
    ],
)
def test_scenarios_fixtures_and_harness_count_as_tests(path: str) -> None:
    assert violations([("M", path)]) == [f"modified: {path}"]


def test_a_rename_counts_as_deleting_the_old_file() -> None:
    changes = [("D", "tests/commands/test_output.py"), ("A", "tests/commands/test_out.py")]
    assert violations(changes) == ["deleted: tests/commands/test_output.py"]


def test_changing_tests_with_the_requirements_is_allowed() -> None:
    changes = [("M", "tests/commands/test_output.py"), ("M", REQUIREMENTS)]
    assert violations(changes) == []


def test_the_generated_coverage_table_is_exempt() -> None:
    assert violations([("M", "tests/COVERAGE.md")]) == []


def test_changes_outside_tests_are_allowed() -> None:
    assert violations([("M", "src/awt_bonus/engine/compute.py"), ("M", "README.md")]) == []


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    if shutil.which("git") is None:
        pytest.skip("needs git")

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "ci@example.invalid")
    git("config", "user.name", "CI")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test_a() -> None: ...\n")
    (tmp_path / REQUIREMENTS).write_text("# Requirements\n")
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("tag", "base")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _commit(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", message], cwd=repo, check=True, capture_output=True
    )


def test_the_script_fails_a_real_commit_that_edits_a_test(repo: Path) -> None:
    (repo / "tests" / "test_a.py").write_text("def test_a() -> None: pass\n")
    _commit(repo, "weaken a test")
    assert main(["--base", "base"]) == 1


def test_the_script_passes_a_real_commit_that_adds_a_test(repo: Path) -> None:
    (repo / "tests" / "test_b.py").write_text("def test_b() -> None: ...\n")
    _commit(repo, "add a test")
    assert main(["--base", "base"]) == 0


def test_the_script_passes_a_test_edit_with_a_requirements_edit(repo: Path) -> None:
    (repo / "tests" / "test_a.py").write_text("def test_a() -> None: pass\n")
    (repo / REQUIREMENTS).write_text("# Requirements\n\nChanged.\n")
    _commit(repo, "HV-4: change the rule and its test")
    assert main(["--base", "base"]) == 0
