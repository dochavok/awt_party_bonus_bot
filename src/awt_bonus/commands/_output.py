"""/partybonus, /mybonus and /breakdown (requirements 6.6).

/partybonus and the party /breakdown use the caller's voice channel; /mybonus and
/breakdown <character> use the voice channel of the character's player; ``channel:``
picks one explicitly (SE-1).
"""

from awt_bonus.commands._base import Context, Refused, no_character_hint
from awt_bonus.commands._presence import Party, build_party, sitting_out, solo
from awt_bonus.commands._types import Reply
from awt_bonus.engine import PartyReport, RecipientReport
from awt_bonus.ids import ChannelId, UserId
from awt_bonus.output import render
from awt_bonus.output.describe import channel_mention, timestamp
from awt_bonus.output.messages import Block, to_messages
from awt_bonus.ports import VoiceChannel
from awt_bonus.store import CharacterRecord


async def partybonus(ctx: Context) -> Reply:
    """OUT-1: public by default; ``private:true`` for a quiet check (OUT-5)."""
    party = await build_party(ctx, await _callers_channel(ctx))
    view = await _view(ctx, party)
    return _reply(render.partybonus(view), party.report, private=ctx.flag("private"))


async def mybonus(ctx: Context) -> Reply:
    """OUT-2, OUT-2a, OUT-4, CH-5. The Bogsy hand-off is its own command, /bogsy."""
    return await _one_character(ctx, render.mybonus)


async def breakdown(ctx: Context) -> Reply:
    """OUT-3 for the party; OUT-3a, OUT-2a and OUT-4 for one character."""
    if ctx.text("character") is None:
        party = await build_party(ctx, await _callers_channel(ctx))
        view = await _view(ctx, party)
        return _reply(render.party_breakdown(view), party.report, private=True)
    return await _one_character(ctx, render.character_breakdown)


async def _one_character(ctx: Context, show: render.RenderOne) -> Reply:
    name = ctx.text("character")
    if name is None:
        character = await ctx.store.current_character(ctx.user)
        if character is None:
            return await _no_character_caller(ctx, show)
    else:
        character = await ctx.character(name)

    channel = await _chosen_channel(ctx)
    owner_in = await ctx.discord.voice_channel_of(character.owner)
    if channel is None:
        channel = owner_in
    if channel is None:
        return await _gives_only(
            ctx,
            character,
            f"{_players(ctx, character)} in a voice channel, so there's no party.",
        )

    party = await build_party(ctx, channel, substitute=character)
    state = party.players.get(character.owner)
    if state is not None and (until := sitting_out(state, ctx.now)) is not None:
        return await _gives_only(
            ctx,
            character,
            f"{_players_is(ctx, character)} sitting out until {timestamp(until, 't')}, "
            f"so {character.name} isn't counted.",
        )
    recipient = _recipient(party.report, character)
    if recipient is None:
        return await _gives_only(
            ctx,
            character,
            f"{_players(ctx, character)} in {channel_mention(channel.id)}, "
            f"so {character.name} isn't in that party.",
        )
    view = await _view(ctx, party, detail_for=_own(ctx, character))
    notice = _notice(ctx, character, state.current if state is not None else None)
    return _reply(show(view, recipient, notice), party.report, private=True)


async def _no_character_caller(ctx: Context, show: render.RenderOne) -> Reply:
    """A caller with no character set up sees their own totals, if counted (SE-5)."""
    channel = await ctx.discord.voice_channel_of(ctx.user)
    if channel is None:
        raise Refused(no_character_hint())
    party = await build_party(ctx, channel)
    recipient = next((r for r in party.report.recipients if r.user_id == ctx.user), None)
    if recipient is None:
        raise Refused(no_character_hint())
    view = await _view(ctx, party)
    return _reply(show(view, recipient, []), party.report, private=True)


def _players(ctx: Context, character: CharacterRecord) -> str:
    """Who plays the character, with the verb: "You aren't" or "Vex's player isn't"."""
    return "You aren't" if character.owner == ctx.user else f"{character.name}'s player isn't"


def _players_is(ctx: Context, character: CharacterRecord) -> str:
    return "You are" if character.owner == ctx.user else f"{character.name}'s player is"


def _recipient(report: PartyReport, character: CharacterRecord) -> RecipientReport | None:
    for recipient in report.recipients:
        if recipient.character is not None and recipient.character.id == character.id:
            return recipient
    return None


def _notice(ctx: Context, character: CharacterRecord, current: CharacterRecord | None) -> list[str]:
    """OUT-2a: shown when the character isn't its player's current character."""
    if current is not None and current.id == character.id:
        return []
    name = character.name
    if character.owner == ctx.user:
        playing = f"you're playing {current.name}" if current else "you have none set"
        place = f"in {current.name}'s place" if current else "as if playing"
        return [
            f"NOTE: {name} isn't your current character ({playing}).",
            f"These totals show {name} {place}. Use `/play {name}` to switch.",
        ]
    playing = f"{current.name} is" if current else "nobody is"
    place = f"in {current.name}'s place" if current else "as if playing"
    return [
        f"NOTE: {name} isn't currently being played ({playing}).",
        f"These totals show {name} {place}.",
    ]


async def _gives_only(ctx: Context, character: CharacterRecord, why: str) -> Reply:
    """OUT-4: what the character gives, and why there are no totals."""
    report = await solo(ctx, character)
    view = render.Party(
        report=report,
        catalog=ctx.catalog,
        channel=None,
        guilds={character.owner: frozenset(character.guilds)},
        detail_for=_own(ctx, character),
    )
    recipient = report.recipients[0]
    return _reply(render.gives_only(view, recipient, why), report, private=True)


async def _callers_channel(ctx: Context) -> VoiceChannel:
    """The ``channel:`` option, or the caller's voice channel (SE-1)."""
    channel = await _chosen_channel(ctx)
    if channel is not None:
        return channel
    channel = await ctx.discord.voice_channel_of(ctx.user)
    if channel is None:
        raise Refused("You aren't in a voice channel. Join one, or pick one with `channel:`.")
    return channel


async def _chosen_channel(ctx: Context) -> VoiceChannel | None:
    value = ctx.options.get("channel")
    if value is None:
        return None
    if isinstance(value, bool) or not str(value).strip().isdigit():
        raise Refused("`channel:` must be a voice channel.")
    channel = await ctx.discord.voice_channel(ChannelId(int(value)))
    if channel is None:
        raise Refused("`channel:` must be a voice channel.")
    return channel


def _own(ctx: Context, character: CharacterRecord) -> UserId | None:
    """The caller, if looking at their own character: secret guild detail is shown only
    then, and only for that character's secret guilds (SG-5)."""
    return ctx.user if character.owner == ctx.user else None


async def _view(ctx: Context, party: Party, detail_for: UserId | None = None) -> render.Party:
    """Everything the output needs about a party, besides the report."""
    fixes: dict[UserId, str] = {}
    for user_id in party.report.no_character:
        if await ctx.store.characters_of(user_id):
            fixes[user_id] = "no current character: use /play <character>"
        else:
            fixes[user_id] = "no character registered: use /character register"
    counted = {c.name: c for c in party.characters.values()}
    return render.Party(
        report=party.report,
        catalog=ctx.catalog,
        channel=party.channel.id,
        level_updated={name: c.level_updated_at for name, c in counted.items()},
        no_character_fix=fixes,
        guilds={c.owner: frozenset(c.guilds) for c in counted.values()},
        detail_for=detail_for,
    )


def _reply(blocks: list[Block], report: PartyReport, *, private: bool) -> Reply:
    return Reply(to_messages(blocks), private=private, report=report)
