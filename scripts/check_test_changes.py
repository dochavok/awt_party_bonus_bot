"""The test-change rule in CI (requirements TF-5, TF-6).

Goal: code is made to pass the tests; tests are never weakened to pass the code.

Part 1 (unless the same change edits the requirements document) fails a change that:
  - changes or removes an existing test function, or other module-level code, in a
    test module (compared as parsed code, so formatting and comments don't count);
  - adds module-level code to a test module that could affect existing tests: a
    new ``pytestmark``, an autouse fixture, a bare statement, or a name that
    redefines one already there;
  - changes or removes an existing scenario, or the scenario catalog, in
    tests/scenarios/engine-scenarios.yaml;
  - changes or deletes any other file under tests/ (fixtures, the harness in
    tests/support/, snapshots), or adds or changes any ``conftest.py``;
  - removes a finished milestone, or changes the pytest or coverage settings or the
    pytest plugins registered in pyproject.toml;
  - changes this script, or changes or removes a CI workflow.
Adding new tests, new scenarios and new test files is always allowed.
tests/COVERAGE.md is exempt: it's documentation generated from the tests (TF-3).

Part 2 (always) fails if the bot's code in src/ refers to the tests: importing
pytest, Hypothesis or the tests package, mentioning pytest, defining pytest hooks,
or naming characters from the test fixtures. ``sitecustomize.py`` and
``usercustomize.py`` files are refused anywhere.

Usage: uv run python scripts/check_test_changes.py --base <git ref>
Compares <base> with HEAD. On GitHub Actions it also writes a job summary.
"""

import argparse
import ast
import os
import re
import subprocess
import sys
import tomllib
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = "party-bonus-bot-requirements.md"
COVERAGE = "tests/COVERAGE.md"
SCENARIOS = "tests/scenarios/engine-scenarios.yaml"
THIS_SCRIPT = "scripts/check_test_changes.py"
WORKFLOWS = ".github/workflows/"
PYTEST_CONFIG_FILES = {"pytest.ini", "setup.cfg", "tox.ini"}
STARTUP_HOOK_FILES = {"sitecustomize.py", "usercustomize.py"}

RULE = """\
The test-change rule (TF-5): a failing test means the code is wrong. A test may only
change after a human confirms it's wrong, and then only in this order:
  1. confirm with a human that the test is wrong;
  2. fix the requirements document ({requirements});
  3. fix the test to match (commit steps 2 and 3 together, naming the requirement);
  4. fix the code until the test passes.
Adding new tests, new scenarios and new test files is always allowed."""

Reader = Callable[[str], str | None]
"""Reads a file's text at one version; None if it doesn't exist there."""


@dataclass(frozen=True)
class Change:
    status: str
    """git's status letter: A (added), M (modified), D (deleted), T (type changed)."""
    path: str


# ---------------------------------------------------------------- part 1: test changes


def violations(changes: Iterable[Change], old: Reader, new: Reader) -> list[str]:
    """Problems with a change set; none if it also edits the requirements document."""
    changes = list(changes)
    if any(c.path == REQUIREMENTS for c in changes):
        return []
    problems: list[str] = []
    for change in changes:
        problems += _change_problems(change, old, new)
    return problems


def _change_problems(change: Change, old: Reader, new: Reader) -> list[str]:
    path, added, deleted = change.path, change.status == "A", change.status == "D"
    name = PurePosixPath(path).name

    if path == COVERAGE:
        return []
    if name in STARTUP_HOOK_FILES and not deleted:
        return [f"{path}: startup hook files aren't allowed"]
    if name == "conftest.py":
        return [f"{path}: {'added' if added else 'deleted' if deleted else 'changed'} conftest.py"]
    if path in PYTEST_CONFIG_FILES:
        return [f"{path}: pytest settings file {'added' if added else 'changed'}"]
    if path == THIS_SCRIPT and not added:
        return [f"{path}: the test-change check itself changed"]
    if path.startswith(WORKFLOWS) and not added:
        return [f"{path}: CI workflow {'deleted' if deleted else 'changed'}"]
    if path == "pyproject.toml" and not (added or deleted):
        return pyproject_problems(old(path) or "", new(path) or "")
    if not path.startswith("tests/") or added:
        return []
    if deleted:
        return [f"{path}: deleted"]
    old_text, new_text = old(path) or "", new(path) or ""
    if path == SCENARIOS:
        return scenario_problems(old_text, new_text)
    if path.endswith(".py") and not path.startswith("tests/support/"):
        return python_problems(path, old_text, new_text)
    return [f"{path}: changed"]


