"""The thin discord.py adapter (TS-8). Command logic lives in ``awt_bonus.commands``."""

import discord


def intents() -> discord.Intents:
    """The gateway intents: Guilds and GuildVoiceStates only (NF-6).

    Both are non-privileged, so the bot never reads message content or member lists
    (NF-5).
    """
    return discord.Intents(guilds=True, voice_states=True)
