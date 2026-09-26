"""Loading a test fixture into a fresh world (requirements TF-2a).

A fixture (``tests/fixtures/<name>.yaml``) describes the fake Discord server, the
players and their characters, sit-outs, and the fake clock's time. ``load_world``
turns it into a running ``App`` on a fresh temporary SQLite database, so every test
sees the same data.

Top-level keys starting with ``x-`` are ignored (they hold YAML anchors).
"""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from awt_bonus.catalog import Catalog, load_catalog_file
from awt_bonus.commands import App, Choice, OptionValue, Reply
from awt_bonus.ids import ChannelId, CharacterId, EntryId, GuildId, UserId
from awt_bonus.settings import Settings
from awt_bonus.store import CharacterRecord, Store
from tests.support.fakes import FakeClock, FakeDiscord

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

type MakeWorld = Callable[[str], Awaitable["World"]]
"""The ``make_world`` pytest fixture: ``world = await make_world("sample-game")``."""

DEFAULT_SETTINGS = Settings(request_channel="bonus-bot-support", sitout_hours=12, max_level=75)
"""The settings in requirement AD-1."""


class _Spec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ChannelSpec(_Spec):
    id: int
    name: str


class MemberSpec(_Spec):
    handle: str
    """How tests refer to this member."""
    id: int
    name: str
    """Discord display name."""
    roles: list[str] = Field(default_factory=list)
    voice: str | None = None
    """The voice channel the member is in, by name."""
    bot: bool = False


class DiscordSpec(_Spec):
    voice_channels: list[ChannelSpec]
    text_channels: list[ChannelSpec] = Field(default_factory=list)
    members: list[MemberSpec]


class CharacterSpec(_Spec):
    name: str
    level: int | None = None
    level_updated: AwareDatetime | None = None
    guilds: list[str] = Field(default_factory=list)
    """Guild IDs."""
    has: list[str] = Field(default_factory=list)
    """Entry IDs."""


class PlayerSpec(_Spec):
    member: str
    """The member's handle."""
    current: str | None = None
    """The current character's name. Left out: the first character. ``null``: none."""
    sitout_until: AwareDatetime | None = None
    characters: list[CharacterSpec] = Field(default_factory=list)

    def current_character(self) -> str | None:
        if "current" in self.model_fields_set:
            return self.current
        return self.characters[0].name if self.characters else None


