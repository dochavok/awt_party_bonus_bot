"""Requirement IDs, DM questions and milestones, read from the documents (TF-3, TF-4).

Tests are tagged with these, and the tags are checked against the documents so a
test can never point at a requirement that doesn't exist.
"""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "party-bonus-bot-requirements.md"
DM_QUESTIONS = ROOT / "dm-rule-questions.md"
COVERAGE = ROOT / "tests" / "COVERAGE.md"

_TABLE_ROW = re.compile(r"^\|\s*([A-Z]{2,3}-\d+[a-z]?)\s*\|(.*)\|\s*$")
_RULE = re.compile(r"^(\d+)\.\s+\*\*")
_QUESTION = re.compile(r"^##\s+(Q\d+)\.")
_MILESTONE = re.compile(r"^\|\s*\*\*(M\d+):")


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    priority: str
    """M, S or C. Rows with no priority column (NF) and the section 4 rules count as M."""


@cache
def requirements() -> dict[str, Requirement]:
    """Every requirement: the IDs in the tables, the section 4 rules ("4.1"...) and "9.1"."""
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
    found["9.1"] = Requirement("9.1", "The sample game (section 9.1)", "M")
    return found


@cache
def dm_questions() -> frozenset[str]:
    """The DM rule question numbers, e.g. "Q7"."""
    lines = DM_QUESTIONS.read_text(encoding="utf-8").splitlines()
    return frozenset(m.group(1) for line in lines if (m := _QUESTION.match(line)))


@cache
def milestones() -> tuple[str, ...]:
    """The milestones in section 17, in order: ("M1", ..., "M6")."""
    lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    return tuple(m.group(1) for line in lines if (m := _MILESTONE.match(line)))
