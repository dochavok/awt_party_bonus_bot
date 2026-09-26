"""Download a snapshot from object storage, for a restore (DB-7; see docs/restore-runbook.md).

Usage:

    python -m awt_bonus.download list
    python -m awt_bonus.download get newest [--to <folder>]
    python -m awt_bonus.download get <snapshot name> [--to <folder>]

``BACKUP_BUCKET`` and ``BACKUP_ENDPOINT_URL`` name the bucket (DB-6). Use a
**read-only** key, not the bot's write-only one. If ``BACKUP_KEY_ID`` and
``BACKUP_KEY`` aren't set, it asks for them without showing what's typed, so the
key is never stored (NF-9).

The B2 website won't download files stored with server-side encryption, which
the snapshots are; this does.
"""

import argparse
import getpass
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from botocore.exceptions import BotoCoreError, ClientError

from awt_bonus.backup import REMOTE_PREFIX, s3_client, snapshot_time
from awt_bonus.settings import Environment


class Storage(Protocol):
    def names(self) -> list[str]:
        """Every snapshot's file name in the bucket."""
        ...

    def fetch(self, name: str, target: Path) -> None:
        """Download one snapshot to ``target``."""
        ...


class S3Storage:
    """Snapshots in an S3-compatible bucket (Backblaze B2 at launch)."""

    def __init__(self, bucket: str, endpoint_url: str, key_id: str, key: str) -> None:
        self._bucket = bucket
        self._client = s3_client(endpoint_url, key_id, key)

    def names(self) -> list[str]:
        found = []
        pages = self._client.get_paginator("list_objects_v2")
        for page in pages.paginate(Bucket=self._bucket, Prefix=REMOTE_PREFIX):
            for item in page.get("Contents", []):
                found.append(item["Key"].removeprefix(REMOTE_PREFIX))
        return found

    def fetch(self, name: str, target: Path) -> None:
        self._client.download_file(self._bucket, REMOTE_PREFIX + name, str(target))


class DownloadError(Exception):
    """The snapshot can't be downloaded. The message says why."""


def newest_first(names: list[str]) -> list[str]:
    """The snapshot names, newest first; anything else in the bucket is left out."""
    dated = [(t, n) for n in names if (t := snapshot_time(Path(n))) is not None]
    return [n for _, n in sorted(dated, reverse=True)]


def download(storage: Storage, which: str, folder: Path) -> Path:
    """Download the snapshot called ``which`` ("newest" for the newest) into ``folder``."""
    names = newest_first(storage.names())
    if not names:
        raise DownloadError("There are no snapshots in the bucket.")
    name = names[0] if which == "newest" else which
    if name not in names:
        raise DownloadError(f"There's no snapshot called {name}. `list` shows them.")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    partial = folder / f"{name}.partial"
    storage.fetch(name, partial)
    partial.replace(target)
    return target


def storage_from(environment: Environment, ask: Callable[[str], str]) -> S3Storage:
    """The bucket the environment names, with a key from the environment or asked for."""
    e = environment
    if not (e.backup_bucket and e.backup_endpoint_url):
        raise DownloadError("Set BACKUP_BUCKET and BACKUP_ENDPOINT_URL (see fly.toml).")
    key_id = e.backup_key_id.get_secret_value() if e.backup_key_id else ask("Read-only keyID: ")
    key = e.backup_key.get_secret_value() if e.backup_key else ask("Read-only applicationKey: ")
    return S3Storage(e.backup_bucket, e.backup_endpoint_url, key_id.strip(), key.strip())


def main(argv: list[str] | None = None, ask: Callable[[str], str] = getpass.getpass) -> int:
    parser = argparse.ArgumentParser(prog="python -m awt_bonus.download", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list the snapshots, newest first")
    get = commands.add_parser("get", help="download one snapshot")
    get.add_argument("snapshot", help='a snapshot name from `list`, or "newest"')
    get.add_argument("--to", type=Path, default=Path("."), help="the folder to save it in")
    args = parser.parse_args(argv)
    try:
        storage = storage_from(Environment(), ask)
        if args.command == "list":
            for name in newest_first(storage.names()):
                print(name)
        else:
            print(f"Downloaded {download(storage, args.snapshot, args.to)}")
    except DownloadError as error:
        print(f"Not downloaded: {error}", file=sys.stderr)
        return 1
    except (BotoCoreError, ClientError) as error:
        print(f"Not downloaded: the storage said: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
