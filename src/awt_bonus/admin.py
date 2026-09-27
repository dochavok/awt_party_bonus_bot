"""Maintainer tasks in the database (CH-1, CH-2, HV-5, HV-6, AD-2; see docs/deployment.md).

Usage, on the bot's host (in the Docker image, the ``awt-admin`` command runs this
as the bot's user, e.g. ``fly ssh console -C "awt-admin history Pip"``):

    python -m awt_bonus.admin history <character>
    python -m awt_bonus.admin holders <entry>
    python -m awt_bonus.admin transfer <character> <new owner's Discord user ID> [--yes]
    python -m awt_bonus.admin remove-character <character> [--yes]
    python -m awt_bonus.admin remove-entry <character> <entry> [--yes]

``history`` and ``holders`` only read. The others, without ``--yes``, only show what
would change. With it, they take a snapshot first (so a mistake can be undone with
the restore runbook), make the change, and record it in the audit log as done by
the maintainer (HV-5). All are safe while the bot is running.

``history`` shows a character's audit log, e.g. for a dispute (HV-5); it also finds
a removed character. ``holders`` lists who has an entry, e.g. before changing it in
the catalog. ``transfer`` moves a character to another Discord account: only the
owner can change a character (CH-1). ``remove-character`` is for a player who asked,
with /request, to have a character removed (CH-2). ``remove-entry`` frees a
one-holder title whose holder can't or won't remove it (HV-6).
"""

import argparse
import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from awt_bonus.backup import take_snapshot
from awt_bonus.catalog import Catalog, load_catalog
from awt_bonus.ids import UserId
from awt_bonus.ports import Clock, SystemClock
from awt_bonus.settings import Environment
from awt_bonus.startup import StartupError, database_path
from awt_bonus.store import AuditRecord, CharacterRecord, Store

MAINTAINER = UserId(0)
"""The audit log's actor for changes the maintainer makes (HV-5). Never a Discord user."""


class AdminError(Exception):
    """The change can't be made. The message says why."""


@dataclass(frozen=True)
class Plan:
    """What a change would do, before it's made."""

    description: list[str]
    character: CharacterRecord


async def _character(store: Store, name: str) -> CharacterRecord:
    record = await store.character_by_name(name)
    if record is None:
        raise AdminError(f"There's no character called {name}.")
    return record


def _entry_names(record: CharacterRecord, catalog: Catalog) -> str:
    names = [catalog.entries[e].name if e in catalog.entries else e for e in record.entries]
    return ", ".join(names) or "none"


def _guild_names(record: CharacterRecord, catalog: Catalog) -> str:
    names = [catalog.guilds[g].full_name if g in catalog.guilds else g for g in record.guilds]
    return ", ".join(names) or "none"


async def remove_character(
    store: Store,
    catalog: Catalog,
    name: str,
    *,
    confirmed: bool,
    snapshot: Callable[[], Awaitable[object]],
    now: datetime,
) -> Plan:
    """Show, or with ``confirmed`` make, the removal of a character (CH-2)."""
    record = await _character(store, name)
    current = await store.current_character(record.owner)
    others = [c for c in await store.characters_of(record.owner) if c.id != record.id]
    if current is None or current.id != record.id:
        after = "  It isn't the player's current character."
    elif others:
        after = (
            "  It's the player's current character; they'll be told to choose another with /play."
        )
    else:
        after = "  It's the player's only character; they'll be told to register a new one."
    plan = Plan(
        description=[
            f"Remove the character {record.name}, owned by Discord user {record.owner}.",
            f"  Level: {record.level if record.level is not None else 'not recorded'}",
            f"  Entries: {_entry_names(record, catalog)}",
            f"  Guilds: {_guild_names(record, catalog)}",
            after,
        ],
        character=record,
    )
    if confirmed:
        await snapshot()
        async with store.transaction():
            await store.add_audit(
                MAINTAINER,
                record.id,
                "remove character",
                {
                    "name": record.name,
                    "owner": record.owner,
                    "level": record.level,
                    "entries": list(record.entries),
                    "guilds": list(record.guilds),
                },
                None,
                now,
            )
            await store.delete_character(record.id)
    return plan


