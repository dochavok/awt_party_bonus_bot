"""Restore a snapshot as the bot's database (DB-7; see docs/restore-runbook.md).

Usage, with the bot stopped:

    python -m awt_bonus.restore <snapshot file> [--database <path>]

The database defaults to the one ``DATABASE_URL`` names (DB-1). The snapshot is
checked first; the current database, if any, is kept beside it as
``<name>.before-restore-<time>``. Refuses while the bot is running (DB-3). If the
snapshot's schema is older, the bot migrates it at its next start (DB-4).
"""

import argparse
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from awt_bonus.settings import Environment
from awt_bonus.startup import StartupError, acquire_instance_lock, database_path


class RestoreError(Exception):
    """The snapshot can't be restored. The message says why."""


def check_snapshot(snapshot: Path) -> int:
    """Check a snapshot is a sound bot database; return how many characters it holds."""
    if not snapshot.is_file():
        raise RestoreError(f"There's no file {snapshot}.")
    try:
        with closing(sqlite3.connect(snapshot)) as db:
            result = db.execute("PRAGMA integrity_check").fetchone()
            if result is None or result[0] != "ok":
                raise RestoreError(f"{snapshot} is damaged: {result}")
            (characters,) = db.execute("SELECT count(*) FROM character").fetchone()
    except sqlite3.DatabaseError as error:
        raise RestoreError(f"{snapshot} isn't a bot database: {error}") from None
    return int(characters)


def restore(snapshot: Path, db_path: Path, now: datetime) -> Path | None:
    """Put ``snapshot`` in place as ``db_path``; return where the old database went.

    Raises RestoreError, or StartupError if the bot is running.
    """
    check_snapshot(snapshot)
    with acquire_instance_lock(db_path):
        incoming = db_path.with_name(db_path.name + ".restoring")
        shutil.copyfile(snapshot, incoming)
        kept = None
        if db_path.exists():
            kept = db_path.with_name(f"{db_path.name}.before-restore-{now:%Y%m%dT%H%M%SZ}")
            db_path.replace(kept)
        for suffix in ("-wal", "-shm"):
            db_path.with_name(db_path.name + suffix).unlink(missing_ok=True)
        incoming.replace(db_path)
    return kept


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m awt_bonus.restore", description=__doc__)
    parser.add_argument("snapshot", type=Path, help="the snapshot file to restore")
    parser.add_argument("--database", type=Path, help="the database file (default: DATABASE_URL)")
    args = parser.parse_args(argv)
    try:
        db_path = args.database or database_path(Environment().database_url)
        characters = check_snapshot(args.snapshot)
        kept = restore(args.snapshot, db_path, datetime.now(UTC))
    except (RestoreError, StartupError) as error:
        print(f"Not restored: {error}", file=sys.stderr)
        return 1
    plural = "" if characters == 1 else "s"
    print(f"Restored {args.snapshot} as {db_path} ({characters} character{plural}).")
    if kept is not None:
        print(f"The previous database is kept as {kept}.")
    print("Start the bot; it migrates the schema if the snapshot is older (DB-4).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
