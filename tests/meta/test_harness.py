"""The test harness itself: the fake clock, the fake Discord and the fixtures (M1).

These test the test doubles, not the bot, so they pass from M1 on.
"""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from awt_bonus.ids import ChannelId, UserId
from awt_bonus.ports import Clock, DiscordGateway
from tests.support.fakes import FakeClock, FakeDiscord
from tests.support.world import FIXTURES, build_discord, fixture_names, read_fixture

pytestmark = pytest.mark.milestone("M1")


# ---------------------------------------------------------------- fake clock


@pytest.mark.req("TF-2", "TS-10", "NF-10")
def test_fake_clock_holds_a_fixed_utc_time() -> None:
    clock: Clock = FakeClock(datetime(2026, 9, 25, 20, 0, tzinfo=UTC))
    assert clock.now() == datetime(2026, 9, 25, 20, 0, tzinfo=UTC)
    assert clock.now() == clock.now()
    assert clock.now().utcoffset() == timedelta(0)


@pytest.mark.req("TF-2", "TS-10")
def test_fake_clock_advances() -> None:
    clock = FakeClock(datetime(2026, 9, 25, 20, 0, tzinfo=UTC))
    clock.advance(timedelta(hours=12, minutes=1))
    assert clock.now() == datetime(2026, 9, 26, 8, 1, tzinfo=UTC)


@pytest.mark.req("TF-2", "TS-10", "NF-10")
def test_fake_clock_refuses_naive_and_non_utc_times() -> None:
    with pytest.raises(ValueError, match="naive"):
        FakeClock(datetime(2026, 9, 25, 20, 0))
    with pytest.raises(ValueError, match="UTC"):
        FakeClock(datetime(2026, 9, 25, 20, 0, tzinfo=timezone(timedelta(hours=-5))))


# ---------------------------------------------------------------- fake Discord


def _server() -> FakeDiscord:
    discord = FakeDiscord()
    discord.add_voice_channel(ChannelId(1), "Voice A")
    discord.add_voice_channel(ChannelId(2), "Voice B")
    discord.add_text_channel(ChannelId(3), "bonus-bot-support")
    discord.add_member(UserId(10), "Ann", frozenset({"Guild Veteran"}))
    discord.add_member(UserId(11), "Bea")
    discord.add_member(UserId(12), "Tunes", frozenset({"Guild Legend"}), is_bot=True)
    discord.add_member(UserId(13), "Cy")
    discord.move(UserId(10), ChannelId(1))
    discord.move(UserId(11), ChannelId(1))
    discord.move(UserId(12), ChannelId(1))
    discord.move(UserId(13), ChannelId(2))
    return discord


@pytest.mark.req("TF-2", "TS-8")
async def test_fake_discord_lists_voice_members_bots_included() -> None:
    discord: DiscordGateway = _server()
    members = await discord.voice_members(ChannelId(1))
    assert [m.display_name for m in members] == ["Ann", "Bea", "Tunes"]
    assert [m.is_bot for m in members] == [False, False, True]
    assert [m.display_name for m in await discord.voice_members(ChannelId(2))] == ["Cy"]


@pytest.mark.req("TF-2", "TS-8")
async def test_fake_discord_tracks_where_members_are() -> None:
    discord = _server()
    channel = await discord.voice_channel_of(UserId(13))
    assert channel is not None
    assert channel.name == "Voice B"
    discord.move(UserId(13), ChannelId(1))
    assert [m.display_name for m in await discord.voice_members(ChannelId(1))][-1] == "Cy"
    discord.move(UserId(13), None)
    assert await discord.voice_channel_of(UserId(13)) is None
    assert await discord.voice_channel(ChannelId(99)) is None


@pytest.mark.req("TF-2", "TS-8")
async def test_fake_discord_roles_can_change() -> None:
    discord = _server()
    member = await discord.member(UserId(11))
    assert member is not None
    assert member.roles == frozenset()
    discord.set_roles(UserId(11), frozenset({"Guild Legend"}))
    member = await discord.member(UserId(11))
    assert member is not None
    assert member.roles == frozenset({"Guild Legend"})
    assert await discord.member(UserId(99)) is None


@pytest.mark.req("TF-2", "TS-8")
async def test_fake_discord_records_posts() -> None:
    discord = _server()
    await discord.post("bonus-bot-support", "Please add the Dragon Scale item")
    assert discord.posts == [("bonus-bot-support", "Please add the Dragon Scale item")]


# ---------------------------------------------------------------- fixtures


@pytest.mark.req("TF-2a")
@pytest.mark.parametrize("name", fixture_names())
def test_fixture_is_valid(name: str) -> None:
    spec = read_fixture(name)
    assert spec.clock.utcoffset() == timedelta(0), "fixture clocks are in GMT (UTC)"
    assert (FIXTURES / spec.catalog).is_file()


@pytest.mark.req("TF-2a")
def test_every_fixture_is_listed() -> None:
    assert set(fixture_names()) >= {"sample-game", "presence", "levels", "setup", "big-party"}


@pytest.mark.req("TF-2a", "9.1")
async def test_sample_game_fixture_matches_section_9() -> None:
    spec = read_fixture("sample-game")
    discord = build_discord(spec)
    in_voice = await discord.voice_members(ChannelId(100))
    assert [m.display_name for m in in_voice] == [
        "Isla", "Kit", "Cora", "Cole", "Maya", "Dana", "DM Sam", "Bob",
    ]  # fmt: skip
    characters = {c.name: (p, c) for p in spec.players for c in p.characters}
    ioseph = characters["Ioseph"][1]
    assert (ioseph.level, ioseph.guilds) == (34, ["goth"])
    assert ioseph.has == ["nuyarus_love", "seraphs_affection", "champion_of_power"]
    assert characters["Kael"][1].level == 8
    assert characters["Crateris"][1].has == [
        "high_priest", "holy_aura", "bolstering_aura", "protective_aura", "devotion_3",
        "wills_ward_stone",
    ]  # fmt: skip
    assert characters["Chris"][1].level is None
    assert characters["Mira"][1].guilds == ["thieves", "cult"]
    assert characters["Crateris"][0].current_character() == "Crateris"
    assert "dana" not in {p.member for p in spec.players}
    sitting_out = {p.member for p in spec.players if p.sitout_until is not None}
    assert sitting_out == {"sam", "bob", "rowan"}


@pytest.mark.req("TF-2a")
def test_player_with_no_current_character() -> None:
    fay = next(p for p in read_fixture("presence").players if p.member == "fay")
    assert fay.current_character() is None


CATALOG_FIXTURES = [FIXTURES / "catalog.yaml", *sorted((FIXTURES / "catalogs").rglob("*.yaml"))]


@pytest.mark.req("TF-2a", "TS-4")
@pytest.mark.parametrize(
    "path", CATALOG_FIXTURES, ids=[p.relative_to(FIXTURES).as_posix() for p in CATALOG_FIXTURES]
)
def test_catalog_fixtures_are_yaml(path: Path) -> None:
    with path.open(encoding="utf-8") as f:
        assert isinstance(yaml.safe_load(f), dict)
