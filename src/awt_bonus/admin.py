"""Maintainer tasks in the database (CH-2, HV-6, AD-2; see docs/deployment.md).

Usage, on the bot's host (in the Docker image, the ``awt-admin`` command runs this
as the bot's user, e.g. ``fly ssh console -C "awt-admin remove-character Pip"``):

    python -m awt_bonus.admin remove-character <character> [--yes]
    python -m awt_bonus.admin remove-entry <character> <entry> [--yes]

Without ``--yes`` it only shows what would change. With it, it takes a snapshot
first (so a mistake can be undone with the restore runbook), makes the change, and
records it in the audit log as done by the maintainer (HV-5). It's safe while the
bot is running.

``remove-character`` is for a player who asked, with /request, to have a character
removed: players can't delete characters themselves (CH-2). ``remove-entry`` frees
a one-holder title whose holder can't or won't remove it (HV-6).
"""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from awt_bonus.backup import take_snapshot
from awt_bonus.catalog import Catalog, load_catalog
from awt_bonus.ids import UserId
from awt_bonus.ports import Clock, SystemClock
from awt_bonus.settings import Environment
from awt_bonus.startup import StartupError, database_path
from awt_bonus.store import CharacterRecord, Store

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
        if args.command == "remove-character":
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
