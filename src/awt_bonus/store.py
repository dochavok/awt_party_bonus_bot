"""The database (requirements section 11 data model, 12.1).

Holds characters, their entries and guilds, current characters, sit-outs and the
audit log. The catalog and settings aren't stored here; only catalog IDs are.
All times are stored in UTC (NF-10).
"""

import json
from collections.abc import AsyncIterator, Iterable, Mapping, Sequence
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Select, delete, event, insert, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from awt_bonus import schema
from awt_bonus.ids import CharacterId, EntryId, GuildId, UserId

BUSY_TIMEOUT_MS = 5000
"""How long SQLite waits for a lock before giving up (DB-3)."""


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


@dataclass(frozen=True)
class PlayerState:
    """What presence needs to know about one player (section 6.5)."""

    current: CharacterRecord | None
    sitout_until: datetime | None
    """The stored sit-out end (UTC), whether or not it has passed."""


class NameTaken(Exception):
    """Another character already has this name, ignoring case (CH-1)."""


class Store:
    """Async access to the SQLite database."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._connection: ContextVar[AsyncConnection | None] = ContextVar(
            f"store-{id(self)}", default=None
        )

    @classmethod
    async def open(cls, url: str) -> Self:
        """Open the database at ``url``, creating or migrating the schema with Alembic.

        Runs SQLite in WAL mode with a busy timeout (DB-3).
        """
        engine = create_async_engine(url)
        event.listen(engine.sync_engine, "connect", _configure_connection)
        async with engine.begin() as connection:
            await connection.run_sync(_upgrade)
        return cls(engine)

    async def close(self) -> None:
        await self._engine.dispose()

    async def pragmas(self) -> Mapping[str, Any]:
        """This connection's SQLite settings, e.g. ``journal_mode`` and ``busy_timeout`` (DB-3)."""
        async with self._connect() as connection:
            found = {}
            for name in ("journal_mode", "busy_timeout", "foreign_keys"):
                result = await connection.exec_driver_sql(f"PRAGMA {name}")
                found[name] = result.scalar()
            return found

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Run the Store calls inside the block in one transaction.

        Used to write a change and its audit record together (HV-5).
        """
        if self._connection.get() is not None:
            yield
            return
        async with self._engine.begin() as connection:
            token = self._connection.set(connection)
            try:
                yield
            finally:
                self._connection.reset(token)

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[AsyncConnection]:
        connection = self._connection.get()
        if connection is not None:
            yield connection
            return
        async with self._engine.begin() as connection:
            yield connection

    # Writes. Test fixtures seed data through these too.

    async def add_character(
        self,
        owner: UserId,
        name: str,
        level: int | None = None,
        level_updated_at: datetime | None = None,
    ) -> CharacterId:
        """Raises NameTaken if the name is taken, ignoring case (CH-1)."""
        statement = insert(schema.character).values(
            discord_user_id=owner, name=name, level=level, level_updated_at=level_updated_at
        )
        try:
            async with self._connect() as connection:
                result = await connection.execute(statement)
        except IntegrityError as error:
            raise NameTaken(name) from error
        key = result.inserted_primary_key
        assert key is not None
        return CharacterId(key[0])

    async def add_entry(self, character_id: CharacterId, entry_id: EntryId) -> None:
        statement = (
            sqlite_insert(schema.character_entry)
            .values(character_id=character_id, entry_id=entry_id)
            .on_conflict_do_nothing()
        )
        async with self._connect() as connection:
            await connection.execute(statement)

    async def join_guild(
        self, character_id: CharacterId, guild_id: GuildId, joined_at: datetime
    ) -> None:
        statement = (
            sqlite_insert(schema.character_guild)
            .values(character_id=character_id, guild_id=guild_id, joined_at=joined_at)
            .on_conflict_do_nothing()
        )
        async with self._connect() as connection:
            await connection.execute(statement)

    async def leave_guild(self, character_id: CharacterId, guild_id: GuildId) -> None:
        """End a guild membership (HV-2). The caller removes the guild's entries."""
        table = schema.character_guild
        statement = delete(table).where(
            table.c.character_id == character_id, table.c.guild_id == guild_id
        )
        async with self._connect() as connection:
            await connection.execute(statement)

    async def set_current(self, owner: UserId, character_id: CharacterId | None) -> None:
        """Set (or clear) the player's current character (CH-3)."""
        statement = sqlite_insert(schema.player).values(
            discord_user_id=owner, current_character_id=character_id
        )
        statement = statement.on_conflict_do_update(
            index_elements=[schema.player.c.discord_user_id],
            set_={"current_character_id": character_id},
        )
        async with self._connect() as connection:
            await connection.execute(statement)

    async def set_sitout(self, user_id: UserId, until: datetime | None) -> None:
        """Set (or clear) the player's sit-out end (SE-2)."""
        async with self._connect() as connection:
            if until is None:
                await connection.execute(
                    delete(schema.sit_out).where(schema.sit_out.c.discord_user_id == user_id)
                )
                return
            statement = sqlite_insert(schema.sit_out).values(discord_user_id=user_id, until=until)
            statement = statement.on_conflict_do_update(
                index_elements=[schema.sit_out.c.discord_user_id], set_={"until": until}
            )
            await connection.execute(statement)

    async def rename_character(self, character_id: CharacterId, name: str) -> None:
        """Raises NameTaken if another character has the name, ignoring case (CH-1, CH-2)."""
        statement = (
            update(schema.character).where(schema.character.c.id == character_id).values(name=name)
        )
        try:
            async with self._connect() as connection:
                await connection.execute(statement)
        except IntegrityError as error:
            raise NameTaken(name) from error

    async def set_level(
        self, character_id: CharacterId, level: int | None, updated_at: datetime
    ) -> None:
        """Set or clear the level, and when it was last updated (CH-4, CH-6)."""
        statement = (
            update(schema.character)
            .where(schema.character.c.id == character_id)
            .values(level=level, level_updated_at=updated_at)
        )
        async with self._connect() as connection:
            await connection.execute(statement)

    async def remove_entry(self, character_id: CharacterId, entry_id: EntryId) -> None:
        table = schema.character_entry
        statement = delete(table).where(
            table.c.character_id == character_id, table.c.entry_id == entry_id
        )
        async with self._connect() as connection:
            await connection.execute(statement)

    async def set_owner(self, character_id: CharacterId, owner: UserId) -> None:
        """Move a character to another Discord user (by the maintainer only, CH-1)."""
        statement = (
            update(schema.character)
            .where(schema.character.c.id == character_id)
            .values(discord_user_id=owner)
        )
        async with self._connect() as connection:
            await connection.execute(statement)

    async def delete_character(self, character_id: CharacterId) -> None:
        """Delete a character (CH-2, by the maintainer only). Its entries and guild
        memberships go with it, and it stops being anyone's current character; its
        audit records stay (HV-5).
        """
        statement = delete(schema.character).where(schema.character.c.id == character_id)
        async with self._connect() as connection:
            await connection.execute(statement)

    async def add_audit(
        self,
        actor: UserId,
        character_id: CharacterId,
        action: str,
        before: Mapping[str, Any] | None,
        after: Mapping[str, Any] | None,
        at: datetime,
    ) -> None:
        """Record a change to a character (HV-5)."""
        statement = insert(schema.audit_log).values(
            actor_user_id=actor,
            character_id=character_id,
            action=action,
            before_json=None if before is None else json.dumps(before),
            after_json=None if after is None else json.dumps(after),
            at=at,
        )
        async with self._connect() as connection:
            await connection.execute(statement)

    # Reads.

    async def character_by_name(self, name: str) -> CharacterRecord | None:
        """Look up a character by name, ignoring case (CH-1)."""
        found = await self._characters(schema.character.c.name == name)
        return found[0] if found else None

    async def character_by_id(self, character_id: CharacterId) -> CharacterRecord | None:
        found = await self._characters(schema.character.c.id == character_id)
        return found[0] if found else None

    async def characters_of(self, owner: UserId) -> list[CharacterRecord]:
        return await self._characters(schema.character.c.discord_user_id == owner)

    async def all_characters(self) -> list[CharacterRecord]:
        return await self._characters()

    async def holders_of(self, entry_id: EntryId) -> list[CharacterRecord]:
        """Every character with this entry, e.g. to keep a title to one holder (HV-6)."""
        holding = select(schema.character_entry.c.character_id).where(
            schema.character_entry.c.entry_id == entry_id
        )
        return await self._characters(schema.character.c.id.in_(holding))

    async def current_character(self, owner: UserId) -> CharacterRecord | None:
        return (await self.players([owner]))[owner].current

    async def sitout_until(self, user_id: UserId) -> datetime | None:
        """The stored sit-out end (UTC), whether or not it has passed."""
        return (await self.players([user_id]))[user_id].sitout_until

    async def players(self, user_ids: Iterable[UserId]) -> dict[UserId, PlayerState]:
        """Each player's current character and sit-out, in one go (section 6.5)."""
        wanted = list(dict.fromkeys(user_ids))
        async with self._connect() as connection:
            currents = await connection.execute(
                select(schema.player.c.discord_user_id, schema.player.c.current_character_id)
                .where(schema.player.c.discord_user_id.in_(wanted))
                .where(schema.player.c.current_character_id.is_not(None))
            )
            current_ids = {UserId(row[0]): CharacterId(row[1]) for row in currents}
            sitouts = await connection.execute(
                select(schema.sit_out.c.discord_user_id, schema.sit_out.c.until).where(
                    schema.sit_out.c.discord_user_id.in_(wanted)
                )
            )
            until = {UserId(row[0]): row[1] for row in sitouts}
        records = {
            r.id: r for r in await self._characters(schema.character.c.id.in_(current_ids.values()))
        }
        return {
            user_id: PlayerState(
                current=records.get(current_ids[user_id]) if user_id in current_ids else None,
                sitout_until=until.get(user_id),
            )
            for user_id in wanted
        }

    async def audit_log(self) -> list[AuditRecord]:
        """Every audit record, oldest first (HV-5)."""
        table = schema.audit_log
        async with self._connect() as connection:
            rows = await connection.execute(select(table).order_by(table.c.id))
            return [
                AuditRecord(
                    id=row.id,
                    actor=UserId(row.actor_user_id),
                    character_id=CharacterId(row.character_id),
                    action=row.action,
                    before=None if row.before_json is None else json.loads(row.before_json),
                    after=None if row.after_json is None else json.loads(row.after_json),
                    at=row.at,
                )
                for row in rows
            ]

    # Helpers.

    async def _characters(self, *where: Any) -> list[CharacterRecord]:
        query: Select[Any] = select(schema.character).order_by(schema.character.c.id)
        if where:
            query = query.where(*where)
        async with self._connect() as connection:
            rows = list(await connection.execute(query))
            ids = [row.id for row in rows]
            entries = await _grouped(connection, schema.character_entry.c.entry_id, ids)
            guilds = await _grouped(connection, schema.character_guild.c.guild_id, ids)
        return [
            CharacterRecord(
                id=CharacterId(row.id),
                owner=UserId(row.discord_user_id),
                name=row.name,
                level=row.level,
                level_updated_at=row.level_updated_at,
                entries=tuple(EntryId(e) for e in entries.get(row.id, ())),
                guilds=tuple(GuildId(g) for g in guilds.get(row.id, ())),
            )
            for row in rows
        ]


async def _grouped(
    connection: AsyncConnection, column: Any, character_ids: Sequence[int]
) -> dict[int, list[str]]:
    """``column``'s values for each character, in the order they were added."""
    table = column.table
    rows = await connection.execute(
        select(table.c.character_id, column)
        .where(table.c.character_id.in_(character_ids))
        .order_by(table.c.id)
    )
    grouped: dict[int, list[str]] = {}
    for character_id, value in rows:
        grouped.setdefault(character_id, []).append(value)
    return grouped


def _configure_connection(dbapi_connection: Any, _record: Any) -> None:
    """WAL mode, a busy timeout and foreign keys on every connection (DB-3)."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _upgrade(connection: Connection) -> None:
    """Bring the schema up to date with Alembic (DB-4)."""
    config = Config()
    config.set_main_option("script_location", "awt_bonus:migrations")
    config.attributes["connection"] = connection
    command.upgrade(config, "head")
