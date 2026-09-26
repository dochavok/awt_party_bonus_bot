"""Presence in the voice channel (requirements 6.5: SE-1 to SE-6), and the TS-2 edge
cases at command level.

Uses the presence fixture (one voice channel per case; see the fixture's header).
"""

from datetime import timedelta

import pytest

from awt_bonus.settings import Settings
from tests.support.text import counted, discord_timestamp, stat
from tests.support.world import MakeWorld

M3 = pytest.mark.milestone("M3")
M4 = pytest.mark.milestone("M4")


# ---------------------------------------------------------------- SE-1: which channel


@M3
@pytest.mark.req("SE-1")
@pytest.mark.parametrize("command", ["partybonus", "breakdown"])
async def test_party_commands_use_the_callers_voice_channel(
    make_world: MakeWorld, command: str
) -> None:
    world = await make_world("presence")
    reply = await world.run("ada", command)
    assert counted(reply) == {"Aria", "Bryn", "Cato"}


@M3
@pytest.mark.req("SE-1")
@pytest.mark.parametrize("command", ["partybonus", "breakdown"])
async def test_party_commands_can_pick_a_channel(make_world: MakeWorld, command: str) -> None:
    world = await make_world("presence")
    reply = await world.run("ada", command, channel=world.channel("Stage"))
    assert counted(reply) == {"Dara", "Esme", "Finn"}


@M3
@pytest.mark.req("SE-1", "OUT-6")
async def test_mybonus_uses_the_channel_the_characters_player_is_in(
    make_world: MakeWorld,
) -> None:
    world = await make_world("presence")
    world.discord.move(world.user("ada"), None)  # the caller isn't in voice at all
    reply = await world.run("ada", "mybonus", character="Finn")

    assert counted(reply) == {"Dara", "Esme", "Finn"}
    assert stat(reply, "Finn", "CR") == 5


