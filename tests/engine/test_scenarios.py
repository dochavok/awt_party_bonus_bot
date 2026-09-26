"""The engine scenarios (TS-1, TS-2): every scenario in tests/scenarios/engine-scenarios.yaml.

Each scenario becomes one test. Its requirement and DM-question tags come from
the scenario's `rule` text, plus the extra tags below for dependencies the text
doesn't state. The scenario file itself is never edited to make code pass (TF-5).
"""

import re
from collections.abc import Mapping
from typing import Any

import pytest

from awt_bonus.engine import PartyReport
from awt_bonus.ids import UserId
from tests.engine.scenarios import (
    EngineInputs,
    PlayerSpec,
    actual_totals,
    expected_totals,
    run,
    scenario_catalog,
    scenarios,
)

# TS-2's edge cases, by scenario name.
EDGE_CASES = {
    "Cult High Priest gives by the recipient's level",  # no level; level exactly 10
    "No character set up still gives Support, and receives",
    "Everyone sitting out gives an empty party",
    "Empty channel",
    "Same skill from two characters stacks",
    "Bots in the channel are ignored",
    "Inspiring Presence doesn't stack",
    "Seraph's Affection replaces Nuyaru's Love",
    "A retired entry still counts for characters who have it",
}

# Dependencies the `rule` text doesn't state.
EXTRA_TAGS: dict[str, list[str]] = {
    "Support from five Guild rank holders": ["4.1", "4.2", "HV-3"],
    "Ordinary Cult members give nothing": ["Q2"],
    "Two High Priests (bad data) still count once": ["Q2"],
    "Helping Hands v2.0 replaces Helping Hands; alone it gives nothing": ["Q7"],
    "No character set up still gives Support, and receives": ["HV-3"],
    "No character set up misses guild-only and holder-only bonuses": ["Q5"],
    "Everyone sitting out gives an empty party": ["SE-2", "4.11"],
    "Empty channel": ["SE-1"],
    "Full sample game (requirements section 9.1)": ["Q1", "Q2", "Q3", "Q6"],
}

_REQ_ID = re.compile(r"\b[A-Z]{2,3}-\d+[a-z]?\b")
_RULE = re.compile(r"(?<![\d.])4\.(\d+)\b")
_QUESTION = re.compile(r"\bQ\d+\b")


def tags(scenario: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """(requirement IDs, DM questions) for one scenario."""
    text = " ".join([str(scenario.get("rule", "")), *EXTRA_TAGS.get(scenario["name"], [])])
    reqs = ["TS-1"]
    reqs += _REQ_ID.findall(text)
    reqs += [f"4.{n}" for n in _RULE.findall(text)]
    if "9.1" in text:
        reqs.append("9.1")
    if scenario["name"] in EDGE_CASES:
        reqs.append("TS-2")
    questions = _QUESTION.findall(text)
    return sorted(set(reqs)), sorted(set(questions))


def _params() -> list[Any]:
    params = []
    for scenario in scenarios():
        reqs, questions = tags(scenario)
        marks = [pytest.mark.milestone("M2"), pytest.mark.req(*reqs)]
        if questions:
            marks.append(pytest.mark.dm(*questions))
        params.append(pytest.param(scenario, id=scenario["name"], marks=marks))
    return params


def _name_of(inputs: EngineInputs, user_id: UserId) -> str:
    return inputs.names[user_id]


@pytest.mark.parametrize("scenario", _params())
def test_scenario(scenario: Mapping[str, Any]) -> None:
    players = [PlayerSpec.from_yaml(p) for p in scenario["players"]]
    report, inputs = run(players, scenario_catalog())

    _check_who_is_counted(scenario, players, report, inputs)
    _check_totals(scenario, report)
    _check_not_applied(scenario, report, inputs)
    _check_conditional(scenario, report, inputs)
    _check_effects(scenario, report, inputs)


def _check_who_is_counted(
    scenario: Mapping[str, Any],
    players: list[PlayerSpec],
    report: PartyReport,
    inputs: EngineInputs,
) -> None:
    counted = {r.name for r in report.recipients}
    assert counted == set(scenario["expect"]), "counted players"

    if "not_counted" in scenario:
        assert {n.name for n in report.not_counted} == set(scenario["not_counted"])
    if "no_character" in scenario:
        no_character = {_name_of(inputs, u) for u in report.no_character}
        assert no_character == set(scenario["no_character"])

    # Bots are ignored and never listed (SE-6).
    bots = {UserId(n) for n, p in enumerate(players, start=1) if p.bot}
    listed = (
        {r.user_id for r in report.recipients}
        | {n.user_id for n in report.not_counted}
        | set(report.no_character)
        | {g.giver for g in report.gives}
    )
    assert not bots & listed, "bots must never appear in the report"


def _check_totals(scenario: Mapping[str, Any], report: PartyReport) -> None:
    for name, expect in scenario["expect"].items():
        assert actual_totals(report, name) == expected_totals(expect), f"totals for {name}"


def _check_not_applied(
    scenario: Mapping[str, Any], report: PartyReport, inputs: EngineInputs
) -> None:
    for name, lines in scenario.get("not_applied", {}).items():
        recipient = report.recipient(name)
        actual = {
            (
                report.give(n.give).entry,
                _name_of(inputs, report.give(n.give).giver),
                n.reason.value,
            )
            for n in recipient.not_applied
        }
        for line in lines:
            wanted = (line["entry"], line["from"], line["reason"])
            assert wanted in actual, f"{name} should have not-applied {wanted}; has {actual}"


def _check_conditional(
    scenario: Mapping[str, Any], report: PartyReport, inputs: EngineInputs
) -> None:
    for name, lines in scenario.get("conditional", {}).items():
        recipient = report.recipient(name)
        actual = sorted(
            (
                report.give(c.give).entry,
                _name_of(inputs, report.give(c.give).giver),
                dict(c.amounts),
                c.condition,
            )
            for c in recipient.conditional
        )
        wanted = sorted(
            (line["entry"], line["from"], dict(line["gives"]), line["condition"]) for line in lines
        )
        assert actual == wanted, f"conditional bonuses for {name}"


def _check_effects(scenario: Mapping[str, Any], report: PartyReport, inputs: EngineInputs) -> None:
    for effect in scenario.get("effects", []):
        receivers: dict[str, int] = {}
        for recipient in report.recipients:
            count = sum(
                1
                for give_id in recipient.effects
                if report.give(give_id).effect == effect["text"]
                and _name_of(inputs, report.give(give_id).giver) == effect["from"]
            )
            if count:
                receivers[recipient.name] = count
        assert set(receivers) == set(effect["to"]), f"who receives {effect['text']!r}"
        assert all(count == 1 for count in receivers.values()), (
            f"{effect['text']!r} from {effect['from']} must be received once each: {receivers}"
        )
