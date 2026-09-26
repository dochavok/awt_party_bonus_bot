"""The requirement coverage table, tests/COVERAGE.md (TF-3).

The file has two parts:
  - "Not automated": written by hand. Each must-have requirement with no
    automated test is listed here with the reason and how it's checked instead.
  - "Tests per requirement": generated from the tests' ``req`` and ``dm`` markers,
    between the BEGIN/END GENERATED lines. Regenerate it with:
        uv run pytest --collect-only -q --write-coverage
"""

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from tests.support.traceability import COVERAGE, requirements

BEGIN = "<!-- BEGIN GENERATED: uv run pytest --collect-only -q --write-coverage -->"
END = "<!-- END GENERATED -->"

_NOT_AUTOMATED_ROW = re.compile(r"^\|\s*([A-Z]{2,3}-\d+[a-z]?|4\.\d+|9\.1)\s*\|")


@dataclass(frozen=True)
class TaggedTest:
    nodeid: str
    """Without parameters, e.g. tests/commands/test_output.py::test_x."""
    milestone: str
    reqs: tuple[str, ...]
    questions: tuple[str, ...]


def _sort_key(req_id: str) -> tuple[int, str, int, str]:
    """Document order: section 4 rules, then 9.1, then IDs by prefix and number."""
    if req_id.startswith("4."):
        return (0, "", int(req_id[2:]), "")
    if req_id == "9.1":
        return (1, "", 0, "")
    prefix, _, number = req_id.partition("-")
    digits = re.match(r"\d+", number)
    return (2, prefix, int(digits.group()) if digits else 0, number)


def render(tests: Iterable[TaggedTest]) -> str:
    """The generated part of COVERAGE.md."""
    by_req: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    by_question: dict[str, set[str]] = defaultdict(set)
    for test in tests:
        for req_id in test.reqs:
            by_req[req_id][test.nodeid].add(test.milestone)
        for question in test.questions:
            by_question[question].add(test.nodeid)

    lines = [
        BEGIN,
        "",
        "## Tests per requirement",
        "",
        "Parametrized tests are listed once. *Not automated* means the requirement is in",
        "the table above instead.",
        "",
        "| ID | Pri | Milestones | Tests |",
        "|---|---|---|---|",
    ]
    for req_id in sorted(requirements(), key=_sort_key):
        req = requirements()[req_id]
        found = by_req.get(req_id, {})
        milestones = ", ".join(sorted(set().union(*found.values()))) or "-"
        tests_cell = "<br>".join(f"`{nodeid}`" for nodeid in sorted(found)) or "*Not automated*"
        lines.append(f"| {req_id} | {req.priority} | {milestones} | {tests_cell} |")

    lines += [
        "",
        "## Tests per DM rule question",
        "",
        "When a DM answers a question, these are the tests to revisit (TF-5, from step 2).",
        "",
        "| Question | Tests |",
        "|---|---|",
    ]
    for question in sorted(by_question, key=lambda q: int(q[1:])):
        tests_cell = "<br>".join(f"`{nodeid}`" for nodeid in sorted(by_question[question]))
        lines.append(f"| {question} | {tests_cell} |")
    lines += ["", END]
    return "\n".join(lines) + "\n"


def current_text() -> str:
    return COVERAGE.read_text(encoding="utf-8")


def generated_part(text: str) -> str:
    start, end = text.index(BEGIN), text.index(END) + len(END)
    return text[start:end] + "\n"


def with_generated_part(text: str, generated: str) -> str:
    start, end = text.index(BEGIN), text.index(END) + len(END)
    return text[:start] + generated.rstrip("\n") + text[end:]


def listed_ids(text: str) -> set[str]:
    """The requirement IDs that start table rows in ``text``."""
    return {m.group(1) for line in text.splitlines() if (m := _NOT_AUTOMATED_ROW.match(line))}


def not_automated(text: str) -> set[str]:
    """The requirement IDs in the hand-written tables (not automated, or partly)."""
    return listed_ids(text[: text.index(BEGIN)])


def partly_automated(text: str) -> set[str]:
    """The requirement IDs in the hand-written "Partly automated" table."""
    return listed_ids(text[text.index("### Partly automated") : text.index(BEGIN)])
