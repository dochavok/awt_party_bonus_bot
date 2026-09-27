"""The thin discord.py adapter (TS-8). Command logic lives in ``awt_bonus.commands``.

This module only translates: slash commands and autocomplete into ``App`` calls,
replies into Discord messages, and the ``DiscordGateway`` port onto discord.py.
It isn't tested by pytest (only ``intents``); it's checked by hand on the private
test server (TS-13, TS-15).
"""

import asyncio
import logging
import os
import signal
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from pydantic import ValidationError

from awt_bonus.backup import Uploader, run_nightly, uploader_from
from awt_bonus.catalog import Catalog, CatalogError, load_catalog
from awt_bonus.commands import App, OptionValue, Reply
from awt_bonus.commands._requests import REQUEST_LENGTH
from awt_bonus.ids import ChannelId, UserId
from awt_bonus.logging_setup import configure_logging
from awt_bonus.ports import Clock, Member, PostFailed, SystemClock, VoiceChannel
from awt_bonus.settings import Environment, Settings, load_settings
from awt_bonus.startup import (
    StartupError,
    acquire_instance_lock,
    check_database_location,
    database_path,
    migrate_database,
)
from awt_bonus.store import Store

log = logging.getLogger(__name__)

ROLE_CACHE = timedelta(seconds=60)
"""How long a member's roles are remembered before they're looked up again (NF-6)."""

CATALOG_DIR = Path("catalog")


def intents() -> discord.Intents:
    """The gateway intents: Guilds and GuildVoiceStates only (NF-6).

    Both are non-privileged, so the bot never reads message content or member lists
    (NF-5).
    """
    return discord.Intents(guilds=True, voice_states=True)


class DiscordAdapter:
    """The ``DiscordGateway`` port on a real Discord server."""

    def __init__(self, client: discord.Client, guild_id: int, clock: Clock) -> None:
        self._client = client
        self._guild_id = guild_id
        self._clock = clock
        self._members: dict[UserId, tuple[datetime, Member | None]] = {}

    def _guild(self) -> discord.Guild:
        guild = self._client.get_guild(self._guild_id)
        if guild is None:
            raise RuntimeError(f"the bot isn't in server {self._guild_id}")
        return guild

    def _voice_channels(self) -> list[discord.VoiceChannel | discord.StageChannel]:
        guild = self._guild()
        return [*guild.voice_channels, *guild.stage_channels]

    async def voice_channel_of(self, user_id: UserId) -> VoiceChannel | None:
        for channel in self._voice_channels():
            if any(m.id == user_id for m in channel.members):
                return VoiceChannel(ChannelId(channel.id), channel.name)
        return None

    async def voice_channel(self, channel_id: ChannelId) -> VoiceChannel | None:
        channel = self._guild().get_channel(channel_id)
        if isinstance(channel, discord.VoiceChannel | discord.StageChannel):
            return VoiceChannel(ChannelId(channel.id), channel.name)
        return None

    async def voice_members(self, channel_id: ChannelId) -> list[Member]:
        channel = self._guild().get_channel(channel_id)
        if not isinstance(channel, discord.VoiceChannel | discord.StageChannel):
            return []
        return [_member(m) for m in channel.members]

    async def member(self, user_id: UserId) -> Member | None:
        """Looked up one at a time, and remembered for about a minute (NF-6)."""
        now = self._clock.now()
        cached = self._members.get(user_id)
        if cached is not None and now - cached[0] < ROLE_CACHE:
            return cached[1]
        try:
            found: Member | None = _member(await self._guild().fetch_member(user_id))
        except discord.NotFound:
            found = None
        self._members[user_id] = (now, found)
        return found

    async def post(self, channel_name: str, text: str) -> None:
        for channel in self._guild().text_channels:
            if channel.name == channel_name:
                try:
                    await channel.send(text, allowed_mentions=discord.AllowedMentions.none())
                except discord.Forbidden as error:
                    # E.g. a private channel the bot hasn't been added to.
                    raise PostFailed(f"the bot can't post in #{channel_name}") from error
                return
        raise PostFailed(f"there's no #{channel_name} channel")


