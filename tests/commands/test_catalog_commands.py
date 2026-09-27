"""The catalog from the players' side (requirements 6.2: CT-2, CT-3, CT-8, CT-9).

Uses the setup fixture (see tests/commands/test_entries.py for who has what).
"""

import pytest

from awt_bonus.catalog import parse_catalog
from awt_bonus.settings import Settings
from tests.support.text import lines_with, stat
from tests.support.world import MakeWorld, catalog_data

M3 = pytest.mark.milestone("M3")
M4 = pytest.mark.milestone("M4")
M5 = pytest.mark.milestone("M5")


# ---------------------------------------------------------------- CT-2, CT-3


@M3
@pytest.mark.req("CT-2")
async def test_renaming_an_entry_in_the_catalog_never_breaks_a_character(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    data = catalog_data()
    data["entries"]["holy_aura"]["name"] = "Holy Radiance"
    app = world.app_with(catalog=parse_catalog(data))

    crateris = await world.character("Crateris")
    assert crateris is not None
    assert "holy_aura" in crateris.entries
    reply = await app.run(world.user("craig"), "breakdown", {"character": "Crateris"})
    assert "Holy Radiance" in reply.text
    assert "Holy Aura" not in reply.text


@M3
@pytest.mark.req("CT-3")
async def test_changing_an_entrys_value_changes_it_for_every_character(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run("ioan", "partybonus")
    assert stat(reply, "Olga", "CR vs fear") == 7  # CR 5 + Holy Aura 2
    assert stat(reply, "Ioseph", "CR vs fear") == 2

    data = catalog_data()
    data["entries"]["holy_aura"]["gives"] = {"CR vs fear": 4}
    app = world.app_with(catalog=parse_catalog(data))
    reply = await app.run(world.user("ioan"), "partybonus")

    assert stat(reply, "Olga", "CR vs fear") == 9
    assert stat(reply, "Ioseph", "CR vs fear") == 4


# ---------------------------------------------------------------- CT-8: /catalog


@M3
@pytest.mark.req("CT-8", "CT-4")
async def test_catalog_entry_shows_what_it_gives_with_card_text_and_the_add_command(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "catalog", entry="Commanding Presence")

    assert "+5 to CM for all allies who are in the same range as you." in reply.text
    assert lines_with(reply.text, "/add", "Commanding Presence")
    assert "same range" in reply.text
    assert reply.private


@M3
@pytest.mark.req("CT-8")
async def test_catalog_doesnt_show_who_has_an_entry(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("ioan", "catalog", entry="Holy Aura")

    assert "Holy Aura" in reply.text
    assert "Crateris" not in reply.text  # Crateris has Holy Aura


@M3
@pytest.mark.req("CT-8")
async def test_catalog_with_no_argument_lists_everything_grouped(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "catalog")

    for name in [
        "Holy Aura", "Aura of Hope", "Inspiring Presence", "Wills ward stone",
        "Champion of Power", "Hero of Passion", "Helping Hands", "Story Teller",
    ]:  # fmt: skip
        assert name in reply.text, name
    for group in ["Holy Knight", "Paladin", "Commander"]:
        assert group in reply.text, group
    assert reply.private


@M4
@pytest.mark.req("CT-8")
async def test_catalog_shows_guild_entries_only_for_the_current_characters_guilds(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "catalog")  # current: Crateris, a Cult member

    assert "High Priest" in reply.text
    for hidden in ["Footpad", "Guild Thief", "Rat Pack", "Seraph's Affection", "Captain", "Chef"]:
        assert hidden not in reply.text, hidden
    for guild in ["Guild of Thieves", "Pirate Coalition", "Guild of the Timeless Heroes"]:
        assert guild in reply.text, guild  # listed by name, with the command to join
    assert "/guild join" in reply.text

    await world.run("craig", "play", character="Elowen")  # Elowen belongs to no guild
    reply = await world.run("craig", "catalog")
    assert "High Priest" not in reply.text


@M4
@pytest.mark.req("CT-8", "SG-3")
async def test_catalog_for_a_guild_shows_its_bonuses_only_to_members(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    outsider = await world.run("craig", "catalog", entry="Guild of Thieves")
    member = await world.run("cole", "catalog", entry="Guild of Thieves")

    assert "/guild join" in outsider.text
    assert "Rat Pack" not in outsider.text
    assert "Rat Pack" in member.text
    assert outsider.private
    assert member.private


def _with_join_text() -> dict[str, object]:
    """The test catalog, with join text for the guild whose membership comes from roles."""
    data = catalog_data()
    data["guilds"]["the_guild"]["how_to_join"] = "Guild tiers come from the test Patreon."
    return data


@M4
@pytest.mark.req("CT-8", "CT-5", "HV-3")
@pytest.mark.parametrize("options", [{"entry": "The Guild"}, {}], ids=["guild", "full-list"])
async def test_catalog_lists_the_roles_that_give_a_role_bonus_with_the_join_text(
    make_world: MakeWorld, options: dict[str, str]
) -> None:
    world = await make_world("setup")
    app = world.app_with(catalog=parse_catalog(_with_join_text()))
    reply = await app.run(world.user("craig"), "catalog", options)

    assert "Junior Adventurer or above" in reply.text, "the lowest role, and above"
    assert (
        "Support Tiers: Junior Adventurer, Guild Veteran, Guild Vanguard, Guild Champion, "
        "Guild Legend" in reply.text
    )
    assert "Guild tiers come from the test Patreon." in reply.text, "shown with the tiers"
    assert reply.private


@M4
@pytest.mark.req("HV-3", "CT-5")
async def test_joining_a_guild_that_comes_with_roles_names_the_lowest_role(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    app = world.app_with(catalog=parse_catalog(_with_join_text()))
    reply = await app.run(
        world.user("craig"), "guild join", {"character": "Elowen", "guild": "The Guild"}
    )

    assert "Junior Adventurer" in reply.text
    assert "Guild tiers come from the test Patreon." in reply.text
    elowen = await world.character("Elowen")
    assert elowen is not None
    assert "the_guild" not in elowen.guilds, "nothing was joined"


# ---------------------------------------------------------------- CT-9: /request


@M5
@pytest.mark.req("CT-9", "AD-1")
async def test_request_posts_to_the_configured_channel_with_the_players_name(
    make_world: MakeWorld,
) -> None:
    world = await make_world("setup")
    reply = await world.run("newbie", "request", text="Please add the Dragon Scale item")

    assert len(world.discord.posts) == 1
    channel, text = world.discord.posts[0]
    assert channel == "bonus-bot-support"
    assert "Please add the Dragon Scale item" in text
    assert "Newbie" in text
    assert reply.private


@M5
@pytest.mark.req("CT-9", "AD-1")
async def test_the_request_channel_is_configurable(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    app = world.app_with(
        settings=Settings(request_channel="maintainer-inbox", sitout_hours=12, max_level=75)
    )
    await app.run(world.user("craig"), "request", {"text": "Please remove my character Elowen"})

    assert [channel for channel, _ in world.discord.posts] == ["maintainer-inbox"]


@M4
@pytest.mark.req("CT-8", "CT-9")
@pytest.mark.parametrize(
    ("command", "options"),
    [
        ("catalog", {}),
        ("catalog", {"entry": "Mega Aura of Doom"}),
        ("add", {"character": "Elowen", "entry": "Mega Aura of Doom"}),
    ],
    ids=["catalog-list", "catalog-not-found", "add-not-found"],
)
async def test_catalog_says_how_to_request_a_missing_entry(
    make_world: MakeWorld, command: str, options: dict[str, str]
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", command, **options)
    assert "/request" in reply.text
    assert reply.private
