"""/guild join and /guild leave: guild membership (requirements HV-2, HV-5, HV-6, SG-2).

Joining only records membership; ranks and boons are then added with /add. Leaving
removes the character's ranks and boons from that guild. Every reply is private,
so secret guild membership is never shown to anyone else (SG-2).
"""

from awt_bonus.catalog import EntryKind, Guild, Membership
from awt_bonus.commands._base import Context, Refused, private
from awt_bonus.commands._types import Reply
from awt_bonus.output.describe import names


async def join(ctx: Context) -> Reply:
    """HV-2: records membership and grants nothing."""
    character = await ctx.own_character()
    guild = _guild(ctx)
    if guild.membership is Membership.ROLES:
        raise Refused(roles_membership(guild))
    if guild.id in character.guilds:
        raise Refused(f"{character.name} is already a member of {guild.full_name}.")
    guilds = [str(g) for g in character.guilds]
    async with ctx.store.transaction():
        await ctx.store.join_guild(character.id, guild.id, ctx.now)
        await ctx.store.add_audit(
            ctx.user,
            character.id,
            "guild join",
            {"guilds": guilds},
            {"guilds": [*guilds, str(guild.id)]},
            ctx.now,
        )
    lines = [f"{character.name} joined **{guild.full_name}**. Joining grants nothing by itself."]
    entries = [e for e in ctx.catalog.guild_entries(guild.id) if not e.retired]
    ranks = [e.name for e in entries if e.kind is EntryKind.RANK]
    boons = [e.name for e in entries if e.kind is EntryKind.BOON]
    for word, found in (("rank", ranks), ("boons", boons)):
        if len(found) == 1:
            lines.append(f"Now add your {word}: `/add {character.name} {found[0]}`")
        elif found:
            options = names(found).replace(" and ", " or ") if word == "rank" else names(found)
            lines.append(f"Now add your {word}: `/add {character.name} <{word}>` ({options})")
    return private(*lines)


async def leave(ctx: Context) -> Reply:
    """HV-2: removes the guild's ranks and boons; one-holder ranks pass on (HV-6)."""
    character = await ctx.own_character()
    guild = _guild(ctx)
    if guild.id not in character.guilds:
        raise Refused(f"{character.name} isn't a member of {guild.full_name}.")
    removed = [
        e
        for e in character.entries
        if e in ctx.catalog.entries and ctx.catalog.entries[e].guild == guild.id
    ]
    async with ctx.store.transaction():
        await ctx.store.leave_guild(character.id, guild.id)
        for entry_id in removed:
            await ctx.store.remove_entry(character.id, entry_id)
        await ctx.store.add_audit(
            ctx.user,
            character.id,
            "guild leave",
            {"guilds": [str(g) for g in character.guilds], "entries": list(character.entries)},
            {
                "guilds": [str(g) for g in character.guilds if g != guild.id],
                "entries": [e for e in character.entries if e not in removed],
            },
            ctx.now,
        )
    lines = [f"{character.name} left **{guild.full_name}**."]
    entries = [ctx.catalog.entries[e] for e in removed]
    if entries:
        lines.append(f"Removed from {character.name}: {names(e.name for e in entries)}.")
    lines += [f"{e.name} is free for another character to hold." for e in entries if e.unique]
    return private(*lines)


def _guild(ctx: Context) -> Guild:
    wanted = ctx.required("guild")
    guild = ctx.catalog.guild_named(wanted)
    if guild is None:
        known = names(g.full_name for g in ctx.catalog.guilds.values())
        raise Refused(f"There's no guild called {wanted}. The guilds are {known}.")
    return guild


def roles_membership(guild: Guild) -> str:
    """Why a guild can't be joined with /guild join (HV-3), and how to join it (CT-5)."""
    why = (
        f"There's nothing to join for {guild.full_name}: its bonuses come with the "
        f"Discord roles {guild.roles[0]} and above."
    )
    return f"{why} {guild.how_to_join}" if guild.how_to_join else why