async def remove_entry(
    store: Store,
    catalog: Catalog,
    name: str,
    entry_name: str,
    *,
    confirmed: bool,
    snapshot: Callable[[], Awaitable[object]],
    now: datetime,
) -> Plan:
    """Show, or with ``confirmed`` make, the removal of one entry from a character (HV-6)."""
    record = await _character(store, name)
    entry = catalog.entry_named(entry_name)
    if entry is None:
        raise AdminError(f"There's no entry called {entry_name} in the catalog.")
    if entry.id not in record.entries:
        raise AdminError(f"{record.name} doesn't have {entry.name}.")
    plan = Plan(
        description=[
            f"Remove {entry.name} from {record.name}, owned by Discord user {record.owner}."
        ],
        character=record,
    )
    if confirmed:
        await snapshot()
        after = [e for e in record.entries if e != entry.id]
        async with store.transaction():
            await store.add_audit(
                MAINTAINER,
                record.id,
                "remove",
                {"entries": list(record.entries)},
                {"entries": after},
                now,
            )
            await store.remove_entry(record.id, entry.id)
    return plan


async def transfer(
    store: Store,
    catalog: Catalog,
    name: str,
    new_owner: int,
    *,
    confirmed: bool,
    snapshot: Callable[[], Awaitable[object]],
    now: datetime,
) -> Plan:
    """Show, or with ``confirmed`` make, the move of a character to another Discord user."""
    record = await _character(store, name)
    if new_owner <= 0:
        raise AdminError("A Discord user ID is a positive number, e.g. 703351998850007040.")
    owner = UserId(new_owner)
    if owner == record.owner:
        raise AdminError(f"{record.name} already belongs to Discord user {owner}.")
    old_current = await store.current_character(record.owner)
    new_current = await store.current_character(owner)
    description = [
        f"Move the character {record.name} from Discord user {record.owner} "
        f"to Discord user {owner}.",
        f"  It keeps its level, entries ({_entry_names(record, catalog)}) and guilds "
        f"({_guild_names(record, catalog)}).",
    ]
    if old_current is not None and old_current.id == record.id:
        others = [c for c in await store.characters_of(record.owner) if c.id != record.id]
        next_step = (
            "choose another with /play" if others else "register a new one, as it's their only one"
        )
        description.append(
            f"  It's Discord user {record.owner}'s current character; they'll be told to "
            f"{next_step}."
        )
    if new_current is None:
        description.append(f"  It becomes Discord user {owner}'s current character.")
    else:
        description.append(
            f"  Discord user {owner} keeps playing {new_current.name}; "
            f"`/play {record.name}` switches."
        )
    if confirmed:
        await snapshot()
        async with store.transaction():
            await store.add_audit(
                MAINTAINER, record.id, "transfer", {"owner": record.owner}, {"owner": owner}, now
            )
            await store.set_owner(record.id, owner)
            if old_current is not None and old_current.id == record.id:
                await store.set_current(record.owner, None)
            if new_current is None:
                await store.set_current(owner, record.id)
    return Plan(description=description, character=record)


async def history(store: Store, catalog: Catalog, name: str) -> list[str]:
    """A character's audit log, oldest first (HV-5). Finds a removed character too."""
    record = await store.character_by_name(name)
    records = await store.audit_log()
    if record is not None:
        character_id, shown = record.id, record.name
    else:
        removed = [
            r
            for r in records
            if r.action == "remove character"
            and r.before is not None
            and str(r.before.get("name", "")).casefold() == name.casefold()
        ]
        if not removed:
            raise AdminError(f"There's no character called {name}, now or removed.")
        character_id, shown = removed[-1].character_id, f"{name} (removed)"
    lines = [f"History of {shown}, oldest first (times in UTC):"]
    mine = [r for r in records if r.character_id == character_id]
    lines += [_history_line(r, catalog) for r in mine] or ["  No changes recorded."]
    return lines


def _history_line(record: AuditRecord, catalog: Catalog) -> str:
    who = "the maintainer" if record.actor == MAINTAINER else f"Discord user {record.actor}"
    at = record.at.astimezone(UTC).strftime("%Y-%m-%d %H:%M")
    before, after = record.before or {}, record.after or {}
    changes = [
        f"{key}: {_shown(key, before.get(key), catalog)} -> {_shown(key, after.get(key), catalog)}"
        for key in dict.fromkeys([*before, *after])
        if before.get(key) != after.get(key)
    ]
    return f"  {at}  {record.action} by {who}" + (f"; {'; '.join(changes)}" if changes else "")


