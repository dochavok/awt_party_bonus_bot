"""The thin discord.py adapter (TS-8). Command logic lives in ``awt_bonus.commands``."""

import discord


def intents() -> discord.Intents:
    """The gateway intents: Guilds and GuildVoiceStates only (NF-6)."""
    raise NotImplementedError
