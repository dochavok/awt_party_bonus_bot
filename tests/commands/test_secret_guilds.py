"""Secret guilds (requirements 6.4: SG-1 to SG-5) and the secrecy tests (TS-6).

The sample game: Chris (Guild Thief) and Mira (Footpad) are in the Guild of
Thieves, a secret guild. Cole plays Chris; Maya plays Mira. Nobody else is a
member.

Line-based checks: a member's name must never share a line with anything that
marks a secret guild bonus, so no output ever says who gave one or who belongs.
A recipient's own totals may show a secret amount (SG-4), so these checks are by
line. The unnamed secret guild block itself is checked whole (TF-7): no line in it
may name anyone, including lines that don't say "secret".
"""

import re

import pytest

from awt_bonus.commands import OptionValue
from tests.support.text import lines_with, stat
from tests.support.world import MakeWorld, World

pytestmark = pytest.mark.milestone("M4")

MEMBER_NAMES = ["Chris", "Mira", "Cole", "Maya"]
SECRET_ABILITIES = ["Rat Pack", "Leadership", "Guild Thief", "Footpad", "Burglar"]
SECRET_MARKERS = [*SECRET_ABILITIES, "Guild of Thieves", "Thieves", "secret", "Secret"]
CHARACTERS = ["Ioseph", "Kael", "Crateris", "Chris", "Mira"]


def _assert_no_member_next_to_a_secret(text: str) -> None:
    for name in MEMBER_NAMES:
        for marker in SECRET_MARKERS:
            assert not lines_with(text, name, marker), f"{name!r} next to {marker!r}"


_SEPARATOR = re.compile(r"^\s*$|^-{3,}\s*$|^```")


