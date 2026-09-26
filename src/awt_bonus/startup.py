"""Checks and preparation at bot startup (DB-2, DB-3, DB-4).

The bot starts in this order: check the database location (DB-2), take the
single-process lock (DB-3), then snapshot and migrate if the schema is behind
(DB-4). Each step raises StartupError with a message saying what to fix.
"""

import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from types import TracebackType
from typing import IO, Self
from uuid import uuid4

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import create_async_engine

from awt_bonus.ports import Clock
from awt_bonus.store import Store

log = logging.getLogger(__name__)

TEMPORARY_FILESYSTEMS = {"tmpfs", "ramfs"}
"""Linux filesystems that live in memory (DB-2)."""

TEMPORARY_FOLDERS = [Path("/tmp"), Path("/var/tmp"), Path("/dev/shm")]
"""Linux folders that are temporary storage (DB-2)."""


class StartupError(Exception):
    """The bot must not start. The message says why."""


def database_path(db_url: str) -> Path:
    """The SQLite file a ``DATABASE_URL`` names (DB-1). Raises StartupError."""
    try:
        url = make_url(db_url)
    except ArgumentError:
        raise StartupError("DATABASE_URL isn't a valid database URL (DB-1).") from None
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        raise StartupError(
            "DATABASE_URL must name a SQLite file, e.g. sqlite+aiosqlite:////data/awt-bonus.db "
            "(DB-1)."
        )
    return Path(url.database)


# ---------------------------------------------------------------- DB-2


def check_database_location(db_path: Path) -> None:
    """Refuse a database on temporary storage, or where a test file can't be written (DB-2).

    The database's folder must already exist: it's never created here, so a
    container started without its volume is refused instead of writing to storage
    that disappears.

    Raises StartupError.
    """
    path = db_path.resolve()
    reason = _temporary(path)
    if reason is not None:
        raise StartupError(
            f"The database {path} is on temporary storage ({reason}). "
            "Point DATABASE_URL at persistent storage (DB-2)."
        )
    folder = path.parent
    if not folder.is_dir():
        raise StartupError(
            f"The database folder {folder} doesn't exist. Mount the persistent volume "
            "there, or create the folder (DB-2)."
        )
    probe = folder / f".write-test-{uuid4().hex}"
    try:
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as error:
        raise StartupError(
            f"Can't write a test file in {folder}: {error.strerror or error} (DB-2)."
        ) from None


def _temporary(path: Path) -> str | None:
    """Why ``path`` is on temporary storage, or None if it isn't."""
    if sys.platform == "win32":
        for name in ("TEMP", "TMP"):
            value = os.environ.get(name)
            if value and _inside(path, Path(value)):
                return f"under %{name}%"
        if _inside(path, Path(tempfile.gettempdir())):
            return "in the temporary folder"
        return None
    for folder in TEMPORARY_FOLDERS:
        if _inside(path, folder):
            return f"under {folder.as_posix()}"
    fstype = _filesystem_type(path)
    if fstype in TEMPORARY_FILESYSTEMS:
        return f"a {fstype} filesystem"
    return None


def _inside(path: Path, folder: Path) -> bool:
    """True if ``path`` is ``folder`` or inside it, ignoring case on Windows."""
    folder = folder.resolve()
    if sys.platform == "win32":
        return Path(str(path).casefold()).is_relative_to(Path(str(folder).casefold()))
    return path.is_relative_to(folder)


def _filesystem_type(path: Path, mounts: Path = Path("/proc/mounts")) -> str | None:
    """The type of the filesystem ``path`` is on, from the mount table (Linux only)."""
    try:
        lines = mounts.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    best: tuple[int, str] | None = None
    for line in lines:
        fields = line.split()
        if len(fields) < 3:
            continue
        # The mount table writes spaces and other awkward characters as octal escapes.
        mount_point = Path(re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), fields[1]))
        if path.is_relative_to(mount_point):
            depth = len(mount_point.parts)
            if best is None or depth >= best[0]:
                best = (depth, fields[2])
    return None if best is None else best[1]


# ---------------------------------------------------------------- DB-3


class InstanceLock:
    """An exclusive lock on a file next to the database (DB-3). Released on exit.

    The operating system holds the lock, so it's released if the process dies:
    a crash never leaves a stale lock behind.
    """

    def __init__(self, path: Path, handle: IO[bytes]) -> None:
        self.path = path
        self._handle: IO[bytes] | None = handle

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()

    def release(self) -> None:
        """Release the lock. Safe to call more than once."""
        handle, self._handle = self._handle, None
        if handle is None:
            return
        try:
            _unlock(handle)
        finally:
            handle.close()


def acquire_instance_lock(db_path: Path) -> InstanceLock:
    """Take the lock, or raise StartupError if another process holds it (DB-3)."""
    lock_path = db_path.with_name(db_path.name + ".lock")
    handle = lock_path.open("a+b")
    try:
        _lock(handle)
    except OSError:
        handle.close()
        raise StartupError(
            f"Another bot process is using {db_path}. Stop it first: only one may run (DB-3)."
        ) from None
    return InstanceLock(lock_path, handle)


if sys.platform == "win32":
    import msvcrt

    def _lock(handle: IO[bytes]) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(handle: IO[bytes]) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock(handle: IO[bytes]) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(handle: IO[bytes]) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


# ---------------------------------------------------------------- DB-4


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", "awt_bonus:migrations")
    return config


def _current_revisions(connection: Connection) -> set[str]:
    return set(MigrationContext.configure(connection).get_current_heads())


async def migrate_database(db_url: str, snapshot_dir: Path, clock: Clock) -> Path | None:
    """Bring the schema up to date with Alembic (DB-4).

    If migrations are pending, a snapshot is written to ``snapshot_dir`` first, and
    its path is returned; otherwise returns None.
    """
    # Imported here: backup imports settings, which imports this module.
    from awt_bonus.backup import take_snapshot

    heads = set(ScriptDirectory.from_config(_alembic_config()).get_heads())
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as connection:
            current = await connection.run_sync(_current_revisions)
    finally:
        await engine.dispose()
    if current == heads:
        return None

    try:
        snapshot = await take_snapshot(database_path(db_url), snapshot_dir, clock)
    except Exception as error:
        raise StartupError(
            f"Couldn't snapshot before migrating, so not migrating (DB-4): {error}"
        ) from error
    info = {"from": sorted(current), "to": sorted(heads), "snapshot": snapshot.name}
    log.info("migrating", extra=info)
    store = await Store.open(db_url)  # runs the migrations
    await store.close()
    log.info("migrated", extra=info)
    return snapshot
