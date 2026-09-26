"""The Discord connection (NF-5, NF-6): only the Guilds and GuildVoiceStates intents,
both non-privileged, so the bot never reads message content or member lists.
"""

import discord
import pytest

from awt_bonus.bot import intents

pytestmark = pytest.mark.milestone("M3")


@pytest.mark.req("NF-6", "NF-5")
def test_the_bot_asks_only_for_guilds_and_voice_states() -> None:
    wanted = intents()

    assert wanted.value == discord.Intents(guilds=True, voice_states=True).value
    assert wanted.guilds
    assert wanted.voice_states


@pytest.mark.req("NF-6", "NF-5")
def test_the_bot_asks_for_no_privileged_intents() -> None:
    wanted = intents()

    assert not wanted.message_content
    assert not wanted.members
    assert not wanted.presences
