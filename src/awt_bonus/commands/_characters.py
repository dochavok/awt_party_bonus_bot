"""/character register, list, rename and level, and /play (requirements 6.1)."""

from awt_bonus.commands._base import (
    Context,
    Refused,
    clean_name,
    no_character_hint,
    parse_level,
    private,
)
from awt_bonus.commands._types import Reply
from awt_bonus.output.describe import guild_name, timestamp
from awt_bonus.store import CharacterRecord, NameTaken


def _taken(name: str) -> Refused:
    return Refused(
        f"The name {name} is taken: names are unique on the server, ignoring case. "
        f"Pick a variant, e.g. {name} II."
    )


async def register(ctx: Context) -> Reply:
    """CH-1, CH-3, CH-4."""
    name = clean_name(ctx.required("name"))
    raw_level = ctx.options.get("level")
    level = (
        None
        if raw_level is None
        else parse_level(raw_level, ctx.settings.max_level, allow_clear=False)
    )
    if await ctx.store.character_by_name(name) is not None:
        raise _taken(name)
    async with ctx.store.transaction():
        try:
            character_id = await ctx.store.add_character(
                ctx.user, name, level, ctx.now if level is not None else None
            )
        except NameTaken:
            raise _taken(name) from None
        # The first character becomes current, so most players never need /play.
        made_current = await ctx.store.current_character(ctx.user) is None
        if made_current:
            await ctx.store.set_current(ctx.user, character_id)
        await ctx.store.add_audit(
            ctx.user, character_id, "register", None, {"name": name, "level": level}, ctx.now
        )
    level_text = f" (level {level})" if level is not None else ""
    lines = [f"Registered **{name}**{level_text}."]
    if made_current:
        lines.append(f"{name} is your current character.")
    else:
        lines.append(f"Use `/play {name}` to play {name}.")
    lines.append(f"Add what {name} has with `/add {name} <entry>`; `/catalog` lists everything.")
    return private(*lines)


async def list_characters(ctx: Context) -> Reply:
    characters = await ctx.store.characters_of(ctx.user)
    if not characters:
        return private(no_character_hint())
    current = await ctx.store.current_character(ctx.user)
    lines = ["**Your characters**"]
    for character in characters:
        lines.append(_summary(ctx, character, current))
    return private(*lines)


def _summary(ctx: Context, character: CharacterRecord, current: CharacterRecord | None) -> str:
    parts = [f"**{character.name}**"]
    parts.append(f"level {character.level}" if character.level is not None else "no level")
    if current is not None and current.id == character.id:
        parts.append("current")
    line = ", ".join(parts)
    guilds = [guild_name(g, ctx.catalog) for g in character.guilds]
    has = [
        ctx.catalog.entries[e].name if e in ctx.catalog.entries else str(e)
        for e in character.entries
    ]
    if guilds:
        line += f"\n  Guilds: {', '.join(guilds)}"
    if has:
        line += f"\n  Has: {', '.join(has)}"
    return line


async def rename(ctx: Context) -> Reply:
    """CH-2."""
    character = await ctx.own_character()
    new = clean_name(ctx.required("new"))
    other = await ctx.store.character_by_name(new)
    if other is not None and other.id != character.id:
        raise _taken(new)
    async with ctx.store.transaction():
        try:
            await ctx.store.rename_character(character.id, new)
        except NameTaken:
            raise _taken(new) from None
        await ctx.store.add_audit(
            ctx.user, character.id, "rename", {"name": character.name}, {"name": new}, ctx.now
        )
    return private(f"Renamed {character.name} to **{new}**.")


async def level(ctx: Context) -> Reply:
    """CH-4, CH-6."""
    character = await ctx.own_character()
    if ctx.options.get("level") is None:
        raise Refused(f"Give a level from 1 to {ctx.settings.max_level}, or `clear`.")
    new = parse_level(ctx.options["level"], ctx.settings.max_level, allow_clear=True)
    before = {
        "level": character.level,
        "level_updated_at": _iso(character),
    }
    async with ctx.store.transaction():
        await ctx.store.set_level(character.id, new, ctx.now)
        await ctx.store.add_audit(
            ctx.user,
            character.id,
            "level",
            before,
            {"level": new, "level_updated_at": ctx.now.isoformat()},
            ctx.now,
        )
    if new is None:
        return private(f"Cleared {character.name}'s level.")
    return private(f"{character.name} is now level {new} (updated {timestamp(ctx.now, 'd')}).")


def _iso(character: CharacterRecord) -> str | None:
    updated = character.level_updated_at
    return updated.isoformat() if updated is not None else None


async def play(ctx: Context) -> Reply:
    """CH-3, SE-3."""
    character = await ctx.own_character()
    await ctx.store.set_current(ctx.user, character.id)
    return private(f"You're now playing **{character.name}**.")
