"""Item classes in commands and output (requirements 6.8: IC-1 to IC-5, CT-10, 9.2).

Uses two fixtures:
  - setup: craig owns Crateris (current) and Elowen; mallory tries to change them.
  - item-class-game: the section 9.2 party. Counts aren't stored in fixtures, so
    ``play_9_2`` sets them with /character items, from the section 9.2 table.

The test catalog has the passion and glizzy classes and test versions of the
three class items (requirements 8.4 and 8.5).
"""

from datetime import UTC, datetime

import pytest

from awt_bonus.admin import remove_character, transfer
from awt_bonus.commands import OptionValue, Reply
from tests.support.text import lines_with, mentions, totals
from tests.support.world import MakeWorld, World

pytestmark = pytest.mark.milestone("M8")

NOW = datetime(2026, 9, 25, 20, 0, tzinfo=UTC)


async def set_count(
    world: World, handle: str, character: str, item_class: str, count: int
) -> Reply:
    """Run /character items (IC-2). ``class`` is a Python keyword, so no ``world.run``."""
    options: dict[str, OptionValue] = {"character": character, "class": item_class, "count": count}
    return await world.app.run(world.user(handle), "character items", options)


async def play_9_2(make_world: MakeWorld) -> World:
    """The section 9.2 item class game, with its counts set."""
    world = await make_world("item-class-game")
    for handle, character, item_class, count in [
        ("eli", "Elizor", "passion", 2),
        ("cam", "Chris", "passion", 1),
        ("mia", "Mira", "glizzy", 1),
        ("gil", "Gus", "glizzy", 1),
        ("tia", "Tess", "glizzy", 2),
        ("sam", "Sable", "passion", 3),
    ]:
        await set_count(world, handle, character, item_class, count)
    return world


async def character_list(world: World, handle: str) -> str:
    return (await world.run(handle, "character list")).text


# ---------------------------------------------------------------- IC-2: /character items


