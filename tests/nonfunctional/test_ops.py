"""Operations code added in M5, beyond the M1 tests: settings errors (AD-1), the
database URL and location (DB-1, DB-2), the lock (DB-3), snapshots, uploads and the
nightly job (DB-6), restoring a snapshot (DB-7, TS-12), /request limits (CT-9) and
the logs (NF-8, NF-9).
"""

import io
import json
import logging
import sqlite3
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from awt_bonus.backup import (
    S3Uploader,
    next_nightly,
    nightly_snapshot,
    prune_snapshots,
    snapshot_due,
    snapshot_time,
    take_snapshot,
    uploader_from,
)
from awt_bonus.ids import UserId
from awt_bonus.logging_setup import configure_logging
from awt_bonus.restore import RestoreError, restore
from awt_bonus.settings import Environment, load_settings
from awt_bonus.startup import (
    StartupError,
    _filesystem_type,
    acquire_instance_lock,
    check_database_location,
    database_path,
)
from awt_bonus.store import Store
from tests.support.fakes import FakeClock
from tests.support.traceability import ROOT
from tests.support.world import MakeWorld

pytestmark = pytest.mark.milestone("M5")

NOW = datetime(2026, 9, 25, 3, 0, tzinfo=UTC)


def _url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


# ---------------------------------------------------------------- AD-1: the settings file


@pytest.mark.req("AD-1")
@pytest.mark.parametrize(
    ("text", "named"),
    [
        ("request_channel: x\nsitout_hours: 12\nmax_level: 75\nmax_levle: 80\n", "max_levle"),
        ("request_channel: x\nsitout_hours: 12\nmax_level: 0\n", "max_level"),
        ("request_channel: x\nsitout_hours: -1\nmax_level: 75\n", "sitout_hours"),
        ("request_channel: '#support'\nsitout_hours: 12\nmax_level: 75\n", "request_channel"),
        ("request_channel: x\nsitout_hours: 12\n", "max_level"),
        ("request_channel: x\nsitout_hours: 12\nmax_level: 75\nmax_level: 80\n", "max_level"),
        ("request_channel: [x\n", "YAML"),
        ("- just a list\n", "request_channel"),
    ],
    ids=[
        "unknown",
        "level-zero",
        "negative-hours",
        "hash",
        "missing",
        "duplicate",
        "bad-yaml",
        "not-a-mapping",
    ],
)
def test_a_bad_settings_file_is_refused_naming_the_problem(
    tmp_path: Path, text: str, named: str
) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(StartupError) as refused:
        load_settings(path)
    assert "settings.yaml" in str(refused.value)
    assert named in str(refused.value)


@pytest.mark.req("AD-1")
def test_a_missing_settings_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(StartupError, match=r"settings\.yaml"):
        load_settings(tmp_path / "settings.yaml")


# ---------------------------------------------------------------- DB-1, DB-2: the database file


@pytest.mark.req("DB-1")
@pytest.mark.parametrize(
    ("url", "path"),
    [
        ("sqlite+aiosqlite:///var/awt-bonus.db", Path("var/awt-bonus.db")),
        ("sqlite+aiosqlite:////data/awt-bonus.db", Path("/data/awt-bonus.db")),
        ("sqlite+aiosqlite:///C:/bot/var/awt-bonus.db", Path("C:/bot/var/awt-bonus.db")),
    ],
)
def test_database_url_names_the_database_file(url: str, path: Path) -> None:
    assert database_path(url) == path


@pytest.mark.req("DB-1")
@pytest.mark.parametrize(
    "url",
    ["postgresql://bot@db/awt", "sqlite+aiosqlite://", "sqlite+aiosqlite:///:memory:", "nonsense"],
)
def test_database_url_must_name_a_sqlite_file(url: str) -> None:
    with pytest.raises(StartupError, match="DATABASE_URL"):
        database_path(url)