@M3
@pytest.mark.req("SE-1", "4.1", "TS-2")
async def test_the_same_skill_from_two_characters_counts_twice(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("cal", "partybonus")

    assert stat(reply, "Cato", "CR vs fear") == 4
    assert stat(reply, "Aria", "CR vs fear") == 2
    assert stat(reply, "Bryn", "CR vs fear") == 2


@M3
@pytest.mark.req("4.4", "TS-2")
async def test_two_givers_of_a_bonus_that_doesnt_stack_count_once(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("fin", "partybonus")

    for name in ["Dara", "Esme", "Finn"]:
        assert stat(reply, name, "CR") == 5, name


# ---------------------------------------------------------------- SE-2: sitting out


@M3
@pytest.mark.req("SE-2", "NF-10", "TS-10")
async def test_sitout_leaves_the_caller_uncounted_for_12_hours(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    now = world.clock.now()
    reply = await world.run("ada", "sitout")

    assert reply.private
    assert await world.store.sitout_until(world.user("ada")) == now + timedelta(hours=12)
    assert discord_timestamp(now + timedelta(hours=12)) in reply.text

    reply = await world.run("ben", "partybonus")
    assert counted(reply) == {"Bryn", "Cato"}
    assert reply.report is not None
    assert world.user("ada") in {n.user_id for n in reply.report.not_counted}
    assert stat(reply, "Cato", "CR vs fear") == 2  # Aria gives nothing

    world.clock.advance(timedelta(hours=11, minutes=59))
    assert "Aria" not in counted(await world.run("ben", "partybonus"))
    world.clock.advance(timedelta(minutes=2))
    assert "Aria" in counted(await world.run("ben", "partybonus"))


@M3
@pytest.mark.req("SE-2")
async def test_sitin_ends_a_sitout_early(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    await world.run("ada", "sitout")
    reply = await world.run("ada", "sitin")

    assert reply.private
    assert "Aria" in counted(await world.run("ben", "partybonus"))


@M3
@pytest.mark.req("SE-2", "TS-10")
async def test_a_sitout_that_has_ended_counts_the_player_again(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("ned", "partybonus")  # Eve's sit-out ended an hour ago

    assert "Evander" in counted(reply)
    assert stat(reply, "Nell", "CM") == 2


@M3
@pytest.mark.req("SE-2")
async def test_the_sitout_duration_is_configurable(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    app = world.app_with(
        settings=Settings(request_channel="bonus-bot-support", sitout_hours=2, max_level=75)
    )
    await app.run(world.user("ada"), "sitout")

    until = await world.store.sitout_until(world.user("ada"))
    assert until == world.clock.now() + timedelta(hours=2)


@M3
@pytest.mark.req("SE-2", "4.11", "TS-2")
async def test_everyone_sitting_out_gives_an_empty_party(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("gus", "partybonus")

    assert counted(reply) == set()
    assert reply.report is not None
    assert {n.user_id for n in reply.report.not_counted} == {world.user("gus"), world.user("hal")}


@M3
@pytest.mark.req("TS-2", "SE-1")
async def test_an_empty_channel_gives_an_empty_party(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("ada", "partybonus", channel=world.channel("Empty Room"))

    assert counted(reply) == set()
    assert reply.text


# ---------------------------------------------------------------- SE-3: current character


@M3
@pytest.mark.req("SE-3", "CH-3")
async def test_each_player_is_counted_with_their_current_character(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("ned", "partybonus")
    assert "Fern" not in counted(reply)
    assert stat(reply, "Nell", "CM") == 2  # Fern's Aura of Hope not counted

    await world.run("fay", "play", character="Fern")
    reply = await world.run("ned", "partybonus")
    assert "Fern" in counted(reply)
    assert stat(reply, "Nell", "CM") == 12


# ---------------------------------------------------------------- SE-4: not counted line


@M3
@pytest.mark.req("SE-4", "NF-10")
@pytest.mark.parametrize("command", ["partybonus", "breakdown"])
async def test_the_not_counted_line_lists_who_is_sitting_out_with_the_end_time(
    make_world: MakeWorld, command: str
) -> None:
    world = await make_world("presence")
    reply = await world.run("ada", command, channel=world.channel("Quiet Room"))

    assert "Gus" in reply.text
    assert "Hal" in reply.text
    spec = {p.member: p.sitout_until for p in world.spec.players}
    gus_until, hal_until = spec["gus"], spec["hal"]
    assert gus_until is not None
    assert hal_until is not None
    assert discord_timestamp(gus_until) in reply.text
    assert discord_timestamp(hal_until) in reply.text


@M3
@pytest.mark.req("SE-4")
@pytest.mark.parametrize("command", ["partybonus", "breakdown"])
async def test_people_sitting_out_elsewhere_arent_listed(
    make_world: MakeWorld, command: str
) -> None:
    world = await make_world("presence")
    reply = await world.run("ada", command)  # Hall; Gus and Hal sit out in Quiet Room

    assert counted(reply) == {"Aria", "Bryn", "Cato"}
    assert "Gus" not in reply.text
    assert "Hal" not in reply.text


@M3
@pytest.mark.req("SE-4", "9.1")
async def test_sample_game_not_counted_line(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("isla", "partybonus")

    assert "DM Sam" in reply.text
    assert "Bob" in reply.text
    assert "Rowan" not in reply.text  # sitting out, but not in AWT Voice
    assert counted(reply) == {"Ioseph", "Kael", "Crateris", "Chris", "Mira", "Dana"}
    assert "Sable" not in reply.text
    assert "Bram" not in reply.text


# ---------------------------------------------------------------- SE-5: no character set up


@M3
@pytest.mark.req("SE-5", "TS-2")
async def test_a_member_with_no_character_is_counted_and_told_how_to_fix_it(
    make_world: MakeWorld,
) -> None:
    world = await make_world("presence")
    for command in ["partybonus", "breakdown"]:
        reply = await world.run("gwen", command)
        assert "Rook" in counted(reply)
        assert reply.report is not None
        assert world.user("rook") in reply.report.no_character
        assert "/character register" in reply.text
        assert stat(reply, "Rook", "CM") == 5  # Champion of Power
        assert stat(reply, "Rook", "CR") == 5


@M3
@pytest.mark.req("SE-5", "CH-3")
async def test_a_member_with_characters_but_none_current_is_told_to_use_play(
    make_world: MakeWorld,
) -> None:
    world = await make_world("presence")
    reply = await world.run("ned", "partybonus")

    assert reply.report is not None
    assert world.user("fay") in reply.report.no_character
    assert "Fay" in counted(reply)
    assert "/play" in reply.text
    assert stat(reply, "Fay", "CM") == 2  # receives like anyone else


@M4
@pytest.mark.req("SE-5", "HV-3", "TS-2")
async def test_a_member_with_no_character_still_gives_support(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("gwen", "partybonus")

    assert stat(reply, "Gwyneth", "CM") == 2
    assert stat(reply, "Rook", "CM") == 5


# ---------------------------------------------------------------- SE-6: bots


@M3
@pytest.mark.req("SE-6", "TS-2")
@pytest.mark.parametrize("command", ["partybonus", "breakdown"])
async def test_bots_are_ignored_and_never_listed(make_world: MakeWorld, command: str) -> None:
    world = await make_world("presence")
    reply = await world.run("gwen", command)

    assert "Jukebox" not in reply.text
    assert counted(reply) == {"Rook", "Gwyneth"}
    assert reply.report is not None
    assert world.user("jukebox") not in reply.report.no_character


@M4
@pytest.mark.req("SE-6", "HV-3")
async def test_a_bot_with_a_guild_rank_role_gives_nothing(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("gwen", "partybonus")
    assert stat(reply, "Gwyneth", "CM") == 2  # Rook's Support only
