"""The TF-6 check, scripts/check_test_changes.py (M1).

The goal it protects: code is made to pass the tests; existing tests are never
weakened. New tests, scenarios and test files are always allowed.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from scripts.check_test_changes import (
    REQUIREMENTS,
    SCENARIOS,
    Change,
    fixture_character_names,
    main,
    pyproject_problems,
    python_problems,
    scenario_problems,
    src_problems,
    violations,
)
from tests.support.traceability import ROOT

pytestmark = [pytest.mark.milestone("M1"), pytest.mark.req("TF-6", "TF-5")]


def _code(text: str) -> str:
    return textwrap.dedent(text).lstrip()


# ---------------------------------------------------------------- test modules

TEST_MODULE = _code('''
    """Tests for something."""

    import pytest

    from tests.support.text import stat

    pytestmark = pytest.mark.milestone("M3")

    TOTALS = {"Chris": 23}


    def _helper(value: int) -> int:
        return value + 1


    @pytest.mark.req("OUT-1")
    async def test_chris(make_world) -> None:
        world = await make_world("sample-game")
        reply = await world.run("isla", "partybonus")
        assert stat(reply, "Chris", "CM") == TOTALS["Chris"]
''')


def _problems(new_text: str) -> list[str]:
    return python_problems("tests/test_x.py", TEST_MODULE, new_text)


def test_an_unchanged_module_is_fine() -> None:
    assert _problems(TEST_MODULE) == []


def test_formatting_and_comments_dont_count() -> None:
    reformatted = TEST_MODULE.replace(
        'reply = await world.run("isla", "partybonus")',
        'reply = await world.run(  # the public table\n        "isla", "partybonus"\n    )',
    )
    reformatted = reformatted.replace('"""Tests for something."""', '"""Better words."""')
    assert _problems(reformatted) == []


def test_new_tests_and_imports_can_be_added() -> None:
    added = TEST_MODULE + _code("""


        from tests.support.text import counted


        @pytest.mark.req("OUT-1")
        async def test_everyone_is_counted(make_world) -> None:
            world = await make_world("sample-game")
            assert len(counted(await world.run("isla", "partybonus"))) == 6
    """)
    assert _problems(added) == []


@pytest.mark.parametrize(
    ("description", "old", "new"),
    [
        ("loosened assertion", '== TOTALS["Chris"]', ">= 0"),
        ("changed expected value", 'TOTALS = {"Chris": 23}', 'TOTALS = {"Chris": 22}'),
        (
            "early return",
            '    world = await make_world("sample-game")',
            '    return\n    world = await make_world("sample-game")',
        ),
        (
            "skip decorator",
            '@pytest.mark.req("OUT-1")',
            '@pytest.mark.skip\n@pytest.mark.req("OUT-1")',
        ),
        (
            "xfail decorator",
            '@pytest.mark.req("OUT-1")',
            '@pytest.mark.xfail\n@pytest.mark.req("OUT-1")',
        ),
        ("changed milestone", 'milestone("M3")', 'milestone("M6")'),
        ("changed helper", "return value + 1", "return value"),
        ("removed test", "async def test_chris", "async def _not_a_test_chris"),
    ],
)
def test_changing_existing_code_is_refused(description: str, old: str, new: str) -> None:
    assert old in TEST_MODULE, description
    assert _problems(TEST_MODULE.replace(old, new)), description


@pytest.mark.parametrize(
    ("description", "addition"),
    [
        ("module-level skip", 'pytest.skip("not today", allow_module_level=True)'),
        ("second pytestmark", "pytestmark = pytest.mark.xfail"),
        ("redefined helper", "def _helper(value: int) -> int:\n    return 0"),
        ("redefined import", "def stat(*args: object) -> int:\n    return 23"),
        (
            "autouse fixture",
            "@pytest.fixture(autouse=True)\ndef _quietly(monkeypatch) -> None:\n    pass",
        ),
    ],
)
def test_additions_that_could_affect_existing_tests_are_refused(
    description: str, addition: str
) -> None:
    assert _problems(TEST_MODULE + "\n\n" + addition + "\n"), description


def test_an_unparsable_module_is_refused() -> None:
    assert _problems("def broken(:\n")


# ---------------------------------------------------------------- scenarios

SCENARIO_FILE = _code("""
    # header comment
    catalog:
      entries:
        Test Buff: {kind: item, gives: {CM: 2}}
    scenarios:
      - name: First
        players: [{name: A, has: [Test Buff]}, {name: B}]
        expect: {A: {}, B: {CM: 2}}