def _member(member: discord.Member) -> Member:
    return Member(
        user_id=UserId(member.id),
        display_name=member.display_name,
        roles=frozenset(r.name for r in member.roles if not r.is_default()),
        is_bot=member.bot,
    )


# ---------------------------------------------------------------- slash commands


async def _answer(
    interaction: discord.Interaction, run: Callable[[], Awaitable[Reply]], *, private: bool
) -> None:
    """Acknowledge at once (NF-1), then send the reply's messages (OUT-3b, OUT-5)."""
    await interaction.response.defer(ephemeral=private, thinking=True)
    try:
        reply = await run()
    except Exception:
        # App.run has already logged it, with the traceback (NF-8).
        await interaction.followup.send("Sorry, something went wrong.", ephemeral=True)
        return
    try:
        for message in reply.messages:
            await interaction.followup.send(
                message, ephemeral=reply.private, allowed_mentions=discord.AllowedMentions.none()
            )
    except discord.HTTPException:
        log.exception("reply failed")


def build_tree(
    client: discord.Client, app: App, guild: discord.Object, settings: Settings
) -> app_commands.CommandTree:
    """Every command in section 7 that this milestone has, for one server."""
    tree = app_commands.CommandTree(client)

    def runner(
        interaction: discord.Interaction, command: str, **options: OptionValue
    ) -> Callable[[], Awaitable[Reply]]:
        user = UserId(interaction.user.id)
        return lambda: app.run(user, command, options)

    def completer(command: str, option: str) -> Any:
        async def complete(
            interaction: discord.Interaction, current: str
        ) -> list[app_commands.Choice[str]]:
            filled = {
                key: value
                for key, value in vars(interaction.namespace).items()
                if isinstance(value, str | int | bool)
            }
            choices = await app.autocomplete(
                UserId(interaction.user.id), command, option, current, filled
            )
            return [app_commands.Choice(name=c.label[:100], value=c.value) for c in choices]

        return complete

    def channel_id(channel: discord.VoiceChannel | discord.StageChannel | None) -> int | None:
        return channel.id if channel is not None else None

    @tree.command(name="partybonus", description="Party bonus totals for your voice channel")
    @app_commands.describe(channel="Another voice channel", private="Only you see the reply")
    async def partybonus(
        interaction: discord.Interaction,
        channel: discord.VoiceChannel | None = None,
        private: bool = False,
    ) -> None:
        await _answer(
            interaction,
            runner(interaction, "partybonus", channel=channel_id(channel), private=private),
            private=private,
        )

    @tree.command(name="mybonus", description="The totals for one of your characters")
    @app_commands.autocomplete(character=completer("mybonus", "character"))
    async def mybonus(interaction: discord.Interaction, character: str | None = None) -> None:
        await _answer(
            interaction, runner(interaction, "mybonus", character=character), private=True
        )

    @tree.command(name="breakdown", description="How the totals are worked out")
    @app_commands.autocomplete(character=completer("breakdown", "character"))
    async def breakdown(
        interaction: discord.Interaction,
        character: str | None = None,
        channel: discord.VoiceChannel | None = None,
    ) -> None:
        options = runner(interaction, "breakdown", character=character, channel=channel_id(channel))
        await _answer(interaction, options, private=True)

    @tree.command(name="play", description="Choose the character you're playing")
    @app_commands.autocomplete(character=completer("play", "character"))
    async def play(interaction: discord.Interaction, character: str) -> None:
        await _answer(interaction, runner(interaction, "play", character=character), private=True)

    @tree.command(name="sitout", description=f"Don't count me for {settings.sitout_hours:g} hours")
    async def sitout(interaction: discord.Interaction) -> None:
        await _answer(interaction, runner(interaction, "sitout"), private=True)

    @tree.command(name="sitin", description="Count me again")
    async def sitin(interaction: discord.Interaction) -> None:
        await _answer(interaction, runner(interaction, "sitin"), private=True)

    @tree.command(name="add", description="Give your character a skill, boon, rank, item or title")
    @app_commands.autocomplete(
        character=completer("add", "character"), entry=completer("add", "entry")
    )
    async def add(interaction: discord.Interaction, character: str, entry: str) -> None:
        await _answer(
            interaction, runner(interaction, "add", character=character, entry=entry), private=True
        )

    @tree.command(name="remove", description="Take something away from your character")
    @app_commands.autocomplete(
        character=completer("remove", "character"), entry=completer("remove", "entry")
    )
    async def remove(interaction: discord.Interaction, character: str, entry: str) -> None:
        await _answer(
            interaction,
            runner(interaction, "remove", character=character, entry=entry),
            private=True,
        )

    @tree.command(name="catalog", description="What an entry or guild gives, or everything")
    @app_commands.autocomplete(entry=completer("catalog", "entry"))
    async def catalog(interaction: discord.Interaction, entry: str | None = None) -> None:
        await _answer(interaction, runner(interaction, "catalog", entry=entry), private=True)

    group = app_commands.Group(name="character", description="Your characters")

    @group.command(name="register", description="Register a new character")
    async def register(
        interaction: discord.Interaction, name: str, level: int | None = None
    ) -> None:
        await _answer(
            interaction,
            runner(interaction, "character register", name=name, level=level),
            private=True,
        )

    @group.command(name="list", description="Your characters")
    async def list_(interaction: discord.Interaction) -> None:
        await _answer(interaction, runner(interaction, "character list"), private=True)

    @group.command(name="rename", description="Rename one of your characters")
    @app_commands.autocomplete(character=completer("character rename", "character"))
    async def rename(interaction: discord.Interaction, character: str, new: str) -> None:
        await _answer(
            interaction,
            runner(interaction, "character rename", character=character, new=new),
            private=True,
        )

    @group.command(name="level", description="Set a character's level, or clear it")
    @app_commands.describe(level="A level, or clear")
    @app_commands.autocomplete(character=completer("character level", "character"))
    async def level(interaction: discord.Interaction, character: str, level: str) -> None:
        await _answer(
            interaction,
            runner(interaction, "character level", character=character, level=level),
            private=True,
        )

    tree.add_command(group)

    guilds = app_commands.Group(name="guild", description="Your characters' guilds")

    @guilds.command(name="join", description="A character joins a guild")
    @app_commands.autocomplete(
        character=completer("guild join", "character"), guild=completer("guild join", "guild")
    )
    async def guild_join(interaction: discord.Interaction, character: str, guild: str) -> None:
        await _answer(
            interaction,
            runner(interaction, "guild join", character=character, guild=guild),
            private=True,
        )

    @guilds.command(name="leave", description="A character leaves a guild")
    @app_commands.autocomplete(
        character=completer("guild leave", "character"), guild=completer("guild leave", "guild")
    )
    async def guild_leave(interaction: discord.Interaction, character: str, guild: str) -> None:
        await _answer(
            interaction,
            runner(interaction, "guild leave", character=character, guild=guild),
            private=True,
        )

    tree.add_command(guilds)

    @tree.command(name="bogsy", description="Your party bonuses as Bogsy dice-bot modifiers")
    async def bogsy(interaction: discord.Interaction) -> None:
        await _answer(interaction, runner(interaction, "bogsy"), private=True)

    @tree.command(name="help", description="How to set up and play, and your next step")
    async def help_(interaction: discord.Interaction) -> None:
        await _answer(interaction, runner(interaction, "help"), private=True)

    @tree.command(name="request", description="Ask the maintainer to add or fix something")
    @app_commands.describe(text="What's missing or wrong, or what you need")
    async def request(
        interaction: discord.Interaction, text: app_commands.Range[str, 1, REQUEST_LENGTH]
    ) -> None:
        await _answer(interaction, runner(interaction, "request", text=text), private=True)

    for command in tree.get_commands():
        tree.remove_command(command.name)
        tree.add_command(command, guild=guild)
    return tree


