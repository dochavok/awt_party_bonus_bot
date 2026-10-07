"""The Discord connection (NF-5, NF-6): only the Guilds and GuildVoiceStates intents,
both non-privileged, so the bot never reads message content or member lists.

The rest of the thin discord.py adapter (TS-8) is checked here with stand-ins for
discord.py's objects, so no network or real server is needed: the DiscordGateway
port on a server, how replies reach Discord, that every command is wired to the
command layer with the right options, and startup and shutdown. What only real
Discord can show stays on the TS-15 checklist.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord import app_commands

from awt_bonus import bot
from awt_bonus.bot import (
    ROLE_CACHE,
    DiscordAdapter,
    _answer,
    _Client,
    _prepare,
    _Prepared,
    _run,
    build_tree,
    intents,
)
from awt_bonus.catalog import load_catalog_file
from awt_bonus.commands import HANDLERS, Choice, OptionValue, Reply
from awt_bonus.ids import ChannelId, UserId
from awt_bonus.ports import PostFailed, VoiceChannel
from awt_bonus.settings import Environment, Settings
from awt_bonus.startup import StartupError, acquire_instance_lock
from tests.support.fakes import FakeClock
from tests.support.traceability import ROOT
from tests.support.world import FIXTURES, MakeWorld

pytestmark = pytest.mark.milestone("M3")

GUILD_ID = 555
NOW = datetime(2026, 9, 25, 20, 0, tzinfo=UTC)
SETTINGS = Settings(request_channel="bonus-bot-support", sitout_hours=12, max_level=75)


@pytest.mark.req("NF-6", "NF-5")
def test_the_bot_asks_only_for_guilds_and_voice_states() -> None:
    wanted = intents()

    assert wanted.value == discord.Intents(guilds=True, voice_states=True).value
    assert wanted.guilds
    assert wanted.voice_states


@pytest.mark.req("NF-6", "NF-5")
def test_the_bot_asks_for_no_privileged_intents() -> None:
    wanted = intents()

    assert not wanted.message_content
    assert not wanted.members
    assert not wanted.presences


# ---------------------------------------------------------------- stand-ins for discord.py


def _http_error(kind: type[discord.HTTPException], status: int) -> discord.HTTPException:
    response: Any = SimpleNamespace(status=status, reason="stand-in")
    return kind(response, "stand-in")


class _Role:
    def __init__(self, name: str, default: bool = False) -> None:
        self.name = name
        self._default = default

    def is_default(self) -> bool:
        return self._default


def _discord_member(user_id: int, name: str, roles: list[str], bot: bool = False) -> Any:
    everyone = _Role("@everyone", default=True)
    return SimpleNamespace(
        id=user_id, display_name=name, bot=bot, roles=[everyone, *(_Role(r) for r in roles)]
    )


def _voice(kind: type, channel_id: int, name: str, members: list[Any]) -> Any:
    """A voice or stage channel that passes discord.py's isinstance checks."""
    channel = MagicMock(spec=kind)
    channel.id = channel_id
    channel.name = name
    channel.members = members
    return channel


class _Guild:
    def __init__(
        self,
        voice: Sequence[Any] = (),
        stage: Sequence[Any] = (),
        text: Sequence[Any] = (),
        members: Mapping[int, Any] | None = None,
    ) -> None:
        self.voice_channels = list(voice)
        self.stage_channels = list(stage)
        self.text_channels = list(text)
        self._members = dict(members or {})
        self.fetches: list[int] = []

    def get_channel(self, channel_id: int) -> Any:
        everything = self.voice_channels + self.stage_channels + self.text_channels
        return next((c for c in everything if c.id == channel_id), None)

    async def fetch_member(self, user_id: int) -> Any:
        self.fetches.append(user_id)
        if user_id not in self._members:
            raise _http_error(discord.NotFound, 404)
        return self._members[user_id]


def _pings_nobody(mentions: discord.AllowedMentions) -> bool:
    return not mentions.everyone and not mentions.users and not mentions.roles


