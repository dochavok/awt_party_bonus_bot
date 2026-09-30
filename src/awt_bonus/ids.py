"""Identifier types shared across the bot."""

from typing import NewType

UserId = NewType("UserId", int)
"""A Discord user ID."""

CharacterId = NewType("CharacterId", int)
"""A character's database ID."""

ChannelId = NewType("ChannelId", int)
"""A Discord channel ID."""

EntryId = NewType("EntryId", str)
"""A catalog entry's permanent ID (CT-2): a skill, boon, rank, item or title."""

GuildId = NewType("GuildId", str)
"""A catalog guild's permanent ID (CT-2)."""

StatId = NewType("StatId", str)
"""A catalog stat's ID, e.g. "CM" or "CR vs fear"."""

ItemClassId = NewType("ItemClassId", str)
"""A catalog item class's permanent ID (CT-10), e.g. "passion"."""
