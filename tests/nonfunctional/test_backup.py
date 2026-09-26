"""Nightly snapshots (DB-6, NF-8): a consistent copy of the database, kept for 30 days.

The upload to object storage needs real credentials, so it isn't tested here; see
the "Not automated" table in tests/COVERAGE.md.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from awt_bonus.backup import prune_snapshots, take_snapshot
from awt_bonus.ids import EntryId, UserId
from awt_bonus.store import Store
from tests.support.fakes import FakeClock

pytestmark = pytest.mark.milestone("M5")

NOW = datetime(2026, 9, 25, 3, 0, tzinfo=UTC)


def _url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


@pytest.mark.req("DB-6", "NF-8", "DB-4")
async def test_a_snapshot_is_a_complete_copy_taken_while_the_bot_runs(tmp_path: Path) -> None:
    db_path = tmp_path / "awt-bonus.db"
    store = await Store.open(_url(db_path))
    try:
        character = await store.add_character(UserId(1), "Crateris", level=22)
        await store.add_entry(character, EntryId("holy_aura"))
        snapshot = await take_snapshot(db_path, tmp_path / "snapshots", FakeClock(NOW))
    finally:
        await store.close()

    assert snapshot.parent == tmp_path / "snapshots"
    copy = await Store.open(_url(snapshot))
    try:
        crateris = await copy.character_by_name("Crateris")
        assert crateris is not None
        assert crateris.level == 22
        assert crateris.entries == ("holy_aura",)
    finally:
        await copy.close()


@pytest.mark.req("DB-6")
async def test_snapshots_older_than_30_days_are_deleted(tmp_path: Path) -> None:
    db_path = tmp_path / "awt-bonus.db"
    store = await Store.open(_url(db_path))
    await store.close()
    snapshot_dir = tmp_path / "snapshots"

    taken = {
        days: await take_snapshot(db_path, snapshot_dir, FakeClock(NOW - timedelta(days=days)))
        for days in [60, 31, 29, 1, 0]
    }
    assert len(set(taken.values())) == len(taken), "each snapshot is a separate file"

    deleted = prune_snapshots(snapshot_dir, FakeClock(NOW))

    assert set(deleted) == {taken[60], taken[31]}
    assert set(snapshot_dir.iterdir()) == {taken[29], taken[1], taken[0]}