def _adapter(guild: _Guild | None, clock: FakeClock | None = None) -> DiscordAdapter:
    client: Any = SimpleNamespace(get_guild=lambda gid: guild if gid == GUILD_ID else None)
    return DiscordAdapter(client, GUILD_ID, clock or FakeClock(NOW))


# ---------------------------------------------------------------- the DiscordGateway port


@pytest.mark.req("NF-6")
async def test_a_members_roles_are_looked_up_once_then_cached_for_about_a_minute() -> None:
    guild = _Guild(members={7: _discord_member(7, "Ada", ["Guild Legend"])})
    clock = FakeClock(NOW)
    adapter = _adapter(guild, clock)

    first = await adapter.member(UserId(7))
    clock.advance(ROLE_CACHE - timedelta(seconds=1))
    second = await adapter.member(UserId(7))
    assert guild.fetches == [7], "looked up once within the cache time"
    assert first == second

    clock.advance(timedelta(seconds=1))
    await adapter.member(UserId(7))
    assert guild.fetches == [7, 7], "looked up again once the cache time has passed"
    assert timedelta(seconds=30) <= ROLE_CACHE <= timedelta(seconds=120), "about 60 s (NF-6)"


@pytest.mark.req("NF-6")
async def test_role_changes_are_seen_after_the_cache_time() -> None:
    guild = _Guild(members={7: _discord_member(7, "Ada", ["Guild Legend"])})
    clock = FakeClock(NOW)
    adapter = _adapter(guild, clock)

    before = await adapter.member(UserId(7))
    assert before is not None
    assert before.roles == {"Guild Legend"}
    guild._members[7] = _discord_member(7, "Ada", [])
    clock.advance(ROLE_CACHE)
    after = await adapter.member(UserId(7))
    assert after is not None
    assert after.roles == frozenset()


@pytest.mark.req("NF-6")
async def test_someone_who_left_the_server_is_none_and_that_is_cached_too() -> None:
    guild = _Guild()
    adapter = _adapter(guild)

    assert await adapter.member(UserId(9)) is None
    assert await adapter.member(UserId(9)) is None
    assert guild.fetches == [9], "a member who isn't found isn't looked up on every command"


@pytest.mark.req("NF-6", "HV-3", "SE-6")
async def test_a_member_has_their_display_name_named_roles_and_bot_flag() -> None:
    guild = _Guild(
        members={
            7: _discord_member(7, "Ada", ["Guild Legend", "Music Lover"]),
            8: _discord_member(8, "Jukebox", [], bot=True),
        }
    )
    adapter = _adapter(guild)

    ada = await adapter.member(UserId(7))
    jukebox = await adapter.member(UserId(8))
    assert ada is not None
    assert jukebox is not None
    assert ada.user_id == 7
    assert ada.display_name == "Ada"
    assert ada.roles == {"Guild Legend", "Music Lover"}, "@everyone isn't a role that counts"
    assert not ada.is_bot
    assert jukebox.is_bot


@pytest.mark.req("SE-1")
async def test_the_callers_voice_channel_is_found_in_voice_and_stage_channels() -> None:
    ada, ben = _discord_member(7, "Ada", []), _discord_member(8, "Ben", [])
    voice = _voice(discord.VoiceChannel, 100, "AWT Voice", [ada])
    stage = _voice(discord.StageChannel, 200, "Stage", [ben])
    adapter = _adapter(_Guild(voice=[voice], stage=[stage]))

    assert await adapter.voice_channel_of(UserId(7)) == VoiceChannel(ChannelId(100), "AWT Voice")
    assert await adapter.voice_channel_of(UserId(8)) == VoiceChannel(ChannelId(200), "Stage")
    assert await adapter.voice_channel_of(UserId(9)) is None


