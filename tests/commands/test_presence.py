"""Presence in the voice channel (requirements 6.5: SE-1 to SE-8), and the TS-2 edge
cases at command level.

Uses the presence fixture (one voice channel per case; see the fixture's header),
except the supporting sit-out tests (SE-7, SE-8), which use the sample game.
"""

import re
from datetime import timedelta

import pytest

from awt_bonus.catalog import parse_catalog
from awt_bonus.settings import Settings
from tests.support.supporters import JOIN_TEXT, supporter_catalog
from tests.support.text import counted, discord_timestamp, stat
from tests.support.world import MakeWorld, catalog_data

M3 = pytest.mark.milestone("M3")
M4 = pytest.mark.milestone("M4")
M10 = pytest.mark.milestone("M10")


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
    assert reply.report is not None
    assert not reply.report.not_counted
    assert not reply.report.no_character
    assert f"<#{world.channel('Empty Room')}>" in reply.text, "the heading names that channel"
    shown = {c.name for p in world.spec.players for c in p.characters} | {
        m.name for m in world.spec.discord.members
    }
    named = {n for n in shown if re.search(rf"\b{re.escape(n)}\b", reply.text)}
    assert not named, "nobody from another channel is shown"


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


# ---------------------------------------------------------------- SE-7: supporting sit-outs
# These use the sample game, with Support allowed while sitting out for Guild
# Champion and Guild Legend (tests/support/supporters.py). DM Sam (Guild Champion,
# plays Sable: Aura of Hope +10 CM) and Bob (Guild Legend, plays Bram) start with
# plain sit-outs; Isla (Guild Vanguard) plays Ioseph.

SAMPLE_COUNTED = {"Ioseph", "Kael", "Crateris", "Chris", "Mira", "Dana"}


def _not_counted_entry(text: str, name: str) -> str:
    """What the *not counted* line says about one person, e.g. "sitting out until …"."""
    lines = [line for line in text.splitlines() if "Not counted" in line]
    assert len(lines) == 1, f"one not-counted line: {lines}"
    found = re.search(rf"{re.escape(name)} \(([^)]*)\)", lines[0])
    assert found is not None, f"{name} isn't on the not-counted line: {lines[0]}"
    return found.group(1)


@M10
@pytest.mark.req("SE-7", "HV-3", "4.11")
async def test_a_supporter_keeps_giving_support_while_sitting_out(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())
    isla, sam = world.user("isla"), world.user("sam")
    before = await app.run(isla, "partybonus")

    reply = await app.run(sam, "sitout", {"support": True})
    after = await app.run(isla, "partybonus")

    assert reply.private
    assert await world.store.sitout_until(sam) == world.clock.now() + timedelta(hours=12)
    assert counted(after) == counted(before) == SAMPLE_COUNTED, "Sable still isn't counted"
    for name in SAMPLE_COUNTED:
        assert stat(after, name, "CM") == stat(before, name, "CM") + 2, name
        assert stat(after, name, "CR") == stat(before, name, "CR"), name
    assert after.report is not None
    assert [g.bonus for g in after.report.gives if g.giver == sam] == ["Support"]


@M10
@pytest.mark.req("SE-7", "NF-4")
async def test_support_true_is_refused_without_an_allowed_role(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())
    isla = world.user("isla")  # Guild Vanguard

    reply = await app.run(isla, "sitout", {"support": True})

    assert reply.private
    assert "Guild Champion" in reply.text
    assert "Guild Legend" in reply.text
    assert JOIN_TEXT in reply.text
    assert await world.store.sitout_until(isla) is None, "no sit-out is recorded"
    assert "Ioseph" in counted(await app.run(isla, "partybonus"))


@M10
@pytest.mark.req("SE-7", "HV-3", "SE-4")
async def test_a_supporter_who_loses_the_role_gives_nothing(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())
    isla, sam = world.user("isla"), world.user("sam")
    before = await app.run(isla, "partybonus")
    await app.run(sam, "sitout", {"support": True})

    world.discord.set_roles(sam, frozenset())
    after = await app.run(isla, "partybonus")

    for name in SAMPLE_COUNTED:
        assert stat(after, name, "CM") == stat(before, name, "CM"), name
    assert after.report is not None
    assert {n.name: n.supporting for n in after.report.not_counted} == {
        "DM Sam": False,
        "Bob": False,
    }
    assert "Support" not in _not_counted_entry(after.text, "DM Sam")


@M10
@pytest.mark.req("SE-7")
async def test_sitting_out_again_replaces_the_sitout_and_restarts_its_time(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())
    isla, sam = world.user("isla"), world.user("sam")
    plain = await app.run(isla, "partybonus")

    await app.run(sam, "sitout", {"support": True})
    world.clock.advance(timedelta(hours=1))
    await app.run(sam, "sitout")
    after_plain = await app.run(isla, "partybonus")
    assert stat(after_plain, "Chris", "CM") == stat(plain, "Chris", "CM")
    assert await world.store.sitout_until(sam) == world.clock.now() + timedelta(hours=12)

    world.clock.advance(timedelta(hours=1))
    await app.run(sam, "sitout", {"support": True})
    after_support = await app.run(isla, "partybonus")
    assert stat(after_support, "Chris", "CM") == stat(plain, "Chris", "CM") + 2
    assert await world.store.sitout_until(sam) == world.clock.now() + timedelta(hours=12)


