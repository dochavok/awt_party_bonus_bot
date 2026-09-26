"""Property tests (TS-3): rules that must hold for every party.

Parties are generated at random from the scenario file's test catalog: any mix of
entries, guild memberships, Guild rank roles, levels, sit-outs, bots and players
with no character. (The engine doesn't enforce one-holder entries, HV-6, so
generated parties may hold them twice, as bad data could.)
"""

from collections import Counter
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from awt_bonus.engine import PartyReport
from awt_bonus.ids import StatId, UserId
from tests.engine.scenarios import PlayerSpec, catalog_data, run, scenario_catalog, stat_parents

pytestmark = [pytest.mark.milestone("M2")]

ENTRIES = sorted(catalog_data()["entries"])
GUILDS = sorted(g for g, spec in catalog_data()["guilds"].items() if spec["membership"] == "open")
GUILD_ROLES = sorted(catalog_data()["guilds"]["Guild"]["roles"])
OTHER_ROLES = ["Moderator", "Music Lover"]


@st.composite
def players(draw: Any, min_size: int = 0, max_size: int = 8) -> list[PlayerSpec]:
    count = draw(st.integers(min_value=min_size, max_value=max_size))
    party = []
    for number in range(count):
        party.append(
            PlayerSpec(
                name=f"P{number}",
                has=tuple(draw(st.lists(st.sampled_from(ENTRIES), max_size=6, unique=True))),
                guilds=tuple(draw(st.lists(st.sampled_from(GUILDS), max_size=3, unique=True))),
                roles=tuple(draw(st.lists(st.sampled_from(GUILD_ROLES + OTHER_ROLES), max_size=2))),
                level=draw(st.none() | st.integers(min_value=1, max_value=75)),
                sitout=draw(st.integers(0, 4)) == 0,
                bot=draw(st.integers(0, 9)) == 0,
                no_character=draw(st.integers(0, 6)) == 0,
            )
        )
    return party


def _totals(report: PartyReport) -> dict[str, dict[StatId, int]]:
    return {
        r.name: {stat: r.totals.get(stat, 0) for stat in stat_parents()} for r in report.recipients
    }


@pytest.mark.req("TS-3", "4.2", "4.3")
@given(players())
def test_nobody_receives_their_own_bonus_unless_the_entry_includes_the_giver(
    party: list[PlayerSpec],
) -> None:
    report, _ = run(party, scenario_catalog())
    for recipient in report.recipients:
        received = [a.give for a in recipient.applied] + [c.give for c in recipient.conditional]
        received += list(recipient.effects)
        for give_id in received:
            give = report.give(give_id)
            if give.giver == recipient.user_id:
                assert give.includes_giver, f"{recipient.name} received own {give.bonus}"


@pytest.mark.req("TS-3", "4.4")
@given(players())
def test_a_bonus_that_doesnt_stack_counts_at_most_once_per_recipient(
    party: list[PlayerSpec],
) -> None:
    report, _ = run(party, scenario_catalog())
    for recipient in report.recipients:
        counts = Counter(
            report.give(a.give).bonus for a in recipient.applied if not report.give(a.give).stacks
        )
        assert all(n == 1 for n in counts.values()), f"{recipient.name}: {counts}"


@pytest.mark.req("TS-3", "4.7", "OUT-3", "OUT-3a")
@given(players())
def test_every_total_equals_the_sum_of_its_breakdown_lines(party: list[PlayerSpec]) -> None:
    report, _ = run(party, scenario_catalog())
    parents = stat_parents()
    for recipient in report.recipients:
        for stat, parent in parents.items():
            lines = sum(a.amounts.get(stat, 0) for a in recipient.applied)
            from_parent = recipient.totals.get(parent, 0) if parent is not None else 0
            assert recipient.totals.get(stat, 0) == lines + from_parent, f"{recipient.name} {stat}"


@pytest.mark.req("TS-3", "4.12")
@given(players())
def test_conditional_bonuses_are_never_in_totals(party: list[PlayerSpec]) -> None:
    report, _ = run(party, scenario_catalog())
    for recipient in report.recipients:
        for applied in recipient.applied:
            assert report.give(applied.give).condition is None


@pytest.mark.req("TS-3", "4.7")
@given(players())
def test_a_subtype_total_is_never_lower_than_its_parent(party: list[PlayerSpec]) -> None:
    report, _ = run(party, scenario_catalog())
    for recipient in report.recipients:
        for stat, parent in stat_parents().items():
            if parent is not None:
                assert recipient.totals.get(stat, 0) >= recipient.totals.get(parent, 0)


@pytest.mark.req("TS-3")
@given(st.data())
def test_the_order_of_players_doesnt_change_the_result(data: st.DataObject) -> None:
    party = data.draw(players())
    shuffled = data.draw(st.permutations(party))
    catalog = scenario_catalog()
    first, _ = run(party, catalog)
    second, _ = run(shuffled, catalog)

    assert _totals(first) == _totals(second)
    assert {n.name for n in first.not_counted} == {n.name for n in second.not_counted}

    def extras(report: PartyReport) -> dict[str, Any]:
        return {
            r.name: (
                sorted(
                    (report.give(c.give).bonus, sorted(c.amounts.items()), c.condition)
                    for c in r.conditional
                ),
                sorted(str(report.give(e).effect) for e in r.effects),
            )
            for r in report.recipients
        }

    assert extras(first) == extras(second)


@pytest.mark.req("TS-3")
@given(st.data())
def test_removing_a_giver_never_increases_anyones_total(data: st.DataObject) -> None:
    party = data.draw(players(min_size=1))
    removed = data.draw(st.integers(min_value=0, max_value=len(party) - 1))
    catalog = scenario_catalog()
    before, _ = run(party, catalog)
    after, _ = run(party[:removed] + party[removed + 1 :], catalog)

    before_totals = _totals(before)
    for name, totals in _totals(after).items():
        for stat, value in totals.items():
            assert value <= before_totals[name][stat], (
                f"removing {party[removed].name} raised {name}'s {stat}"
            )


@pytest.mark.req("TS-3", "SE-6", "4.11")
@given(players())
def test_only_counted_players_give_or_receive(party: list[PlayerSpec]) -> None:
    report, _ = run(party, scenario_catalog())
    counted = {UserId(n) for n, p in enumerate(party, start=1) if not (p.bot or p.sitout)}
    assert {r.user_id for r in report.recipients} == counted
    assert len(report.recipients) == len(counted), "each counted player appears once"
    assert {g.giver for g in report.gives} <= counted
    sitting_out = {UserId(n) for n, p in enumerate(party, start=1) if p.sitout and not p.bot}
    assert {n.user_id for n in report.not_counted} == sitting_out