@pytest.mark.req("IC-2", "IC-1")
async def test_setting_a_count_confirms_it_privately_and_lists_the_other_counts(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    await set_count(world, "craig", "Crateris", "glizzy", 1)
    reply = await set_count(world, "craig", "Crateris", "passion", 2)

    assert reply.private
    assert mentions(reply.text, "Crateris")
    assert lines_with(reply.text, "2", "passion"), "confirms the new count"
    assert lines_with(reply.text, "glizzy", "1"), "lists the other counts"
    assert "Item classes: passion 2, glizzy 1" in await character_list(world, "craig")


@pytest.mark.req("IC-2")
@pytest.mark.parametrize("count", [1, 15, 30])
async def test_a_count_from_1_to_30_is_accepted(make_world: MakeWorld, count: int) -> None:
    world = await make_world("setup")
    await set_count(world, "craig", "Elowen", "passion", count)
    assert f"Item classes: passion {count}" in await character_list(world, "craig")


@pytest.mark.req("IC-2")
@pytest.mark.parametrize("count", [-1, 31, 200])
async def test_a_count_outside_0_to_30_is_refused_and_changes_nothing(
    make_world: MakeWorld, count: int
) -> None:
    world = await make_world("setup")
    await set_count(world, "craig", "Elowen", "passion", 3)
    reply = await set_count(world, "craig", "Elowen", "passion", count)

    assert reply.private
    assert "30" in reply.text, "says what's allowed"
    assert "Item classes: passion 3" in await character_list(world, "craig")


@pytest.mark.req("IC-2", "IC-1", "IC-3")
async def test_0_clears_a_count(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await set_count(world, "craig", "Elowen", "passion", 3)
    assert "Item classes: passion 3" in await character_list(world, "craig")
    await set_count(world, "craig", "Elowen", "passion", 0)

    assert "Item classes" not in await character_list(world, "craig")


@pytest.mark.req("IC-2", "CT-10")
async def test_an_unknown_class_is_refused(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await set_count(world, "craig", "Elowen", "sausage", 1)

    assert reply.private
    assert mentions(reply.text, "sausage")
    assert "Item classes" not in await character_list(world, "craig")


@pytest.mark.req("IC-2", "CT-10")
@pytest.mark.parametrize(
    ("typed", "expected"), [("hot", "glizzy"), ("Will", "passion"), ("pas", "passion")]
)
async def test_class_autocomplete_matches_display_names_and_other_names(
    make_world: MakeWorld, typed: str, expected: str
) -> None:
    world = await make_world("setup")
    choices = await world.autocomplete(
        "craig", "character items", "class", typed, character="Elowen"
    )
    assert expected in {c.value for c in choices}


@pytest.mark.req("IC-2", "HV-5")
async def test_each_count_change_is_written_to_the_audit_log(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    elowen = await world.character("Elowen")
    assert elowen is not None
    before = len(await world.store.audit_log())

    await set_count(world, "craig", "Elowen", "passion", 2)
    await set_count(world, "craig", "Elowen", "passion", 0)

    records = (await world.store.audit_log())[before:]
    assert len(records) == 2
    assert {r.actor for r in records} == {world.user("craig")}
    assert {r.character_id for r in records} == {elowen.id}
    assert records[0].before != records[0].after


@pytest.mark.req("IC-2", "NF-4", "TS-9")
async def test_no_player_can_set_another_players_counts(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await set_count(world, "craig", "Crateris", "passion", 1)
    reply = await set_count(world, "mallory", "Crateris", "passion", 5)

    assert reply.private
    assert "Item classes: passion 1" in await character_list(world, "craig")
    assert not [r for r in await world.store.audit_log() if r.actor == world.user("mallory")]


# ---------------------------------------------------------------- IC-3: showing counts


@pytest.mark.req("IC-3")
async def test_character_list_shows_only_counts_above_0(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await set_count(world, "craig", "Crateris", "glizzy", 1)

    text = await character_list(world, "craig")
    assert "Item classes: glizzy 1" in text
    assert "passion 0" not in text
    assert text.count("Item classes") == 1, "Elowen has none, so no line for Elowen"


@pytest.mark.req("IC-3", "OUT-3a")
async def test_a_character_breakdown_shows_the_counts_and_how_to_change_them(
    make_world: MakeWorld,
) -> None:
    world = await play_9_2(make_world)
    reply = await world.run("eli", "breakdown", character="Elizor")

    assert lines_with(reply.text, "passion", "2")
    assert "/character items" in reply.text


@pytest.mark.req("IC-3", "4.14", "OUT-3a")
async def test_a_character_breakdown_says_no_passion_item_in_use(make_world: MakeWorld) -> None:
    world = await play_9_2(make_world)
    reply = await world.run("mia", "breakdown", character="Mira")

    assert lines_with(reply.text, "Aura of Passion", "no passion item in use")


@pytest.mark.req("IC-3", "4.15", "OUT-3a")
async def test_a_token_holder_is_told_when_the_party_has_no_passion_items(
    make_world: MakeWorld,
) -> None:
    world = await play_9_2(make_world)
    await set_count(world, "eli", "Elizor", "passion", 0)
    await set_count(world, "cam", "Chris", "passion", 0)
    reply = await world.run("cam", "breakdown", character="Chris")

    assert lines_with(
        reply.text, "Will Passions Adventure Token", "no passion items in use in the party"
    )


@pytest.mark.req("IC-3", "4.15", "OUT-3")
async def test_the_party_breakdown_shows_the_tokens_working_by_wearer(
    make_world: MakeWorld,
) -> None:
    world = await play_9_2(make_world)
    reply = await world.run("cam", "breakdown")

    [working] = lines_with(reply.text, "Will Passions Adventure Token", "Chris 1", "Elizor 2")
    assert "+6" in working
    assert "Sable" not in working, "sitting out, so not counted"


@pytest.mark.req("IC-3", "4.14", "OUT-2")
async def test_mybonus_notes_a_class_bonus_missed_with_the_command_to_fix_it(
    make_world: MakeWorld,
) -> None:
    world = await play_9_2(make_world)
    reply = await world.run("mia", "mybonus")

    [note] = lines_with(reply.text, "Aura of Passion")
    assert "/character items Mira passion 1" in note
    assert reply.private


@pytest.mark.req("IC-3", "9.2")
@pytest.mark.parametrize(
    ("handle", "character", "missed"),
    [
        ("mia", "Mira", {"Aura of Passion"}),
        ("gil", "Gus", {"Aura of Passion"}),
        ("tia", "Tess", {"Aura of Passion"}),
        ("eli", "Elizor", {"Glizzy Support"}),
        ("cam", "Chris", {"Glizzy Support"}),
    ],
)
async def test_the_item_class_game_mybonus_notes(
    make_world: MakeWorld, handle: str, character: str, missed: set[str]
) -> None:
    world = await play_9_2(make_world)
    text = (await world.run(handle, "mybonus")).text

    noted = {
        b for b in ["Aura of Passion", "Glizzy Support"] if lines_with(text, b, "/character items")
    }
    assert noted == missed, character


@pytest.mark.req("IC-3")
async def test_mybonus_has_one_note_for_each_class_bonus_missed(make_world: MakeWorld) -> None:
    world = await play_9_2(make_world)
    await set_count(world, "tia", "Tess", "glizzy", 0)
    text = (await world.run("tia", "mybonus")).text

    assert len(lines_with(text, "/character items Tess passion 1")) == 1
    assert len(lines_with(text, "/character items Tess glizzy 1")) == 1


@pytest.mark.req("IC-3")
async def test_mybonus_has_no_class_note_when_nothing_is_missed_for_a_count(
    make_world: MakeWorld,
) -> None:
    world = await play_9_2(make_world)
    await set_count(world, "gil", "Gus", "passion", 1)
    assert "Item classes: passion 1, glizzy 1" in await character_list(world, "gil")
    text = (await world.run("gil", "mybonus")).text

    assert "/character items" not in text


@pytest.mark.req("IC-3", "CT-8", "CT-10")
async def test_catalog_shows_a_class_its_other_names_and_the_entries_that_use_it(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "catalog", entry="passion")

    assert reply.private
    assert "Will Passion" in reply.text
    assert "Path of Passion" in reply.text, "the description"
    assert "Will Passion's Pendant" in reply.text
    assert "Will Passions Adventure Token" in reply.text
    assert "/character items" in reply.text


@pytest.mark.req("IC-3", "CT-8")
@pytest.mark.parametrize(
    ("entry", "says"),
    [
        ("Will Passion's Pendant", "needs a passion item in use"),
        ("Will Passions Adventure Token", "per passion item in use in the party"),
    ],
)
async def test_catalog_says_when_an_entry_depends_on_a_class(
    make_world: MakeWorld, entry: str, says: str
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "catalog", entry=entry)
    assert mentions(reply.text, says)


# ---------------------------------------------------------------- 9.2: the item class game


@pytest.mark.req("9.2", "4.14", "4.15", "IC-4", "IC-5")
async def test_the_item_class_game_partybonus_totals(make_world: MakeWorld) -> None:
    world = await play_9_2(make_world)
    reply = await world.run("eli", "partybonus")

    assert totals(reply, "Elizor") == {}
    assert totals(reply, "Chris") == {"CM": 6, "Damage": 5}
    for name in ["Mira", "Gus", "Tess"]:
        assert totals(reply, name) == {"CM": 3, "Damage": 5}, name


@pytest.mark.req("9.2", "IC-1")
async def test_changing_a_count_changes_the_next_calculation(make_world: MakeWorld) -> None:
    world = await play_9_2(make_world)
    await set_count(world, "mia", "Mira", "passion", 1)
    reply = await world.run("eli", "partybonus")

    assert totals(reply, "Mira") == {"CM": 3, "Damage": 7}, "Aura of Passion now applies"
    assert totals(reply, "Chris") == {"CM": 8, "Damage": 6}, "4 passion items in the party"


# ---------------------------------------------------------------- the maintainer tools


@pytest.mark.req("IC-1", "CH-2", "AD-2")
async def test_removing_a_character_removes_its_counts(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await set_count(world, "craig", "Crateris", "passion", 2)
    assert "Item classes: passion 2" in await character_list(world, "craig")

    async def snapshot() -> None:
        return None

    await remove_character(
        world.store, world.catalog, "Crateris", confirmed=True, snapshot=snapshot, now=NOW
    )
    await world.run("newbie", "character register", name="Crateris")

    assert "Item classes" not in await character_list(world, "newbie"), "nothing left behind"


@pytest.mark.req("IC-1", "AD-2")
async def test_a_transferred_character_keeps_its_counts(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await set_count(world, "craig", "Elowen", "glizzy", 2)

    async def snapshot() -> None:
        return None

    await transfer(
        world.store,
        world.catalog,
        "Elowen",
        int(world.user("newbie")),
        confirmed=True,
        snapshot=snapshot,
        now=NOW,
    )

    assert "Item classes: glizzy 2" in await character_list(world, "newbie")