def _shown(key: str, value: object, catalog: Catalog) -> str:
    """An audit value, with catalog IDs shown by name."""
    if value is None:
        return "none"
    if key == "entries" and isinstance(value, list):
        return (
            "["
            + ", ".join(catalog.entries[v].name if v in catalog.entries else str(v) for v in value)
            + "]"
        )
    if key == "guilds" and isinstance(value, list):
        return (
            "["
            + ", ".join(
                catalog.guilds[v].full_name if v in catalog.guilds else str(v) for v in value
            )
            + "]"
        )
    return json.dumps(value)


async def holders(store: Store, catalog: Catalog, entry_name: str) -> list[str]:
    """Every character with this entry, e.g. before changing it in the catalog."""
    entry = catalog.entry_named(entry_name)
    if entry is None:
        raise AdminError(f"There's no entry called {entry_name} in the catalog.")
    found = sorted(await store.holders_of(entry.id), key=lambda c: c.name.casefold())
    retired = " (retired)" if entry.retired else ""
    lines = [f"{entry.name}{retired}: {len(found)} character{'' if len(found) == 1 else 's'}"]
    lines += [f"  {c.name}, owned by Discord user {c.owner}" for c in found]
    return lines


class SnapshotTaker:
    """Takes the snapshot before a change, next to the database (DB-6)."""

    def __init__(self, db_path: Path, clock: Clock) -> None:
        self._db_path = db_path
        self._clock = clock
        self.taken: Path | None = None

    async def __call__(self) -> None:
        self.taken = await take_snapshot(
            self._db_path, self._db_path.parent / "snapshots", self._clock
        )


async def _run(args: argparse.Namespace) -> int:
    environment = Environment()
    db_path = database_path(environment.database_url)
    catalog = load_catalog(args.catalog)
    clock = SystemClock()
    snapshot = SnapshotTaker(db_path, clock)
    store = await Store.open(environment.database_url)
    try:
        if args.command in ("history", "holders"):
            if args.command == "history":
                lines = await history(store, catalog, args.character)
            else:
                lines = await holders(store, catalog, args.entry)
            print("\n".join(lines))
            return 0
        if args.command == "transfer":
            plan = await transfer(
                store,
                catalog,
                args.character,
                args.new_owner,
                confirmed=args.yes,
                snapshot=snapshot,
                now=clock.now(),
            )
        elif args.command == "remove-character":
            plan = await remove_character(
                store,
                catalog,
                args.character,
                confirmed=args.yes,
                snapshot=snapshot,
                now=clock.now(),
            )
        else:
            plan = await remove_entry(
                store,
                catalog,
                args.character,
                args.entry,
                confirmed=args.yes,
                snapshot=snapshot,
                now=clock.now(),
            )
    finally:
        await store.close()
    print("\n".join(plan.description))
    if args.yes:
        print(f"Done. A snapshot from just before is {snapshot.taken}.")
    else:
        print("Nothing changed. Run it again with --yes to make the change.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m awt_bonus.admin", description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("catalog"), help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    shown = commands.add_parser("history", help="a character's audit log (HV-5)")
    shown.add_argument("character")
    held = commands.add_parser("holders", help="who has an entry")
    held.add_argument("entry")
    moved = commands.add_parser("transfer", help="move a character to another Discord user")
    moved.add_argument("character")
    moved.add_argument("new_owner", type=int, help="the new owner's Discord user ID")
    moved.add_argument("--yes", action="store_true", help="make the change")
    character = commands.add_parser("remove-character", help="remove a character (CH-2)")
    character.add_argument("character")
    character.add_argument("--yes", action="store_true", help="make the change")
    entry = commands.add_parser("remove-entry", help="remove an entry from a character (HV-6)")
    entry.add_argument("character")
    entry.add_argument("entry")
    entry.add_argument("--yes", action="store_true", help="make the change")
    args = parser.parse_args(argv)
    try:
        return asyncio.run(_run(args))
    except (AdminError, StartupError) as error:
        print(f"Nothing changed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
