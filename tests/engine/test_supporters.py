"""Supporting sit-outs in the engine: SE-7, rule 4.11, section 11 step 0, and TS-3.

These use the scenario file's test catalog, with Support allowed while sitting out
for Guild Champion and Guild Legend (CT-5), added here so the scenario file itself
doesn't change (TF-6). A supporting sit-out is ``PresentPlayer.supporting`` on a
player with an active sit-out (section 11).
"""

import copy
from collections.abc import Collection, Sequence
from dataclasses import replace
from typing import Any

import pytest
from hypothesis import given

from awt_bonus.catalog import Catalog, parse_catalog
from awt_bonus.engine import PartyReport, compute
from awt_bonus.ids import StatId, UserId
from tests.engine.scenarios import (
    PlayerSpec,
    build_inputs,
    catalog_data,
    scenario_catalog,
    stat_parents,
)
from tests.engine.test_properties import players

pytestmark = [pytest.mark.milestone("M10")]

ALLOWED = ["Guild Champion", "Guild Legend"]


def supporter_catalog_data() -> dict[str, Any]:
    data = copy.deepcopy(dict(catalog_data()))
    data["guilds"]["Guild"]["from_roles"][0]["while_sitting_out"] = list(ALLOWED)
    return data


def supporter_catalog() -> Catalog:
    return parse_catalog(supporter_catalog_data())


def run(
    party: Sequence[PlayerSpec], supporting: Collection[str], catalog: Catalog | None = None
) -> PartyReport:
    """Run the engine with the named players' sit-outs marked as supporting."""
    inputs = build_inputs(party)
    present = [
        replace(p, supporting=True) if party[n].name in supporting else p
        for n, p in enumerate(inputs.present_players)
    ]
    return compute(
        present,
        inputs.player_roles,
        inputs.character_entries,
        inputs.character_guilds,
        catalog or supporter_catalog(),
    )


def totals(report: PartyReport, name: str) -> dict[str, int]:
    recipient = report.recipient(name)
    return {stat: n for stat, n in recipient.totals.items() if n}


def gives_from(report: PartyReport, giver: int) -> list[str]:
    return sorted(g.bonus for g in report.gives if g.giver == UserId(giver))


def supporting(report: PartyReport) -> dict[str, bool]:
    return {n.name: n.supporting for n in report.not_counted}


# ---------------------------------------------------------------- SE-7: Support only


@pytest.mark.req("SE-7", "4.11", "HV-3")
def test_a_supporter_gives_support_to_each_counted_player_and_nothing_else() -> None:
    party = [
        PlayerSpec(
            name="Gwen",
            roles=("Guild Legend",),
            has=("Test Buff", "Aura of Hope", "Inspiring Presence"),
            sitout=True,
        ),
        PlayerSpec(name="Ash"),
        PlayerSpec(name="Bea", has=("Test Focus",)),
    ]
    report = run(party, supporting={"Gwen"})

    assert {r.name for r in report.recipients} == {"Ash", "Bea"}, "Gwen is still not counted"
    assert totals(report, "Ash") == {"CM": 2, "CR": 2, **_subtypes(2)}
    assert totals(report, "Bea") == {"CM": 2}
    assert gives_from(report, 1) == ["Support"], "only Support, not Gwen's character's entries"
    assert supporting(report) == {"Gwen": True}


@pytest.mark.req("SE-7", "OUT-3")
def test_a_supporters_give_shows_their_guild_rank_role() -> None:
    party = [
        PlayerSpec(name="Gwen", roles=("Guild Champion", "Moderator"), sitout=True),
        PlayerSpec(name="Ash"),
    ]
    report = run(party, supporting={"Gwen"})

    [give] = [g for g in report.gives if g.giver == UserId(1)]
    assert give.bonus == "Support"
    assert give.giver_rank == ("Guild Champion",)


@pytest.mark.req("SE-7", "4.11")
@pytest.mark.parametrize("roles", [(), ("Guild Vanguard",), ("Junior Adventurer", "Moderator")])
def test_a_supporter_without_an_allowed_role_gives_nothing(roles: tuple[str, ...]) -> None:
    party = [
        PlayerSpec(name="Vera", roles=roles, has=("Test Buff",), sitout=True),
        PlayerSpec(name="Ash"),
    ]
    report = run(party, supporting={"Vera"})

    assert totals(report, "Ash") == {}
    assert gives_from(report, 1) == []
    assert supporting(report) == {"Vera": False}, "shown as plainly sitting out (SE-4)"