@pytest.mark.req("DB-2")
def test_a_missing_database_folder_is_refused_not_created() -> None:
    """E.g. a container started without its volume: refuse, don't write to throwaway storage.

    The folder is in the project's var/, so it isn't temporary storage.
    """
    folder = ROOT / "var" / f"volume-not-mounted-{uuid.uuid4().hex}"
    with pytest.raises(StartupError, match="doesn't exist"):
        check_database_location(folder / "awt-bonus.db")
    assert not folder.exists()


@pytest.mark.req("DB-2")
def test_memory_filesystems_are_found_from_the_mount_table(tmp_path: Path) -> None:
    mounts = tmp_path / "mounts"
    mounts.write_text(
        "/dev/sda1 / ext4 rw 0 0\n"
        "tmpfs /run/user/1000 tmpfs rw 0 0\n"
        "none /srv/ram\\040disk ramfs rw 0 0\n"
        "/dev/sdb1 /data ext4 rw 0 0\n",
        encoding="utf-8",
    )
    assert _filesystem_type(Path("/run/user/1000/bot/awt.db"), mounts) == "tmpfs"
    assert _filesystem_type(Path("/srv/ram disk/awt.db"), mounts) == "ramfs"
    assert _filesystem_type(Path("/data/awt-bonus.db"), mounts) == "ext4"
    assert _filesystem_type(Path("/home/bot/awt.db"), mounts) == "ext4"
    assert _filesystem_type(Path("/data/x.db"), tmp_path / "no-mount-table") is None


# ---------------------------------------------------------------- DB-3: the lock


@pytest.mark.req("DB-3")
def test_the_lock_file_is_next_to_the_database_and_can_be_released_twice(tmp_path: Path) -> None:
    lock = acquire_instance_lock(tmp_path / "awt-bonus.db")
    assert lock.path == tmp_path / "awt-bonus.db.lock"
    lock.release()
    lock.release()
    with acquire_instance_lock(tmp_path / "awt-bonus.db"):
        pass


# ---------------------------------------------------------------- DB-6: snapshots


@pytest.fixture
async def database(tmp_path: Path) -> Path:
    path = tmp_path / "awt-bonus.db"
    store = await Store.open(_url(path))
    await store.add_character(UserId(1), "Pip")
    await store.close()
    return path


@pytest.mark.req("DB-6")
async def test_two_snapshots_at_the_same_moment_are_separate_files(
    database: Path, tmp_path: Path
) -> None:
    clock = FakeClock(NOW)
    first = await take_snapshot(database, tmp_path / "snapshots", clock)
    second = await take_snapshot(database, tmp_path / "snapshots", clock)

    assert first != second
    assert snapshot_time(first) == snapshot_time(second) == NOW
    assert sorted(p.name for p in (tmp_path / "snapshots").iterdir()) == sorted(
        [first.name, second.name]
    ), "no partial files are left behind"


@pytest.mark.req("DB-6")
async def test_pruning_leaves_other_files_alone(database: Path, tmp_path: Path) -> None:
    snapshot_dir = tmp_path / "snapshots"
    old = await take_snapshot(database, snapshot_dir, FakeClock(NOW - timedelta(days=45)))
    notes = snapshot_dir / "notes.txt"
    notes.write_text("kept", encoding="utf-8")

    assert prune_snapshots(snapshot_dir, FakeClock(NOW)) == [old]
    assert list(snapshot_dir.iterdir()) == [notes]


class _Uploads:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.uploaded: list[Path] = []

    def upload(self, path: Path) -> None:
        if self.fail:
            raise ConnectionError("storage unreachable")
        self.uploaded.append(path)


