"""/catalog: what the catalog holds, from the players' side (CT-8).

It never shows which characters have an entry; /breakdown does that. Guild ranks
and boons are shown only for guilds the player's current character belongs to;
other guilds are listed by name, with the command to join.
"""

from collections import defaultdict

from awt_bonus.catalog import Ability, Entry, EntryKind, Guild, Membership
from awt_bonus.commands._base import Context, Refused, private
from awt_bonus.commands._types import Reply
from awt_bonus.ids import GuildId
from awt_bonus.output.describe import ability, entry_lines, guild_name, kind_label
from awt_bonus.output.messages import Block, text

KIND_HEADINGS = {EntryKind.ITEM: "Items", EntryKind.TITLE: "Titles"}


async def catalog(ctx: Context) -> Reply:
    wanted = ctx.text("entry")
    current = await ctx.store.current_character(ctx.user)
    who = current.name if current is not None else "<character>"
    joined = frozenset(current.guilds) if current is not None else frozenset()
    if wanted is None:
        return private(*_everything(ctx, who, joined))
    entry = ctx.catalog.entry_named(wanted)
    if entry is not None and entry.guild is not None and entry.guild not in joined:
        return private(_not_joined(ctx, entry, who))
    if entry is not None:
        return private(_entry(ctx, entry, who))
    guild = ctx.catalog.guild_named(wanted)
    if guild is not None:
        return private(_guild(ctx, guild, who, joined))
    raise Refused(f"There's no entry or guild called {wanted}. `/catalog` lists everything.")


def _entry(ctx: Context, entry: Entry, who: str) -> Block:
    block = text(f"**{entry.name}** ({kind_label(entry, ctx.catalog)})")
    block.add(*(f"- {line}" for line in entry_lines(entry, ctx.catalog)))
    if entry.replaces:
        replaced = [ctx.catalog.entries[e].name for e in entry.replaces if e in ctx.catalog.entries]
        block.add(f"- Replaces {', '.join(replaced)}: a character with both gives only this.")
    if entry.unique:
        block.add("- Only one character can hold it at a time.")
    for label, card in _cards(entry):
        lines = [line for line in card.splitlines() if line.strip()]
        block.add(*(f"> {label}{line}" if i == 0 else f"> {line}" for i, line in enumerate(lines)))
    if entry.retired:
        block.add("Retired: it can't be added any more.")
    else:
        block.add(f"Add it with `/add {who} {entry.name}`")
    return block


def _not_joined(ctx: Context, entry: Entry, who: str) -> Block:
    """A guild entry, for a character outside the guild: only how to join (CT-8)."""
    guild = guild_name(entry.guild, ctx.catalog)
    return text(
        f"**{entry.name}** is a {guild} {entry.kind.value}. It's shown once {who} is a member.",
        f"Join with `/guild join {who} {guild}`",
    )


def _cards(entry: Entry) -> list[tuple[str, str]]:
    """The card text quoted from the source (CT-4): the entry's, then each ability's own."""
    cards = [("", entry.card)] if entry.card else []
    for bonus in entry.abilities:
        if bonus.card and bonus.card != entry.card:
            label = f"{bonus.name}: " if len(entry.abilities) > 1 else ""
            cards.append((label, bonus.card))
    return cards


def _guild(ctx: Context, guild: Guild, who: str, joined: frozenset[GuildId]) -> Block:
    block = text(f"**{guild.full_name}** ({guild.short_name})")
    if guild.membership is Membership.ROLES:
        for bonus in guild.role_abilities:
            block.add(f"- {bonus.name}: {_role_bonus(ctx, guild, bonus)}")
        block.add(_how_to_join(guild))
    elif guild.id in joined:
        block.add(f"{who} is a member.")
        for entry in ctx.catalog.guild_entries(guild.id):
            if not entry.retired:
                block.add(_line(ctx, entry))
    else:
        block.add(
            f"Join with `/guild join {who} {guild.full_name}`. "
            f"Its ranks and boons are shown once {who} is a member."
        )
    return block


def _how_to_join(guild: Guild) -> str:
    """For a guild whose membership comes from roles (HV-3, CT-5)."""
    return guild.how_to_join or f"Membership comes from Discord roles: {', '.join(guild.roles)}."


def _role_bonus(ctx: Context, guild: Guild, bonus: Ability) -> str:
    """A bonus from Discord roles, e.g. Support (HV-3)."""
    described = ability(bonus, ctx.catalog, guild=guild.id)
    return f"{described}, given once by each player with any of {guild.full_name}'s ranks"


def _everything(ctx: Context, who: str, joined: frozenset[GuildId]) -> list[Block]:
    """Everything that can be added, grouped by kind and tree or guild (CT-8)."""
    skills: dict[str, list[Entry]] = defaultdict(list)
    others: dict[EntryKind, list[Entry]] = defaultdict(list)
    for entry in ctx.catalog.entries.values():
        if entry.retired or entry.guild is not None:
            continue
        if entry.kind is EntryKind.SKILL:
            skills[entry.tree or "Other"].append(entry)
        else:
            others[entry.kind].append(entry)
    blocks = [text("**The catalog**: `/catalog <entry or guild>` shows one, with its card text.")]
    for tree, entries in skills.items():
        blocks.append(_group(ctx, f"{tree} skills", entries))
    for guild in ctx.catalog.guilds.values():
        entries = [e for e in ctx.catalog.guild_entries(guild.id) if not e.retired]
        block = text("", f"__{guild.full_name}__")
        if guild.membership is Membership.ROLES:
            for bonus in guild.role_abilities:
                block.add(f"- {bonus.name}: {_role_bonus(ctx, guild, bonus)}")
            block.add(f"  {_how_to_join(guild)}")
        elif guild.id in joined:
            block.add(*(_line(ctx, e) for e in entries))
        else:
            block.add(f"  Join with `/guild join {who} {guild.full_name}`")
        blocks.append(block)
    for kind, heading in KIND_HEADINGS.items():
        if others[kind]:
            blocks.append(_group(ctx, heading, others[kind]))
    return blocks


def _group(ctx: Context, heading: str, entries: list[Entry]) -> Block:
    return text("", f"__{heading}__", *(_line(ctx, e) for e in entries))


def _line(ctx: Context, entry: Entry) -> str:
    return f"- **{entry.name}**: {'; '.join(entry_lines(entry, ctx.catalog))}"
