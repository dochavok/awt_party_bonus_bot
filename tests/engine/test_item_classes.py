"""Item classes in the engine: rules 4.14 and 4.15, section 9.2 and TS-3.

These use the scenario file's test catalog, plus the two item classes and test
versions of the three class items (requirements 8.4 and 8.5), added here so the
scenario file itself doesn't change (TF-6). Item class counts are the optional
``character_item_counts`` input to ``compute`` (section 11, TF-2).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from awt_bonus.catalog import Catalog, parse_catalog
from awt_bonus.engine import PartyReport, Reason, compute
from awt_bonus.ids import CharacterId, ItemClassId, StatId
from tests.engine.scenarios import PlayerSpec, build_inputs, catalog_data, stat_parents

pytestmark = [pytest.mark.milestone("M8")]

PENDANT = "Will Passion's Pendant"
GLIZZY = "Glizzy from God"
TOKEN = "Will Passions Adventure Token"

CLASS_ITEMS: dict[str, dict[str, Any]] = {
    PENDANT: {
        "kind": "item",
        "ability": "Aura of Passion",
        "gives": {"Damage": 2},
        "needs_item_class": "passion",
    },
    GLIZZY: {
        "kind": "item",
        "ability": "Glizzy Support",
        "includes_giver": True,
        "gives": {"Damage": 5, "CM": 3},
        "needs_item_class": "glizzy",
    },
    TOKEN: {"kind": "item", "gives": {"CM": 2, "Damage": 1}, "per_item_class": "passion"},
}

ITEM_CLASSES: dict[str, dict[str, Any]] = {
    "passion": {
        "other_names": ["Will Passion"],
        "description": "Items made by Will Passion or through the Path of Passion quest",
    },
    "glizzy": {"other_names": ["hotdog"], "description": "Glizzy (hot dog) themed items"},
}


def class_catalog_data() -> dict[str, Any]:
    data = dict(catalog_data())
    data["entries"] = {**data["entries"], **CLASS_ITEMS}
    data["item_classes"] = ITEM_CLASSES
    return data


def class_catalog() -> Catalog:
    return parse_catalog(class_catalog_data())


@dataclass(frozen=True)
class Member:
    """A scenario player and their item class counts."""

    player: PlayerSpec
    counts: Mapping[str, int] = field(default_factory=dict)


def member(name: str, *has: str, sitout: bool = False, **counts: int) -> Member:
    return Member(PlayerSpec(name=name, has=has, sitout=sitout), counts)


def run(members: Sequence[Member], catalog: Catalog | None = None) -> PartyReport:
    """Run the engine, passing each character's counts (character N is player N)."""
    inputs = build_inputs([m.player for m in members])
    counts = {
        CharacterId(number): {ItemClassId(c): n for c, n in m.counts.items()}
        for number, m in enumerate(members, start=1)
        if not (m.player.no_character or m.player.bot)
    }
    return compute(
        inputs.present_players,
        inputs.player_roles,
        inputs.character_entries,
        inputs.character_guilds,
        catalog or class_catalog(),
        character_item_counts=counts,
    )


def totals(report: PartyReport, name: str) -> dict[str, int]:
    """The recipient's non-zero totals, e.g. {"CM": 6, "Damage": 3}."""
    recipient = report.recipient(name)
    return {stat: n for stat, n in recipient.totals.items() if n}


def reasons(report: PartyReport, name: str, bonus: str) -> set[Reason]:
    """Why each give of this bonus wasn't applied to the recipient."""
    recipient = report.recipient(name)
    return {n.reason for n in recipient.not_applied if report.give(n.give).bonus == bonus}


# ---------------------------------------------------------------- CT-10: the catalog


@pytest.mark.req("CT-10", "CT-4")
def test_a_catalog_with_item_classes_and_class_fields_loads() -> None:
    catalog = class_catalog()
    assert {PENDANT, GLIZZY, TOKEN} <= {e.name for e in catalog.entries.values()}


# ---------------------------------------------------------------- rule 4.14


@pytest.mark.req("4.14", "IC-4", "4.2")
def test_aura_of_passion_goes_only_to_allies_with_a_passion_item_in_use() -> None:
    report = run(
        [
            member("Elizor", PENDANT, passion=2),
            member("Chris", passion=1),
            member("Mira"),
            member("Gus", glizzy=1),
        ]
    )
    assert totals(report, "Chris") == {"Damage": 2}
    assert totals(report, "Elizor") == {}, "the giver isn't included"
    assert totals(report, "Mira") == {}
    assert totals(report, "Gus") == {}, "a glizzy item isn't a passion item"
    assert reasons(report, "Mira", "Aura of Passion") == {Reason.NO_ITEM_CLASS}
    assert reasons(report, "Gus", "Aura of Passion") == {Reason.NO_ITEM_CLASS}
    assert reasons(report, "Elizor", "Aura of Passion") == {Reason.GIVER_EXCLUDED}


