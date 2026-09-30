"""The loaded catalog (requirements 6.2): stats, entries and guilds, resolved and checked."""

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from awt_bonus.ids import EntryId, GuildId, ItemClassId, StatId


class CatalogError(Exception):
    """The catalog is invalid. ``problems`` lists every problem found (CT-7)."""

    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems: list[str] = list(problems)


class StatKind(StrEnum):
    ROLL = "roll"
    """CM, CR and the CR subtypes."""
    COMBAT_NOTE = "combat_note"
    """Damage, damage reduction and healing, in hearts."""


class EntryKind(StrEnum):
    SKILL = "skill"
    BOON = "boon"
    RANK = "rank"
    ITEM = "item"
    TITLE = "title"


class AudienceKind(StrEnum):
    """Who can receive an ability (rule 4.8)."""

    PARTY = "party"
    GUILD = "guild"
    """Members of the entry's guild."""
    HOLDERS = "holders"
    """Other holders of the same entry."""


class Membership(StrEnum):
    OPEN = "open"
    """Players join with ``/guild join``."""
    ROLES = "roles"
    """Membership comes from Discord roles (HV-3)."""


@dataclass(frozen=True)
class Stat:
    id: StatId
    kind: StatKind
    parent: StatId | None
    """For CR subtypes: the parent stat, whose total flows into this one (rule 4.7)."""
    unit: str | None
    description: str | None


@dataclass(frozen=True)
class LevelBand:
    """What an ability gives recipients within a range of levels (rule 4.10)."""

    min_level: int | None
    """Lowest level, inclusive; None for no lower bound."""
    max_level: int | None
    """Highest level, inclusive; None for no upper bound."""
    gives: Mapping[StatId, int]

    def covers(self, level: int) -> bool:
        return (self.min_level is None or level >= self.min_level) and (
            self.max_level is None or level <= self.max_level
        )


@dataclass(frozen=True)
class Ability:
    """One bonus an entry gives (CT-4, CT-5). A plain entry has one, named after it."""

    name: str
    """The bonus's display name, e.g. "Rat Pack"."""
    gives: Mapping[StatId, int]
    effect: str | None
    condition: str | None
    """Set for conditional bonuses, which are never added to totals (rule 4.12)."""
    audience: AudienceKind
    includes_giver: bool
    stacks: bool
    level_rules: tuple[LevelBand, ...]
    tags: frozenset[str]
    """The entry's tags and the ability's own, e.g. ``aura``."""
    card: str | None

    @property
    def has_numbers(self) -> bool:
        return bool(self.gives or self.level_rules)


@dataclass(frozen=True)
class Modifier:
    """Adds to the numbers of the same character's other gives (rule 4.6)."""

    add: int
    tag: str | None
    """Only abilities with this tag; None for every ability."""

    def applies_to(self, ability: Ability) -> bool:
        return self.tag is None or self.tag in ability.tags


@dataclass(frozen=True)
class Entry:
    """A skill, boon, rank, item or title a character can have (CT-4)."""

    id: EntryId
    name: str
    kind: EntryKind
    tree: str | None
    guild: GuildId | None
    abilities: tuple[Ability, ...]
    """What it gives; empty for modifiers and titles with no party bonus."""
    tags: frozenset[str]
    modifier: Modifier | None
    replaces: frozenset[EntryId]
    """Every entry this one replaces, directly or through another (rule 4.5)."""
    unique: bool
    """Only one character may hold it at a time (HV-6)."""
    retired: bool
    """Can't be added any more; characters who have it keep it (CT-6)."""
    card: str | None
    """Card text quoted from the source."""


@dataclass(frozen=True)
class Guild:
    """A guild, order, cult or coalition (CT-5)."""

    id: GuildId
    short_name: str
    full_name: str
    membership: Membership
    roles: tuple[str, ...]
    """For ``Membership.ROLES``: the Discord roles that make a player a member."""
    role_abilities: tuple[Ability, ...]
    """Bonuses a player gives once for having any of ``roles``, e.g. Support (HV-3)."""
    secret: bool
    """Members are never revealed (SG-1)."""
    how_to_join: str | None = None
    """What to tell players about joining, e.g. a Patreon link, instead of /guild join (CT-5)."""


@dataclass(frozen=True)
class ItemClass:
    """A family of items with a common theme, e.g. passion items (CT-10)."""

    id: ItemClassId
    name: str
    other_names: tuple[str, ...]
    """Other names players use, e.g. "Will Passion" for passion."""
    description: str
    retired: bool = False


class Catalog:
    """A loaded, validated catalog. ``Catalog()`` is an empty one.

    Build one with ``parse_catalog``, ``load_catalog_file`` or ``load_catalog``,
    which check it first; this constructor doesn't.
    """

    def __init__(
        self,
        stats: Iterable[Stat] = (),
        entries: Iterable[Entry] = (),
        guilds: Iterable[Guild] = (),
        item_classes: Iterable[ItemClass] = (),
    ) -> None:
        self.stats: Mapping[StatId, Stat] = {s.id: s for s in stats}
        """In file order."""
        self.entries: Mapping[EntryId, Entry] = {e.id: e for e in entries}
        self.guilds: Mapping[GuildId, Guild] = {g.id: g for g in guilds}
        self.item_classes: Mapping[ItemClassId, ItemClass] = {c.id: c for c in item_classes}
        """Item classes (CT-10). Not loaded from files yet: item classes are M8."""
        self._entry_names = {e.name.casefold(): e for e in self.entries.values()}
        self._guild_names = {
            name.casefold(): g for g in self.guilds.values() for name in (g.short_name, g.full_name)
        }
        self.stat_order: tuple[StatId, ...] = _parents_first(self.stats)
        """Every stat, each after its parent: the order to add up totals in (rule 4.7)."""

    def entry_named(self, name: str) -> Entry | None:
        """The entry with this display name, ignoring case."""
        return self._entry_names.get(name.casefold())

    def guild_named(self, name: str) -> Guild | None:
        """The guild with this short or full name, ignoring case."""
        return self._guild_names.get(name.casefold())

    def guild_entries(self, guild: GuildId) -> tuple[Entry, ...]:
        """The guild's rank and boon entries."""
        return tuple(e for e in self.entries.values() if e.guild == guild)

    def role_guilds(self, roles: Collection[str]) -> tuple[Guild, ...]:
        """The guilds these Discord roles make a player a member of (HV-3)."""
        return tuple(
            g
            for g in self.guilds.values()
            if g.membership is Membership.ROLES and any(r in roles for r in g.roles)
        )


def _parents_first(stats: Mapping[StatId, Stat]) -> tuple[StatId, ...]:
    order: list[StatId] = []
    visited: set[StatId] = set()

    def visit(stat: StatId) -> None:
        if stat in visited:
            return
        visited.add(stat)
        parent = stats[stat].parent
        if parent is not None and parent in stats:
            visit(parent)
        order.append(stat)

    for stat in stats:
        visit(stat)
    return tuple(order)
