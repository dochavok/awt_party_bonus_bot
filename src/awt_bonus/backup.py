"""Database snapshots (DB-4, DB-6, NF-8).

A snapshot is a consistent copy made with SQLite's backup API. Nightly snapshots
are kept for 30 days. Uploading them to object storage is
done by the deployment (M5), with credentials from environment variables (NF-9).
"""

from pathlib import Path

from awt_bonus.ports import Clock


async def take_snapshot(db_path: Path, snapshot_dir: Path, clock: Clock) -> Path:
    """Copy the database consistently into ``snapshot_dir``; return the new file.

    Safe while the bot is running. Each call makes a separate file.
    """
    raise NotImplementedError


def prune_snapshots(snapshot_dir: Path, clock: Clock, keep_days: int = 30) -> list[Path]:
    """Delete snapshots older than ``keep_days``; return the files deleted (DB-6)."""
    raise NotImplementedError