@pytest.mark.req("4.14", "IC-4", "4.3")
def test_glizzy_support_includes_its_holder_when_the_holder_has_a_glizzy_item_in_use() -> None:
    report = run([member("Gus", GLIZZY, glizzy=1), member("Mira", glizzy=1)])
    assert totals(report, "Gus") == {"CM": 3, "Damage": 5}
    assert totals(report, "Mira") == {"CM": 3, "Damage": 5}


@pytest.mark.req("4.14", "IC-4", "IC-1")
def test_a_holder_with_no_item_of_the_class_in_use_doesnt_receive_their_own_bonus() -> None:
    report = run([member("Gus", GLIZZY), member("Mira", glizzy=1)])
    assert totals(report, "Gus") == {}
    assert reasons(report, "Gus", "Glizzy Support") == {Reason.NO_ITEM_CLASS}
    assert totals(report, "Mira") == {"CM": 3, "Damage": 5}


@pytest.mark.req("4.14", "IC-4")
def test_more_items_of_the_class_dont_multiply_a_bonus_that_needs_one() -> None:
    report = run([member("Gus", GLIZZY, glizzy=1), member("Tess", glizzy=2)])
    assert totals(report, "Tess") == {"CM": 3, "Damage": 5}


@pytest.mark.req("4.14", "4.1")
def test_every_giver_of_a_bonus_that_needs_a_class_counts() -> None:
    report = run([member("Elizor", PENDANT), member("Wren", PENDANT), member("Chris", passion=1)])
    assert totals(report, "Chris") == {"Damage": 4}


@pytest.mark.req("4.14", "SE-5")
def test_a_player_with_no_character_doesnt_receive_bonuses_that_need_a_class() -> None:
    dana = Member(PlayerSpec(name="Dana", no_character=True))
    report = run([member("Gus", GLIZZY, glizzy=1), member("Elizor", PENDANT), dana])
    assert totals(report, "Dana") == {}


@pytest.mark.req("IC-1", "4.14", "TF-2")
def test_with_no_counts_given_every_character_has_0() -> None:
    inputs = build_inputs(
        [PlayerSpec(name="Elizor", has=(PENDANT,)), PlayerSpec(name="Chris", has=(TOKEN,))]
    )
    report = compute(
        inputs.present_players,
        inputs.player_roles,
        inputs.character_entries,
        inputs.character_guilds,
        class_catalog(),
    )
    assert totals(report, "Chris") == {}
    assert reasons(report, "Chris", "Aura of Passion") == {Reason.NO_ITEM_CLASS}


# ---------------------------------------------------------------- rule 4.15


@pytest.mark.req("4.15", "IC-5")
def test_the_token_multiplies_by_the_partys_passion_items_the_holders_own_included() -> None:
    # The worked example in rule 4.15.
    report = run([member("Chris", TOKEN, passion=1), member("Elizor", passion=2), member("Mira")])
    assert totals(report, "Chris") == {"CM": 6, "Damage": 3}
    assert totals(report, "Elizor") == {}
    assert totals(report, "Mira") == {}


@pytest.mark.req("4.15", "IC-5", "4.11")
def test_characters_sitting_out_add_nothing_to_the_partys_count() -> None:
    report = run(
        [
            member("Chris", TOKEN, passion=1),
            member("Elizor", passion=2),
            member("Sable", passion=3, sitout=True),
        ]
    )
    assert totals(report, "Chris") == {"CM": 6, "Damage": 3}


@pytest.mark.req("4.15", "IC-5")
def test_counts_for_characters_not_in_the_channel_are_ignored() -> None:
    inputs = build_inputs([PlayerSpec(name="Chris", has=(TOKEN,))])
    report = compute(
        inputs.present_players,
        inputs.player_roles,
        inputs.character_entries,
        inputs.character_guilds,
        class_catalog(),
        character_item_counts={
            CharacterId(1): {ItemClassId("passion"): 1},
            CharacterId(99): {ItemClassId("passion"): 5},
        },
    )
    assert totals(report, "Chris") == {"CM": 2, "Damage": 1}


@pytest.mark.req("4.15", "IC-5")
def test_a_lone_holder_counts_their_own_passion_items() -> None:
    report = run([member("Chris", TOKEN, passion=2)])
    assert totals(report, "Chris") == {"CM": 4, "Damage": 2}