def _is_docstring(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _body(module: ast.Module) -> list[ast.stmt]:
    """Module-level statements, without the module docstring."""
    body = list(module.body)
    return body[1:] if body and _is_docstring(body[0]) else body


def _bound_names(statement: ast.stmt) -> set[str]:
    if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return {statement.name}
    if isinstance(statement, ast.Import | ast.ImportFrom):
        return {(alias.asname or alias.name).split(".")[0] for alias in statement.names}
    if isinstance(statement, ast.TypeAlias):
        return {statement.name.id}
    targets: list[ast.expr] = []
    if isinstance(statement, ast.Assign):
        targets = list(statement.targets)
    elif isinstance(statement, ast.AnnAssign | ast.AugAssign):
        targets = [statement.target]
    return {n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)}


def _is_autouse_fixture(statement: ast.stmt) -> bool:
    if not isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    for decorator in statement.decorator_list:
        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if (
                    keyword.arg == "autouse"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    return True
    return False


def _describe(path: str, statement: ast.stmt) -> str:
    names = sorted(_bound_names(statement))
    what = ", ".join(names) if names else f"the statement at line {statement.lineno}"
    return f"{path}::{what}"


def python_problems(path: str, old_text: str, new_text: str) -> list[str]:
    """Existing code in a test module must be unchanged; new tests may be added."""
    try:
        old_body, new_body = _body(ast.parse(old_text)), _body(ast.parse(new_text))
    except SyntaxError as error:
        return [f"{path}: can't be parsed ({error.msg})"]

    problems: list[str] = []
    new_dumps = Counter(ast.dump(s) for s in new_body)
    for statement in old_body:
        dump = ast.dump(statement)
        if new_dumps[dump]:
            new_dumps[dump] -= 1
        else:
            problems.append(f"{_describe(path, statement)}: changed or removed")

    old_names = set().union(*(_bound_names(s) for s in old_body)) if old_body else set()
    old_dumps = Counter(ast.dump(s) for s in old_body)
    for statement in new_body:
        dump = ast.dump(statement)
        if old_dumps[dump]:
            old_dumps[dump] -= 1
            continue
        names = _bound_names(statement)
        if not names:
            problems.append(f"{_describe(path, statement)}: new module-level statement")
        elif "pytestmark" in names:
            problems.append(f"{path}::pytestmark: added")
        elif names & old_names:
            problems.append(f"{path}::{', '.join(sorted(names & old_names))}: redefined")
        elif _is_autouse_fixture(statement):
            problems.append(f"{_describe(path, statement)}: new autouse fixture")
    return problems


def scenario_problems(old_text: str, new_text: str) -> list[str]:
    """Existing scenarios and the scenario catalog must be unchanged; new ones may be added."""
    old: dict[str, Any] = yaml.safe_load(old_text) or {}
    new: dict[str, Any] = yaml.safe_load(new_text) or {}
    problems = [
        f"{SCENARIOS}: `{key}` changed"
        for key in old
        if key != "scenarios" and old[key] != new.get(key)
    ]
    new_scenarios = new.get("scenarios") or []
    names = [s.get("name") for s in new_scenarios]
    for name, count in Counter(names).items():
        if count > 1:
            problems.append(f"{SCENARIOS}: scenario {name!r} appears {count} times")
    by_name = {s.get("name"): s for s in new_scenarios}
    for scenario in old.get("scenarios") or []:
        name = scenario.get("name")
        if name not in by_name:
            problems.append(f"{SCENARIOS}: scenario {name!r} removed or renamed")
        elif by_name[name] != scenario:
            problems.append(f"{SCENARIOS}: scenario {name!r} changed")
    return problems


def pyproject_problems(old_text: str, new_text: str) -> list[str]:
    """Finished milestones may only be added; test settings and plugins must not change."""
    old, new = tomllib.loads(old_text), tomllib.loads(new_text)
    old_tool, new_tool = old.get("tool", {}), new.get("tool", {})
    problems = []
    for section in ["pytest", "coverage"]:
        if old_tool.get(section) != new_tool.get(section):
            problems.append(f"pyproject.toml: [tool.{section}] changed")
    old_plugins = old.get("project", {}).get("entry-points", {}).get("pytest11")
    new_plugins = new.get("project", {}).get("entry-points", {}).get("pytest11")
    if old_plugins != new_plugins:
        problems.append("pyproject.toml: pytest plugins (entry-points.pytest11) changed")

    old_awt, new_awt = old_tool.get("awt_bonus", {}), new_tool.get("awt_bonus", {})
    removed = set(old_awt.get("finished_milestones", [])) - set(
        new_awt.get("finished_milestones", [])
    )
    if removed:
        problems.append(f"pyproject.toml: finished milestones removed: {sorted(removed)}")
    for key in (set(old_awt) | set(new_awt)) - {"finished_milestones"}:
        if old_awt.get(key) != new_awt.get(key):
            problems.append(f"pyproject.toml: [tool.awt_bonus] {key} changed")
    return problems


# ---------------------------------------------------------------- part 2: the bot's code

_TEST_MODULES = {"pytest", "_pytest", "hypothesis", "tests"}


def fixture_character_names(fixtures: Path) -> set[str]:
    """Character names from the world fixtures, long enough to be distinctive."""
    names: set[str] = set()
    for path in fixtures.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for player in data.get("players") or []:
            for character in player.get("characters") or []:
                name = str(character.get("name", ""))
                if len(name) >= 4:
                    names.add(name)
    return names


def _docstring_nodes(tree: ast.Module) -> set[int]:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and _is_docstring(first):
                found.add(id(first.value))
    return found


def src_problems(files: Mapping[str, str], forbidden_names: Iterable[str]) -> list[str]:
    """Problems if the bot's code refers to the tests or the test data."""
    names = sorted(set(forbidden_names))
    name_pattern = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b") if names else None
    problems = []
    for path, text in sorted(files.items()):
        try:
            tree = ast.parse(text)
        except SyntaxError as error:
            problems.append(f"{path}: can't be parsed ({error.msg})")
            continue
        docstrings = _docstring_nodes(tree)
        for node in ast.walk(tree):
            line = getattr(node, "lineno", "?")
            if isinstance(node, ast.Import | ast.ImportFrom):
                modules = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                for module in modules:
                    if module.split(".")[0] in _TEST_MODULES:
                        problems.append(f"{path}:{line}: imports {module}")
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name.startswith("pytest_"):
                    problems.append(f"{path}:{line}: defines pytest hook {node.name}")
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
            ):
                if "pytest" in node.value.lower():
                    problems.append(f"{path}:{line}: mentions pytest")
                if name_pattern and (match := name_pattern.search(node.value)):
                    problems.append(f"{path}:{line}: names test character {match.group()!r}")
            elif isinstance(node, ast.Name) and name_pattern and name_pattern.fullmatch(node.id):
                problems.append(f"{path}:{line}: names test character {node.id!r}")
    return problems


