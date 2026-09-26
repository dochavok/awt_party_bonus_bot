"""Time zones (NF-10, TS-10): everything is stored and checked in GMT (UTC), and times
shown to players use Discord timestamps. Tested with the fake clock, including a
host set to a different time zone.
"""

import os
import time
from collections.abc import Iterator
from datetime import timedelta

import pytest

from tests.support.text import discord_timestamp
from tests.support.world import MakeWorld

pytestmark = pytest.mark.milestone("M3")


@pytest.fixture
def host_time_zone() -> Iterator[None]:
    """Pretend the host is in a far-off time zone (UTC+14) for the test."""
    if not hasattr(time, "tzset"):
        pytest.skip("changing the host time zone needs time.tzset (not on Windows); runs in CI")
    old = os.environ.get("TZ")
    os.environ["TZ"] = "Pacific/Kiritimati"
    time.tzset()
    try:
        yield
    finally:
        if old is None:
            del os.environ["TZ"]
        else:
            os.environ["TZ"] = old
        time.tzset()


@pytest.mark.req("NF-10", "TS-10", "SE-2")
async def test_sitout_ends_are_stored_in_utc(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    await world.run("ada", "sitout")

    until = await world.store.sitout_until(world.user("ada"))
    assert until is not None
    assert until.utcoffset() == timedelta(0)
    assert until == world.clock.now() + timedelta(hours=12)


@pytest.mark.req("NF-10", "TS-10", "CH-6")
async def test_level_updates_are_stored_in_utc(make_world: MakeWorld) -> None:
    world = await make_world("setup")
    await world.run("craig", "character level", character="Elowen", level=13)

    elowen = await world.character("Elowen")
    assert elowen is not None
    assert elowen.level_updated_at is not None
    assert elowen.level_updated_at.utcoffset() == timedelta(0)
    assert elowen.level_updated_at == world.clock.now()


@pytest.mark.req("NF-10", "TS-10", "SE-2", "SE-4")
async def test_times_shown_to_players_are_discord_timestamps(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    reply = await world.run("ada", "sitout")
    assert discord_timestamp(world.clock.now() + timedelta(hours=12)) in reply.text

    reply = await world.run("ben", "partybonus")
    assert discord_timestamp(world.clock.now() + timedelta(hours=12)) in reply.text  # not counted


@pytest.mark.req("NF-10", "TS-10", "SE-2")
async def test_a_host_in_another_time_zone_changes_nothing(
    make_world: MakeWorld, host_time_zone: None
) -> None:
    world = await make_world("presence")
    reply = await world.run("ada", "sitout")

    until = await world.store.sitout_until(world.user("ada"))
    assert until == world.clock.now() + timedelta(hours=12)
    assert until is not None
    assert until.utcoffset() == timedelta(0)
    assert discord_timestamp(world.clock.now() + timedelta(hours=12)) in reply.text

    world.clock.advance(timedelta(hours=11))
    reply = await world.run("ben", "partybonus")
    assert reply.report is not None
    assert "Aria" not in {r.name for r in reply.report.recipients}  # still sitting out


@pytest.mark.req("NF-10", "TS-10", "SE-2")
async def test_sitouts_are_checked_against_the_clock_not_the_host(make_world: MakeWorld) -> None:
    world = await make_world("presence")
    # Gus sits out until 02:00 UTC on the 26th; Hal until 21:00 UTC on the 25th.
    world.clock.advance(timedelta(hours=1, minutes=1))  # 21:01 UTC
    reply = await world.run("gus", "partybonus")

    assert reply.report is not None
    assert {r.name for r in reply.report.recipients} == {"Hollis"}
