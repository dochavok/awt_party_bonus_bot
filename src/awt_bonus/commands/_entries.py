"""/add and /remove: what characters have (requirements 6.3)."""

from awt_bonus.catalog import Entry
from awt_bonus.commands._base import Context, Refused, private
from awt_bonus.commands._types import Reply
from awt_bonus.ids import EntryId
from awt_bonus.output.describe import entry_lines, kind_label, names
from awt_bonus.store import CharacterRecord


def _names(ctx: Context, character: CharacterRecord) -> list[str]:
    """The character's entry IDs, for the audit log (HV-5)."""
    return [str(e) for e in character.entries]


async def add(ctx: Context) -> Reply:
    """HV-1, HV-4, HV-6, CT-1, CT-6."""
    character = await ctx.own_character()
    wanted = ctx.required("entry")
    entry = ctx.catalog.entry_named(wanted)
    if entry is None:
        raise Refused(
            f"{wanted} isn't in the catalog. `/catalog` lists everything that can be added."
        )
    if entry.id in character.entries:
        raise Refused(f"{character.name} already has {entry.name}.")
    if entry.retired:
        raise Refused(f"{entry.name} is retired, so it can't be added any more.")
    if entry.unique:
        holders = [c for c in await ctx.store.holders_of(entry.id) if c.id != character.id]
        if holders:
            raise Refused(
                f"{entry.name} is held by {names(c.name for c in holders)}. "
                "Only one character can hold it at a time."
            )
    async with ctx.store.transaction():
        await ctx.store.add_entry(character.id, entry.id)
        await ctx.store.add_audit(
            ctx.user,
            character.id,
            "add",
            {"entries": _names(ctx, character)},
            {"entries": [*_names(ctx, character), entry.id]},
            ctx.now,
        )
    lines = [f"Added **{entry.name}** ({kind_label(entry, ctx.catalog)}) to {character.name}."]
    lines += [f"  {line}" for line in entry_lines(entry, ctx.catalog)]
    lines += _notes(ctx, character, entry)
    return private(*lines)


def _notes(ctx: Context, character: CharacterRecord, entry: Entry) -> list[str]:
    """Warnings that don't stop the /add (HV-4), and what replaces what (rule 4.5)."""
    held = [ctx.catalog.entries[e] for e in character.entries if e in ctx.catalog.entries]
    notes = []
    tag = entry.modifier.tag if entry.modifier is not None else None
    if tag is not None and not any(tag in a.tags for e in held for a in e.abilities):
        notes.append(
            f"Note: {entry.name} adds to {tag} bonuses, and {character.name} has no "
            f"{tag}s yet, so it changes nothing until {character.name} has one."
        )
    for other in held:
        if other.id in entry.replaces:
            notes.append(
                f"Note: {entry.name} replaces {other.name}, so {character.name} gives only "
                f"{entry.name}."
            )
        elif entry.id in other.replaces:
            notes.append(
                f"Note: {other.name} replaces {entry.name}, so {character.name} gives only "
                f"{other.name}."
            )
    return notes


async def remove(ctx: Context) -> Reply:
    """HV-1, HV-6."""
    character = await ctx.own_character()
    wanted = ctx.required("entry")
    entry = ctx.catalog.entry_named(wanted)
    entry_id = entry.id if entry is not None else EntryId(wanted)
    if entry_id not in character.entries:
        raise Refused(f"{character.name} doesn't have {wanted}.")
    name = entry.name if entry is not None else wanted
    remaining = [e for e in _names(ctx, character) if e != entry_id]
    async with ctx.store.transaction():
        await ctx.store.remove_entry(character.id, entry_id)
        await ctx.store.add_audit(
            ctx.user,
            character.id,
            "remove",
            {"entries": _names(ctx, character)},
            {"entries": remaining},
            ctx.now,
        )
    lines = [f"Removed **{name}** from {character.name}."]
    if entry is not None and entry.unique:
        lines.append(f"{name} is free for another character to hold.")
    return private(*lines)
