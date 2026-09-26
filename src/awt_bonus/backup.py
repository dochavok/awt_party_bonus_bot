"""Database snapshots (DB-4, DB-6, NF-8).

A snapshot is a consistent copy made with SQLite's backup API (what ``sqlite3
.backup`` uses), safe while the bot is running. Snapshots are named after the UTC
time they were taken, e.g. ``awt-bonus-20260925T080000Z.db``, and kept for 30 days.

Every night the bot takes one, uploads it to object storage (Backblaze B2, through
its S3-compatible API) and prunes the old ones. The upload key comes from
environment variables (NF-9); the bucket's own lifecycle rule deletes uploaded
snapshots after 30 days, so the key only needs to write.
"""

import asyncio
import logging
import re
import sqlite3
from collections.abc import Awaitable
from contextlib import closing
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Protocol

from awt_bonus.ports import Clock
from awt_bonus.settings import Environment

log = logging.getLogger(__name__)

KEEP_DAYS = 30
"""How long snapshots are kept (DB-6)."""

NIGHTLY_AT = time(8, 0, tzinfo=UTC)
"""When the nightly snapshot is taken: 08:00 UTC, the small hours in the US."""

REMOTE_PREFIX = "snapshots/"
"""Where uploaded snapshots go in the bucket."""

_STAMP = "%Y%m%dT%H%M%SZ"
_NAME = re.compile(r"^(?P<stem>.+)-(?P<stamp>\d{8}T\d{6}Z)(?:-\d+)?\.db$")


def snapshot_time(path: Path) -> datetime | None:
    """When a snapshot was taken, from its name; None if it isn't a snapshot."""
    match = _NAME.match(path.name)
    if match is None:
        return None
    return datetime.strptime(match["stamp"], _STAMP).replace(tzinfo=UTC)


def snapshots(snapshot_dir: Path) -> list[Path]:
    """The snapshots in ``snapshot_dir``, oldest first."""
    if not snapshot_dir.is_dir():
        return []
    found = [p for p in snapshot_dir.iterdir() if p.is_file() and snapshot_time(p) is not None]
    return sorted(found, key=lambda p: (snapshot_time(p), p.name))


async def take_snapshot(db_path: Path, snapshot_dir: Path, clock: Clock) -> Path:
    """Copy the database consistently into ``snapshot_dir``; return the new file.

    Safe while the bot is running. Each call makes a separate file.
    """
    target, size = await asyncio.to_thread(_copy, db_path, snapshot_dir, clock.now())
    log.info("snapshot taken", extra={"snapshot": target.name, "bytes": size})
    return target


def _copy(source: Path, snapshot_dir: Path, now: datetime) -> tuple[Path, int]:
    """SQLite's online backup into a temporary file, renamed when complete."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{source.stem}-{now.astimezone(UTC).strftime(_STAMP)}"
    target = snapshot_dir / f"{stem}.db"
    n = 1
    while target.exists():
        target = snapshot_dir / f"{stem}-{n}.db"
        n += 1
    partial = target.with_name(target.name + ".partial")
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(partial)) as dst:
        src.backup(dst)
    partial.replace(target)
    return target, target.stat().st_size


def prune_snapshots(snapshot_dir: Path, clock: Clock, keep_days: int = KEEP_DAYS) -> list[Path]:
    """Delete snapshots older than ``keep_days``; return the files deleted (DB-6)."""
    cutoff = clock.now() - timedelta(days=keep_days)
    deleted = []
    for path in snapshots(snapshot_dir):
        taken = snapshot_time(path)
        if taken is not None and taken < cutoff:
            path.unlink()
            deleted.append(path)
    if deleted:
        log.info("snapshots pruned", extra={"deleted": [p.name for p in deleted]})
    return deleted


# ---------------------------------------------------------------- upload


class Uploader(Protocol):
    def upload(self, path: Path) -> None:
        """Copy one snapshot to object storage. Raises on failure."""
        ...


class S3Uploader:
    """Uploads to an S3-compatible bucket (Backblaze B2 at launch)."""

    def __init__(self, bucket: str, endpoint_url: str, key_id: str, key: str) -> None:
        import boto3
        from botocore.config import Config

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=_region(endpoint_url),
            aws_access_key_id=key_id,
            aws_secret_access_key=key,
            # B2 doesn't need the newer default checksums; send them only when required.
            config=Config(
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                retries={"max_attempts": 5, "mode": "standard"},
            ),
        )

    def upload(self, path: Path) -> None:
        self._client.upload_file(str(path), self._bucket, REMOTE_PREFIX + path.name)


def _region(endpoint_url: str) -> str | None:
    """The region in an endpoint like ``https://s3.us-east-005.backblazeb2.com``."""
    match = re.match(r"^(?:https?://)?s3\.([a-z0-9-]+)\.", endpoint_url)
    return match[1] if match else None


def uploader_from(environment: Environment) -> Uploader | None:
    """The uploader the environment describes, or None if it describes none."""
    e = environment
    if not (e.backup_bucket and e.backup_endpoint_url and e.backup_key_id and e.backup_key):
        return None
    endpoint = e.backup_endpoint_url
    if "://" not in endpoint:
        endpoint = f"https://{endpoint}"
    return S3Uploader(
        e.backup_bucket,
        endpoint,
        e.backup_key_id.get_secret_value(),
        e.backup_key.get_secret_value(),
    )


# ---------------------------------------------------------------- the nightly job


async def nightly_snapshot(
    db_path: Path, snapshot_dir: Path, clock: Clock, uploader: Uploader | None
) -> Path:
    """Take a snapshot, upload it, and prune old ones (DB-6)."""
    snapshot = await take_snapshot(db_path, snapshot_dir, clock)
    if uploader is None:
        log.warning("snapshot not uploaded: no object storage configured")
    else:
        try:
            await asyncio.to_thread(uploader.upload, snapshot)
        except Exception:
            log.exception("snapshot upload failed", extra={"snapshot": snapshot.name})
        else:
            log.info("snapshot uploaded", extra={"snapshot": snapshot.name})
    prune_snapshots(snapshot_dir, clock)
    return snapshot


def next_nightly(now: datetime) -> datetime:
    """The next nightly snapshot time after ``now``."""
    today = datetime.combine(now.astimezone(UTC).date(), NIGHTLY_AT)
    return today if today > now else today + timedelta(days=1)


def snapshot_due(snapshot_dir: Path, now: datetime) -> bool:
    """True if the newest snapshot is more than a day old, or there's none.

    Checked at startup, so a bot that was down at snapshot time still takes one.
    """
    times = [t for p in snapshots(snapshot_dir) if (t := snapshot_time(p)) is not None]
    return not times or now - max(times) > timedelta(days=1)


async def run_nightly(
    db_path: Path, snapshot_dir: Path, clock: Clock, uploader: Uploader | None
) -> None:
    """Take a snapshot now if one is due, then every night at ``NIGHTLY_AT``. Runs forever."""
    if snapshot_due(snapshot_dir, clock.now()):
        await _safely(nightly_snapshot(db_path, snapshot_dir, clock, uploader))
    while True:
        now = clock.now()
        await asyncio.sleep(max((next_nightly(now) - now).total_seconds(), 1))
        await _safely(nightly_snapshot(db_path, snapshot_dir, clock, uploader))


async def _safely(job: Awaitable[object]) -> None:
    """Log a failed snapshot and carry on; the bot keeps running (NF-3)."""
    try:
        await job
    except Exception:
        log.exception("nightly snapshot failed")