@pytest.mark.req("SE-1", "SE-6")
async def test_a_channels_members_are_everyone_in_it_bots_included() -> None:
    ada = _discord_member(7, "Ada", ["Guild Legend"])
    jukebox = _discord_member(8, "Jukebox", [], bot=True)
    voice = _voice(discord.VoiceChannel, 100, "AWT Voice", [ada, jukebox])
    adapter = _adapter(_Guild(voice=[voice]))

    members = await adapter.voice_members(ChannelId(100))
    assert [(m.user_id, m.is_bot) for m in members] == [(7, False), (8, True)]
    assert members[0].roles == {"Guild Legend"}


@pytest.mark.req("SE-1")
async def test_a_text_channel_or_unknown_id_is_not_a_voice_channel() -> None:
    text = _voice(discord.TextChannel, 300, "general", [])
    voice = _voice(discord.VoiceChannel, 100, "AWT Voice", [])
    adapter = _adapter(_Guild(voice=[voice], text=[text]))

    assert await adapter.voice_channel(ChannelId(100)) == VoiceChannel(ChannelId(100), "AWT Voice")
    assert await adapter.voice_channel(ChannelId(300)) is None
    assert await adapter.voice_channel(ChannelId(999)) is None
    assert await adapter.voice_members(ChannelId(300)) == []
    assert await adapter.voice_members(ChannelId(999)) == []


@pytest.mark.req("CT-9")
async def test_a_request_is_posted_to_the_named_channel_without_pinging_anyone() -> None:
    general = SimpleNamespace(id=1, name="general", send=AsyncMock())
    support = SimpleNamespace(id=2, name="bonus-bot-support", send=AsyncMock())
    adapter = _adapter(_Guild(text=[general, support]))

    await adapter.post("bonus-bot-support", "Please add @everyone's Dragon Scale")

    general.send.assert_not_called()
    support.send.assert_awaited_once()
    args, kwargs = support.send.call_args
    assert args == ("Please add @everyone's Dragon Scale",)
    mentions = kwargs["allowed_mentions"]
    assert _pings_nobody(mentions)


@pytest.mark.req("CT-9")
async def test_a_request_that_cant_be_posted_raises_post_failed_naming_the_channel() -> None:
    forbidden = AsyncMock(side_effect=_http_error(discord.Forbidden, 403))
    private = SimpleNamespace(id=2, name="bonus-bot-support", send=forbidden)

    with pytest.raises(PostFailed, match="bonus-bot-support"):
        await _adapter(_Guild(text=[private])).post("bonus-bot-support", "text")
    with pytest.raises(PostFailed, match="bonus-bot-support"):
        await _adapter(_Guild()).post("bonus-bot-support", "text")


@pytest.mark.req("SE-1")
async def test_a_server_the_bot_isnt_in_is_an_error_not_an_empty_party() -> None:
    adapter = _adapter(None)

    with pytest.raises(RuntimeError, match=str(GUILD_ID)):
        await adapter.voice_channel_of(UserId(7))
    with pytest.raises(RuntimeError, match=str(GUILD_ID)):
        await adapter.voice_members(ChannelId(100))


# ---------------------------------------------------------------- replies


class _Interaction:
    """Records what the bot sends back, in order."""

    def __init__(self, user_id: int = 7, namespace: Mapping[str, Any] | None = None) -> None:
        self.user = SimpleNamespace(id=user_id)
        self.namespace = SimpleNamespace(**(namespace or {}))
        self.events: list[tuple[str, Any, bool]] = []
        self.response = SimpleNamespace(defer=self._defer)
        self.followup = SimpleNamespace(send=self._send)
        self.mentions: list[discord.AllowedMentions | None] = []

    async def _defer(self, *, ephemeral: bool, thinking: bool) -> None:
        assert thinking, "Discord shows the bot is working on it"
        self.events.append(("defer", None, ephemeral))

    async def _send(self, content: str, *, ephemeral: bool, allowed_mentions: Any = None) -> None:
        self.events.append(("send", content, ephemeral))
        self.mentions.append(allowed_mentions)


