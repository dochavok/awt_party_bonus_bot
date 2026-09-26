"""Presence in the voice channel (requirements 6.5): /sitout, /sitin, and who is counted.

There are no sessions: each time an output command runs, the party is worked out from
whoever is in the voice channel, their sit-outs and their current characters.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from awt_bonus.commands._base import Context, private
from awt_bonus.commands._types import Reply
from awt_bonus.engine import CharacterRef, PartyReport, PresentPlayer, compute
from awt_bonus.ids import CharacterId, EntryId, GuildId, UserId
from awt_bonus.output.describe import timestamp
from awt_bonus.ports import VoiceChannel
from awt_bonus.store import CharacterRecord, PlayerState


async def sitout(ctx: Context) -> Reply:
    """SE-2: only ever the caller (NF-4)."""
    until = ctx.now + timedelta(hours=ctx.settings.sitout_hours)
    await ctx.store.set_sitout(ctx.user, until)
    return private(
        f"You're sitting out until {timestamp(until, 'f')} ({timestamp(until, 'R')}), "
        "so you aren't counted in any voice channel. `/sitin` ends it early."
    )


async def sitin(ctx: Context) -> Reply:
    """SE-2."""
    was = await ctx.store.sitout_until(ctx.user)
    await ctx.store.set_sitout(ctx.user, None)
    if was is None or was <= ctx.now:
        return private("You weren't sitting out, so you're already counted.")
    return private("You're counted again.")


def sitting_out(state: PlayerState, now: datetime) -> datetime | None:
    """The end of an **active** sit-out, checked against the clock (SE-2, NF-10)."""
    until = state.sitout_until
    return until if until is not None and until > now else None


@dataclass(frozen=True)
class Party:
    """A voice channel's party, and what the output needs to describe it."""

    channel: VoiceChannel
    report: PartyReport
    characters: dict[CharacterId, CharacterRecord]
    """Every counted character, by ID (for levels and when they were updated)."""
    players: dict[UserId, PlayerState]
    """Every person in the channel (bots excepted), with their real current character."""


async def build_party(
    ctx: Context, channel: VoiceChannel, substitute: CharacterRecord | None = None
) -> Party:
    """Work out the party in ``channel`` (section 11, step 0).

    ``substitute`` is the OUT-2a character: it takes its player's place instead of
    their current character, if that player is in the channel.
    """
    members = await ctx.discord.voice_members(channel.id)
    states = await ctx.store.players(m.user_id for m in members if not m.is_bot)
    present: list[PresentPlayer] = []
    counted: dict[CharacterId, CharacterRecord] = {}
    for member in members:
        if member.is_bot:  # ignored and never listed (SE-6)
            present.append(PresentPlayer(member.user_id, member.display_name, is_bot=True))
            continue
        state = states[member.user_id]
        until = sitting_out(state, ctx.now)
        record = state.current
        if substitute is not None and substitute.owner == member.user_id:
            record = substitute
        if until is None and record is not None:
            counted[record.id] = record
        present.append(
            PresentPlayer(
                user_id=member.user_id,
                display_name=member.display_name,
                sitting_out_until=until,
                character=_ref(record),
            )
        )
    report = compute(
        present,
        {},  # Support from Discord roles (HV-3) comes with the Guilds milestone.
        {i: tuple(EntryId(e) for e in c.entries) for i, c in counted.items()},
        {i: tuple(GuildId(g) for g in c.guilds) for i, c in counted.items()},
        ctx.catalog,
    )
    return Party(channel, report, counted, states)


async def solo(ctx: Context, character: CharacterRecord) -> PartyReport:
    """A party of one: what ``character`` gives, with modifiers applied (OUT-4)."""
    player = PresentPlayer(character.owner, character.name, character=_ref(character))
    return compute(
        [player],
        {},
        {character.id: character.entries},
        {character.id: character.guilds},
        ctx.catalog,
    )


def _ref(record: CharacterRecord | None) -> CharacterRef | None:
    if record is None:
        return None
    return CharacterRef(record.id, record.name, record.level)
