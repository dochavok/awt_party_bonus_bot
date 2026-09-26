"""The database and startup (TS-11, DB-1 to DB-4, NF-2, NF-3, DP-4).

Every test gets a fresh temporary SQLite file (TS-11). The DB-2 location check
and the DB-3 lock run at bot startup, not whenever the database is opened, so
tests can keep using temporary files.
"""

import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from awt_bonus.commands import App
from awt_bonus.ids import UserId
from awt_bonus.settings import Environment
from awt_bonus.startup import (
    StartupError,
    acquire_instance_lock,
    check_database_location,
    migrate_database,
)
from awt_bonus.store import Store
from tests.support.fakes import FakeClock
from tests.support.text import counted, recipient
from tests.support.traceability import ROOT
from tests.support.world import MakeWorld

M3 = pytest.mark.milestone("M3")
M5 = pytest.mark.milestone("M5")


def _url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


# ---------------------------------------------------------------- TS-11, DB-3 (store)


@M3
@pytest.mark.req("TS-11")
async def test_a_fresh_database_is_empty(tmp_path: Path) -> None:
    store = await Store.open(_url(tmp_path / "fresh.db"))
    try:
        assert await store.characters_of(UserId(1)) == []
        assert await store.audit_log() == []
        assert await store.character_by_name("Crateris") is None
    finally:
        await store.close()


@M3
@pytest.mark.req("TS-11")
async def test_each_test_gets_its_own_database(make_world: MakeWorld) -> None:
    first = await make_world("setup")
    await first.run("newbie", "character register", name="Pip")
    assert await first.character("Pip") is not None
    second = await make_world("presence")
    assert await second.character("Pip") is None


@M3
@pytest.mark.req("DB-3")
async def test_sqlite_runs_in_wal_mode_with_a_busy_timeout(tmp_path: Path) -> None:
    store = await Store.open(_url(tmp_path / "wal.db"))
    try:
        pragmas = await store.pragmas()
        assert str(pragmas["journal_mode"]).lower() == "wal"
        assert int(pragmas["busy_timeout"]) > 0
    finally:
        await store.close()


# ---------------------------------------------------------------- NF-3, DP-4: restarts


