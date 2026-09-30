"""/character register, list, rename, level and items, and /play (requirements 6.1, 6.8)."""

from awt_bonus.catalog import Catalog, ItemClass
from awt_bonus.commands._base import (
    Context,
    Refused,
    clean_name,
    no_character_hint,
    parse_level,
    private,
)
from awt_bonus.commands._types import Reply
from awt_bonus.ids import ItemClassId
from awt_bonus.output.describe import guild_name, item_counts, plural, timestamp
from awt_bonus.store import CharacterRecord, NameTaken

MAX_ITEM_COUNT = 30
"""The most items of one class a character can have in use (IC-2)."""


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
    counts = item_counts(character.item_counts, ctx.catalog)
    if counts:
        line += f"\n  Item classes: {counts}"
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


async def items(ctx: Context) -> Reply:
    """IC-2: how many items of a class the character has in use."""
    character = await ctx.own_character()
    item_class = _item_class(ctx.catalog, ctx.required("class"))
    count = _count(ctx.options.get("count"))
    if item_class.retired and count > 0:
        raise Refused(f"The {item_class.name} class is retired: its counts can only be cleared.")
    before = dict(character.item_counts)
    after = {c: n for c, n in before.items() if c != item_class.id}
    if count:
        after[item_class.id] = count
    if after != before:
        async with ctx.store.transaction():
            await ctx.store.set_item_count(character.id, item_class.id, count)
            await ctx.store.add_audit(
                ctx.user,
                character.id,
                "items",
                {"item_counts": before},
                {"item_counts": after},
                ctx.now,
            )
    others = item_counts({c: n for c, n in after.items() if c != item_class.id}, ctx.catalog)
    now_has = plural(count, f"{item_class.name} item") if count else f"no {item_class.name} items"
    return private(
        f"{character.name} now has {now_has} in use.",
        f"Other counts: {others}." if others else "No other item classes in use.",
        "Change it whenever you stop or start using one.",
    )


def _item_class(catalog: Catalog, name: str) -> ItemClass:
    """The class with this display name, other name or ID, ignoring case (CT-10)."""
    found = catalog.item_class_named(name) or catalog.item_classes.get(ItemClassId(name))
    if found is None:
        classes = ", ".join(
            c.name + (f" (also {', '.join(c.other_names)})" if c.other_names else "")
            for c in catalog.item_classes.values()
            if not c.retired
        )
        raise Refused(f"There's no item class called {name}. The classes are: {classes}.")
    return found


def _count(value: object) -> int:
    """A count from 0 to 30 (IC-2)."""
    allowed = f"Give a count from 0 to {MAX_ITEM_COUNT}; 0 clears it."
    if isinstance(value, bool) or value is None:
        raise Refused(allowed)
    try:
        count = int(str(value).strip())
    except ValueError:
        raise Refused(allowed) from None
    if not 0 <= count <= MAX_ITEM_COUNT:
        raise Refused(allowed)
    return count


def _iso(character: CharacterRecord) -> str | None:
    updated = character.level_updated_at
    return updated.isoformat() if updated is not None else None


async def play(ctx: Context) -> Reply:
    """CH-3, SE-3."""
    character = await ctx.own_character()
    await ctx.store.set_current(ctx.user, character.id)
    return private(f"You're now playing **{character.name}**.")
