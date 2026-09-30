"""Checking a catalog mapping and building the ``Catalog`` (CT-4, CT-5, CT-7, CT-10).

Every problem is collected, each naming the ID it's about, and reported together.
"""

import re
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ValidationError
from pydantic_core import ErrorDetails

from awt_bonus.catalog._format import BonusFields, EntrySpec, GuildSpec, ItemClassSpec, StatSpec
from awt_bonus.catalog._model import (
    Ability,
    AudienceKind,
    Catalog,
    CatalogError,
    Entry,
    EntryKind,
    Guild,
    ItemClass,
    LevelBand,
    Membership,
    Modifier,
    Stat,
    StatKind,
)
from awt_bonus.ids import EntryId, GuildId, ItemClassId, StatId

SECTIONS = ("stats", "entries", "guilds", "item_classes")


def parse_catalog(data: Mapping[str, Any]) -> Catalog:
    """Validate one catalog mapping (``stats``, ``entries``, ``guilds``, ``item_classes``).

    Raises CatalogError listing every problem.
    """
    if not isinstance(data, Mapping):
        raise CatalogError(
            ["the catalog must be a mapping of `stats`, `entries`, `guilds` and `item_classes`"]
        )
    problems: list[str] = []
    for section in data:
        if section not in SECTIONS:
            problems.append(f"unknown section {section!r}: expected {', '.join(SECTIONS)}")

    stats = _specs(data, "stats", "stat", StatSpec, problems)
    entries = _specs(data, "entries", "entry", EntrySpec, problems)
    guilds = _specs(data, "guilds", "guild", GuildSpec, problems)
    classes = _specs(data, "item_classes", "item class", ItemClassSpec, problems)

    bands = _level_bands(entries, guilds, problems)
    _check_stats(stats, problems)
    _check_references(stats, entries, guilds, problems)
    _check_item_classes(entries, guilds, classes, problems)
    replaces = _replacements(entries, problems)
    _check_unique(entries, guilds, classes, problems)
    if problems:
        raise CatalogError(problems)

    return Catalog(
        stats=[_stat(key, spec) for key, spec in stats.items()],
        entries=[_entry(key, spec, replaces[key], bands) for key, spec in entries.items()],
        guilds=[_guild(key, spec, bands) for key, spec in guilds.items()],
        item_classes=[_item_class(key, spec) for key, spec in classes.items()],
    )


# ---------------------------------------------------------------- format


def _specs[T: BaseModel](
    data: Mapping[str, Any], section: str, what: str, model: type[T], problems: list[str]
) -> dict[str, T]:
    """Each item in one section, validated on its own so every bad one is reported."""
    raw = data.get(section)
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        problems.append(f"`{section}` must be a mapping of IDs")
        return {}
    specs: dict[str, T] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            problems.append(f"{what} ID {key!r} must be text")
            continue
        try:
            specs[key] = model.model_validate(value if value is not None else {})
        except ValidationError as error:
            problems += [f"{what} {key!r}: {_describe(e)}" for e in error.errors()]
    return specs


def _describe(error: ErrorDetails) -> str:
    where = ".".join(str(part) for part in error["loc"])
    message = error["msg"].removeprefix("Value error, ")
    return f"{where}: {message}" if where else message


# ---------------------------------------------------------------- level rules

_WHEN = re.compile(r"^\s*(?:(<=|>=|<|>|=)\s*(\d+)|(\d+)\s*-\s*(\d+))\s*$")

Range = tuple[int | None, int | None]


def _range(when: str) -> Range | None:
    """(lowest, highest) level for a level rule's ``when``, or None if it can't be read."""
    match = _WHEN.match(when)
    if match is None:
        return None
    operator, number, low, high = match.groups()
    if operator is None:
        return int(low), int(high)
    n = int(number)
    ranges: dict[str, Range] = {
        "<": (None, n - 1),
        "<=": (None, n),
        ">": (n + 1, None),
        ">=": (n, None),
        "=": (n, n),
    }
    return ranges[operator]


def _overlap(a: Range, b: Range) -> bool:
    lows = [x for x in (a[0], b[0]) if x is not None]
    highs = [x for x in (a[1], b[1]) if x is not None]
    return not (lows and highs and max(lows) > min(highs))


Bands = dict[int, tuple[LevelBand, ...]]
"""Parsed level rules, keyed by ``id()`` of the bonus fields they belong to."""