@M3
@pytest.mark.req("NF-3", "DP-4")
async def test_a_restart_mid_game_loses_nothing(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    await world.run("cal", "add", character="Cato", entry="Bolstering Aura")
    await world.run("ada", "sitout")
    before = await world.run("ben", "partybonus")

    # A new store and app on the same file, as after a restart.
    store = await Store.open(_url(world.store_path))
    try:
        app = App(
            store=store,
            discord=world.discord,
            clock=world.clock,
            catalog=world.catalog,
            settings=world.settings,
        )
        after = await app.run(world.user("ben"), "partybonus", {})
        assert counted(after) == counted(before) == {"Bryn", "Cato"}
        assert recipient(after, "Bryn").totals == recipient(before, "Bryn").totals
        cato = await store.character_by_name("Cato")
        assert cato is not None
        assert "bolstering_aura" in cato.entries
    finally:
        await store.close()


# ---------------------------------------------------------------- NF-2: scale


@M3
@pytest.mark.req("NF-2")
async def test_300_characters_on_the_server(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    for n in range(300):
        owner = UserId(90_000 + n // 2)
        await world.store.add_character(owner, f"Extra {n:03}", level=1 + n % 75)

    reply = await world.run("ada", "partybonus")
    assert counted(reply) == {"Aria", "Bryn", "Cato"}
    await world.run("cal", "character register", name="extra 150")
    extra = await world.character("Extra 150")
    assert extra is not None
    assert extra.owner == UserId(90_075), "names stay unique among hundreds of characters"


# ---------------------------------------------------------------- DB-1


@pytest.mark.milestone("M1")
@pytest.mark.req("DB-1")
def test_the_database_location_comes_from_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:////srv/awt-bonus/var/awt-bonus.db")
    assert Environment().database_url == "sqlite+aiosqlite:////srv/awt-bonus/var/awt-bonus.db"


@pytest.mark.milestone("M1")
@pytest.mark.req("DB-1", "DB-2")
def test_the_default_database_is_in_the_projects_var_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert Environment().database_url == "sqlite+aiosqlite:///var/awt-bonus.db"


# ---------------------------------------------------------------- DB-2: persistent storage


@M5
@pytest.mark.req("DB-2")
def test_the_default_location_passes_the_startup_check() -> None:
    check_database_location(ROOT / "var" / "awt-bonus.db")


@M5
@pytest.mark.req("DB-2")
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux paths; runs in CI")
@pytest.mark.parametrize("directory", ["/tmp", "/var/tmp", "/dev/shm"])
def test_a_temporary_location_is_refused_on_linux(directory: str) -> None:
    with pytest.raises(StartupError):
        check_database_location(Path(directory) / "awt-bonus" / "awt-bonus.db")


@M5
@pytest.mark.req("DB-2")
@pytest.mark.skipif(sys.platform != "win32", reason="Windows paths")
def test_a_temporary_location_is_refused_on_windows() -> None:
    with pytest.raises(StartupError):
        check_database_location(Path(os.environ["TEMP"]) / "awt-bonus" / "awt-bonus.db")


@pytest.fixture
def read_only_directory() -> Iterator[Path]:
    """A read-only folder inside the project's var/ (so it isn't temporary storage)."""
    geteuid = getattr(os, "geteuid", None)
    if geteuid is None or geteuid() == 0:
        pytest.skip("needs a POSIX system and a non-root user; runs in CI")
    directory = ROOT / "var" / f"read-only-{uuid.uuid4().hex}"
    directory.mkdir()
    directory.chmod(0o500)
    try:
        yield directory
    finally:
        directory.chmod(0o700)
        directory.rmdir()


@M5
@pytest.mark.req("DB-2")
def test_a_location_where_a_test_file_cant_be_written_is_refused(
    read_only_directory: Path,
) -> None:
    with pytest.raises(StartupError):
        check_database_location(read_only_directory / "awt-bonus.db")


# ---------------------------------------------------------------- DB-3: one bot process

_TRY_LOCK = """
import sys
from pathlib import Path
from awt_bonus.startup import StartupError, acquire_instance_lock
try:
    acquire_instance_lock(Path(sys.argv[1]))
except StartupError:
    sys.exit(3)
sys.exit(0)
"""


def _other_process_can_lock(db_path: Path) -> bool:
    result = subprocess.run(
        [sys.executable, "-c", _TRY_LOCK, str(db_path)], capture_output=True, timeout=60
    )
    assert result.returncode in (0, 3), result.stderr.decode()
    return result.returncode == 0


@M5
@pytest.mark.req("DB-3")
def test_a_second_bot_process_refuses_to_start(tmp_path: Path) -> None:
    db_path = tmp_path / "awt-bonus.db"
    lock = acquire_instance_lock(db_path)
    try:
        assert not _other_process_can_lock(db_path)
    finally:
        lock.release()
    assert _other_process_can_lock(db_path), "the lock is released when the bot stops"


@M5
@pytest.mark.req("DB-3")
def test_the_lock_is_a_context_manager(tmp_path: Path) -> None:
    db_path = tmp_path / "awt-bonus.db"
    with acquire_instance_lock(db_path):
        assert not _other_process_can_lock(db_path)
    assert _other_process_can_lock(db_path)


# ---------------------------------------------------------------- DB-4: migrations


@M5
@pytest.mark.req("DB-4", "TS-11")
async def test_migrations_bring_an_empty_database_up_to_date(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 9, 25, 20, 0, tzinfo=UTC))
    url = _url(tmp_path / "awt-bonus.db")
    await migrate_database(url, tmp_path / "snapshots", clock)

    store = await Store.open(url)
    try:
        await store.add_character(UserId(1), "Pip")
        assert await store.character_by_name("Pip") is not None
    finally:
        await store.close()


@M5
@pytest.mark.req("DB-4")
async def test_an_up_to_date_database_needs_no_migration_or_snapshot(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 9, 25, 20, 0, tzinfo=UTC))
    url = _url(tmp_path / "awt-bonus.db")
    await migrate_database(url, tmp_path / "snapshots", clock)
    store = await Store.open(url)
    await store.add_character(UserId(1), "Pip")
    await store.close()

    assert await migrate_database(url, tmp_path / "snapshots", clock) is None
    store = await Store.open(url)
    try:
        assert await store.character_by_name("Pip") is not None
    finally:
        await store.close()
