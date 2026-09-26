"""What characters have (requirements 6.3: HV-1 to HV-6), and retired entries (CT-6).

Uses the setup fixture: craig owns Crateris (Cult; High Priest, Holy Aura) and
Elowen (no guilds, nothing); ioan owns Ioseph (GoTH; Nuyaru's Love, Champion of
Power); cole owns Chris (Guild of Thieves; Guild Thief); olga owns Olga (Old Charm,
retired).
"""

from datetime import timedelta

import pytest

from awt_bonus.engine import Reason
from awt_bonus.store import CharacterRecord
from tests.support.text import counted, mentions, recipient, stat
from tests.support.world import MakeWorld, World

M3 = pytest.mark.milestone("M3")
M4 = pytest.mark.milestone("M4")


async def _get(world: World, name: str) -> CharacterRecord:
    record = await world.character(name)
    assert record is not None, f"no character {name}"
    return record


# ---------------------------------------------------------------- HV-1: /add and /remove


@M3
@pytest.mark.req("HV-1")
async def test_add_gives_a_character_a_catalog_entry(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "add", character="Elowen", entry="Bolstering Aura")
    await world.run("craig", "add", character="Elowen", entry="Wills ward stone")
    await world.run("craig", "add", character="Elowen", entry="Story Teller")

    elowen = await _get(world, "Elowen")
    assert set(elowen.entries) == {"bolstering_aura", "wills_ward_stone", "story_teller"}
    assert reply.private


@M3
@pytest.mark.req("HV-1", "CT-1")
async def test_add_refuses_anything_not_in_the_catalog(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "add", character="Elowen", entry="Mega Aura of Doom")

    assert (await _get(world, "Elowen")).entries == ()
    assert reply.text


@M3
@pytest.mark.req("HV-1")
async def test_remove_takes_away_anything_the_character_has(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "remove", character="Crateris", entry="Holy Aura")
    await world.run("craig", "remove", character="Crateris", entry="High Priest")

    crateris = await _get(world, "Crateris")
    assert crateris.entries == ()
    assert crateris.guilds == ("cult",)  # removing a rank doesn't leave the guild
    assert reply.private


