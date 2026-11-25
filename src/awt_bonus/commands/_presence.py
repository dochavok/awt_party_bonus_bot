"""Presence in the voice channel (requirements 6.5): /sitout, /sitin, and who is counted.

There are no sessions: each time an output command runs, the party is worked out from
whoever is in the voice channel, their sit-outs and their current characters.
"""

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from awt_bonus.catalog import Catalog, Guild
from awt_bonus.commands._base import Context, Refused, private
from awt_bonus.commands._types import Reply
from awt_bonus.engine import CharacterRef, PartyReport, PresentPlayer, compute
from awt_bonus.ids import CharacterId, EntryId, GuildId, UserId
from awt_bonus.output.describe import timestamp
from awt_bonus.ports import VoiceChannel
from awt_bonus.store import CharacterRecord, PlayerState


async def sitout(ctx: Context) -> Reply:
    """SE-2: only ever the caller (NF-4). ``support:true`` is a supporting sit-out (SE-7)."""
    support = ctx.flag("support")
    member = await ctx.discord.member(ctx.user)
    roles = member.roles if member is not None else frozenset()
    allowances = sitting_out_allowances(ctx.catalog)
    held = [r for a in allowances for r in a.roles if r in roles]
    if support and not held:
        raise Refused(*_support_refusal(allowances))

    until = ctx.now + timedelta(hours=ctx.settings.sitout_hours)
    await ctx.store.set_sitout(ctx.user, until, supporting=support)
    when = f"until {timestamp(until, 'f')} ({timestamp(until, 'R')})"
    if support:
        bonuses = " and ".join(dict.fromkeys(b for a in allowances for b in a.bonuses))
        return private(
            f"You're sitting out {when}, but still giving {bonuses} while you're in the "
            "voice channel. `/sitin` ends it early."
        )
    lines = [
        f"You're sitting out {when}, so you aren't counted in any voice channel. "
        "`/sitin` ends it early."
    ]
    if held:  # SE-8
        bonuses = " and ".join(dict.fromkeys(b for a in allowances for b in a.bonuses))
        lines.append(
            f"You have {held[0]}, so you can keep giving {bonuses} while you listen in: "
            "`/sitout support:true`."
        )
    return private(*lines)


@dataclass(frozen=True)
class Allowance:
    """A role guild's bonuses that some of its roles still give while sitting out (CT-5)."""

    guild: Guild
    roles: tuple[str, ...]
    """The allowed roles, in the guild's order (lowest first)."""
    bonuses: tuple[str, ...]


def sitting_out_allowances(catalog: Catalog) -> list[Allowance]:
    """Every role guild with a bonus allowed while sitting out (SE-7)."""
    found = []
    for guild in catalog.guilds.values():
        abilities = [a for a in guild.role_abilities if a.while_sitting_out]
        if abilities:
            allowed = set().union(*(a.while_sitting_out for a in abilities))
            roles = tuple(r for r in guild.roles if r in allowed)
            found.append(Allowance(guild, roles, tuple(a.name for a in abilities)))
    return found


def _support_refusal(allowances: list[Allowance]) -> list[str]:
    if not allowances:
        return [
            "Nobody can keep giving a bonus while sitting out at the moment. "
            "`/sitout` on its own sits you out."
        ]
    lines = []
    for a in allowances:
        lines.append(
            f"Only players with {_or(a.roles)} can keep giving {' and '.join(a.bonuses)} "
            "while sitting out, so you're not sitting out. `/sitout` on its own sits you out."
        )
        if a.guild.how_to_join is not None:
            lines.append(a.guild.how_to_join)
    return lines


def _or(items: tuple[str, ...]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} or {items[-1]}"


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
    counted_players: list[UserId] = []
    supporters: list[UserId] = []
    for member in members:
        if member.is_bot:  # ignored and never listed (SE-6)
            present.append(PresentPlayer(member.user_id, member.display_name, is_bot=True))
            continue
        state = states[member.user_id]
        until = sitting_out(state, ctx.now)
        record = state.current
        if substitute is not None and substitute.owner == member.user_id:
            record = substitute
        supporting = until is not None and state.sitout_supporting
        if until is None:
            counted_players.append(member.user_id)
            if record is not None:
                counted[record.id] = record
        elif supporting:  # still gives Support, so their roles are needed (SE-7)
            supporters.append(member.user_id)
        present.append(
            PresentPlayer(
                user_id=member.user_id,
                display_name=member.display_name,
                sitting_out_until=until,
                character=_ref(record),
                supporting=supporting,
            )
        )
    report = compute(
        present,
        await roles(ctx, counted_players + supporters),
        {i: tuple(EntryId(e) for e in c.entries) for i, c in counted.items()},
        {i: tuple(GuildId(g) for g in c.guilds) for i, c in counted.items()},
        ctx.catalog,
        {i: c.item_counts for i, c in counted.items()},
    )
    return Party(channel, report, counted, states)


async def solo(ctx: Context, character: CharacterRecord) -> PartyReport:
    """A party of one: what ``character`` gives, with modifiers applied (OUT-4)."""
    player = PresentPlayer(character.owner, character.name, character=_ref(character))
    return compute(
        [player],
        await roles(ctx, [character.owner]),
        {character.id: character.entries},
        {character.id: character.guilds},
        ctx.catalog,
        {character.id: character.item_counts},
    )


async def roles(ctx: Context, user_ids: Iterable[UserId]) -> dict[UserId, frozenset[str]]:
    """Each player's Discord roles, for Support (HV-3).

    Looked up one member at a time on every calculation (NF-6); the Discord
    adapter remembers each answer for about a minute.
    """
    wanted = list(dict.fromkeys(user_ids))
    members = await asyncio.gather(*(ctx.discord.member(u) for u in wanted))
    return {u: m.roles for u, m in zip(wanted, members, strict=True) if m is not None}


def _ref(record: CharacterRecord | None) -> CharacterRef | None:
    if record is None:
        return None
    return CharacterRef(record.id, record.name, record.level)
