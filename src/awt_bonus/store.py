"""The database (requirements section 11 data model, 12.1).

Holds characters, their entries and guilds, current characters, sit-outs and the
audit log. The catalog and settings aren't stored here; only catalog IDs are.
All times are stored in UTC (NF-10).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from awt_bonus.ids import CharacterId, EntryId, GuildId, UserId


@dataclass(frozen=True)
class CharacterRecord:
    id: CharacterId
    owner: UserId
    """The Discord user who registered the character (CH-1)."""
    name: str
    level: int | None
    level_updated_at: datetime | None
    entries: tuple[EntryId, ...]
    guilds: tuple[GuildId, ...]


@dataclass(frozen=True)
class AuditRecord:
    """One change to a character (HV-5)."""

    id: int
    actor: UserId
    character_id: CharacterId
    action: str
    before: Mapping[str, Any] | None
    after: Mapping[str, Any] | None
    at: datetime


class Store:
    """Async access to the SQLite database."""

    @classmethod
    async def open(cls, url: str) -> Self:
        """Open the database at ``url``, creating or migrating the schema with Alembic.

        Runs SQLite in WAL mode with a busy timeout (DB-3).
        """
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    async def pragmas(self) -> Mapping[str, Any]:
        """This connection's SQLite settings, e.g. ``journal_mode`` and ``busy_timeout`` (DB-3)."""
        raise NotImplementedError

    # Writes. Test fixtures seed data through these too.

    async def add_character(
        self,
        owner: UserId,
        name: str,
        level: int | None = None,
        level_updated_at: datetime | None = None,
    ) -> CharacterId:
        raise NotImplementedError

    async def add_entry(self, character_id: CharacterId, entry_id: EntryId) -> None:
        raise NotImplementedError

    async def join_guild(
        self, character_id: CharacterId, guild_id: GuildId, joined_at: datetime
    ) -> None:
        raise NotImplementedError

    async def set_current(self, owner: UserId, character_id: CharacterId | None) -> None:
        """Set (or clear) the player's current character (CH-3)."""
        raise NotImplementedError

    async def set_sitout(self, user_id: UserId, until: datetime | None) -> None:
        """Set (or clear) the player's sit-out end (SE-2)."""
        raise NotImplementedError

    # Reads.

    async def character_by_name(self, name: str) -> CharacterRecord | None:
        """Look up a character by name, ignoring case (CH-1)."""
        raise NotImplementedError

    async def characters_of(self, owner: UserId) -> list[CharacterRecord]:
        raise NotImplementedError

    async def current_character(self, owner: UserId) -> CharacterRecord | None:
        raise NotImplementedError

    async def sitout_until(self, user_id: UserId) -> datetime | None:
        """The stored sit-out end (UTC), whether or not it has passed."""
        raise NotImplementedError

    async def audit_log(self) -> list[AuditRecord]:
        """Every audit record, oldest first (HV-5)."""
        raise NotImplementedError
