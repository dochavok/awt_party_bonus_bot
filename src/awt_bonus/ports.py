"""Interfaces to the outside world: the clock and Discord (requirements TF-2, TS-8).

The real Discord adapter and the test fakes both implement these, so command
logic never touches discord.py directly.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from awt_bonus.ids import ChannelId, UserId


class Clock(Protocol):
    def now(self) -> datetime:
        """The current time, timezone-aware, in UTC (NF-10)."""
        ...


@dataclass(frozen=True)
class Member:
    """A server member, as Discord reports them."""

    user_id: UserId
    display_name: str
    roles: frozenset[str]
    """Role names."""
    is_bot: bool = False


@dataclass(frozen=True)
class VoiceChannel:
    id: ChannelId
    name: str


class DiscordGateway(Protocol):
    async def voice_channel_of(self, user_id: UserId) -> VoiceChannel | None:
        """The voice channel this member is in, if any (SE-1)."""
        ...

    async def voice_channel(self, channel_id: ChannelId) -> VoiceChannel | None:
        """A voice channel by ID, for the ``channel:`` option (SE-1)."""
        ...

    async def voice_members(self, channel_id: ChannelId) -> list[Member]:
        """Everyone in a voice channel, bots included."""
        ...

    async def member(self, user_id: UserId) -> Member | None:
        """One member, with current roles, looked up individually (NF-6)."""
        ...

    async def post(self, channel_name: str, text: str) -> None:
        """Post a message to a text channel, e.g. a ``/request`` (CT-9)."""
        ...


class SystemClock:
    """The real clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)