def _level_bands(
    entries: Mapping[str, EntrySpec], guilds: Mapping[str, GuildSpec], problems: list[str]
) -> Bands:
    bands: Bands = {}
    for owner, bonus in _bonuses(entries, guilds):
        rules = bonus.level_rules or []
        ranges: list[Range] = []
        for rule in rules:
            found = _range(rule.when)
            if found is None:
                problems.append(f"{owner}: level rule {rule.when!r} isn't a level range")
            elif found[0] is not None and found[1] is not None and found[0] > found[1]:
                problems.append(f"{owner}: level rule {rule.when!r} covers no levels")
            else:
                if any(_overlap(found, other) for other in ranges):
                    problems.append(f"{owner}: level rule {rule.when!r} overlaps another")
                ranges.append(found)
        if rules and len(ranges) == len(rules):
            bands[id(bonus)] = tuple(
                LevelBand(low, high, {StatId(s): n for s, n in rule.gives.items()})
                for (low, high), rule in zip(ranges, rules, strict=True)
            )
    return bands


def _bonuses(
    entries: Mapping[str, EntrySpec], guilds: Mapping[str, GuildSpec]
) -> list[tuple[str, BonusFields]]:
    """Every set of bonus fields, with a description of where it is."""
    found: list[tuple[str, BonusFields]] = []
    for key, entry in entries.items():
        found.append((f"entry {key!r}", entry))
        found += [(f"entry {key!r} ability {a.name!r}", a) for a in entry.abilities or []]
    for key, guild in guilds.items():
        found += [(f"guild {key!r} ability {a.name!r}", a) for a in guild.from_roles]
    return found


# ---------------------------------------------------------------- references


def _check_stats(stats: Mapping[str, StatSpec], problems: list[str]) -> None:
    for key, spec in stats.items():
        if spec.parent is None:
            continue
        parent = stats.get(spec.parent)
        if parent is None:
            problems.append(f"stat {key!r}: parent stat {spec.parent!r} isn't defined")
            continue
        if parent.kind != spec.kind:
            problems.append(f"stat {key!r}: parent {spec.parent!r} is a different kind of stat")
        seen = {key}
        current: str | None = spec.parent
        while current is not None and current in stats:
            if current in seen:
                problems.append(f"stat {key!r}: its parents go round in a circle")
                break
            seen.add(current)
            current = stats[current].parent


def _check_references(
    stats: Mapping[str, StatSpec],
    entries: Mapping[str, EntrySpec],
    guilds: Mapping[str, GuildSpec],
    problems: list[str],
) -> None:
    for owner, bonus in _bonuses(entries, guilds):
        amounts = [bonus.gives or {}] + [rule.gives for rule in bonus.level_rules or []]
        for stat in sorted({s for gives in amounts for s in gives}):
            if stat not in stats:
                problems.append(f"{owner}: gives stat {stat!r}, which isn't defined")

    tags = {t for spec in entries.values() for t in spec.tags}
    tags |= {t for spec in entries.values() for a in spec.abilities or [] for t in a.tags}
    for key, spec in entries.items():
        if spec.guild is not None and spec.guild not in guilds:
            problems.append(f"entry {key!r}: guild {spec.guild!r} isn't defined")
        for target in spec.replaces:
            if target == key:
                problems.append(f"entry {key!r} replaces itself")
            elif target not in entries:
                problems.append(f"entry {key!r}: replaces {target!r}, which isn't defined")
        tag = spec.modifies.tag if spec.modifies is not None else None
        if tag is not None and tag not in tags:
            problems.append(f"entry {key!r}: modifies tag {tag!r}, which no entry has")


def _check_item_classes(
    entries: Mapping[str, EntrySpec],
    guilds: Mapping[str, GuildSpec],
    classes: Mapping[str, ItemClassSpec],
    problems: list[str],
) -> None:
    """Every class an ability depends on exists; a current entry's isn't retired (CT-10)."""
    for owner, bonus in _bonuses(entries, guilds):
        for field in ("needs_item_class", "per_item_class"):
            name = getattr(bonus, field)
            if name is not None and name not in classes:
                problems.append(f"{owner}: {field} {name!r} isn't a defined item class")
    for key, spec in entries.items():
        bonuses = [spec, *(spec.abilities or [])]
        uses = {c for b in bonuses for c in (b.needs_item_class, b.per_item_class) if c}
        for name in sorted(uses):
            if name in classes and classes[name].retired and not spec.retired:
                problems.append(f"entry {key!r}: item class {name!r} is retired; retire it too")