@M10
@pytest.mark.req("SE-7", "SE-2")
async def test_sitin_ends_a_supporting_sitout(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())
    isla, sam = world.user("isla"), world.user("sam")
    plain = await app.run(isla, "partybonus")
    await app.run(sam, "sitout", {"support": True})

    reply = await app.run(sam, "sitin")
    after = await app.run(isla, "partybonus")

    assert reply.private
    assert "Sable" in counted(after)
    # Counted again: Sable's Aura of Hope (+10) and DM Sam's Support (+2).
    assert stat(after, "Chris", "CM") == stat(plain, "Chris", "CM") + 12


@M10
@pytest.mark.req("SE-7", "SE-2", "TS-10")
async def test_a_supporting_sitout_ends_after_12_hours(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())
    isla, sam = world.user("isla"), world.user("sam")
    await app.run(sam, "sitout", {"support": True})

    world.clock.advance(timedelta(hours=11, minutes=59))
    assert "Sable" not in counted(await app.run(isla, "partybonus"))
    world.clock.advance(timedelta(minutes=2))
    assert "Sable" in counted(await app.run(isla, "partybonus"))


# ---------------------------------------------------------------- SE-8: the hint


@M10
@pytest.mark.req("SE-8")
@pytest.mark.parametrize(("handle", "role"), [("bob", "Guild Legend"), ("sam", "Guild Champion")])
async def test_a_plain_sitout_tells_an_allowed_player_about_support(
    make_world: MakeWorld, handle: str, role: str
) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())

    reply = await app.run(world.user(handle), "sitout")

    assert reply.private
    assert "/sitout support:true" in reply.text
    assert role in reply.text, "names the role that allows it"
    assert discord_timestamp(world.clock.now() + timedelta(hours=12)) in reply.text


@M10
@pytest.mark.req("SE-8")
@pytest.mark.parametrize("handle", ["isla", "kit", "maya"])  # Vanguard, Junior Adventurer, none
async def test_a_plain_sitout_doesnt_offer_support_to_anyone_else(
    make_world: MakeWorld, handle: str
) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())

    reply = await app.run(world.user(handle), "sitout")

    assert "support:true" not in reply.text
    assert await world.store.sitout_until(world.user(handle)) is not None


# ---------------------------------------------------------------- SE-4: marking supporters


@M10
@pytest.mark.req("SE-4", "SE-7")
@pytest.mark.parametrize("command", ["partybonus", "breakdown"])
async def test_the_not_counted_line_marks_a_supporter(make_world: MakeWorld, command: str) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())
    await app.run(world.user("sam"), "sitout", {"support": True})

    reply = await app.run(world.user("isla"), command)

    sam = _not_counted_entry(reply.text, "DM Sam")
    assert "giving Support" in sam
    assert discord_timestamp(world.clock.now() + timedelta(hours=12)) in sam
    assert "Support" not in _not_counted_entry(reply.text, "Bob"), "Bob's sit-out is plain"
    assert reply.report is not None
    assert {n.name: n.supporting for n in reply.report.not_counted} == {
        "DM Sam": True,
        "Bob": False,
    }


@M10
@pytest.mark.req("SE-7", "SE-2")
async def test_a_refused_supporting_sitout_leaves_an_existing_sitout_unchanged(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())
    isla = world.user("isla")  # Guild Vanguard
    await app.run(isla, "sitout")
    until = await world.store.sitout_until(isla)
    assert until is not None
    world.clock.advance(timedelta(minutes=30))

    reply = await app.run(isla, "sitout", {"support": True})

    assert reply.private
    assert "unchanged" in reply.text
    assert "not sitting out" not in reply.text
    assert discord_timestamp(until) in reply.text, "says when the existing sit-out ends"
    assert await world.store.sitout_until(isla) == until
    assert "Ioseph" not in counted(await app.run(world.user("kit"), "partybonus"))


@M10
@pytest.mark.req("SE-7", "SE-8")
async def test_the_sitout_replies_name_only_the_bonuses_the_callers_roles_allow(
    make_world: MakeWorld,
) -> None:
    data = catalog_data()
    guild = data["guilds"]["the_guild"]
    guild["from_roles"] = [
        {"name": "Support", "gives": {"CM": 2}, "while_sitting_out": ["Guild Legend"]},
        {"name": "Rally", "gives": {"CR": 1}, "while_sitting_out": ["Guild Champion"]},
    ]
    world = await make_world("sample-game")
    app = world.app_with(catalog=parse_catalog(data))

    supporting = await app.run(world.user("sam"), "sitout", {"support": True})  # Champion
    hint = await app.run(world.user("bob"), "sitout")  # Legend

    assert "Rally" in supporting.text
    assert "Support" not in supporting.text.replace("support:true", "")
    assert "Support" in hint.text
    assert "Rally" not in hint.text


@M10
@pytest.mark.req("SE-2", "SE-8")
async def test_a_plain_sitout_is_recorded_even_if_discord_cant_look_up_roles(
    make_world: MakeWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = await make_world("sample-game")
    app = world.app_with(catalog=supporter_catalog())

    async def unavailable(user_id: object) -> None:
        raise RuntimeError("Discord is unavailable")

    monkeypatch.setattr(world.discord, "member", unavailable)
    reply = await app.run(world.user("bob"), "sitout")

    assert reply.private
    assert await world.store.sitout_until(world.user("bob")) == world.clock.now() + timedelta(
        hours=12
    )
    assert "support:true" not in reply.text, "no roles known, so no hint"
