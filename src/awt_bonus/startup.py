"""Checks and preparation at bot startup (DB-2, DB-3, DB-4)."""

from pathlib import Path
from types import TracebackType
from typing import Self

from awt_bonus.ports import Clock


class StartupError(Exception):
    """The bot must not start. The message says why."""


def check_database_location(db_path: Path) -> None:
    """Refuse a database on temporary storage, or where a test file can't be written (DB-2).

    Raises StartupError.
    """
    raise NotImplementedError


class InstanceLock:
    """An exclusive lock on a file next to the database (DB-3). Released on exit."""

    def __enter__(self) -> Self:
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    def release(self) -> None:
        raise NotImplementedError


def acquire_instance_lock(db_path: Path) -> InstanceLock:
    """Take the lock, or raise StartupError if another process holds it (DB-3)."""
    raise NotImplementedError


async def migrate_database(db_url: str, snapshot_dir: Path, clock: Clock) -> Path | None:
    """Bring the schema up to date with Alembic (DB-4).

    If migrations are pending, a snapshot is written to ``snapshot_dir`` first, and
    its path is returned; otherwise returns None.
    """
    raise NotImplementedError
