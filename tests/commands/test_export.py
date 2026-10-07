"""Hand-off to Bogsy's dice bot (section 14: BG-1 to BG-3). A could-have, for M6.

/bogsy replies privately with Bogsy /modifier commands for the player's current
character: roll stats only (combat notes, effects and conditional bonuses are never
exported). CM and CR hold the totals; each CR subtype holds only the extra on top of
CR, because Bogsy adds modifiers together when rolling.
"""

import re

import pytest

from tests.support.world import MakeWorld

pytestmark = pytest.mark.milestone("M6")

NAMES = [
    "bonus_cm",
    "bonus_cr",
    "bonus_fear",
    "bonus_stealth",
    "bonus_escape",
    "bonus_would_hurt",
]
"""Every roll stat's modifier, in the catalog's order (BG-1, BG-2)."""


def _modifiers(text: str) -> list[tuple[str, int]]:
    """The /modifier commands in a reply, in order, as (name, value)."""
    found = re.findall(r"/modifier name:(\w+) value:(-?\d+)", text)
    return [(name, int(value)) for name, value in found]


@pytest.mark.req("BG-1", "BG-2", "9.1")
async def test_export_lists_roll_stat_modifiers_to_copy(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("maya", "bogsy")

    assert reply.private
    values = dict(_modifiers(reply.text))
    assert values["bonus_cm"] == 33
    assert values["bonus_cr"] == 10
    assert values["bonus_fear"] == 3  # 13 - 10: only the extra
    assert values["bonus_stealth"] == 2  # 12 - 10
    assert values["bonus_escape"] == 1  # 11 - 10


@pytest.mark.req("BG-1", "4.12")
async def test_export_leaves_out_combat_notes_effects_and_conditional_bonuses(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    world.discord.move(world.user("vic"), world.channel("AWT Voice"))  # Commanding Presence
    reply = await world.run("kit", "bogsy")

    assert "Damage" not in reply.text
    assert "heart" not in reply.text
    assert "Resistance" not in reply.text
    assert "Commanding Presence" not in reply.text
    assert dict(_modifiers(reply.text))["bonus_cm"] == 28  # 18 + Vex's Aura of Hope


@pytest.mark.req("BG-3")
async def test_export_sets_stats_that_are_now_zero_to_0(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("ada", "bogsy")  # Aria: CR vs fear +2, nothing else

    assert dict(_modifiers(reply.text)) == {
        name: 2 if name == "bonus_fear" else 0 for name in NAMES
    }


@pytest.mark.req("BG-1", "BG-2", "BG-3", "OUT-5", "OUT-3b", "9.1")
async def test_every_roll_stat_is_one_line_in_the_catalogs_order(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("maya", "bogsy")

    assert _modifiers(reply.text) == [
        ("bonus_cm", 33),
        ("bonus_cr", 10),
        ("bonus_fear", 3),
        ("bonus_stealth", 2),
        ("bonus_escape", 1),
        ("bonus_would_hurt", 0),
    ]
    assert reply.private
    assert len(reply.messages) == 1


@pytest.mark.req("BG-1")
async def test_export_ends_with_how_to_set_up_and_roll(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    text = (await world.run("maya", "bogsy")).text

    note = text[text.rindex("/modifier") :]
    assert "quickroll" in note.casefold()
    assert "bonus_cr" in note.split("\n", 1)[1], "a quickroll example using bonus_cr"
    assert "/roll command:" in note


@pytest.mark.req("BG-1", "CH-3")
async def test_the_combat_quickroll_is_named_after_the_current_character(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    text = (await world.run("maya", "bogsy")).text

    assert "/quickroll name:mira dicestring:<your dice> + my_cm + bonus_cm" in text
    assert "/quickroll name:challenge dicestring:1d20 + cr_level + my_cr_bonus + bonus_cr" in text
    assert "/roll command:mira" in text


@pytest.mark.req("BG-3", "OUT-4", "SE-2")
@pytest.mark.parametrize("away", ["not-in-voice", "sitting-out"])
async def test_with_no_party_every_value_is_0_and_the_reply_says_why(
    make_world: MakeWorld, away: str
) -> None:
    world = await make_world("sample-game")
    if away == "not-in-voice":
        world.discord.move(world.user("maya"), None)
    else:
        await world.run("maya", "sitout")
    reply = await world.run("maya", "bogsy")

    assert _modifiers(reply.text) == [(name, 0) for name in NAMES]
    reason = "voice" if away == "not-in-voice" else "sitting out"
    assert reason in reply.text.casefold()
    assert reply.private


@pytest.mark.req("BG-3", "CH-3", "SE-5")
async def test_with_no_current_character_the_reply_says_how_to_get_one(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("dana", "bogsy")  # in voice, no character registered

    assert _modifiers(reply.text) == []
    assert "/character register" in reply.text
    assert reply.private