def _replacements(
    entries: Mapping[str, EntrySpec], problems: list[str]
) -> dict[str, frozenset[EntryId]]:
    """Everything each entry replaces, directly or through another (rule 4.5)."""
    closure: dict[str, frozenset[EntryId]] = {}
    for key, spec in entries.items():
        found: set[str] = set()
        todo = [t for t in spec.replaces if t in entries and t != key]
        while todo:
            target = todo.pop()
            if target not in found:
                found.add(target)
                todo += [t for t in entries[target].replaces if t in entries]
        if key in found:
            problems.append(f"entry {key!r}: its replacements go round in a circle")
        closure[key] = frozenset(EntryId(t) for t in found - {key})
    return closure


def _check_unique(
    entries: Mapping[str, EntrySpec],
    guilds: Mapping[str, GuildSpec],
    classes: Mapping[str, ItemClassSpec],
    problems: list[str],
) -> None:
    """IDs are unique across entries and guilds; names, ignoring case, across entries,
    guilds and item classes (their other names included), so /catalog finds one (CT-7)."""
    for key in sorted(set(entries) & set(guilds)):
        problems.append(f"ID {key!r} is used by both an entry and a guild")

    users: dict[str, list[str]] = defaultdict(list)
    shown: dict[str, str] = {}
    names = [(f"entry {key!r}", spec.name or key) for key, spec in entries.items()]
    for key, guild in guilds.items():
        names += [(f"guild {key!r}", name) for name in {guild.short_name or key, guild.full_name}]
    for key, item_class in classes.items():
        own = {n.casefold(): n for n in [item_class.name or key, *item_class.other_names]}
        names += [(f"item class {key!r}", name) for name in own.values()]
    for owner, name in names:
        users[name.casefold()].append(owner)
        shown.setdefault(name.casefold(), name)
    for folded, owners in users.items():
        if len(owners) > 1:
            problems.append(f"name {shown[folded]!r} is used by {' and '.join(owners)}")


# ---------------------------------------------------------------- building


def _stat(key: str, spec: StatSpec) -> Stat:
    parent = StatId(spec.parent) if spec.parent is not None else None
    return Stat(StatId(key), StatKind(spec.kind), parent, spec.unit, spec.description)


def _ability(
    name: str, bonus: BonusFields, tags: frozenset[str], card: str | None, bands: Bands
) -> Ability:
    return Ability(
        name=name,
        gives={StatId(s): n for s, n in (bonus.gives or {}).items()},
        effect=bonus.effect,
        condition=bonus.condition,
        audience=AudienceKind(bonus.audience or "party"),
        includes_giver=bool(bonus.includes_giver),
        stacks=bonus.stacks is not False,
        level_rules=bands.get(id(bonus), ()),
        tags=tags,
        card=card,
        needs_item_class=_class_id(bonus.needs_item_class),
        per_item_class=_class_id(bonus.per_item_class),
    )


def _class_id(name: str | None) -> ItemClassId | None:
    return ItemClassId(name) if name is not None else None


def _entry(key: str, spec: EntrySpec, replaces: frozenset[EntryId], bands: Bands) -> Entry:
    name = spec.name or key
    tags = frozenset(spec.tags)
    if spec.abilities is not None:
        abilities = tuple(
            _ability(a.name, a, tags | frozenset(a.tags), a.card, bands) for a in spec.abilities
        )
    elif spec.gives or spec.level_rules or spec.effect:
        abilities = (_ability(spec.ability or name, spec, tags, spec.card, bands),)
    else:
        abilities = ()
    modifier = None
    if spec.modifies is not None:
        modifier = Modifier(spec.modifies.add, spec.modifies.tag)
    return Entry(
        id=EntryId(key),
        name=name,
        kind=EntryKind(spec.kind),
        tree=spec.tree,
        guild=GuildId(spec.guild) if spec.guild is not None else None,
        abilities=abilities,
        tags=tags,
        modifier=modifier,
        replaces=replaces,
        unique=spec.unique,
        retired=spec.retired,
        card=spec.card,
    )


def _item_class(key: str, spec: ItemClassSpec) -> ItemClass:
    return ItemClass(
        id=ItemClassId(key),
        name=spec.name or key,
        other_names=tuple(spec.other_names),
        description=spec.description,
        retired=spec.retired,
    )


def _guild(key: str, spec: GuildSpec, bands: Bands) -> Guild:
    return Guild(
        id=GuildId(key),
        short_name=spec.short_name or key,
        full_name=spec.full_name,
        membership=Membership(spec.membership),
        roles=tuple(spec.roles),
        role_abilities=tuple(
            _ability(a.name, a, frozenset(a.tags), a.card, bands) for a in spec.from_roles
        ),
        secret=spec.secret,
        how_to_join=spec.how_to_join,
    )
