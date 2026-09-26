"""Structured logs (NF-8): JSON lines with time, level and event; one line per
command; nothing secret (NF-9) and no reply text (section 6.4).
"""

import io
import json
import logging
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any

import pytest

from awt_bonus.logging_setup import configure_logging
from tests.support.world import MakeWorld

pytestmark = pytest.mark.milestone("M5")


@pytest.fixture
def log_stream() -> Iterator[io.StringIO]:
    """Capture the bot's logs, and put Python's logging back afterwards."""
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    stream = io.StringIO()
    configure_logging(stream)
    try:
        yield stream
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


def _lines(stream: io.StringIO) -> list[dict[str, Any]]:
    """Every log line, parsed; fails if any line isn't a JSON object."""
    parsed = []
    for line in stream.getvalue().splitlines():
        record = json.loads(line)
        assert isinstance(record, dict), f"not a JSON object: {line!r}"
        parsed.append(record)
    return parsed


def _command_lines(stream: io.StringIO) -> list[dict[str, Any]]:
    return [r for r in _lines(stream) if "command" in r]


@pytest.mark.req("NF-8", "NF-10")
async def test_every_log_line_is_json_with_utc_time_level_and_event(
    make_world: MakeWorld, log_stream: io.StringIO
) -> None:
    world = await make_world("setup")
    await world.run("craig", "partybonus")
    await world.run("craig", "mybonus")

    records = _lines(log_stream)
    assert records
    for record in records:
        assert {"time", "level", "event"} <= set(record), record
        moment = datetime.fromisoformat(str(record["time"]).replace("Z", "+00:00"))
        assert moment.utcoffset() == timedelta(0), f"not UTC: {record['time']}"


@pytest.mark.req("NF-8")
async def test_each_command_logs_one_line_with_its_outcome_and_duration(
    make_world: MakeWorld, log_stream: io.StringIO
) -> None:
    world = await make_world("setup")
    await world.run("craig", "partybonus")
    await world.run("craig", "add", character="Elowen", entry="Holy Aura")

    commands = _command_lines(log_stream)
    assert [r["command"] for r in commands] == ["partybonus", "add"]
    for record in commands:
        assert record["user_id"] == world.user("craig")
        assert record["outcome"] == "ok"
        assert isinstance(record["duration_ms"], int | float)
        assert record["duration_ms"] >= 0


@pytest.mark.req("NF-8", "NF-4")
async def test_a_refused_command_is_logged_as_refused(
    make_world: MakeWorld, log_stream: io.StringIO
) -> None:
    world = await make_world("setup")
    await world.run("mallory", "character rename", character="Crateris", new="Stolen")

    commands = _command_lines(log_stream)
    assert len(commands) == 1
    assert commands[0]["command"] == "character rename"
    assert commands[0]["user_id"] == world.user("mallory")
    assert commands[0]["outcome"] == "refused"


@pytest.mark.req("NF-8")
def test_errors_include_the_traceback(log_stream: io.StringIO) -> None:
    try:
        raise RuntimeError("the database went away")
    except RuntimeError:
        logging.getLogger("awt_bonus").exception("unexpected failure")

    records = _lines(log_stream)
    assert len(records) == 1
    assert records[0]["level"].lower() == "error"
    assert "RuntimeError: the database went away" in records[0]["error"]
    assert "Traceback" in records[0]["error"]


@pytest.mark.req("NF-8", "NF-9", "SG-3", "NF-5")
async def test_logs_never_contain_secrets_or_reply_text(
    make_world: MakeWorld, log_stream: io.StringIO, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "never-log-this-token")
    world = await make_world("sample-game")
    replies = [
        await world.run("cole", "breakdown", character="Chris"),  # secret guild detail
        await world.run("maya", "mybonus", character="Mira"),
        await world.run("isla", "breakdown"),
    ]

    logged = log_stream.getvalue()
    assert _command_lines(log_stream), "the commands were logged"
    assert "never-log-this-token" not in logged
    assert "Rat Pack" not in logged
    assert "Leadership" not in logged
    for reply in replies:
        for line in reply.text.splitlines():
            if len(line.strip()) >= 20:
                assert line.strip() not in logged, f"reply text in the logs: {line.strip()!r}"
