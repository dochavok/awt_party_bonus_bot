"""Hand-off to Bogsy's dice bot (section 14: BG-1 to BG-3). A could-have, for M6.

The export lists roll stats only; combat notes, effects and conditional bonuses
are never exported.
"""

import re

import pytest

from tests.support.world import MakeWorld

pytestmark = pytest.mark.milestone("M6")


@pytest.mark.req("BG-1", "9.1")
async def test_export_lists_roll_stat_modifiers_to_copy(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("maya", "mybonus", character="Mira", export="bogsy")

    assert reply.private
    assert ".awt_cm = +33" in reply.text
    assert ".awt_cr = +10" in reply.text
    assert ".awt_cr_fear = +13" in reply.text


@pytest.mark.req("BG-1", "4.12")
async def test_export_leaves_out_combat_notes_effects_and_conditional_bonuses(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    world.discord.move(world.user("vic"), world.channel("AWT Voice"))  # Commanding Presence
    reply = await world.run("kit", "mybonus", character="Kael", export="bogsy")

    assert "Damage" not in reply.text
    assert "heart" not in reply.text
    assert "Resistance" not in reply.text
    assert "Commanding Presence" not in reply.text
    assert ".awt_cm = +28" in reply.text  # 18 + Vex's Aura of Hope; not the conditional +5


@pytest.mark.req("BG-3")
async def test_export_clears_modifiers_for_stats_that_are_now_zero(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("ada", "mybonus", character="Aria", export="bogsy")  # CR vs fear +2

    lines = [line.strip() for line in reply.text.splitlines()]
    assert ".awt_cr_fear = +2" in reply.text
    assert any(re.fullmatch(r"`?\.awt_cm =`?", line) for line in lines)
    assert any(re.fullmatch(r"`?\.awt_cr =`?", line) for line in lines)