""")

SECOND_SCENARIO = """\
  - name: Second
    players: [{name: C}]
    expect: {C: {}}
"""


def test_new_scenarios_and_comments_are_fine() -> None:
    new = SCENARIO_FILE.replace("# header comment", "# a better comment") + SECOND_SCENARIO
    assert scenario_problems(SCENARIO_FILE, new) == []


@pytest.mark.parametrize(
    ("description", "old", "new"),
    [
        ("changed expectation", "B: {CM: 2}", "B: {CM: 3}"),
        ("changed catalog", "gives: {CM: 2}", "gives: {CM: 3}"),
        ("renamed scenario", "name: First", "name: Renamed"),
        ("removed player", ", {name: B}", ""),
    ],
)
def test_changing_existing_scenarios_is_refused(description: str, old: str, new: str) -> None:
    assert old in SCENARIO_FILE, description
    assert scenario_problems(SCENARIO_FILE, SCENARIO_FILE.replace(old, new)), description


def test_duplicate_scenario_names_are_refused() -> None:
    duplicated = SCENARIO_FILE + SCENARIO_FILE[SCENARIO_FILE.index("  - name") :]
    assert scenario_problems(SCENARIO_FILE, duplicated)


# ---------------------------------------------------------------- pyproject.toml

PYPROJECT = _code("""
    [project]
    name = "x"
    dependencies = ["pyyaml"]

    [tool.awt_bonus]
    finished_milestones = ["M1", "M2"]

    [tool.pytest.ini_options]
    addopts = ["--strict-markers"]

    [tool.coverage.run]
    branch = true