# ---------------------------------------------------------------- running the bot


@dataclass(frozen=True)
class _Prepared:
    """Everything startup checked, for the client to use."""

    environment: Environment
    guild_id: int
    token: str
    settings: Settings
    catalog: Catalog
    db_path: Path
    uploader: Uploader | None

    @property
    def snapshot_dir(self) -> Path:
        return self.db_path.parent / "snapshots"


class _Client(discord.Client):
    def __init__(self, prepared: _Prepared) -> None:
        # The bot never plays audio, so the voice libraries aren't needed (NF-6).
        discord.VoiceClient.warn_nacl = False
        discord.VoiceClient.warn_dave = False
        super().__init__(intents=intents(), allowed_mentions=discord.AllowedMentions.none())
        self._prepared = prepared
        self.store: Store | None = None
        self._nightly: asyncio.Task[None] | None = None

    async def setup_hook(self) -> None:
        p = self._prepared
        clock = SystemClock()
        self.store = await Store.open(p.environment.database_url)
        app = App(
            store=self.store,
            discord=DiscordAdapter(self, p.guild_id, clock),
            clock=clock,
            catalog=p.catalog,
            settings=p.settings,
        )
        guild = discord.Object(id=p.guild_id)
        tree = build_tree(self, app, guild, p.settings)
        await tree.sync(guild=guild)
        log.info("commands synced", extra={"guild_id": p.guild_id})
        self._nightly = asyncio.create_task(
            run_nightly(p.db_path, p.snapshot_dir, clock, p.uploader)
        )

    async def on_ready(self) -> None:
        version = os.environ.get("GIT_SHA", "dev")
        log.info("ready", extra={"guild_id": self._prepared.guild_id, "version": version})

    async def on_disconnect(self) -> None:
        log.warning("gateway disconnected")

    async def on_resumed(self) -> None:
        log.info("gateway resumed")

    async def close(self) -> None:
        if self._nightly is not None:
            self._nightly.cancel()
        if self.store is not None:
            await self.store.close()
            self.store = None
        await super().close()