class FixtureSpec(_Spec):
    requirements: list[str]
    """The requirement IDs this fixture was made for."""
    clock: AwareDatetime
    catalog: str
    """The catalog file, relative to tests/fixtures/."""
    settings: Settings = DEFAULT_SETTINGS
    discord: DiscordSpec
    players: list[PlayerSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> "FixtureSpec":
        problems: list[str] = []
        handles = [m.handle for m in self.discord.members]
        ids = [m.id for m in self.discord.members]
        channels = self.discord.voice_channels + self.discord.text_channels
        voice_names = {c.name for c in self.discord.voice_channels}
        if len(set(handles)) != len(handles):
            problems.append("member handles must be unique")
        if len(set(ids)) != len(ids):
            problems.append("member IDs must be unique")
        if len({c.id for c in channels}) != len(channels):
            problems.append("channel IDs must be unique")
        for member in self.discord.members:
            if member.voice is not None and member.voice not in voice_names:
                problems.append(f"{member.handle}: no voice channel {member.voice!r}")
        names = [c.name.casefold() for p in self.players for c in p.characters]
        if len(set(names)) != len(names):
            problems.append("character names must be unique, ignoring case (CH-1)")
        seen_players: set[str] = set()
        for player in self.players:
            if player.member not in handles:
                problems.append(f"player {player.member!r} isn't a member")
            if player.member in seen_players:
                problems.append(f"player {player.member!r} is listed twice")
            seen_players.add(player.member)
            current = player.current_character()
            if current is not None and current not in {c.name for c in player.characters}:
                problems.append(f"{player.member}: current {current!r} isn't one of theirs")
        if problems:
            raise ValueError("; ".join(problems))
        return self


def read_fixture(name: str) -> FixtureSpec:
    """Read and check ``tests/fixtures/<name>.yaml``."""
    path = FIXTURES / f"{name}.yaml"
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    data = {key: value for key, value in data.items() if not key.startswith("x-")}
    return FixtureSpec.model_validate(data)


def catalog_data(name: str = "catalog.yaml") -> dict[str, Any]:
    """A test catalog as plain data, to change and pass to ``parse_catalog``."""
    with (FIXTURES / name).open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return data


def fixture_names() -> list[str]:
    """Every world fixture (the YAML files directly in tests/fixtures/, except the catalog)."""
    return sorted(p.stem for p in FIXTURES.glob("*.yaml") if p.name != "catalog.yaml")


def build_discord(spec: FixtureSpec) -> FakeDiscord:
    discord = FakeDiscord()
    voice_ids = {c.name: ChannelId(c.id) for c in spec.discord.voice_channels}
    for channel in spec.discord.voice_channels:
        discord.add_voice_channel(ChannelId(channel.id), channel.name)
    for channel in spec.discord.text_channels:
        discord.add_text_channel(ChannelId(channel.id), channel.name)
    for member in spec.discord.members:
        user_id = UserId(member.id)
        discord.add_member(user_id, member.name, frozenset(member.roles), member.bot)
        if member.voice is not None:
            discord.move(user_id, voice_ids[member.voice])
    return discord


@dataclass
class World:
    """A loaded fixture: the App under test and everything around it."""

    spec: FixtureSpec
    app: App
    store: Store
    discord: FakeDiscord
    clock: FakeClock
    catalog: Catalog
    settings: Settings
    users: Mapping[str, UserId]
    """Member handle -> Discord user ID."""
    channels: Mapping[str, ChannelId]
    """Channel name -> channel ID."""
    store_path: Path
    """The SQLite file, e.g. to reopen it as after a restart."""

    def user(self, handle: str) -> UserId:
        return self.users[handle]

    def channel(self, name: str) -> ChannelId:
        return self.channels[name]

    async def run(self, handle: str, command: str, **options: OptionValue) -> Reply:
        """Run a command as the member with this handle."""
        return await self.app.run(self.user(handle), command, options)

    async def autocomplete(
        self, handle: str, command: str, option: str, typed: str, **options: OptionValue
    ) -> list[Choice]:
        return await self.app.autocomplete(self.user(handle), command, option, typed, options)

    def app_with(self, *, catalog: Catalog | None = None, settings: Settings | None = None) -> App:
        """Another App on the same database and Discord, e.g. after a catalog change."""
        return App(
            store=self.store,
            discord=self.discord,
            clock=self.clock,
            catalog=catalog or self.catalog,
            settings=settings or self.settings,
        )

    async def character(self, name: str) -> CharacterRecord | None:
        return await self.store.character_by_name(name)

    async def set_current(self, handle: str, character: str | None) -> None:
        """Change a player's current character directly in the database (test setup)."""
        character_id: CharacterId | None = None
        if character is not None:
            record = await self.store.character_by_name(character)
            assert record is not None, f"no character {character!r}"
            character_id = record.id
        await self.store.set_current(self.user(handle), character_id)


async def load_world(name: str, directory: Path) -> World:
    """Load ``tests/fixtures/<name>.yaml`` into a fresh database in ``directory``."""
    spec = read_fixture(name)
    clock = FakeClock(spec.clock)
    discord = build_discord(spec)
    users = {m.handle: UserId(m.id) for m in spec.discord.members}
    channels = {
        c.name: ChannelId(c.id) for c in spec.discord.voice_channels + spec.discord.text_channels
    }
    catalog = load_catalog_file(FIXTURES / spec.catalog)

    directory.mkdir(parents=True, exist_ok=True)
    store_path = directory / "bot.db"
    store = await Store.open(f"sqlite+aiosqlite:///{store_path.as_posix()}")
    for player in spec.players:
        owner = users[player.member]
        ids: dict[str, CharacterId] = {}
        for character in player.characters:
            character_id = await store.add_character(
                owner, character.name, character.level, character.level_updated
            )
            ids[character.name] = character_id
            for guild in character.guilds:
                await store.join_guild(character_id, GuildId(guild), spec.clock)
            for entry in character.has:
                await store.add_entry(character_id, EntryId(entry))
        current = player.current_character()
        await store.set_current(owner, None if current is None else ids[current])
        if player.sitout_until is not None:
            await store.set_sitout(owner, player.sitout_until)

    app = App(store=store, discord=discord, clock=clock, catalog=catalog, settings=spec.settings)
    return World(
        spec=spec,
        app=app,
        store=store,
        discord=discord,
        clock=clock,
        catalog=catalog,
        settings=spec.settings,
        users=users,
        channels=channels,
        store_path=store_path,
    )