def _secret_blocks(text: str) -> list[list[str]]:
    """Each block of output that starts with a secret guild heading, as its lines.

    A block runs until a blank line, a ``---`` rule or a code fence, so it includes
    the wrapped and indented lines under the heading.
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in [*text.splitlines(), ""]:
        if _SEPARATOR.match(line):
            if current and "secret guild" in current[0].casefold():
                blocks.append(current)
            current = []
        else:
            current.append(line)
    return blocks


def _everyone(world: World) -> set[str]:
    """Every character name and Discord display name in the fixture."""
    names = {m.name for m in world.spec.discord.members}
    names |= {c.name for p in world.spec.players for c in p.characters}
    return names


def _assert_secret_blocks_name_nobody(world: World, text: str) -> None:
    for block in _secret_blocks(text):
        for line in block:
            named = {n for n in _everyone(world) if re.search(rf"\b{re.escape(n)}\b", line)}
            assert not named, f"the secret guild block names {named}: {line!r}"


def _views() -> list[tuple[str, str, dict[str, OptionValue]]]:
    """Every output a non-member can see in the sample game."""
    views: list[tuple[str, str, dict[str, OptionValue]]] = []
    for viewer in ["isla", "kit", "cora", "dana"]:
        views.append((viewer, "partybonus", {}))
        views.append((viewer, "partybonus", {"private": True}))
        views.append((viewer, "breakdown", {}))
        for character in CHARACTERS:
            views.append((viewer, "breakdown", {"character": character}))
            views.append((viewer, "mybonus", {"character": character}))
    return views


# ---------------------------------------------------------------- TS-6, SG-3, SG-4


@pytest.mark.req("TS-6", "SG-3", "SG-4", "OUT-6", "NF-5")
@pytest.mark.parametrize(
    ("viewer", "command", "options"),
    _views(),
    ids=[f"{v}-{c}-{'-'.join(map(str, o.values())) or 'party'}" for v, c, o in _views()],
)
async def test_a_non_member_never_sees_who_is_in_the_secret_guild(
    make_world: MakeWorld, viewer: str, command: str, options: dict[str, OptionValue]
) -> None:
    world = await make_world("sample-game")
    reply = await world.run(viewer, command, **options)

    assert reply.text
    _assert_no_member_next_to_a_secret(reply.text)
    _assert_secret_blocks_name_nobody(world, reply.text)
    for ability in SECRET_ABILITIES:
        assert ability not in reply.text, f"{ability} must not be named to a non-member"


@pytest.mark.req("SG-3", "SG-4")
@pytest.mark.parametrize("viewer", ["cole", "maya"])
async def test_members_dont_see_who_the_other_members_are_in_the_party_breakdown(
    make_world: MakeWorld, viewer: str
) -> None:
    world = await make_world("sample-game")
    for command, options in [
        ("breakdown", {}),
        ("partybonus", {}),
        ("breakdown", {"character": "Ioseph"}),
        ("breakdown", {"character": "Crateris"}),
    ]:
        reply = await world.run(viewer, command, **options)
        assert "Ioseph" in reply.text
        _assert_no_member_next_to_a_secret(reply.text)
        _assert_secret_blocks_name_nobody(world, reply.text)


@pytest.mark.req("SG-4", "9.1")
@pytest.mark.dm("Q6")
async def test_secret_guild_bonuses_are_included_in_public_totals(make_world: MakeWorld) -> None:
    world = await make_world("sample-game")
    reply = await world.run("isla", "partybonus")

    assert not reply.private
    assert stat(reply, "Chris", "CM") == 23
    assert stat(reply, "Chris", "CR stealth") == 12
    assert stat(reply, "Chris", "CR escape") == 11
    assert stat(reply, "Mira", "CM") == 33


@pytest.mark.req("SG-4", "OUT-3")
async def test_a_non_member_sees_one_unnamed_secret_guild_bonus_block(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("isla", "breakdown")

    blocks = _secret_blocks(reply.text)
    assert len(blocks) == 1, f"one secret guild block, not {len(blocks)}"
    assert len(blocks[0]) > 1, "the block's own lines are checked, not just its heading"
    _assert_secret_blocks_name_nobody(world, reply.text)
    for ability in SECRET_ABILITIES:
        assert ability not in reply.text, f"{ability} must not be named in the party breakdown"


# ---------------------------------------------------------------- SG-5


@pytest.mark.req("SG-5", "OUT-2")
@pytest.mark.dm("Q6")
async def test_a_member_sees_secret_bonuses_in_detail_with_a_count_not_names(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("maya", "mybonus", character="Mira")

    assert reply.private
    rat_pack = lines_with(reply.text, "Rat Pack")
    assert rat_pack, "Rat Pack is shown to a member"
    assert all("(1 other member present)" in line for line in rat_pack), (
        "with how many other members contributed: Chris, so 1"
    )
    assert lines_with(reply.text, "Leadership")
    for line in rat_pack + lines_with(reply.text, "Leadership"):
        assert "Chris" not in line
        assert "Cole" not in line


@pytest.mark.req("SG-5", "OUT-3a")
@pytest.mark.dm("Q6")
async def test_a_members_breakdown_shows_secret_bonuses_without_givers(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    reply = await world.run("cole", "breakdown", character="Chris")

    assert reply.private
    assert lines_with(reply.text, "Rat Pack")
    assert lines_with(reply.text, "Leadership")
    for line in lines_with(reply.text, "Rat Pack") + lines_with(reply.text, "Leadership"):
        assert "Mira" not in line
        assert "Maya" not in line


# ---------------------------------------------------------------- SG-1, SG-2


JOIN = ("guild join", {"character": "Kael", "guild": "Guild of Thieves"})
ADD = ("add", {"character": "Kael", "entry": "Footpad"})
REMOVE = ("remove", {"character": "Kael", "entry": "Footpad"})
LEAVE = ("guild leave", {"character": "Kael", "guild": "Guild of Thieves"})


@pytest.mark.req("SG-1", "SG-2", "HV-2", "OUT-5")
@pytest.mark.parametrize(
    ("setup", "step"),
    [([], JOIN), ([JOIN], ADD), ([JOIN, ADD], REMOVE), ([JOIN, ADD], LEAVE)],
    ids=["join", "add", "remove", "leave"],
)
async def test_secret_guild_setup_replies_are_private(
    make_world: MakeWorld,
    setup: list[tuple[str, dict[str, OptionValue]]],
    step: tuple[str, dict[str, OptionValue]],
) -> None:
    world = await make_world("sample-game")
    for command, options in setup:
        await world.run("kit", command, **options)

    command, options = step
    reply = await world.run("kit", command, **options)
    assert reply.private


@pytest.mark.req("SG-1", "SG-3")
async def test_joining_the_secret_guild_changes_totals_but_names_nobody(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    await world.run("kit", "guild join", character="Kael", guild="Guild of Thieves")
    await world.run("kit", "add", character="Kael", entry="Footpad")
    reply = await world.run("isla", "breakdown")

    # Kael now gets Rat Pack from Chris and Mira (+2 CM), and Leadership (+2 CM).
    assert stat(reply, "Kael", "CM") == 18 + 4
    assert _secret_blocks(reply.text), "the party breakdown still has its secret guild block"
    _assert_secret_blocks_name_nobody(world, reply.text)
    for ability in SECRET_ABILITIES:
        assert ability not in reply.text, f"{ability} must not be named in the party breakdown"
    for name in ["Kael", *MEMBER_NAMES]:
        for marker in SECRET_MARKERS:
            assert not lines_with(reply.text, name, marker), f"{name!r} next to {marker!r}"
