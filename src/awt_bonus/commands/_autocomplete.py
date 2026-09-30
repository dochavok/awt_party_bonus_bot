"""Autocomplete suggestions (CH-1, HV-1). Autocomplete isn't a lock: every command
still checks what it's given when it runs (HV-4)."""

from collections.abc import Iterable, Mapping

from awt_bonus.catalog import Catalog, Entry, ItemClass, Membership
from awt_bonus.commands._types import Choice, OptionValue
from awt_bonus.ids import UserId
from awt_bonus.output.describe import kind_label
from awt_bonus.store import CharacterRecord, Store

MAX_CHOICES = 25
"""Discord shows at most 25 suggestions."""

OWN_CHARACTER_COMMANDS = frozenset(
    {
        "play",
        "character rename",
        "character level",
        "character items",
        "add",
        "remove",
        "guild join",
        "guild leave",
    }
)
"""Commands that act on the caller's own characters (NF-4)."""

ANY_CHARACTER_COMMANDS = frozenset({"mybonus", "breakdown"})
"""Commands that can look up anyone's character (OUT-6)."""


async def suggest(
    store: Store,
    catalog: Catalog,
    user: UserId,
    command: str,
    option: str,
    typed: str,
    options: Mapping[str, OptionValue],
) -> list[Choice]:
    typed = typed.strip().casefold()
    if option == "character":
        if command in OWN_CHARACTER_COMMANDS:
            characters = await store.characters_of(user)
        elif command in ANY_CHARACTER_COMMANDS:
            characters = await store.all_characters()
        else:
            return []
        return _matching(((c.name, c.name) for c in characters), typed)
    if option == "entry" and command in {"add", "remove"}:
        character = await _character(store, user, options)
        if command == "remove":
            held = [] if character is None else list(character.entries)
            entries = [catalog.entries[e] for e in held if e in catalog.entries]
            return _matching(((_label(e, catalog), e.name) for e in entries), typed)
        # Entries the character already has are offered too, marked, after the rest.
        has = set() if character is None else set(character.entries)
        entries = [e for e in _available(catalog, character) if not e.retired]
        entries.sort(key=lambda e: e.id in has)
        return _matching(
            (
                (
                    _label(e, catalog, has=character.name if character and e.id in has else ""),
                    e.name,
                )
                for e in entries
            ),
            typed,
        )
    if option == "entry" and command == "catalog":
        current = await store.current_character(user)
        entries = [e for e in _available(catalog, current) if not e.retired]
        pairs = [(_label(e, catalog), e.name) for e in entries]
        pairs += [(f"{g.full_name} (guild)", g.full_name) for g in catalog.guilds.values()]
        pairs += [
            (_class_label(c, "item class"), c.name)
            for c in catalog.item_classes.values()
            if not c.retired
        ]
        return _matching(pairs, typed)
    if option == "class" and command == "character items":
        character = await _character(store, user, options)
        counts = {} if character is None else character.item_counts
        return _matching(
            (
                (
                    _class_label(
                        c,
                        f"{character.name} has {counts[c.id]}"
                        if character and c.id in counts
                        else "",
                    ),
                    c.name,
                )
                for c in catalog.item_classes.values()
                if not c.retired
            ),
            typed,
        )
    if option == "guild" and command in {"guild join", "guild leave"}:
        character = await _character(store, user, options)
        joined = set() if character is None else set(character.guilds)
        guilds = [
            g
            for g in catalog.guilds.values()
            if g.membership is Membership.OPEN and (g.id in joined) == (command == "guild leave")
        ]
        return _matching(((g.full_name, g.full_name) for g in guilds), typed)
    return []


def _available(catalog: Catalog, character: CharacterRecord | None) -> list[Entry]:
    """Entries the character can use: guild entries only for its guilds (HV-1, CT-8)."""
    guilds = set() if character is None else set(character.guilds)
    return [e for e in catalog.entries.values() if e.guild is None or e.guild in guilds]


async def _character(
    store: Store, user: UserId, options: Mapping[str, OptionValue]
) -> CharacterRecord | None:
    """The character named so far, or the player's current one (HV-1)."""
    name = options.get("character")
    if isinstance(name, str) and name.strip():
        record = await store.character_by_name(name.strip())
        if record is not None and record.owner == user:
            return record
        return None
    return await store.current_character(user)


def _class_label(item_class: ItemClass, note: str) -> str:
    """E.g. "glizzy (also hotdog; Crateris has 1)": other names are matched too (IC-2)."""
    parts = [f"also {', '.join(item_class.other_names)}"] if item_class.other_names else []
    parts += [note] if note else []
    return f"{item_class.name} ({'; '.join(parts)})" if parts else item_class.name


def _label(entry: Entry, catalog: Catalog, has: str = "") -> str:
    """E.g. "Holy Aura (Holy Knight skill)", or "(Holy Knight skill; Crateris has it)" (HV-1)."""
    held = f"; {has} has it" if has else ""
    return f"{entry.name} ({kind_label(entry, catalog)}{held})"


def _matching(pairs: Iterable[tuple[str, str]], typed: str) -> list[Choice]:
    """Suggestions whose label contains what's typed, those starting with it first."""
    found = [Choice(label, value) for label, value in pairs if typed in label.casefold()]
    found.sort(key=lambda c: not c.label.casefold().startswith(typed))
    return found[:MAX_CHOICES]
