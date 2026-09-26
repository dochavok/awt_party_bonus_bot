"""Permissions (NF-4, TS-9, CH-1): no player can change another player's characters,
whatever Discord roles they have. Every command that acts on a character is checked.

Mallory has Guild Legend, Admin, Moderator, Server Owner and DM roles, and tries
each command on Craig's characters (setup fixture).
"""

import pytest

from awt_bonus.commands import OptionValue
from tests.support.world import MakeWorld, World


async def _state(world: World) -> object:
    """Everything a character command could change for Craig's characters."""
    craig = world.user("craig")
    characters = sorted(
        (c.name, c.level, c.level_updated_at, c.entries, c.guilds)
        for c in await world.store.characters_of(craig)
    )
    current = await world.store.current_character(craig)
    return characters, current.name if current else None


_ATTEMPTS: list[tuple[str, str, dict[str, OptionValue]]] = [
    ("M3", "character rename", {"character": "Crateris", "new": "Stolen"}),
    ("M3", "character level", {"character": "Crateris", "level": 1}),
    ("M3", "character level", {"character": "Crateris", "level": "clear"}),
    ("M3", "add", {"character": "Elowen", "entry": "Holy Aura"}),
    ("M3", "remove", {"character": "Crateris", "entry": "Holy Aura"}),
    ("M3", "remove", {"character": "Crateris", "entry": "High Priest"}),
    ("M3", "play", {"character": "Crateris"}),
    ("M4", "guild join", {"character": "Elowen", "guild": "Pirate Coalition"}),
    ("M4", "guild leave", {"character": "Crateris", "guild": "Cult of the Dragon"}),
]


@pytest.mark.req("NF-4", "TS-9", "CH-1")
@pytest.mark.parametrize(
    ("command", "options"),
    [
        pytest.param(
            command,
            options,
            marks=pytest.mark.milestone(milestone),
            id=f"{command}-{'-'.join(map(str, options.values()))}",
        )
        for milestone, command, options in _ATTEMPTS
    ],
)
async def test_no_player_can_change_another_players_character(
    make_world: MakeWorld, command: str, options: dict[str, OptionValue]
) -> None:
    world = await make_world("setup")
    before = await _state(world)
    reply = await world.run("mallory", command, **options)

    assert await _state(world) == before, f"/{command} changed Craig's character"
    assert reply.private
    mallory_current = await world.store.current_character(world.user("mallory"))
    assert mallory_current is not None
    assert mallory_current.name == "Mal", "nobody can play someone else's character"


@pytest.mark.milestone("M3")
@pytest.mark.req("NF-4", "TS-9")
async def test_the_owner_can_make_the_same_changes(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "character level", character="Crateris", level=23)
    await world.run("craig", "remove", character="Crateris", entry="Holy Aura")

    crateris = await world.character("Crateris")
    assert crateris is not None
    assert crateris.level == 23
    assert "holy_aura" not in crateris.entries


@pytest.mark.milestone("M3")
@pytest.mark.req("NF-4", "SE-2")
async def test_sitout_only_ever_affects_the_caller(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("mallory", "sitout")

    assert await world.store.sitout_until(world.user("mallory")) is not None
    for other in ["craig", "ioan", "olga", "cole", "newbie"]:
        assert await world.store.sitout_until(world.user(other)) is None, other
