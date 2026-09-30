"""Migrating from the released schema (DB-4, TS-11).

The first release's schema is Alembic revision 0001. M8 adds the first migration
after release (the item class counts, section 11), so these tests build a
database at 0001, as the bot at AWT has it, and migrate it the way startup does.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from awt_bonus.startup import migrate_database
from awt_bonus.store import Store
from tests.support.fakes import FakeClock

pytestmark = pytest.mark.milestone("M8")

RELEASE = "0001"
"""The schema revision the bot was released with."""


def _release_database(path: Path) -> None:
    """A database at the released schema, holding one character with one entry."""
    config = Config()
    config.set_main_option("script_location", "awt_bonus:migrations")
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, RELEASE)
    engine.dispose()
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO character (id, discord_user_id, name) VALUES (1, 4001, 'Pip')")
        db.execute("INSERT INTO character_entry (character_id, entry_id) VALUES (1, 'holy_aura')")
    db.close()


def _revision(path: Path) -> str:
    with sqlite3.connect(path) as db:
        [(revision,)] = db.execute("SELECT version_num FROM alembic_version").fetchall()
    db.close()
    return str(revision)


def _tables(path: Path) -> set[str]:
    with sqlite3.connect(path) as db:
        rows = db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    db.close()
    return {name for (name,) in rows}


@pytest.mark.req("TS-11", "DB-4", "IC-1")
async def test_the_released_schema_migrates_keeping_its_data(tmp_path: Path) -> None:
    database = tmp_path / "awt-bonus.db"
    _release_database(database)
    url = f"sqlite+aiosqlite:///{database.as_posix()}"
    clock = FakeClock(datetime(2026, 10, 1, 20, 0, tzinfo=UTC))

    snapshot = await migrate_database(url, tmp_path / "snapshots", clock)

    assert snapshot is not None, "a migration is pending after release"
    assert "character_item_count" in _tables(database)
    assert _revision(database) != RELEASE
    store = await Store.open(url)
    try:
        pip = await store.character_by_name("Pip")
        assert pip is not None
        assert list(pip.entries) == ["holy_aura"]
    finally:
        await store.close()


@pytest.mark.req("DB-4", "TS-11")
async def test_a_snapshot_of_the_released_schema_is_taken_before_migrating(
    tmp_path: Path,
) -> None:
    database = tmp_path / "awt-bonus.db"
    _release_database(database)
    url = f"sqlite+aiosqlite:///{database.as_posix()}"
    clock = FakeClock(datetime(2026, 10, 1, 20, 0, tzinfo=UTC))

    snapshot = await migrate_database(url, tmp_path / "snapshots", clock)

    assert snapshot is not None
    assert _revision(snapshot) == RELEASE, "taken before the migration"
    assert "character_item_count" not in _tables(snapshot)
    with sqlite3.connect(snapshot) as db:
        assert db.execute("SELECT name FROM character").fetchall() == [("Pip",)]
    db.close()