# ---------------------------------------------------------------- git and reporting


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


def changed_files(root: Path, base: str) -> list[Change]:
    changes = []
    for line in _git(root, "diff", "--name-status", "--no-renames", base, "HEAD").splitlines():
        status, _, path = line.partition("\t")
        changes.append(Change(status[:1], path))
    return changes


def reader(root: Path, ref: str) -> Reader:
    def read(path: str) -> str | None:
        result = subprocess.run(
            ["git", "show", f"{ref}:{path}"], cwd=root, capture_output=True, text=True
        )
        return result.stdout if result.returncode == 0 else None

    return read


def _summary(base: str, changes: list[Change], problems: list[str]) -> str:
    requirements_changed = any(c.path == REQUIREMENTS for c in changes)
    test_changes = [c for c in changes if c.path.startswith("tests/") and c.path != COVERAGE]
    lines = [
        "## Test-change rule (TF-6)",
        "",
        f"Compared `{base}` with `HEAD`.",
        f"Requirements document changed: **{'yes' if requirements_changed else 'no'}**",
        "",
    ]
    if test_changes:
        lines += ["Files under `tests/` in this change:", ""]
        lines += [f"- `{c.status}` `{c.path}`" for c in test_changes]
        lines.append("")
    if problems:
        lines += ["**Broken:**", ""] + [f"- {p}" for p in problems]
    else:
        lines.append("**OK**")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--base", required=True, help="git ref to compare HEAD with")
    parser.add_argument("--root", type=Path, default=ROOT, help="the repository (default: this)")
    args = parser.parse_args(argv)
    root: Path = args.root

    changes = changed_files(root, args.base)
    problems = violations(changes, reader(root, args.base), reader(root, "HEAD"))
    src_files = {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in (root / "src").rglob("*.py")
    }
    problems += src_problems(src_files, fixture_character_names(root / "tests" / "fixtures"))
    problems += [
        f"{path}: startup hook files aren't allowed"
        for path in _git(root, "ls-files").splitlines()
        if PurePosixPath(path).name in STARTUP_HOOK_FILES
    ]

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(_summary(args.base, changes, problems))

    if not problems:
        print(f"Test-change rule: OK (compared {args.base}..HEAD)")
        return 0
    print("Test-change rule broken:")
    for problem in problems:
        print(f"  {problem}")
    print()
    print(RULE.format(requirements=REQUIREMENTS))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
