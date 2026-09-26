"""Self-tests for the engine test code (M1).

Until M2 the engine tests stop at the first stub, so their checking code never
runs. These tests run that code against hand-built reports (and a null engine),
so a mistake in the test code shows up now, not after the engine exists, when
fixing a test needs the TF-5 sequence.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pytest

import tests.engine.scenarios as scenarios_module
import tests.engine.test_properties as properties
import tests.engine.test_scenarios as scenario_tests
from awt_bonus.catalog import Catalog
from awt_bonus.engine import (
    Applied,
    Audience,
    AudienceKind,
    ConditionalBonus,
    Give,
    NotApplied,
    NotCounted,
    PartyReport,
    PresentPlayer,
    Reason,
    RecipientReport,
    Source,
    SourceKind,
)
from awt_bonus.ids import CharacterId, EntryId, GuildId, StatId, UserId
from tests.engine.scenarios import NOW, scenarios

pytestmark = pytest.mark.milestone("M1")

Compute = Callable[..., PartyReport]


def _scenario(name: str) -> Mapping[str, Any]:
    return next(s for s in scenarios() if s["name"] == name)


def _give(
    give_id: int,
    giver: int,
    entry: str,
    amounts: Mapping[str, int] | None = None,
    *,
    effect: str | None = None,
    condition: str | None = None,
    stacks: bool = True,
    includes_giver: bool = False,
) -> Give:
    stat_amounts = {StatId(k): v for k, v in (amounts or {}).items()}
    return Give(
        id=give_id,
        giver=UserId(giver),
        entry=EntryId(entry),
        bonus=entry,
        source=Source(SourceKind.ITEM),
        giver_rank=(),
        base=stat_amounts,
        adjustments=(),
        amounts=stat_amounts,
        level_rules=(),
        effect=effect,
        condition=condition,
        audience=Audience(AudienceKind.PARTY),
        includes_giver=includes_giver,
        stacks=stacks,
        secret_guild=None,
        retired=False,
    )


def _recipient(
    user: int,
    name: str,
    totals: Mapping[str, int],
    applied: Sequence[tuple[int, Mapping[str, int]]] = (),
    not_applied: Sequence[tuple[int, Reason]] = (),
    conditional: Sequence[tuple[int, Mapping[str, int], str]] = (),
    effects: Sequence[int] = (),
) -> RecipientReport:
    return RecipientReport(
        user_id=UserId(user),
        name=name,
        character=None,
        totals={StatId(k): v for k, v in totals.items()},
        applied=tuple(Applied(g, {StatId(k): v for k, v in a.items()}) for g, a in applied),
        not_applied=tuple(NotApplied(g, r) for g, r in not_applied),
        conditional=tuple(
            ConditionalBonus(g, {StatId(k): v for k, v in a.items()}, c) for g, a, c in conditional
        ),
        effects=tuple(effects),
    )


def _fake_engine(monkeypatch: pytest.MonkeyPatch, compute: Compute) -> None:
    monkeypatch.setattr(scenarios_module, "compute", compute)
    monkeypatch.setattr(scenario_tests, "scenario_catalog", Catalog)
    monkeypatch.setattr(properties, "scenario_catalog", Catalog)


def _returning(report: PartyReport) -> Compute:
    return lambda *args, **kwargs: report


# Section 4.1/4.2 scenario: A, B, C each give Test Buff (+2 CM); D gives nothing.
CM_TO_ALLIES = PartyReport(
    gives=(_give(1, 1, "Test Buff", {"CM": 2}), _give(2, 2, "Test Buff", {"CM": 2}),
           _give(3, 3, "Test Buff", {"CM": 2})),
    recipients=(
        _recipient(1, "A", {"CM": 4}, [(2, {"CM": 2}), (3, {"CM": 2})],
                   [(1, Reason.GIVER_EXCLUDED)]),
        _recipient(2, "B", {"CM": 4}, [(1, {"CM": 2}), (3, {"CM": 2})],
                   [(2, Reason.GIVER_EXCLUDED)]),
        _recipient(3, "C", {"CM": 4}, [(1, {"CM": 2}), (2, {"CM": 2})],
                   [(3, Reason.GIVER_EXCLUDED)]),
        _recipient(4, "D", {"CM": 6}, [(1, {"CM": 2}), (2, {"CM": 2}), (3, {"CM": 2})]),
    ),
    not_counted=(),
    no_character=(),
)  # fmt: skip


@pytest.mark.req("TF-2", "TS-1")
def test_scenario_runner_accepts_a_correct_report(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_engine(monkeypatch, _returning(CM_TO_ALLIES))
    scenario_tests.test_scenario(_scenario("CM goes to allies (three givers of +2 CM)"))


@pytest.mark.req("TF-2", "TS-1")
def test_scenario_runner_catches_a_wrong_total(monkeypatch: pytest.MonkeyPatch) -> None:
    wrong = PartyReport(
        gives=CM_TO_ALLIES.gives,
        recipients=(*CM_TO_ALLIES.recipients[:3], _recipient(4, "D", {"CM": 5})),
        not_counted=(),
        no_character=(),
    )
    _fake_engine(monkeypatch, _returning(wrong))
    with pytest.raises(AssertionError, match="totals for D"):
        scenario_tests.test_scenario(_scenario("CM goes to allies (three givers of +2 CM)"))


@pytest.mark.req("TF-2", "TS-1")
def test_scenario_runner_catches_a_missing_not_applied_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a = CM_TO_ALLIES.recipients[0]
    wrong = PartyReport(
        gives=CM_TO_ALLIES.gives,
        recipients=(
            _recipient(1, "A", {"CM": 4}, [(2, {"CM": 2}), (3, {"CM": 2})]),
            *CM_TO_ALLIES.recipients[1:],
        ),
        not_counted=(),
        no_character=(),
    )
    assert a.not_applied  # the correct report has the line
    _fake_engine(monkeypatch, _returning(wrong))
    with pytest.raises(AssertionError, match="not-applied"):
        scenario_tests.test_scenario(_scenario("CM goes to allies (three givers of +2 CM)"))


@pytest.mark.req("TF-2", "TS-1", "4.12")
def test_scenario_runner_checks_conditional_bonuses(monkeypatch: pytest.MonkeyPatch) -> None:
    # Cmd has Commanding Presence (conditional); A has Test Buff.
    gives = (
        _give(1, 1, "Commanding Presence", {"CM": 5}, condition="allies in the same range"),
        _give(2, 2, "Test Buff", {"CM": 2}),
    )
    right = PartyReport(
        gives=gives,
        recipients=(
            _recipient(1, "Cmd", {"CM": 2}, [(2, {"CM": 2})]),
            _recipient(2, "A", {}, conditional=[(1, {"CM": 5}, "allies in the same range")]),
        ),
        not_counted=(),
        no_character=(),
    )
    scenario = _scenario("Conditional bonuses stay out of totals but follow the other rules")
    _fake_engine(monkeypatch, _returning(right))
    scenario_tests.test_scenario(scenario)

    wrong = PartyReport(
        gives=gives,
        recipients=(right.recipients[0], _recipient(2, "A", {})),
        not_counted=(),
        no_character=(),
    )
    _fake_engine(monkeypatch, _returning(wrong))
    with pytest.raises(AssertionError, match="conditional bonuses for A"):
        scenario_tests.test_scenario(scenario)


@pytest.mark.req("TF-2", "TS-1")
def test_scenario_runner_checks_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    resistance = "Resistance to damage from an Evil source"
    lore = "Challenge rolls to resist natural effects are one roll category easier"
    gives = (
        _give(1, 1, "Protective Aura", effect=resistance),
        _give(2, 2, "Ranger Captain", effect=lore, includes_giver=True),
        _give(3, 2, "Master Ranger", effect=lore, includes_giver=True),
    )
    scenario = _scenario("Effects follow the giver rule; a higher rank replaces the lower")

    def report(r2_effects: Sequence[int]) -> PartyReport:
        return PartyReport(
            gives=gives,
            recipients=(
                _recipient(1, "K", {}, effects=[3]),
                _recipient(2, "R1", {}, effects=[1, 3]),
                _recipient(3, "R2", {}, effects=r2_effects),
            ),
            not_counted=(),
            no_character=(),
        )

    _fake_engine(monkeypatch, _returning(report([1, 3])))
    scenario_tests.test_scenario(scenario)

    _fake_engine(monkeypatch, _returning(report([1, 2, 3])))  # Wilderness Lore twice
    with pytest.raises(AssertionError, match="received once each"):
        scenario_tests.test_scenario(scenario)


@pytest.mark.req("TF-2", "TS-1", "SE-4", "SE-5")
def test_scenario_runner_checks_not_counted_and_no_character(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sitting_out = PartyReport(
        gives=(_give(1, 2, "Test Buff", {"CM": 2}),),
        recipients=(_recipient(2, "A", {}), _recipient(3, "B", {"CM": 2}, [(1, {"CM": 2})])),
        not_counted=(NotCounted(UserId(1), "DM", NOW),),
        no_character=(),
    )
    _fake_engine(monkeypatch, _returning(sitting_out))
    scenario_tests.test_scenario(_scenario("Sitting out removes giving and receiving"))

    no_character = PartyReport(
        gives=(
            _give(1, 1, "Support", {"CM": 2}),
            _give(2, 2, "Champion of Power", {"CM": 5, "CR": 5}),
        ),
        recipients=(
            _recipient(1, "Dana", {"CM": 5, "CR": 5, "CR vs fear": 5, "CR stealth": 5,
                                   "CR escape": 5, "CR would hurt": 5},
                       [(2, {"CM": 5, "CR": 5})]),
            _recipient(2, "B", {"CM": 2}, [(1, {"CM": 2})]),
        ),
        not_counted=(),
        no_character=(UserId(1),),
    )  # fmt: skip
    _fake_engine(monkeypatch, _returning(no_character))
    scenario_tests.test_scenario(_scenario("No character set up still gives Support, and receives"))


@pytest.mark.req("TF-2", "TS-1", "SE-6")
def test_scenario_runner_catches_a_listed_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    # Players: MusicBot (user 1, a bot), A (2, Test Buff), B (3).
    with_bot = PartyReport(
        gives=(_give(1, 2, "Test Buff", {"CM": 2}),),
        recipients=(_recipient(2, "A", {}), _recipient(3, "B", {"CM": 2}, [(1, {"CM": 2})])),
        not_counted=(NotCounted(UserId(1), "MusicBot", NOW),),
        no_character=(),
    )
    _fake_engine(monkeypatch, _returning(with_bot))
    with pytest.raises(AssertionError, match="bots must never appear"):
        scenario_tests.test_scenario(_scenario("Bots in the channel are ignored"))


@pytest.mark.req("TF-2", "TS-1")
def test_scenario_tags_are_read_from_the_rule_text() -> None:
    tags = {s["name"]: scenario_tests.tags(s) for s in scenarios()}
    assert tags["Devotion III boosts Paladin auras but not Presence skills"] == (
        ["4.12", "4.6", "TS-1"],
        ["Q1"],
    )
    assert tags["Full sample game (requirements section 9.1)"] == (
        ["9.1", "TS-1"],
        ["Q1", "Q2", "Q3", "Q6"],
    )
    assert "TS-2" in tags["Empty channel"][0]
    assert tags["Support from five Guild rank holders"][0] == ["4.1", "4.2", "HV-3", "TS-1"]


def _null_engine(
    present_players: Sequence[PresentPlayer],
    player_roles: Mapping[UserId, frozenset[str]],
    character_entries: Mapping[CharacterId, Sequence[EntryId]],
    character_guilds: Mapping[CharacterId, Sequence[GuildId]],
    catalog: Catalog,
) -> PartyReport:
    """Counts the right people but gives nobody anything: enough to run the property checks."""
    people = [p for p in present_players if not p.is_bot]
    return PartyReport(
        gives=(),
        recipients=tuple(
            RecipientReport(
                user_id=p.user_id,
                name=p.character.name if p.character else p.display_name,
                character=p.character,
                totals={},
                applied=(),
                not_applied=(),
                conditional=(),
                effects=(),
            )
            for p in people
            if p.sitting_out_until is None
        ),
        not_counted=tuple(
            NotCounted(p.user_id, p.display_name, p.sitting_out_until)
            for p in people
            if p.sitting_out_until is not None
        ),
        no_character=tuple(
            p.user_id for p in people if p.character is None and p.sitting_out_until is None
        ),
    )


@pytest.mark.req("TF-2", "TS-3")
@pytest.mark.parametrize(
    "prop",
    [
        properties.test_nobody_receives_their_own_bonus_unless_the_entry_includes_the_giver,
        properties.test_a_bonus_that_doesnt_stack_counts_at_most_once_per_recipient,
        properties.test_every_total_equals_the_sum_of_its_breakdown_lines,
        properties.test_conditional_bonuses_are_never_in_totals,
        properties.test_a_subtype_total_is_never_lower_than_its_parent,
        properties.test_the_order_of_players_doesnt_change_the_result,
        properties.test_removing_a_giver_never_increases_anyones_total,
        properties.test_only_counted_players_give_or_receive,
    ],
    ids=lambda f: f.__name__,
)
def test_property_checks_run(monkeypatch: pytest.MonkeyPatch, prop: Callable[[], None]) -> None:
    _fake_engine(monkeypatch, _null_engine)
    prop()
