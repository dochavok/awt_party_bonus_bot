"""Downloading a snapshot for a restore (DB-7, NF-9): python -m awt_bonus.download.

The real bucket needs real credentials; these tests use a stand-in for it.
"""

from pathlib import Path

import pytest

from awt_bonus.download import DownloadError, S3Storage, download, newest_first, storage_from
from awt_bonus.settings import Environment

pytestmark = pytest.mark.milestone("M5")

NAMES = [
    "awt-bonus-20260925T080000Z.db",
    "awt-bonus-20260926T221141Z.db",
    "notes.txt",
    "awt-bonus-20260926T080000Z.db",
]


class _Bucket:
    def __init__(self, names: list[str]) -> None:
        self._names = names
        self.fetched: list[str] = []

    def names(self) -> list[str]:
        return list(self._names)

    def fetch(self, name: str, target: Path) -> None:
        self.fetched.append(name)
        target.write_text(f"snapshot {name}", encoding="utf-8")


@pytest.mark.req("DB-7")
def test_snapshots_are_listed_newest_first_and_other_files_left_out() -> None:
    assert newest_first(NAMES) == [
        "awt-bonus-20260926T221141Z.db",
        "awt-bonus-20260926T080000Z.db",
        "awt-bonus-20260925T080000Z.db",
    ]


@pytest.mark.req("DB-7")
def test_the_newest_snapshot_is_downloaded_whole(tmp_path: Path) -> None:
    bucket = _Bucket(NAMES)
    saved = download(bucket, "newest", tmp_path / "downloads")

    assert saved == tmp_path / "downloads" / "awt-bonus-20260926T221141Z.db"
    assert saved.read_text(encoding="utf-8") == "snapshot awt-bonus-20260926T221141Z.db"
    assert list(saved.parent.iterdir()) == [saved], "no partial file is left behind"


@pytest.mark.req("DB-7")
def test_a_snapshot_can_be_picked_by_name(tmp_path: Path) -> None:
    bucket = _Bucket(NAMES)
    saved = download(bucket, "awt-bonus-20260925T080000Z.db", tmp_path)
    assert saved.name == "awt-bonus-20260925T080000Z.db"
    assert bucket.fetched == ["awt-bonus-20260925T080000Z.db"]


@pytest.mark.req("DB-7")
@pytest.mark.parametrize(
    ("names", "which"),
    [(NAMES, "awt-bonus-20200101T000000Z.db"), (NAMES, "notes.txt"), ([], "newest")],
    ids=["unknown", "not-a-snapshot", "empty-bucket"],
)
def test_only_a_snapshot_in_the_bucket_is_downloaded(
    tmp_path: Path, names: list[str], which: str
) -> None:
    bucket = _Bucket(names)
    with pytest.raises(DownloadError):
        download(bucket, which, tmp_path)
    assert bucket.fetched == []


@pytest.mark.req("DB-7", "NF-9")
def test_the_key_is_asked_for_when_not_in_the_environment() -> None:
    asked: list[str] = []

    def ask(prompt: str) -> str:
        asked.append(prompt)
        return "typed-at-the-prompt"

    environment = Environment(
        backup_bucket="awt-backups", backup_endpoint_url="s3.us-east-005.backblazeb2.com"
    )
    assert isinstance(storage_from(environment, ask), S3Storage)
    assert len(asked) == 2, "the key ID and the key"


@pytest.mark.req("DB-7")
def test_the_bucket_must_be_named() -> None:
    with pytest.raises(DownloadError, match="BACKUP_BUCKET"):
        storage_from(Environment(backup_bucket=None, backup_endpoint_url=None), lambda _: "x")
