"""/bogsy: the current character's party bonuses as Bogsy /modifier commands (section 14).

Roll stats only (BG-1; combat notes, effects and conditional bonuses are never
exported, rule 4.12). CM and CR hold the totals; each CR subtype holds only the extra
on top of its parent, because Bogsy adds modifiers together when rolling. Every roll
stat is always listed, with 0 for none, so quickrolls keep working (BG-3).
"""

from collections.abc import Mapping

from awt_bonus.catalog import Catalog, StatKind
from awt_bonus.commands._base import Context, Refused, no_character_hint, private
from awt_bonus.commands._presence import build_party, sitting_out
from awt_bonus.commands._types import Reply
from awt_bonus.ids import StatId
from awt_bonus.output.describe import channel_mention, timestamp
from awt_bonus.output.messages import code, text

PREFIX = "bonus_"
"""Keeps the party's modifiers apart from players' own, e.g. my_fear (BG-2)."""

SETUP = (
    "Set up your quickrolls once with `bonus_cm` and `bonus_cr`, e.g. "
    "`challenge = 1d20 + cr_level + my_cr_bonus + bonus_cr`. For a roll of one CR type, "
    "add its modifiers when you roll, e.g. `/roll command:challenge+my_fear+bonus_fear`. "
    "Keep your own bonuses in modifiers of your own (e.g. `my_fear`), so these never "
    "overwrite them."
)
"""How to use the export (BG-1). It mustn't mention the /modifier command itself."""


def modifier_name(catalog: Catalog, stat_id: StatId) -> str:
    """``bonus_`` and the stat's name; for CR subtypes, without "CR" or "vs" (BG-2)."""
    words = str(stat_id).casefold().split()
    if catalog.stats[stat_id].parent is not None:
        words = [w for w in words if w not in ("cr", "vs")]
    return PREFIX + "_".join(words)


def modifier_values(catalog: Catalog, totals: Mapping[StatId, int]) -> list[tuple[str, int]]:
    """Every roll stat in the catalog's order, as (name, value) (BG-1, BG-3)."""
    values = []
    for stat in catalog.stats.values():
        if stat.kind is not StatKind.ROLL:
            continue
        value = totals.get(stat.id, 0)
        if stat.parent is not None:
            value = max(0, value - totals.get(stat.parent, 0))  # only the extra
        values.append((modifier_name(catalog, stat.id), value))
    return values


async def bogsy(ctx: Context) -> Reply:
    """Section 14: always private (OUT-5), for the caller's current character."""
    character = await ctx.store.current_character(ctx.user)
    if character is None:
        if await ctx.store.characters_of(ctx.user):
            raise Refused("You have no current character. Choose one with `/play <character>`.")
        raise Refused(no_character_hint())

    channel = await ctx.discord.voice_channel_of(ctx.user)
    if channel is None:
        return _export(
            ctx, character.name, {}, "You aren't in a voice channel, so there's no party."
        )
    party = await build_party(ctx, channel)
    state = party.players.get(ctx.user)
    if state is not None and (until := sitting_out(state, ctx.now)) is not None:
        return _export(
            ctx,
            character.name,
            {},
            f"You're sitting out until {timestamp(until, 't')}, so {character.name} isn't counted.",
        )
    recipient = next(
        (
            r
            for r in party.report.recipients
            if r.character is not None and r.character.id == character.id
        ),
        None,
    )
    if recipient is None:
        return _export(ctx, character.name, {}, f"{character.name} isn't in that party.")
    return _export(ctx, character.name, recipient.totals, None, where=channel_mention(channel.id))


def _export(
    ctx: Context,
    name: str,
    totals: Mapping[StatId, int],
    why_zero: str | None,
    where: str | None = None,
) -> Reply:
    heading = f"**Bogsy modifiers** for {name}" + (f" ({where})" if where else "")
    lines = [heading]
    if why_zero is not None:
        lines.append(f"{why_zero} These set every party bonus to 0.")
    lines.append("Paste the lines your rolls use:")
    commands = [f"/modifier name:{n} value:{v}" for n, v in modifier_values(ctx.catalog, totals)]
    return private(text(*lines), code(*commands), text(SETUP))