@pytest.mark.req("DB-6", "NF-8")
async def test_the_nightly_job_snapshots_uploads_and_prunes(
    database: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    snapshot_dir = tmp_path / "snapshots"
    old = await take_snapshot(database, snapshot_dir, FakeClock(NOW - timedelta(days=31)))
    uploads = _Uploads()

    with caplog.at_level(logging.INFO):
        snapshot = await nightly_snapshot(database, snapshot_dir, FakeClock(NOW), uploads)

    assert uploads.uploaded == [snapshot]
    assert not old.exists()
    assert {"snapshot taken", "snapshot uploaded", "snapshots pruned"} <= {
        r.getMessage() for r in caplog.records
    }


@pytest.mark.req("DB-6", "NF-8")
async def test_a_failed_upload_is_logged_and_the_snapshot_kept(
    database: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        snapshot = await nightly_snapshot(
            database, tmp_path / "snapshots", FakeClock(NOW), _Uploads(fail=True)
        )
    assert snapshot.exists()
    failed = [r for r in caplog.records if r.getMessage() == "snapshot upload failed"]
    assert len(failed) == 1
    assert failed[0].levelno == logging.ERROR
    assert failed[0].exc_info is not None


@pytest.mark.req("DB-6")
async def test_without_storage_the_snapshot_stays_local_with_a_warning(
    database: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    snapshot = await nightly_snapshot(database, tmp_path / "snapshots", FakeClock(NOW), None)
    assert snapshot.exists()
    assert any(r.levelno == logging.WARNING for r in caplog.records)


@pytest.mark.req("DB-6", "NF-10")
def test_the_nightly_snapshot_runs_once_a_day_at_a_fixed_utc_time() -> None:
    before = datetime(2026, 9, 25, 7, 59, tzinfo=UTC)
    after = datetime(2026, 9, 25, 8, 0, tzinfo=UTC)
    first = next_nightly(before)
    assert first > before
    assert first - before < timedelta(days=1)
    assert next_nightly(after) > after
    assert next_nightly(first) == first + timedelta(days=1)
    assert first.utcoffset() == timedelta(0)


@pytest.mark.req("DB-6")
async def test_a_snapshot_is_due_at_startup_if_the_newest_is_over_a_day_old(
    database: Path, tmp_path: Path
) -> None:
    snapshot_dir = tmp_path / "snapshots"
    assert snapshot_due(snapshot_dir, NOW), "no snapshots yet"
    await take_snapshot(database, snapshot_dir, FakeClock(NOW - timedelta(hours=30)))
    assert snapshot_due(snapshot_dir, NOW)
    await take_snapshot(database, snapshot_dir, FakeClock(NOW - timedelta(hours=2)))
    assert not snapshot_due(snapshot_dir, NOW)


@pytest.mark.req("DB-6", "NF-9")
def test_uploads_need_the_whole_storage_setup_from_the_environment() -> None:
    complete = {
        "backup_bucket": "awt-backups",
        "backup_endpoint_url": "s3.us-east-005.backblazeb2.com",
        "backup_key_id": "key-id",
        "backup_key": "key-secret",
    }
    assert isinstance(uploader_from(Environment(**complete)), S3Uploader)  # type: ignore[arg-type]
    for missing in complete:
        partial = {k: v for k, v in complete.items() if k != missing}
        assert uploader_from(Environment(**partial)) is None, missing  # type: ignore[arg-type]


# ---------------------------------------------------------------- DB-7, TS-12: restoring


@pytest.mark.req("DB-7", "TS-12")
async def test_a_restored_snapshot_holds_the_data_it_was_taken_with(
    database: Path, tmp_path: Path
) -> None:
    snapshot = await take_snapshot(database, tmp_path / "snapshots", FakeClock(NOW))
    store = await Store.open(_url(database))
    await store.add_character(UserId(1), "Added later")
    await store.close()

    kept = restore(snapshot, database, NOW)

    store = await Store.open(_url(database))
    try:
        assert [c.name for c in await store.all_characters()] == ["Pip"]
    finally:
        await store.close()
    assert kept is not None
    assert kept.exists(), "the database it replaced is kept"


@pytest.mark.req("DB-7", "TS-12")
async def test_a_snapshot_restores_onto_a_new_host(database: Path, tmp_path: Path) -> None:
    snapshot = await take_snapshot(database, tmp_path / "snapshots", FakeClock(NOW))
    new_host = tmp_path / "new-host"
    new_host.mkdir()

    assert restore(snapshot, new_host / "awt-bonus.db", NOW) is None

    store = await Store.open(_url(new_host / "awt-bonus.db"))
    try:
        assert await store.character_by_name("Pip") is not None
    finally:
        await store.close()


@pytest.mark.req("DB-7", "DB-3")
async def test_restoring_is_refused_while_the_bot_runs(database: Path, tmp_path: Path) -> None:
    snapshot = await take_snapshot(database, tmp_path / "snapshots", FakeClock(NOW))
    with acquire_instance_lock(database), pytest.raises(StartupError):
        restore(snapshot, database, NOW)


@pytest.mark.req("DB-7")
def test_only_a_sound_bot_database_is_restored(tmp_path: Path) -> None:
    junk = tmp_path / "junk.db"
    junk.write_text("not a database", encoding="utf-8")
    empty = tmp_path / "empty.db"
    sqlite3.connect(empty).close()
    target = tmp_path / "awt-bonus.db"

    for bad in (junk, empty, tmp_path / "missing.db"):
        with pytest.raises(RestoreError):
            restore(bad, target, NOW)
    assert not target.exists()


# ---------------------------------------------------------------- CT-9: /request limits


@pytest.mark.req("CT-9")
@pytest.mark.parametrize("text", ["", "   ", "x" * 1001], ids=["empty", "blank", "1001-chars"])
async def test_a_blank_or_overlong_request_is_refused_and_not_posted(
    make_world: MakeWorld, text: str
) -> None:
    world = await make_world("setup")
    reply = await world.run("craig", "request", text=text)
    assert reply.private
    assert world.discord.posts == []


@pytest.mark.req("CT-9")
async def test_a_request_names_the_players_current_character(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "request", text="Please add the Dragon Scale item")
    [(_, text)] = world.discord.posts
    assert "Craig" in text
    assert "Crateris" in text
    assert str(world.user("craig")) in text, "a mention, so the maintainer can reply"


# ---------------------------------------------------------------- NF-8, NF-9: logs


@pytest.fixture
def root_logging() -> Iterator[None]:
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    try:
        yield
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


@pytest.mark.req("NF-8", "NF-9")
@pytest.mark.usefixtures("root_logging")
def test_secret_values_are_redacted_wherever_they_appear(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "token-value-123")
    monkeypatch.setenv("BACKUP_KEY", "storage-key-456")
    stream = io.StringIO()
    configure_logging(stream)

    logging.getLogger("awt_bonus").info(
        "connecting with token-value-123", extra={"detail": "key=storage-key-456"}
    )

    logged = stream.getvalue()
    assert "token-value-123" not in logged
    assert "storage-key-456" not in logged
    assert json.loads(logged)["event"] == "connecting with [redacted]"


@pytest.mark.req("NF-8")
@pytest.mark.usefixtures("root_logging")
async def test_a_command_that_fails_is_logged_once_as_an_error_with_the_traceback(
    make_world: MakeWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = await make_world("setup")
    stream = io.StringIO()
    configure_logging(stream)

    async def broken_post(channel_name: str, text: str) -> None:
        raise RuntimeError("no text channel called #bonus-bot-support")

    monkeypatch.setattr(world.discord, "post", broken_post)
    with pytest.raises(RuntimeError):
        await world.run("craig", "request", text="Please add the Dragon Scale item")

    commands = [r for r in map(json.loads, stream.getvalue().splitlines()) if "command" in r]
    assert len(commands) == 1
    assert commands[0]["outcome"] == "error"
    assert commands[0]["level"] == "error"
    assert "RuntimeError: no text channel" in commands[0]["error"]
    assert "Dragon Scale" not in stream.getvalue(), "never the player's text"


@pytest.mark.req("NF-8")
@pytest.mark.usefixtures("root_logging")
async def test_an_unknown_command_is_logged_as_refused(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    stream = io.StringIO()
    configure_logging(stream)

    reply = await world.run("craig", "teleport")

    assert reply.private
    [record] = [r for r in map(json.loads, stream.getvalue().splitlines()) if "command" in r]
    assert record["command"] == "teleport"
    assert record["outcome"] == "refused"
