"""Characters and level (requirements 6.1: CH-1 to CH-6).

Uses the setup fixture: craig owns Crateris (current) and Elowen; ioan owns
Ioseph; newbie has no characters yet. Permission checks are in
tests/nonfunctional/test_permissions.py.
"""

import pytest

from awt_bonus.settings import Settings
from tests.support.text import mentions, recipient, stat
from tests.support.world import MakeWorld

pytestmark = pytest.mark.milestone("M3")


# ---------------------------------------------------------------- CH-1


@pytest.mark.req("CH-1")
async def test_register_creates_a_character_owned_by_the_caller(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("newbie", "character register", name="Pip", level=5)

    pip = await world.character("Pip")
    assert pip is not None
    assert pip.owner == world.user("newbie")
    assert pip.level == 5
    assert reply.private


@pytest.mark.req("CH-1")
async def test_a_player_can_register_several_characters(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("newbie", "character register", name="Pip")
    await world.run("newbie", "character register", name="Pod")

    names = {c.name for c in await world.store.characters_of(world.user("newbie"))}
    assert names == {"Pip", "Pod"}


@pytest.mark.req("CH-1")
@pytest.mark.parametrize("taken", ["Crateris", "crateris", "CRATERIS"])
async def test_a_taken_name_is_refused_ignoring_case(make_world: MakeWorld, taken: str) -> None:
    world = await make_world("setup")
    reply = await world.run("newbie", "character register", name=taken)

    assert await world.store.characters_of(world.user("newbie")) == []
    crateris = await world.character("Crateris")
    assert crateris is not None
    assert crateris.owner == world.user("craig")
    assert reply.text, "the refusal must say something (with a suggestion to pick a variant)"


@pytest.mark.req("CH-1")
async def test_a_name_always_means_one_character_ignoring_case(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "play", character="elowen")

    current = await world.store.current_character(world.user("craig"))
    assert current is not None
    assert current.name == "Elowen"


@pytest.mark.req("CH-1")
async def test_character_names_autocomplete(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    choices = await world.autocomplete("craig", "play", "character", "")
    assert {"Crateris", "Elowen"} <= {c.value for c in choices}

    choices = await world.autocomplete("craig", "character rename", "character", "Elo")
    assert "Elowen" in {c.value for c in choices}
    assert "Crateris" not in {c.value for c in choices}


# ---------------------------------------------------------------- CH-2


@pytest.mark.req("CH-2")
async def test_a_player_can_rename_their_character(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    before = await world.character("Crateris")
    reply = await world.run("craig", "character rename", character="Crateris", new="Kratos")

    after = await world.character("Kratos")
    assert before is not None
    assert after is not None
    assert after.id == before.id
    assert after.entries == before.entries
    assert after.guilds == before.guilds
    assert after.level == before.level
    assert await world.character("Crateris") is None
    assert reply.private


@pytest.mark.req("CH-2", "CH-1")
async def test_renaming_to_a_taken_name_is_refused(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "character rename", character="Elowen", new="ioseph")

    assert await world.character("Elowen") is not None
    ioseph = await world.character("Ioseph")
    assert ioseph is not None
    assert ioseph.owner == world.user("ioan")


@pytest.mark.req("CH-2")
async def test_renaming_frees_the_old_name(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "character rename", character="Elowen", new="Elowyn")
    await world.run("newbie", "character register", name="Elowen")

    elowen = await world.character("Elowen")
    assert elowen is not None
    assert elowen.owner == world.user("newbie")


# ---------------------------------------------------------------- CH-3


@pytest.mark.req("CH-3")
async def test_the_first_registered_character_becomes_current(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("newbie", "character register", name="Pip")
    await world.run("newbie", "character register", name="Pod")

    current = await world.store.current_character(world.user("newbie"))
    assert current is not None
    assert current.name == "Pip"


@pytest.mark.req("CH-3")
async def test_play_sets_the_current_character_until_changed(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "play", character="Elowen")
    await world.run("craig", "character level", character="Crateris", level=23)
    await world.run("craig", "partybonus")

    current = await world.store.current_character(world.user("craig"))
    assert current is not None
    assert current.name == "Elowen"
    assert reply.private


@pytest.mark.req("CH-3", "SE-3")
async def test_commands_with_no_character_use_the_current_one(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "mybonus")
    assert "Crateris" in reply.text
    assert recipient(reply, "Crateris").user_id == world.user("craig")

    await world.run("craig", "play", character="Elowen")
    reply = await world.run("craig", "mybonus")
    assert "Elowen" in reply.text
    assert recipient(reply, "Elowen").user_id == world.user("craig")


# ---------------------------------------------------------------- CH-4


@pytest.mark.req("CH-4")
@pytest.mark.parametrize("level", [1, 42, 75])
async def test_a_level_from_1_to_the_maximum_is_accepted(make_world: MakeWorld, level: int) -> None:
    world = await make_world("setup")
    await world.run("craig", "character level", character="Elowen", level=level)

    elowen = await world.character("Elowen")
    assert elowen is not None
    assert elowen.level == level


@pytest.mark.req("CH-4")
@pytest.mark.parametrize("level", [0, -1, 76, 1000])
async def test_a_level_outside_1_to_the_maximum_is_refused(
    make_world: MakeWorld, level: int
) -> None:
    world = await make_world("setup")
    await world.run("craig", "character level", character="Elowen", level=level)
    await world.run("newbie", "character register", name="Pip", level=level)

    elowen = await world.character("Elowen")
    assert elowen is not None
    assert elowen.level == 12
    pip = await world.character("Pip")
    assert pip is None or pip.level is None


@pytest.mark.req("CH-4")
async def test_the_level_can_be_left_blank_or_cleared(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("newbie", "character register", name="Pip")
    await world.run("craig", "character level", character="Elowen", level="clear")

    pip = await world.character("Pip")
    elowen = await world.character("Elowen")
    assert pip is not None
    assert pip.level is None
    assert elowen is not None
    assert elowen.level is None


@pytest.mark.req("CH-4")
async def test_the_maximum_level_is_configurable(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    app = world.app_with(
        settings=Settings(request_channel="bonus-bot-support", sitout_hours=12, max_level=80)
    )
    await app.run(world.user("craig"), "character level", {"character": "Elowen", "level": 80})
    await app.run(world.user("craig"), "character level", {"character": "Crateris", "level": 81})

    elowen = await world.character("Elowen")
    crateris = await world.character("Crateris")
    assert elowen is not None
    assert elowen.level == 80
    assert crateris is not None
    assert crateris.level == 22


# ---------------------------------------------------------------- CH-5 (levels fixture)


@pytest.mark.req("CH-5", "OUT-2", "4.10")
async def test_mybonus_notes_a_bonus_missed_because_the_level_is_missing(
    make_world: MakeWorld,
) -> None:
    world = await make_world("levels")
    reply = await world.run("noor", "mybonus")

    assert stat(reply, "Nola", "CM") == 0
    assert "/character level" in reply.text
    assert reply.private


@pytest.mark.req("CH-5", "OUT-2")
@pytest.mark.parametrize(("handle", "name"), [("tom", "Tenna"), ("olly", "Otto"), ("opie", "Opal")])
async def test_no_level_note_when_recording_a_level_wouldnt_help(
    make_world: MakeWorld, handle: str, name: str
) -> None:
    world = await make_world("levels")
    reply = await world.run(handle, "mybonus")

    assert name in reply.text
    assert "/character level" not in reply.text


@pytest.mark.req("CH-5", "4.10", "TS-2")
async def test_level_based_bonuses_follow_the_recipients_level(make_world: MakeWorld) -> None:
    world = await make_world("levels")
    reply = await world.run("hana", "partybonus")

    assert stat(reply, "Tenna", "CM") == 10  # exactly 10
    assert stat(reply, "Nix", "Damage") == 1  # level 9
    assert stat(reply, "Nix", "CM") == 0
    assert stat(reply, "Nola", "CM") == 0  # no level
    assert stat(reply, "Nola", "Damage") == 0


# ---------------------------------------------------------------- CH-6


@pytest.mark.req("CH-6", "NF-10")
async def test_the_date_a_level_was_last_updated_is_stored(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "character level", character="Elowen", level=13)

    elowen = await world.character("Elowen")
    assert elowen is not None
    assert elowen.level_updated_at == world.clock.now()


@pytest.mark.req("CH-6", "OUT-3a")
async def test_breakdown_shows_the_level(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "breakdown", character="Crateris")
    assert mentions(reply.text, "level 22")