@pytest.mark.req("SE-7", "CT-5")
def test_with_no_roles_allowed_in_the_catalog_a_supporter_gives_nothing() -> None:
    party = [
        PlayerSpec(name="Gwen", roles=("Guild Legend",), sitout=True),
        PlayerSpec(name="Ash"),
    ]
    report = run(party, supporting={"Gwen"}, catalog=scenario_catalog())

    assert totals(report, "Ash") == {}
    assert gives_from(report, 1) == []
    assert supporting(report) == {"Gwen": False}


@pytest.mark.req("SE-7", "SE-2")
def test_a_plain_sitout_with_an_allowed_role_still_gives_nothing() -> None:
    party = [
        PlayerSpec(name="Gwen", roles=("Guild Legend",), has=("Test Buff",), sitout=True),
        PlayerSpec(name="Ash"),
    ]
    report = run(party, supporting=set())

    assert totals(report, "Ash") == {}
    assert gives_from(report, 1) == []
    assert supporting(report) == {"Gwen": False}


@pytest.mark.req("SE-7", "HV-3", "4.1", "4.2")
def test_supporters_and_counted_support_givers_each_count() -> None:
    party = [
        PlayerSpec(name="Gwen", roles=("Guild Legend",), sitout=True),
        PlayerSpec(name="Hal", roles=("Guild Champion", "Guild Legend"), sitout=True),
        PlayerSpec(name="Ivo", roles=("Guild Vanguard",)),
        PlayerSpec(name="Ash"),
    ]
    report = run(party, supporting={"Gwen", "Hal"})

    assert totals(report, "Ash") == {"CM": 6}, "Gwen, Hal and Ivo: +2 each"
    assert totals(report, "Ivo") == {"CM": 4}, "Gwen and Hal; never Ivo's own Support"
    assert gives_from(report, 2) == ["Support"], "Hal gives Support once, however many roles"


@pytest.mark.req("SE-7", "SE-5")
def test_a_supporter_with_no_character_still_gives_support() -> None:
    party = [
        PlayerSpec(name="Gwen", roles=("Guild Legend",), no_character=True, sitout=True),
        PlayerSpec(name="Ash"),
    ]
    report = run(party, supporting={"Gwen"})

    assert totals(report, "Ash") == {"CM": 2}
    assert report.no_character == (), "Gwen isn't counted, so isn't listed as no character"


@pytest.mark.req("SE-7", "4.11")
def test_a_supporter_never_receives_anything() -> None:
    party = [
        PlayerSpec(name="Gwen", roles=("Guild Legend",), sitout=True),
        PlayerSpec(name="Ash", has=("Test Buff",), roles=("Guild Veteran",)),
    ]
    report = run(party, supporting={"Gwen"})

    assert "Gwen" not in {r.name for r in report.recipients}
    assert totals(report, "Ash") == {"CM": 2}, "from Gwen; Ash's own bonuses go to allies"


@pytest.mark.req("SE-7", "SE-6")
def test_a_bot_marked_supporting_is_still_ignored() -> None:
    party = [
        PlayerSpec(name="Jukebox", roles=("Guild Legend",), bot=True, sitout=True),
        PlayerSpec(name="Ash"),
    ]
    report = run(party, supporting={"Jukebox"})

    assert totals(report, "Ash") == {}
    assert report.not_counted == ()


# ---------------------------------------------------------------- TS-3: properties


@pytest.mark.req("TS-3", "SE-7", "4.11")
@given(players())
def test_supporting_adds_exactly_support_for_each_allowed_supporter(
    party: list[PlayerSpec],
) -> None:
    sitting_out = {p.name for p in party if p.sitout and not p.bot}
    allowed = {p.name for p in party if p.name in sitting_out and set(p.roles) & set(ALLOWED)}
    plain = run(party, supporting=set())
    supported = run(party, supporting=sitting_out)

    assert [r.name for r in supported.recipients] == [r.name for r in plain.recipients]
    extra = 2 * len(allowed)
    for before, after in zip(plain.recipients, supported.recipients, strict=True):
        for stat in stat_parents():
            expected = before.totals.get(stat, 0) + (extra if stat == StatId("CM") else 0)
            assert after.totals.get(stat, 0) == expected, f"{after.name}'s {stat}"
    assert supporting(supported) == {n: n in allowed for n in sitting_out}
    supporter_ids = {UserId(n) for n, p in enumerate(party, start=1) if p.name in allowed}
    for give in supported.gives:
        if give.giver in supporter_ids:
            assert give.bonus == "Support", f"a supporter gave {give.bonus}"


def _subtypes(cr: int) -> dict[str, int]:
    """The CR subtypes, which each include CR (rule 4.7)."""
    return {s: cr for s, parent in stat_parents().items() if parent == StatId("CR")}
