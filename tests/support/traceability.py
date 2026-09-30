"""Requirement IDs and milestones, read from the requirements document (TF-3, TF-4).

Tests are tagged with these, and the tags are checked against the document so a
test can never point at a requirement that doesn't exist. Tests are also tagged with
the DM rule questions they depend on, but dm-rule-questions.md is documentation
for the DMs, so nothing checks those tags against it (TF-3).
"""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "party-bonus-bot-requirements.md"
COVERAGE = ROOT / "tests" / "COVERAGE.md"

_TABLE_ROW = re.compile(r"^\|\s*([A-Z]{2,3}-\d+[a-z]?)\s*\|(.*)\|\s*$")
_RULE = re.compile(r"^(\d+)\.\s+\*\*")
_MILESTONE = re.compile(r"^\|\s*\*\*(M\d+):")
_EXAMPLE = re.compile(r"^### (9\.\d+) (.+)$")


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    priority: str
    """M, S or C. Rows with no priority column (NF) and the section 4 rules count as M."""


@cache
def requirements() -> dict[str, Requirement]:
    """Every requirement: the IDs in the tables, the section 4 rules ("4.1"...) and the
    section 9 worked examples ("9.1" the sample game, "9.2"...)."""
    found: dict[str, Requirement] = {}
    section = ""
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line
            continue
        row = _TABLE_ROW.match(line)
        if row:
            req_id, rest = row.groups()
            cells = [cell.strip() for cell in rest.split("|")]
            priority = cells[-1] if len(cells) >= 2 and cells[-1] in {"M", "S", "C"} else "M"
            found[req_id] = Requirement(req_id, cells[0], priority)
            continue
        rule = _RULE.match(line)
        if rule and section.startswith("## 4."):
            rule_id = f"4.{rule.group(1)}"
            found[rule_id] = Requirement(rule_id, line, "M")
            continue
        example = _EXAMPLE.match(line)
        if example and section.startswith("## 9."):
            example_id, title = example.groups()
            found[example_id] = Requirement(example_id, f"{title} (section {example_id})", "M")
    return found


@cache
def milestones() -> tuple[str, ...]:
    """The milestones in section 17, in order: ("M1", ..., "M6")."""
    lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    return tuple(m.group(1) for line in lines if (m := _MILESTONE.match(line)))
