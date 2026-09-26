"""Autocomplete suggestions (CH-1, HV-1). Autocomplete isn't a lock: every command
still checks what it's given when it runs (HV-4)."""

from collections.abc import Iterable, Mapping

from awt_bonus.catalog import Catalog, Entry
from awt_bonus.commands._types import Choice, OptionValue
from awt_bonus.ids import UserId
from awt_bonus.output.describe import kind_label
from awt_bonus.store import CharacterRecord, Store

MAX_CHOICES = 25
"""Discord shows at most 25 suggestions."""

OWN_CHARACTER_COMMANDS = frozenset(
    {"play", "character rename", "character level", "add", "remove", "guild join", "guild leave"}
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
        else:
            has = set() if character is None else set(character.entries)
            entries = [e for e in catalog.entries.values() if not e.retired and e.id not in has]
        return _matching(((_label(e, catalog), e.name) for e in entries), typed)
    if option == "entry" and command == "catalog":
        entries = [e for e in catalog.entries.values() if not e.retired]
        pairs = [(_label(e, catalog), e.name) for e in entries]
        pairs += [(f"{g.full_name} (guild)", g.full_name) for g in catalog.guilds.values()]
        return _matching(pairs, typed)
    return []


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


def _label(entry: Entry, catalog: Catalog) -> str:
    """E.g. "Holy Aura (Holy Knight skill)" (HV-1)."""
    return f"{entry.name} ({kind_label(entry, catalog)})"


def _matching(pairs: Iterable[tuple[str, str]], typed: str) -> list[Choice]:
    """Suggestions whose label contains what's typed, those starting with it first."""
    found = [Choice(label, value) for label, value in pairs if typed in label.casefold()]
    found.sort(key=lambda c: not c.label.casefold().startswith(typed))
    return found[:MAX_CHOICES]
