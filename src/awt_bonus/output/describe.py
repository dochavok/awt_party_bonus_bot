"""Words for stats, amounts and bonuses, shared by every command's output.

Output never uses pronouns for characters (OUT-7): it names them, or says "the giver".
"""

from collections.abc import Iterable, Mapping
from datetime import datetime

from awt_bonus.catalog import Ability, AudienceKind, Catalog, Entry, EntryKind, LevelBand, StatKind
from awt_bonus.ids import ChannelId, GuildId, StatId


def timestamp(moment: datetime, style: str) -> str:
    """A Discord timestamp, shown in each reader's own time zone (NF-10).

    Styles: ``t`` short time, ``d`` short date, ``f`` date and time, ``R`` relative.
    """
    return f"<t:{int(moment.timestamp())}:{style}>"


def channel_mention(channel_id: ChannelId) -> str:
    """A voice channel, as Discord shows it: by name (OUT-1)."""
    return f"<#{channel_id}>"


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def has_subtypes(stat: StatId, catalog: Catalog) -> bool:
    return any(s.parent == stat for s in catalog.stats.values())


def amount(stat: StatId, n: int, catalog: Catalog) -> str:
    """One amount, e.g. "+2 CR vs fear", "+5 all CR" or "+1 heart damage"."""
    info = catalog.stats.get(stat)
    if info is not None and info.kind is StatKind.COMBAT_NOTE:
        unit = info.unit or ""
        if unit.endswith("s") and n == 1:
            unit = unit[:-1]
        return f"{n:+d} {unit} {stat.lower()}".replace("  ", " ")
    label = f"all {stat}" if has_subtypes(stat, catalog) else stat
    return f"{n:+d} {label}"


def amounts(values: Mapping[StatId, int], catalog: Catalog) -> str:
    """Several amounts, e.g. "+5 all CR, +5 CM"."""
    return ", ".join(amount(stat, n, catalog) for stat, n in values.items())


def total(stat: StatId, n: int, catalog: Catalog) -> str:
    """A total as shown next to its stat, e.g. "+12", or "+1 heart" for a combat note."""
    info = catalog.stats.get(stat)
    if info is not None and info.kind is StatKind.COMBAT_NOTE and info.unit:
        unit = info.unit[:-1] if info.unit.endswith("s") and n == 1 else info.unit
        return f"{n:+d} {unit}"
    return f"{n:+d}"


def band(level_band: LevelBand) -> str:
    """A level band, e.g. "level under 10", "level 10 or higher", "level 5 to 9"."""
    low, high = level_band.min_level, level_band.max_level
    if low is None and high is None:
        return "any level"
    if low is None:
        assert high is not None
        return f"level under {high + 1}"
    if high is None:
        return f"level {low} or higher"
    if low == high:
        return f"level {low}"
    return f"level {low} to {high}"


def guild_name(guild: GuildId | None, catalog: Catalog) -> str:
    found = catalog.guilds.get(guild) if guild is not None else None
    return found.full_name if found is not None else str(guild)


def kind_label(entry: Entry, catalog: Catalog) -> str:
    """What an entry is, e.g. "Holy Knight skill", "Cult rank", "GoTH boon", "item"."""
    if entry.kind is EntryKind.SKILL:
        return f"{entry.tree} skill" if entry.tree else "skill"
    if entry.kind in (EntryKind.RANK, EntryKind.BOON):
        guild = catalog.guilds.get(entry.guild) if entry.guild is not None else None
        short = guild.short_name if guild is not None else entry.guild
        return f"{short} {entry.kind.value}"
    return entry.kind.value


def audience(
    kind: AudienceKind,
    includes_giver: bool,
    guild: GuildId | None,
    holders_of: str,
    catalog: Catalog,
) -> str:
    """Who receives a bonus, e.g. "to allies", "to all Guild of Thieves members"."""
    if kind is AudienceKind.GUILD:
        name = guild_name(guild, catalog)
        return f"to all {name} members" if includes_giver else f"to other {name} members"
    if kind is AudienceKind.HOLDERS:
        return (
            f"to all holders of {holders_of}"
            if includes_giver
            else f"to other {holders_of} holders"
        )
    return "to the giver and allies" if includes_giver else "to allies"


def ability(
    bonus: Ability, catalog: Catalog, *, guild: GuildId | None = None, entry_name: str = ""
) -> str:
    """What one bonus gives, e.g. "+2 CR vs fear to allies" (CT-8).

    ``guild`` and ``entry_name`` say who a guild or holders audience means.
    """
    who = audience(bonus.audience, bonus.includes_giver, guild, entry_name, catalog)
    parts: list[str] = []
    if bonus.level_rules:
        rules = "; ".join(f"{band(b)}: {amounts(b.gives, catalog)}" for b in bonus.level_rules)
        parts.append(f"{who}, by the recipient's level: {rules}")
    elif bonus.gives:
        parts.append(f"{amounts(bonus.gives, catalog)} {who}")
    if bonus.effect is not None:
        parts.append(f"effect {who}: {bonus.effect}")
    text = "; ".join(parts) if parts else "nothing to others"
    if bonus.condition is not None:
        text += f", only for {bonus.condition} (conditional: never in totals)"
    if not bonus.stacks:
        text += ", doesn't stack"
    return text


def modifier(entry: Entry) -> str | None:
    """What a modifier does, e.g. "+1 to each of the holder's aura bonuses" (rule 4.6)."""
    if entry.modifier is None:
        return None
    add = f"{entry.modifier.add:+d}"
    if entry.modifier.tag is None:
        return f"{add} to each number of every bonus the holder gives"
    return f"{add} to each number of the holder's {entry.modifier.tag} bonuses"


def entry_lines(entry: Entry, catalog: Catalog) -> list[str]:
    """What an entry gives, one line per bonus, e.g. "Rat Pack: +1 CM ... members"."""
    lines = []
    for bonus in entry.abilities:
        described = ability(bonus, catalog, guild=entry.guild, entry_name=entry.name)
        lines.append(described if bonus.name == entry.name else f"{bonus.name}: {described}")
    if (mod := modifier(entry)) is not None:
        lines.append(mod)
    if not lines:
        lines.append("no party bonus")
    return lines


def names(values: Iterable[str]) -> str:
    """ "A", "A and B", "A, B and C"."""
    items = list(values)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]