def _reply(*messages: str, private: bool) -> Callable[[], Awaitable[Reply]]:
    async def run() -> Reply:
        return Reply(messages=messages, private=private)

    return run


@pytest.mark.req("NF-1")
async def test_a_command_is_acknowledged_before_it_runs() -> None:
    interaction: Any = _Interaction()

    async def run() -> Reply:
        assert interaction.events == [("defer", None, True)], "acknowledged first (NF-1)"
        return Reply(messages=("done",), private=True)

    await _answer(interaction, run, private=True)
    assert interaction.events[-1] == ("send", "done", True)


@pytest.mark.req("OUT-3b", "OUT-5")
@pytest.mark.parametrize("private", [True, False])
async def test_every_message_of_a_reply_is_sent_in_order_with_its_privacy(private: bool) -> None:
    interaction: Any = _Interaction()
    await _answer(interaction, _reply("one", "two", "three", private=private), private=private)

    assert interaction.events == [
        ("defer", None, private),
        ("send", "one", private),
        ("send", "two", private),
        ("send", "three", private),
    ]
    for mentions in interaction.mentions:
        assert mentions is not None
        assert _pings_nobody(mentions)


@pytest.mark.req("OUT-5", "NF-8")
async def test_a_command_that_crashes_gets_one_private_apology_and_no_details() -> None:
    interaction: Any = _Interaction()

    async def run() -> Reply:
        raise ValueError("database path C:/secret/place")

    await _answer(interaction, run, private=False)
    sends = [e for e in interaction.events if e[0] == "send"]
    assert len(sends) == 1
    _, text, ephemeral = sends[0]
    assert ephemeral, "the apology is private even for a public command"
    assert "secret" not in text
    assert "ValueError" not in text


@pytest.mark.req("NF-3", "NF-8")
async def test_a_reply_discord_rejects_is_logged_and_doesnt_crash_the_bot(
    caplog: pytest.LogCaptureFixture,
) -> None:
    interaction: Any = _Interaction()
    interaction.followup = SimpleNamespace(
        send=AsyncMock(side_effect=_http_error(discord.HTTPException, 500))
    )

    with caplog.at_level(logging.ERROR, logger="awt_bonus.bot"):
        await _answer(interaction, _reply("one", private=True), private=True)

    assert [r.message for r in caplog.records] == ["reply failed"]
    assert caplog.records[0].exc_info is not None, "with the traceback (NF-8)"


# ---------------------------------------------------------------- slash commands


class _RecordingApp:
    """Stands in for App: records what each slash command passes it."""

    def __init__(self) -> None:
        self.runs: list[tuple[UserId, str, dict[str, OptionValue]]] = []
        self.completions: list[tuple[UserId, str, str, str, dict[str, OptionValue]]] = []

    async def run(
        self, user_id: UserId, command: str, options: Mapping[str, OptionValue] | None = None
    ) -> Reply:
        self.runs.append((user_id, command, dict(options or {})))
        return Reply(messages=("ok",), private=command != "partybonus")

    async def autocomplete(
        self,
        user_id: UserId,
        command: str,
        option: str,
        typed: str,
        options: Mapping[str, OptionValue] | None = None,
    ) -> list[Choice]:
        self.completions.append((user_id, command, option, typed, dict(options or {})))
        return [Choice(label="L" * 150, value="the value")]


async def _commands(app: Any) -> list[app_commands.Command[Any, Any, Any]]:
    client = discord.Client(intents=intents())
    guild = discord.Object(id=GUILD_ID)
    tree = build_tree(client, app, guild, SETTINGS)
    found = [c for c in tree.walk_commands(guild=guild) if isinstance(c, app_commands.Command)]
    assert not tree.get_commands(), "every command is registered for the one server only"
    await client.close()
    return found


def _argument(parameter: app_commands.Parameter) -> tuple[Any, OptionValue]:
    """A value to call a command with, and what the command layer should receive."""
    kind = parameter.type
    if kind is discord.AppCommandOptionType.channel:
        return SimpleNamespace(id=4242), 4242
    if kind is discord.AppCommandOptionType.integer:
        return 3, 3
    if kind is discord.AppCommandOptionType.boolean:
        return True, True
    return f"typed {parameter.display_name}", f"typed {parameter.display_name}"