@M3
@pytest.mark.req("HV-1")
async def test_remove_autocomplete_lists_what_the_character_has(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    choices = await world.autocomplete("craig", "remove", "entry", "", character="Crateris")
    labels = " | ".join(c.label for c in choices)

    assert "Holy Aura" in labels
    assert "High Priest" in labels
    assert "Wills ward stone" not in labels
    assert "Champion of Power" not in labels


@M3
@pytest.mark.req("HV-1")
async def test_add_autocomplete_labels_entries_with_kind_and_tree(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    choices = await world.autocomplete("craig", "add", "entry", "Holy", character="Elowen")

    assert "Holy Aura (Holy Knight skill)" in {c.label for c in choices}


@M4
@pytest.mark.req("HV-1")
async def test_add_autocomplete_shows_guild_entries_only_for_the_characters_guilds(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    crateris = " | ".join(
        c.label for c in await world.autocomplete("craig", "add", "entry", "", character="Crateris")
    )
    elowen = " | ".join(
        c.label for c in await world.autocomplete("craig", "add", "entry", "", character="Elowen")
    )

    assert "High Priest" in crateris  # a Cult rank; Crateris is in the Cult
    for guild_entry in ["Footpad", "Guild Thief", "Captain", "Seraph's Affection", "Chef"]:
        assert guild_entry not in crateris
    for guild_entry in ["High Priest", "Footpad", "Captain", "Seraph's Affection"]:
        assert guild_entry not in elowen
    assert "Holy Aura" in elowen  # entries outside guilds are always offered


@M4
@pytest.mark.req("HV-1", "CH-3")
async def test_add_autocomplete_uses_the_current_character_when_none_is_given(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    choices = await world.autocomplete("craig", "add", "entry", "High")
    assert "High Priest" in " | ".join(c.label for c in choices)  # current: Crateris (Cult)

    await world.run("craig", "play", character="Elowen")
    choices = await world.autocomplete("craig", "add", "entry", "High")
    assert "High Priest" not in " | ".join(c.label for c in choices)  # Elowen: no guilds


# ---------------------------------------------------------------- CT-6: retired entries


@M3
@pytest.mark.req("CT-6", "HV-1")
async def test_a_retired_entry_cant_be_added(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "add", character="Elowen", entry="Old Charm")
    assert (await _get(world, "Elowen")).entries == ()


@M3
@pytest.mark.req("CT-6")
async def test_characters_keep_a_retired_entry_and_it_still_counts(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("ioan", "partybonus")

    assert (await _get(world, "Olga")).entries == ("old_charm",)
    assert reply.report is not None
    received = [reply.report.give(a.give).entry for a in recipient(reply, "Ioseph").applied]
    assert "old_charm" in received


@M3
@pytest.mark.req("CT-6", "OUT-3a")
async def test_breakdown_marks_a_retired_entry(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("olga", "breakdown", character="Olga")
    assert "Old Charm" in reply.text
    assert mentions(reply.text, "retired")


# ---------------------------------------------------------------- HV-2: guild join and leave


@M4
@pytest.mark.req("HV-2")
async def test_joining_a_guild_records_membership_and_grants_nothing(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "guild join", character="Elowen", guild="Pirate Coalition")

    elowen = await _get(world, "Elowen")
    assert elowen.guilds == ("pirates",)
    assert elowen.entries == ()
    assert reply.private
    assert "/add Elowen" in reply.text  # tells the player to add their rank


@M4
@pytest.mark.req("HV-2")
async def test_leaving_a_guild_removes_its_ranks_and_boons_and_lists_them(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run(
        "craig", "guild leave", character="Crateris", guild="Cult of the Dragon"
    )

    crateris = await _get(world, "Crateris")
    assert crateris.guilds == ()
    assert crateris.entries == ("holy_aura",)
    assert "High Priest" in reply.text
    assert reply.private

    reply = await world.run(
        "ioan", "guild leave", character="Ioseph", guild="Guild of the Timeless Heroes"
    )
    ioseph = await _get(world, "Ioseph")
    assert ioseph.entries == ("champion_of_power",)
    assert "Nuyaru's Love" in reply.text


# ---------------------------------------------------------------- HV-3: Support from roles


@M4
@pytest.mark.req("HV-3")
async def test_support_comes_from_roles_not_guild_join(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "guild join", character="Crateris", guild="The Guild")
    reply = await world.run("craig", "partybonus")

    # Only Ioseph's player has a Guild rank role; Crateris gives no Support.
    assert reply.report is not None
    supporters = {
        reply.report.give(a.give).giver
        for a in recipient(reply, "Olga").applied
        if reply.report.give(a.give).bonus == "Support"
    }
    assert supporters == {world.user("ioan")}


@M4
@pytest.mark.req("HV-3")
async def test_roles_are_checked_each_time_and_apply_to_any_character(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run("ioan", "partybonus")
    # Olga: Support 2 (Ioseph), Nuyaru's Love 1, Champion of Power 5.
    assert stat(reply, "Olga", "CM") == 8

    world.discord.set_roles(world.user("craig"), frozenset({"Guild Veteran"}))
    reply = await world.run("ioan", "partybonus")
    assert stat(reply, "Olga", "CM") == 10  # plus Support from Crateris

    await world.run("craig", "play", character="Elowen")
    reply = await world.run("ioan", "partybonus")
    assert "Elowen" in counted(reply)
    assert stat(reply, "Olga", "CM") == 10  # Support now from Elowen


@M4
@pytest.mark.req("HV-3", "OUT-3")
async def test_several_guild_rank_roles_give_support_once_and_are_all_shown(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    world.discord.set_roles(world.user("ioan"), frozenset({"Guild Vanguard", "Guild Legend"}))
    reply = await world.run("ioan", "partybonus")
    assert stat(reply, "Olga", "CM") == 8

    reply = await world.run("olga", "breakdown")
    assert "Guild Vanguard" in reply.text
    assert "Guild Legend" in reply.text


# ---------------------------------------------------------------- HV-4: checks when adding


@M4
@pytest.mark.req("HV-4")
@pytest.mark.parametrize(
    ("entry", "join"),
    [
        ("Captain", "/guild join Elowen Pirate Coalition"),
        ("Seraph's Affection", "/guild join Elowen Guild of the Timeless Heroes"),
        ("Chef", "/guild join Elowen Order of Cookery"),
    ],
)
async def test_adding_a_guild_entry_without_membership_is_refused_with_the_join_command(
    make_world: MakeWorld, entry: str, join: str
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "add", character="Elowen", entry=entry)

    assert (await _get(world, "Elowen")).entries == ()
    assert join in reply.text


@M4
@pytest.mark.req("HV-4")
async def test_rank_itself_is_never_checked(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "guild join", character="Elowen", guild="Guild of Thieves")
    await world.run("craig", "add", character="Elowen", entry="Guild Thief")  # no Footpad first

    assert (await _get(world, "Elowen")).entries == ("guild_thief",)


@M3
@pytest.mark.req("HV-4")
async def test_devotion_iii_with_no_auras_is_added_with_a_warning(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "add", character="Elowen", entry="Devotion III")

    assert (await _get(world, "Elowen")).entries == ("devotion_3",)
    assert mentions(reply.text, "aura")


# ---------------------------------------------------------------- HV-5: audit log


@M3
@pytest.mark.req("HV-5", "NF-10")
@pytest.mark.parametrize(
    ("command", "options"),
    [
        ("add", {"character": "Elowen", "entry": "Holy Aura"}),
        ("remove", {"character": "Crateris", "entry": "Holy Aura"}),
        ("character level", {"character": "Elowen", "level": 13}),
        ("character rename", {"character": "Elowen", "new": "Elowyn"}),
        ("character register", {"name": "Pip"}),
    ],
)
async def test_every_change_to_a_character_is_audited(
    make_world: MakeWorld, command: str, options: dict[str, str | int]
) -> None:
    world = await make_world("setup")
    before = len(await world.store.audit_log())
    await world.run("craig", command, **options)

    log = await world.store.audit_log()
    assert len(log) > before
    record = log[-1]
    assert record.actor == world.user("craig")
    assert record.at == world.clock.now()
    assert record.at.utcoffset() == timedelta(0)
    assert record.before is not None or record.after is not None


@M4
@pytest.mark.req("HV-5")
@pytest.mark.parametrize("command", ["guild join", "guild leave"])
async def test_guild_changes_are_audited(make_world: MakeWorld, command: str) -> None:
    world = await make_world("setup")
    guild = "Cult of the Dragon" if command == "guild leave" else "Pirate Coalition"
    character = "Crateris" if command == "guild leave" else "Elowen"
    before = len(await world.store.audit_log())
    await world.run("craig", command, character=character, guild=guild)

    log = await world.store.audit_log()
    assert len(log) > before
    assert log[-1].actor == world.user("craig")
    assert log[-1].at == world.clock.now()


# ---------------------------------------------------------------- HV-6: one holder at a time


@M3
@pytest.mark.req("HV-6")
async def test_a_one_holder_title_is_refused_while_held_naming_the_holder(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "add", character="Elowen", entry="Champion of Power")

    assert (await _get(world, "Elowen")).entries == ()
    assert "Ioseph" in reply.text


@M3
@pytest.mark.req("HV-6")
async def test_a_one_holder_title_passes_on_when_removed(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("ioan", "remove", character="Ioseph", entry="Champion of Power")
    await world.run("craig", "add", character="Elowen", entry="Champion of Power")

    assert (await _get(world, "Elowen")).entries == ("champion_of_power",)


@M4
@pytest.mark.req("HV-6", "HV-2")
async def test_high_priest_is_one_holder_and_passes_on_when_the_holder_leaves(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    await world.run("ioan", "guild join", character="Ioseph", guild="Cult of the Dragon")
    reply = await world.run("ioan", "add", character="Ioseph", entry="High Priest")
    assert "high_priest" not in (await _get(world, "Ioseph")).entries
    assert "Crateris" in reply.text

    await world.run("craig", "guild leave", character="Crateris", guild="Cult of the Dragon")
    await world.run("ioan", "add", character="Ioseph", entry="High Priest")
    assert "high_priest" in (await _get(world, "Ioseph")).entries


@M3
@pytest.mark.req("HV-6", "4.4")
async def test_entries_that_arent_one_holder_can_be_held_by_many(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "add", character="Elowen", entry="Holy Aura")  # Crateris has it too
    assert (await _get(world, "Elowen")).entries == ("holy_aura",)


@M3
@pytest.mark.req("4.1", "OUT-2")
async def test_giver_is_excluded_from_their_own_bonus_through_the_commands(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "mybonus")
    assert reply.report is not None
    report = reply.report
    reasons = {
        (report.give(n.give).entry, n.reason) for n in recipient(reply, "Crateris").not_applied
    }
    assert ("holy_aura", Reason.GIVER_EXCLUDED) in reasons
