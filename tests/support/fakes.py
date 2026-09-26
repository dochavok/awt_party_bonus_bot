"""The fake Discord and the fake clock (requirements TF-2, TS-8, TS-10).

These are test doubles, fully implemented: they only hold and return test data.
"""

from datetime import datetime, timedelta

from awt_bonus.ids import ChannelId, UserId
from awt_bonus.ports import Member, VoiceChannel


class FakeClock:
    """A controllable clock that only ever holds a UTC time (NF-10, TS-10)."""

    def __init__(self, now: datetime) -> None:
        self._now = self._check(now)

    @staticmethod
    def _check(value: datetime) -> datetime:
        offset = value.utcoffset()
        if offset is None:
            raise ValueError(f"FakeClock needs a timezone-aware time, got naive {value!r}")
        if offset != timedelta(0):
            raise ValueError(f"FakeClock needs a UTC time, got offset {offset}")
        return value

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = self._check(now)

    def advance(self, delta: timedelta) -> None:
        self._now = self._now + delta


class FakeDiscord:
    """A fake server: voice channels, members with roles, bots, and posted messages."""

    def __init__(self) -> None:
        self._members: dict[UserId, Member] = {}
        self._voice: dict[ChannelId, VoiceChannel] = {}
        self._text: dict[ChannelId, str] = {}
        self._location: dict[UserId, ChannelId] = {}
        self.posts: list[tuple[str, str]] = []
        """Every message posted, as (channel name, text)."""
        self.role_lookups = 0
        """How many times a member's roles were looked up."""

    # Setting up the fake server.

    def add_voice_channel(self, channel_id: ChannelId, name: str) -> None:
        self._voice[channel_id] = VoiceChannel(id=channel_id, name=name)

    def add_text_channel(self, channel_id: ChannelId, name: str) -> None:
        self._text[channel_id] = name

    def add_member(
        self,
        user_id: UserId,
        display_name: str,
        roles: frozenset[str] = frozenset(),
        is_bot: bool = False,
    ) -> None:
        self._members[user_id] = Member(
            user_id=user_id, display_name=display_name, roles=roles, is_bot=is_bot
        )

    def move(self, user_id: UserId, channel_id: ChannelId | None) -> None:
        """Put a member in a voice channel, or take them out of voice (None).

        A member who moves goes to the end of the channel's member list.
        """
        self._location.pop(user_id, None)
        if channel_id is not None:
            if channel_id not in self._voice:
                raise KeyError(f"no voice channel {channel_id}")
            self._location[user_id] = channel_id

    def set_roles(self, user_id: UserId, roles: frozenset[str]) -> None:
        old = self._members[user_id]
        self._members[user_id] = Member(
            user_id=old.user_id, display_name=old.display_name, roles=roles, is_bot=old.is_bot
        )

    def text_channel_names(self) -> list[str]:
        return list(self._text.values())

    # The DiscordGateway interface.

    async def voice_channel_of(self, user_id: UserId) -> VoiceChannel | None:
        channel_id = self._location.get(user_id)
        return None if channel_id is None else self._voice[channel_id]

    async def voice_channel(self, channel_id: ChannelId) -> VoiceChannel | None:
        return self._voice.get(channel_id)

    async def voice_members(self, channel_id: ChannelId) -> list[Member]:
        return [
            self._members[user_id]
            for user_id, where in self._location.items()
            if where == channel_id
        ]

    async def member(self, user_id: UserId) -> Member | None:
        self.role_lookups += 1
        return self._members.get(user_id)

    async def post(self, channel_name: str, text: str) -> None:
        self.posts.append((channel_name, text))