@pytest.mark.req("4.15", "IC-5", "IC-3")
def test_with_no_passion_items_in_the_party_the_holder_gets_nothing_and_is_told_why() -> None:
    report = run([member("Chris", TOKEN), member("Mira", glizzy=1)])
    assert totals(report, "Chris") == {}
    assert reasons(report, "Chris", TOKEN) == {Reason.NO_ITEM_CLASS}


@pytest.mark.req("4.15", "IC-5")
def test_each_token_holder_receives_their_own_token() -> None:
    report = run([member("Chris", TOKEN, passion=1), member("Dee", TOKEN, passion=1)])
    assert totals(report, "Chris") == {"CM": 4, "Damage": 2}
    assert totals(report, "Dee") == {"CM": 4, "Damage": 2}


# ---------------------------------------------------------------- section 9.2


NINE_TWO = [
    member("Elizor", PENDANT, passion=2),
    member("Chris", TOKEN, passion=1),
    member("Mira", glizzy=1),
    member("Gus", GLIZZY, glizzy=1),
    member("Tess", glizzy=2),
    member("Sable", passion=3, sitout=True),
]


@pytest.mark.req("9.2", "4.14", "4.15")
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Elizor", {}),
        ("Chris", {"CM": 6, "Damage": 5}),
        ("Mira", {"CM": 3, "Damage": 5}),
        ("Gus", {"CM": 3, "Damage": 5}),
        ("Tess", {"CM": 3, "Damage": 5}),
    ],
)
def test_the_item_class_game_totals(name: str, expected: dict[str, int]) -> None:
    assert totals(run(NINE_TWO), name) == expected


@pytest.mark.req("9.2", "4.14")
def test_the_item_class_game_reasons() -> None:
    report = run(NINE_TWO)
    for name in ["Mira", "Gus", "Tess"]:
        assert reasons(report, name, "Aura of Passion") == {Reason.NO_ITEM_CLASS}, name
    assert reasons(report, "Elizor", "Glizzy Support") == {Reason.NO_ITEM_CLASS}
    assert reasons(report, "Chris", "Glizzy Support") == {Reason.NO_ITEM_CLASS}
    assert "Sable" not in {r.name for r in report.recipients}


# ---------------------------------------------------------------- TS-3: properties

ENTRIES = sorted(class_catalog_data()["entries"])


@st.composite
def parties(draw: Any) -> list[Member]:
    count = draw(st.integers(min_value=0, max_value=7))
    party = []
    for number in range(count):
        has = draw(st.lists(st.sampled_from(ENTRIES), max_size=5, unique=True))
        has += draw(st.lists(st.sampled_from(sorted(CLASS_ITEMS)), max_size=2, unique=True))
        player = PlayerSpec(
            name=f"P{number}",
            has=tuple(dict.fromkeys(has)),
            level=draw(st.none() | st.integers(min_value=1, max_value=75)),
            sitout=draw(st.integers(0, 4)) == 0,
            no_character=draw(st.integers(0, 6)) == 0,
        )
        counts = {c: draw(st.integers(0, 4)) for c in ITEM_CLASSES}
        party.append(Member(player, counts))
    return party


@pytest.mark.req("TS-3", "4.15")
@given(parties())
def test_a_bonus_counted_across_the_party_never_goes_to_anyone_but_its_holder(
    party: list[Member],
) -> None:
    report = run(party)
    for recipient in report.recipients:
        for applied in recipient.applied:
            give = report.give(applied.give)
            if give.entry == TOKEN:
                assert give.giver == recipient.user_id, f"{recipient.name} got another's token"


@pytest.mark.req("TS-3", "4.14", "4.15")
@given(st.data())
def test_raising_a_characters_count_never_lowers_anyone_s_total(data: st.DataObject) -> None:
    party = data.draw(parties().filter(bool))
    index = data.draw(st.integers(0, len(party) - 1))
    item_class = data.draw(st.sampled_from(sorted(ITEM_CLASSES)))
    raised = list(party)
    counts = dict(party[index].counts)
    counts[item_class] = counts.get(item_class, 0) + data.draw(st.integers(1, 3))
    raised[index] = replace(party[index], counts=counts)

    before, after = run(party), run(raised)
    for recipient in before.recipients:
        for stat in stat_parents():
            old = recipient.totals.get(StatId(stat), 0)
            new = after.recipient(recipient.name).totals.get(StatId(stat), 0)
            assert new >= old, f"{recipient.name} {stat}: {old} -> {new}"