def _prepare() -> _Prepared:
    """Read and check everything the bot needs before it touches the database."""
    try:
        environment = Environment()
    except ValidationError as error:
        # Name the variables only: the values may be secret (NF-8).
        names = ", ".join(str(e["loc"][0]).upper() for e in error.errors())
        raise StartupError(f"These environment variables aren't valid: {names}.") from None
    token, guild_id = environment.discord_token, environment.discord_guild_id
    if token is None or guild_id is None:
        raise StartupError("Set DISCORD_TOKEN and DISCORD_GUILD_ID (NF-9).")
    settings = load_settings()
    try:
        catalog = load_catalog(CATALOG_DIR)
    except CatalogError as error:
        raise StartupError(f"The catalog is invalid: {error}") from None
    db_path = database_path(environment.database_url)
    check_database_location(db_path)
    uploader = uploader_from(environment)
    if uploader is None:
        log.warning("no object storage configured: snapshots stay on this host")
    return _Prepared(
        environment=environment,
        guild_id=guild_id,
        token=token.get_secret_value(),
        settings=settings,
        catalog=catalog,
        db_path=db_path,
        uploader=uploader,
    )


async def _run() -> int:
    """Start the bot (DB-2, DB-3, DB-4), and run it until it's stopped."""
    try:
        prepared = _prepare()
        lock = acquire_instance_lock(prepared.db_path)
    except StartupError as error:
        log.error("startup refused", extra={"reason": str(error)})
        return 1
    with lock:
        try:
            await migrate_database(
                prepared.environment.database_url, prepared.snapshot_dir, SystemClock()
            )
        except StartupError as error:
            log.error("startup refused", extra={"reason": str(error)})
            return 1
        except Exception:
            log.exception("migration failed; the snapshot taken before it is the way back")
            return 1
        client = _Client(prepared)
        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for stop in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(stop, lambda: asyncio.ensure_future(client.close()))
        async with client:
            try:
                await client.start(prepared.token)
            except discord.LoginFailure:
                log.error("startup refused", extra={"reason": "Discord rejected DISCORD_TOKEN."})
                return 1
    return 0


def main() -> None:
    """Run the bot: ``uv run python -m awt_bonus``. Needs DISCORD_TOKEN and DISCORD_GUILD_ID."""
    configure_logging()
    log.info("startup", extra={"version": os.environ.get("GIT_SHA", "dev")})
    try:
        code = asyncio.run(_run())
    except KeyboardInterrupt:
        code = 0
    except Exception:
        log.exception("crashed")  # the host restarts the bot (NF-3)
        code = 1
    log.info("shutdown", extra={"exit_code": code})
    raise SystemExit(code)