""")


def test_finishing_a_milestone_and_other_settings_are_fine() -> None:
    new = PYPROJECT.replace('["M1", "M2"]', '["M1", "M2", "M3"]').replace(
        '["pyyaml"]', '["pyyaml", "rich"]'
    )
    assert pyproject_problems(PYPROJECT, new) == []


@pytest.mark.parametrize(
    ("description", "old", "new"),
    [
        ("unfinished milestone", '["M1", "M2"]', '["M1"]'),
        ("deselected tests", '["--strict-markers"]', '["--strict-markers", "--deselect=tests"]'),
        ("coverage settings", "branch = true", "branch = false"),
        (
            "pytest plugin",
            'dependencies = ["pyyaml"]',
            'dependencies = ["pyyaml"]\n\n[project.entry-points.pytest11]\nx = "awt_bonus.x"',
        ),
    ],
)
def test_changing_what_runs_is_refused(description: str, old: str, new: str) -> None:
    assert pyproject_problems(PYPROJECT, PYPROJECT.replace(old, new)), description


# ---------------------------------------------------------------- change sets

OLD = {
    "tests/commands/test_output.py": TEST_MODULE,
    "tests/fixtures/sample-game.yaml": "clock: 2026-09-25T20:00:00Z\n",
    "tests/support/world.py": "X = 1\n",
    "tests/conftest.py": "X = 1\n",
    "tests/COVERAGE.md": "old\n",
    SCENARIOS: SCENARIO_FILE,
    "scripts/check_test_changes.py": "X = 1\n",
    ".github/workflows/ci.yml": "name: CI\n",
    "pyproject.toml": PYPROJECT,
    "src/awt_bonus/engine/compute.py": "X = 1\n",
}

type ChangeSpec = list[tuple[str, str, str | None]]
"""(git status letter, path, new text or None for a deletion)."""


def _check(changes: ChangeSpec) -> list[str]:
    """Run ``violations`` on these changes, starting from OLD."""
    new = dict(OLD)
    for status, path, text in changes:
        if status == "D":
            new.pop(path, None)
        else:
            new[path] = text or ""
    return violations([Change(status, path) for status, path, _ in changes], OLD.get, new.get)


@pytest.mark.parametrize(
    ("description", "changes"),
    [
        ("new test file", [("A", "tests/commands/test_new.py", "def test_x() -> None: ...\n")]),
        ("new fixture", [("A", "tests/fixtures/new.yaml", "clock: x\n")]),
        ("regenerated coverage table", [("M", "tests/COVERAGE.md", "new\n")]),
        ("bot code", [("M", "src/awt_bonus/engine/compute.py", "X = 2\n")]),
        ("new workflow", [("A", ".github/workflows/deploy.yml", "name: Deploy\n")]),
        (
            "new test in an existing file",
            [
                (
                    "M",
                    "tests/commands/test_output.py",
                    TEST_MODULE + "\n\ndef test_y() -> None: ...\n",
                )
            ],
        ),
        (
            "new scenario",
            [("M", SCENARIOS, SCENARIO_FILE + SECOND_SCENARIO)],
        ),
    ],
)
def test_allowed_changes(description: str, changes: ChangeSpec) -> None:
    assert _check(changes) == [], description


@pytest.mark.parametrize(
    ("description", "changes"),
    [
        ("changed fixture", [("M", "tests/fixtures/sample-game.yaml", "clock: 2027\n")]),
        ("deleted fixture", [("D", "tests/fixtures/sample-game.yaml", None)]),
        ("changed harness", [("M", "tests/support/world.py", "X = 2\n")]),
        ("changed conftest", [("M", "tests/conftest.py", "X = 2\n")]),
        ("new conftest", [("A", "tests/commands/conftest.py", "X = 1\n")]),
        ("new root conftest", [("A", "conftest.py", "X = 1\n")]),
        ("new pytest.ini", [("A", "pytest.ini", "[pytest]\n")]),
        ("deleted test file", [("D", "tests/commands/test_output.py", None)]),
        ("changed check script", [("M", "scripts/check_test_changes.py", "X = 2\n")]),
        ("changed workflow", [("M", ".github/workflows/ci.yml", "name: Other\n")]),
        ("deleted workflow", [("D", ".github/workflows/ci.yml", None)]),
        ("sitecustomize", [("A", "src/sitecustomize.py", "X = 1\n")]),
        (
            "unfinished milestone",
            [("M", "pyproject.toml", PYPROJECT.replace('["M1", "M2"]', '["M1"]'))],
        ),
        (
            "weakened test",
            [("M", "tests/commands/test_output.py", TEST_MODULE.replace("== TOTALS", "!= TOTALS"))],
        ),
        (
            "changed scenario",
            [("M", SCENARIOS, SCENARIO_FILE.replace("B: {CM: 2}", "B: {CM: 3}"))],
        ),
    ],
)
def test_refused_changes(description: str, changes: ChangeSpec) -> None:
    assert _check(changes), description


def test_refused_changes_are_allowed_with_a_requirements_change() -> None:
    changes: ChangeSpec = [
        ("M", "tests/fixtures/sample-game.yaml", "clock: 2027\n"),
        ("M", "tests/commands/test_output.py", TEST_MODULE.replace("== TOTALS", ">= TOTALS")),
        ("M", REQUIREMENTS, "# Requirements, v1.2\n"),
    ]
    assert _check(changes) == []


# ---------------------------------------------------------------- the bot's code

NAMES = {"Crateris", "Hero Aldric"}


@pytest.mark.parametrize(
    ("description", "code"),
    [
        ("imports pytest", "import pytest\n"),
        ("imports the tests", "from tests.support.world import World\n"),
        ("imports hypothesis", "from hypothesis import given\n"),
        ("checks for pytest", 'import os\nRUNNING = "PYTEST_CURRENT_TEST" in os.environ\n'),
        ("checks sys.modules", 'import sys\nRUNNING = "pytest" in sys.modules\n'),
        ("defines a pytest hook", "def pytest_collection_modifyitems(items):\n    pass\n"),
        (
            "names a test character",
            'def total(name):\n    return 12 if name == "Crateris" else 0\n',
        ),
        ("names a character in a variable", "Crateris = 12\n"),
    ],
)
def test_the_bots_code_mustnt_refer_to_the_tests(description: str, code: str) -> None:
    assert src_problems({"src/awt_bonus/x.py": code}, NAMES), description


def test_docstrings_and_comments_may_mention_examples() -> None:
    code = _code('''
        """The notice, e.g. "Crateris isn't your current character"."""


        def notice(name: str) -> str:  # e.g. Crateris
            """Like the section 9 example for Crateris."""
            return f"{name} isn't your current character"
    ''')
    assert src_problems({"src/awt_bonus/x.py": code}, NAMES) == []


def test_the_fixture_names_are_read_from_the_fixtures() -> None:
    names = fixture_character_names(ROOT / "tests" / "fixtures")
    assert {"Crateris", "Ioseph", "Elowen", "Hero Aldric", "Gwyneth"} <= names
    assert "Mal" not in names  # too short to be distinctive


def test_the_bots_code_today_is_clean() -> None:
    files = {
        p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8")
        for p in (ROOT / "src").rglob("*.py")
    }
    assert src_problems(files, fixture_character_names(ROOT / "tests" / "fixtures")) == []


# ---------------------------------------------------------------- end to end, with git


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    if shutil.which("git") is None:
        pytest.skip("needs git")
    (tmp_path / "tests" / "fixtures").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text(TEST_MODULE, encoding="utf-8")
    (tmp_path / "tests" / "fixtures" / "world.yaml").write_text(
        "players:\n  - characters: [{name: Crateris}]\n", encoding="utf-8"
    )
    (tmp_path / "src" / "bot.py").write_text("X = 1\n", encoding="utf-8")
    (tmp_path / REQUIREMENTS).write_text("# Requirements\n", encoding="utf-8")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "ci@example.invalid")
    _git(tmp_path, "config", "user.name", "CI")
    _git(tmp_path, "config", "core.autocrlf", "false")
    _commit(tmp_path, "base")
    _git(tmp_path, "tag", "base")
    return tmp_path


def _run(repo: Path) -> int:
    return main(["--base", "base", "--root", str(repo)])


def test_a_commit_that_weakens_a_test_fails(repo: Path) -> None:
    path = repo / "tests" / "test_a.py"
    path.write_text(TEST_MODULE.replace("== TOTALS", ">= TOTALS"), encoding="utf-8")
    _commit(repo, "weaken a test")
    assert _run(repo) == 1


def test_a_commit_that_adds_tests_passes(repo: Path) -> None:
    path = repo / "tests" / "test_a.py"
    path.write_text(TEST_MODULE + "\n\ndef test_more() -> None: ...\n", encoding="utf-8")
    (repo / "tests" / "test_b.py").write_text("def test_b() -> None: ...\n", encoding="utf-8")
    _commit(repo, "add tests")
    assert _run(repo) == 0


def test_a_commit_that_changes_a_test_with_the_requirements_passes(repo: Path) -> None:
    path = repo / "tests" / "test_a.py"
    path.write_text(TEST_MODULE.replace("== TOTALS", ">= TOTALS"), encoding="utf-8")
    (repo / REQUIREMENTS).write_text("# Requirements\n\nOUT-1 changed.\n", encoding="utf-8")
    _commit(repo, "OUT-1: change the rule and its test")
    assert _run(repo) == 0


def test_bot_code_that_special_cases_test_data_fails(repo: Path) -> None:
    (repo / "src" / "bot.py").write_text('SPECIAL = "Crateris"\n', encoding="utf-8")
    _commit(repo, "special-case the sample game")
    assert _run(repo) == 1