@pytest.mark.req("TS-8")
async def test_every_command_the_bot_handles_is_a_slash_command_and_nothing_else() -> None:
    names = {c.qualified_name for c in await _commands(_RecordingApp())}
    assert names == set(HANDLERS)


@pytest.mark.req("TS-8", "OUT-5")
async def test_each_slash_command_passes_its_options_to_the_command_it_names() -> None:
    app = _RecordingApp()
    for command in await _commands(app):
        interaction = _Interaction(user_id=31)
        arguments, expected = {}, {}
        for parameter in command.parameters:
            value, received = _argument(parameter)
            arguments[parameter.name] = value
            expected[parameter.display_name] = received
        app.runs.clear()

        callback: Any = command.callback
        await callback(interaction, **arguments)

        assert len(app.runs) == 1, command.qualified_name
        user, name, options = app.runs[0]
        assert (user, name) == (31, command.qualified_name)
        assert options == expected, f"/{command.qualified_name} options"
        public = command.qualified_name == "partybonus" and not arguments.get("private")
        assert interaction.events[0] == ("defer", None, not public), command.qualified_name


@pytest.mark.req("OUT-5", "OUT-1")
@pytest.mark.parametrize("private", [False, True])
async def test_partybonus_is_public_unless_private_is_chosen(private: bool) -> None:
    app = _RecordingApp()
    partybonus = next(c for c in await _commands(app) if c.qualified_name == "partybonus")
    interaction: Any = _Interaction()

    callback: Any = partybonus.callback
    await callback(interaction, channel=None, private=private)

    assert app.runs[0][2] == {"channel": None, "private": private}
    assert interaction.events[0] == ("defer", None, private)


@pytest.mark.req("CH-1", "HV-1", "IC-2")
async def test_each_autocomplete_asks_for_its_own_command_and_option() -> None:
    app = _RecordingApp()
    checked = 0
    for command in await _commands(app):
        for parameter in command.parameters:
            complete = command._params[parameter.name].autocomplete
            if complete is None:
                continue
            filled = {"character": "Kael", "channel": SimpleNamespace(id=1), "count": 2}
            app.completions.clear()

            choices = await complete(_Interaction(user_id=31, namespace=filled), "ka")

            name = f"/{command.qualified_name} {parameter.display_name}"
            assert app.completions == [
                (31, command.qualified_name, parameter.display_name, "ka",
                 {"character": "Kael", "count": 2})
            ], name  # fmt: skip
            assert [(c.value, len(c.name)) for c in choices] == [("the value", 100)], (
                f"{name}: labels are cut to Discord's 100 characters"
            )
            checked += 1
    assert checked >= 15, "every autocompleted option is checked"


@pytest.mark.req("CH-1", "HV-1", "IC-2")
async def test_every_autocompleted_option_gets_suggestions_from_the_command_layer(
    make_world: MakeWorld,
) -> None:
    world = await make_world("sample-game")
    counts: dict[str, OptionValue] = {"character": "Ioseph", "class": "passion", "count": 1}
    await world.run("isla", "character items", **counts)
    empty = []
    for command in await _commands(world.app):
        for parameter in command.parameters:
            complete = command._params[parameter.name].autocomplete
            if complete is None:
                continue
            filled = {"character": "Ioseph"}
            interaction = _Interaction(user_id=world.user("isla"), namespace=filled)
            if not await complete(interaction, ""):
                empty.append(f"/{command.qualified_name} {parameter.display_name}")
    assert not empty, f"no suggestions for {empty}"


# ---------------------------------------------------------------- starting and stopping

