"""What every command handler shares: its context, refusals and option checks."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

from awt_bonus.catalog import Catalog
from awt_bonus.commands._types import OptionValue, Reply
from awt_bonus.ids import UserId
from awt_bonus.output.messages import Block, text, to_messages
from awt_bonus.ports import Clock, DiscordGateway
from awt_bonus.settings import Settings
from awt_bonus.store import CharacterRecord, Store

NAME_LENGTH = 32
"""The longest character name allowed."""

NAME_PUNCTUATION = " '-."
"""What a character name may hold besides letters and digits."""


class Refused(Exception):
    """The command can't do what was asked. The reply says why, privately."""

    def __init__(self, *lines: str) -> None:
        super().__init__(" ".join(lines))
        self.lines = lines


@dataclass(frozen=True)
class Services:
    store: Store
    discord: DiscordGateway
    clock: Clock
    catalog: Catalog
    settings: Settings


@dataclass(frozen=True)
class Context:
    """One run of one command."""

    services: Services
    user: UserId
    options: Mapping[str, OptionValue]
    now: datetime
    """When the command started (UTC, NF-10)."""

    @property
    def store(self) -> Store:
        return self.services.store

    @property
    def catalog(self) -> Catalog:
        return self.services.catalog

    @property
    def settings(self) -> Settings:
        return self.services.settings

    @property
    def discord(self) -> DiscordGateway:
        return self.services.discord

    def text(self, name: str) -> str | None:
        """A text option, trimmed; None if it's missing or blank."""
        value = self.options.get(name)
        if value is None or isinstance(value, bool):
            return None
        value = str(value).strip()
        return value or None

    def required(self, name: str) -> str:
        value = self.text(name)
        if value is None:
            raise Refused(f"Give a `{name}`.")
        return value

    def flag(self, name: str) -> bool:
        return self.options.get(name) is True

    async def character(self, name: str) -> CharacterRecord:
        """The character with this name, ignoring case (CH-1)."""
        record = await self.store.character_by_name(name)
        if record is None:
            raise Refused(f"There's no character called {name}. `/character list` shows yours.")
        return record

    async def own_character(self, option: str = "character") -> CharacterRecord:
        """The named character, if the caller owns it (CH-1, NF-4). Roles never matter."""
        record = await self.character(self.required(option))
        if record.owner != self.user:
            raise Refused(
                f"{record.name} belongs to another player. You can only change your own characters."
            )
        return record

    async def own_or_current(self) -> CharacterRecord:
        """The named character (the caller's own), or the caller's current one (CH-3)."""
        if self.text("character") is not None:
            return await self.own_character()
        current = await self.store.current_character(self.user)
        if current is None:
            raise Refused(no_character_hint())
        return current


type Handler = Callable[[Context], Awaitable[Reply]]


def private(*blocks: Block | str) -> Reply:
    return Reply(to_messages(_blocks(blocks)), private=True)


def _blocks(items: tuple[Block | str, ...]) -> list[Block]:
    return [text(item) if isinstance(item, str) else item for item in items]


def no_character_hint() -> str:
    return "You have no character yet. Register one with `/character register <name>`."


def clean_name(raw: str) -> str:
    """A valid character name, with runs of spaces collapsed (CH-1)."""
    name = " ".join(raw.split())
    if not 1 <= len(name) <= NAME_LENGTH:
        raise Refused(f"A character name is 1 to {NAME_LENGTH} characters long.")
    if not name[0].isalnum() or not all(c.isalnum() or c in NAME_PUNCTUATION for c in name):
        raise Refused(
            "A character name starts with a letter or digit, and holds only letters, "
            "digits, spaces, apostrophes, hyphens and full stops."
        )
    return name


def parse_level(value: OptionValue, max_level: int, *, allow_clear: bool) -> int | None:
    """A level from 1 to the maximum (CH-4), or None for "clear"."""
    if allow_clear and isinstance(value, str) and value.strip().casefold() == "clear":
        return None
    number: int | None = None
    if isinstance(value, int) and not isinstance(value, bool):
        number = value
    elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
        number = int(value.strip())
    if number is None or not 1 <= number <= max_level:
        clear = ", or `clear`" if allow_clear else ""
        raise Refused(f"A level is a whole number from 1 to {max_level}{clear}.")
    return number
