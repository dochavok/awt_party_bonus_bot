"""Test harness plugin: milestone markers (TF-4), traceability tags (TF-3) and fixtures.

Every test must be marked with:
  - ``@pytest.mark.milestone("M3")``: the milestone that implements what it checks;
  - ``@pytest.mark.req("HV-4", ...)``: the requirement IDs it checks;
  - ``@pytest.mark.dm("Q7", ...)`` if it depends on a DM rule question.

Tests for milestones not listed in ``[tool.awt_bonus] finished_milestones`` in
pyproject.toml run as expected failures. Tests for finished milestones must pass.

``--expect-xfail-cause=NotImplementedError`` fails the run if any expected failure
was caused by something else, or if any test passed unexpectedly. M1 uses it to
show that every test fails only because nothing is implemented yet.
"""

import os
import tomllib
from collections import Counter
from collections.abc import AsyncIterator, Awaitable, Callable, Generator
from pathlib import Path

import pytest
from hypothesis import HealthCheck, settings

from tests.support.traceability import ROOT, dm_questions, milestones, requirements
from tests.support.world import World, load_world

# ---------------------------------------------------------------- Hypothesis (TS-3)

settings.register_profile(
    "ci", max_examples=1000, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)
settings.register_profile(
    "dev", max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


# ---------------------------------------------------------------- milestones and tags


def finished_milestones() -> frozenset[str]:
    """The single list of finished milestones (TF-4), from pyproject.toml."""
    with (ROOT / "pyproject.toml").open("rb") as f:
        config = tomllib.load(f)
    return frozenset(config["tool"]["awt_bonus"]["finished_milestones"])


_CAUSES = pytest.StashKey[Counter[str]]()
_OTHER_CAUSES = pytest.StashKey[list[str]]()
_XPASSED = pytest.StashKey[list[str]]()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--expect-xfail-cause",
        metavar="EXCEPTION",
        default=None,
        help="Fail the run if an expected failure had another cause, or a test passed "
        "unexpectedly (e.g. NotImplementedError during M1).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.stash[_CAUSES] = Counter()
    config.stash[_OTHER_CAUSES] = []
    config.stash[_XPASSED] = []


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    known_requirements = requirements()
    known_questions = dm_questions()
    known_milestones = milestones()
    finished = finished_milestones()
    problems: list[str] = []

    for name in finished:
        if name not in known_milestones:
            problems.append(f"pyproject.toml: finished milestone {name!r} isn't in section 17")

    for item in items:
        milestone_marks = list(item.iter_markers("milestone"))
        if not milestone_marks:
            problems.append(f"{item.nodeid}: no milestone marker (TF-4)")
            continue
        milestone = milestone_marks[0].args[0]
        if milestone not in known_milestones:
            problems.append(f"{item.nodeid}: unknown milestone {milestone!r}")

        req_ids = [arg for mark in item.iter_markers("req") for arg in mark.args]
        if not req_ids:
            problems.append(f"{item.nodeid}: no req marker naming its requirement IDs (TF-3)")
        for req_id in req_ids:
            if req_id not in known_requirements:
                problems.append(f"{item.nodeid}: unknown requirement {req_id!r}")
        for mark in item.iter_markers("dm"):
            for question in mark.args:
                if question not in known_questions:
                    problems.append(f"{item.nodeid}: unknown DM question {question!r}")

        if milestone not in finished:
            item.add_marker(
                pytest.mark.xfail(
                    reason=f"milestone {milestone} isn't finished (TF-4)", strict=False
                )
            )

    if problems:
        raise pytest.UsageError("Test tagging problems:\n  " + "\n  ".join(problems))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    report = yield
    if hasattr(report, "wasxfail"):
        if report.skipped and call.excinfo is not None:
            cause = call.excinfo.typename
            item.config.stash[_CAUSES][cause] += 1
            expected = item.config.getoption("--expect-xfail-cause")
            if expected is not None and cause != expected:
                item.config.stash[_OTHER_CAUSES].append(f"{item.nodeid} ({cause})")
        elif report.passed and call.when == "call":
            item.config.stash[_XPASSED].append(item.nodeid)
    return report


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    config = terminalreporter.config
    causes = config.stash[_CAUSES]
    if causes:
        summary = ", ".join(f"{name}: {count}" for name, count in causes.most_common())
        terminalreporter.write_line(f"Expected failures by cause: {summary}")
    if config.getoption("--expect-xfail-cause") is not None:
        for nodeid in config.stash[_OTHER_CAUSES]:
            terminalreporter.write_line(f"UNEXPECTED XFAIL CAUSE: {nodeid}", red=True)
        for nodeid in config.stash[_XPASSED]:
            terminalreporter.write_line(f"UNEXPECTED PASS: {nodeid}", red=True)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    if config.getoption("--expect-xfail-cause") is None:
        return
    if config.stash[_OTHER_CAUSES] or config.stash[_XPASSED]:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


# ---------------------------------------------------------------- fixtures (TF-2a)


@pytest.fixture
async def make_world(tmp_path: Path) -> AsyncIterator[Callable[[str], Awaitable[World]]]:
    """Load a fixture from tests/fixtures/ into a fresh temporary database.

    Call it inside the test: ``world = await make_world("sample-game")``.
    """
    worlds: list[World] = []

    async def make(name: str) -> World:
        world = await load_world(name, tmp_path / name)
        worlds.append(world)
        return world

    yield make
    for world in worlds:
        await world.store.close()