_ENV = (
    "DATABASE_URL",
    "DISCORD_TOKEN",
    "DISCORD_GUILD_ID",
    "BACKUP_BUCKET",
    "BACKUP_ENDPOINT_URL",
    "BACKUP_KEY_ID",
    "BACKUP_KEY",
)
TOKEN = "stand-in-token-must-never-be-shown"


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """A clean environment, run from the project folder (for config/ and catalog/)."""
    for name in _ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(ROOT)
    return monkeypatch


@pytest.mark.req("NF-9", "NF-8")
def test_a_bad_environment_variable_is_named_but_its_value_never_shown(
    environment: pytest.MonkeyPatch,
) -> None:
    environment.setenv("DISCORD_TOKEN", TOKEN)
    environment.setenv("DISCORD_GUILD_ID", "not-a-number-but-maybe-secret")

    with pytest.raises(StartupError) as refused:
        _prepare()
    assert "DISCORD_GUILD_ID" in str(refused.value)
    shown = str(refused.value).casefold()
    assert "not-a-number-but-maybe-secret" not in shown
    assert TOKEN.casefold() not in shown


@pytest.mark.req("NF-9")
@pytest.mark.parametrize("missing", ["DISCORD_TOKEN", "DISCORD_GUILD_ID"])
def test_the_bot_wont_start_without_its_token_and_server(
    environment: pytest.MonkeyPatch, missing: str
) -> None:
    values = {"DISCORD_TOKEN": TOKEN, "DISCORD_GUILD_ID": str(GUILD_ID)}
    for name, value in values.items():
        if name != missing:
            environment.setenv(name, value)

    with pytest.raises(StartupError, match=missing):
        _prepare()


@pytest.mark.req("CT-7", "NF-8")
def test_the_bot_wont_start_with_an_invalid_catalog(environment: pytest.MonkeyPatch) -> None:
    environment.setenv("DISCORD_TOKEN", TOKEN)
    environment.setenv("DISCORD_GUILD_ID", str(GUILD_ID))
    environment.setattr(bot, "CATALOG_DIR", FIXTURES / "catalogs" / "split-duplicate")

    with pytest.raises(StartupError, match="catalog is invalid") as refused:
        _prepare()
    assert TOKEN not in str(refused.value)


def _prepared(db_path: Path) -> _Prepared:
    return _Prepared(
        environment=Environment(database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}"),
        guild_id=GUILD_ID,
        token=TOKEN,
        settings=SETTINGS,
        catalog=load_catalog_file(FIXTURES / "catalog.yaml"),
        db_path=db_path,
        uploader=None,
    )


class _FakeClient:
    """Stands in for the discord.py client in ``_run``."""

    started: list[str]
    locked_while_running: list[bool]
    fail: BaseException | None = None

    def __init__(self, prepared: _Prepared) -> None:
        self.prepared = prepared

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def start(self, token: str) -> None:
        _FakeClient.started.append(token)
        _FakeClient.locked_while_running.append(_locked(self.prepared.db_path))
        if _FakeClient.fail is not None:
            raise _FakeClient.fail

    async def close(self) -> None:
        return None


@pytest.fixture
def startup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Callable[..., Path]:
    """Set _run up with a prepared bot, stand-in migration and client; returns the DB path."""

    def setup(
        *,
        migrate: Callable[..., Awaitable[None]] | None = None,
        fail: BaseException | None = None,
    ) -> Path:
        db_path = tmp_path / "bot.db"
        monkeypatch.setattr(bot, "_prepare", lambda: _prepared(db_path))

        async def no_migration(*args: object) -> None:
            return None

        monkeypatch.setattr(bot, "migrate_database", migrate or no_migration)
        _FakeClient.started = []
        _FakeClient.locked_while_running = []
        _FakeClient.fail = fail
        monkeypatch.setattr(bot, "_Client", _FakeClient)
        return db_path

    return setup


def _refusals(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.reason for r in caplog.records if r.getMessage() == "startup refused"]  # type: ignore[attr-defined]


def _locked(db_path: Path) -> bool:
    """Whether another process would be refused the database now (DB-3)."""
    try:
        acquire_instance_lock(db_path).release()
    except StartupError:
        return True
    return False


def _assert_lock_released(db_path: Path) -> None:
    assert not _locked(db_path), "the lock is released when the bot stops"


@pytest.mark.req("DB-3", "DB-4")
async def test_the_bot_holds_the_lock_while_it_migrates_and_runs(
    startup: Callable[..., Path],
) -> None:
    order: list[str] = []
    db_path = Path()

    async def migrate(*args: object) -> None:
        assert not _FakeClient.started, "migrated before connecting (DB-4)"
        assert _locked(db_path), "nobody else can open the database during a migration"
        order.append("migrated")

    db_path = startup(migrate=migrate)
    assert await _run() == 0
    assert order == ["migrated"]
    assert _FakeClient.started == [TOKEN]
    assert _FakeClient.locked_while_running == [True], "locked for as long as the bot runs"
    _assert_lock_released(db_path)


@pytest.mark.req("DB-3")
async def test_a_second_bot_on_the_same_database_is_refused(
    startup: Callable[..., Path], caplog: pytest.LogCaptureFixture
) -> None:
    db_path = startup()
    held = acquire_instance_lock(db_path)
    try:
        with caplog.at_level(logging.ERROR, logger="awt_bonus.bot"):
            assert await _run() == 1
    finally:
        held.release()
    assert _FakeClient.started == [], "never connects to Discord"
    assert any("Another bot process" in reason for reason in _refusals(caplog))


@pytest.mark.req("NF-8", "NF-9")
async def test_a_refused_startup_is_logged_with_the_reason_and_exits_1(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def refuse() -> _Prepared:
        raise StartupError("Set DISCORD_TOKEN and DISCORD_GUILD_ID (NF-9).")

    monkeypatch.setattr(bot, "_prepare", refuse)
    with caplog.at_level(logging.ERROR, logger="awt_bonus.bot"):
        assert await _run() == 1
    assert _refusals(caplog) == ["Set DISCORD_TOKEN and DISCORD_GUILD_ID (NF-9)."]


@pytest.mark.req("DB-4", "NF-8")
async def test_a_failed_migration_stops_the_bot_before_it_connects(
    startup: Callable[..., Path], caplog: pytest.LogCaptureFixture
) -> None:
    async def migrate(*args: object) -> None:
        raise RuntimeError("bad revision")

    db_path = startup(migrate=migrate)
    with caplog.at_level(logging.ERROR, logger="awt_bonus.bot"):
        assert await _run() == 1
    assert _FakeClient.started == []
    failed = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert failed
    assert failed[0].exc_info is not None, "logged with the traceback"
    _assert_lock_released(db_path)


@pytest.mark.req("NF-8", "NF-9")
async def test_a_rejected_token_exits_1_without_logging_the_token(
    startup: Callable[..., Path], caplog: pytest.LogCaptureFixture
) -> None:
    db_path = startup(fail=discord.LoginFailure("Improper token has been passed."))
    with caplog.at_level(logging.DEBUG):
        assert await _run() == 1
    assert _refusals(caplog) == ["Discord rejected DISCORD_TOKEN."]
    assert not [r for r in caplog.records if TOKEN in r.getMessage() or TOKEN in str(r.__dict__)]
    _assert_lock_released(db_path)


@pytest.mark.req("NF-3", "DB-3")
async def test_closing_the_bot_stops_the_nightly_job_and_closes_the_database(
    tmp_path: Path,
) -> None:
    client = _Client(_prepared(tmp_path / "bot.db"))
    store = SimpleNamespace(close=AsyncMock())
    nightly = asyncio.create_task(asyncio.sleep(3600))
    client.store = store  # type: ignore[assignment]
    client._nightly = nightly

    await client.close()
    await asyncio.sleep(0)

    assert nightly.cancelled()
    store.close.assert_awaited_once()
    assert client.store is None
    await client.close()  # closing twice (a signal during shutdown) is harmless
    store.close.assert_awaited_once()
