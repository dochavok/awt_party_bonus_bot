"""Reading tests/scenarios/engine-scenarios.yaml and turning it into engine inputs (TS-1).

The scenario file's conventions (from its header):
  - players are keyed by character name, or Discord name if they have no character;
  - totals list only non-zero stats: a stat not listed is 0, except a CR subtype
    not listed, which equals CR;
  - `not_applied`, `effects`, `conditional`, `not_counted` and `no_character`
    are optional.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from awt_bonus.catalog import Catalog, parse_catalog
from awt_bonus.engine import CharacterRef, PartyReport, PresentPlayer, compute
from awt_bonus.ids import CharacterId, EntryId, GuildId, StatId, UserId

SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios" / "engine-scenarios.yaml"

NOW = datetime(2026, 9, 25, 20, 0, tzinfo=UTC)
"""The time scenario sit-outs are measured from; `sitout: true` means active until NOW + 12 h."""


@cache
def scenario_file() -> Mapping[str, Any]:
    with SCENARIOS.open(encoding="utf-8") as f:
        data: Mapping[str, Any] = yaml.safe_load(f)
    return data


def catalog_data() -> Mapping[str, Any]:
    """The scenario file's own test catalog, as plain data."""
    catalog: Mapping[str, Any] = scenario_file()["catalog"]
    return catalog


def scenarios() -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = scenario_file()["scenarios"]
    return found


def scenario_catalog() -> Catalog:
    return parse_catalog(catalog_data())


def stat_parents() -> dict[StatId, StatId | None]:
    """Each stat in the scenario catalog, with its parent stat (for CR subtypes)."""
    stats: Mapping[str, Mapping[str, Any]] = catalog_data()["stats"]
    return {StatId(name): _parent(spec) for name, spec in stats.items()}


def _parent(spec: Mapping[str, Any]) -> StatId | None:
    parent = spec.get("parent")
    return None if parent is None else StatId(parent)


@dataclass(frozen=True)
class PlayerSpec:
    """One scenario player, as data (also used by the property tests)."""

    name: str
    has: tuple[str, ...] = ()
    guilds: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    level: int | None = None
    sitout: bool = False
    bot: bool = False
    no_character: bool = False

    @classmethod
    def from_yaml(cls, data: Mapping[str, Any]) -> "PlayerSpec":
        return cls(
            name=data["name"],
            has=tuple(data.get("has", ())),
            guilds=tuple(data.get("guilds", ())),
            roles=tuple(data.get("roles", ())),
            level=data.get("level"),
            sitout=bool(data.get("sitout", False)),
            bot=bool(data.get("bot", False)),
            no_character=bool(data.get("no_character", False)),
        )


@dataclass(frozen=True)
class EngineInputs:
    present_players: list[PresentPlayer]
    player_roles: dict[UserId, frozenset[str]]
    character_entries: dict[CharacterId, list[EntryId]]
    character_guilds: dict[CharacterId, list[GuildId]]
    names: dict[UserId, str]
    """User ID -> the scenario's name for that player."""


def build_inputs(players: Sequence[PlayerSpec]) -> EngineInputs:
    """Turn scenario players into ``compute`` arguments.

    User IDs are 1, 2, 3... in list order; a player's character has the same number.
    """
    present: list[PresentPlayer] = []
    roles: dict[UserId, frozenset[str]] = {}
    entries: dict[CharacterId, list[EntryId]] = {}
    guilds: dict[CharacterId, list[GuildId]] = {}
    names: dict[UserId, str] = {}
    for number, player in enumerate(players, start=1):
        user_id = UserId(number)
        names[user_id] = player.name
        roles[user_id] = frozenset(player.roles)
        character: CharacterRef | None = None
        if not (player.no_character or player.bot):
            character_id = CharacterId(number)
            character = CharacterRef(id=character_id, name=player.name, level=player.level)
            entries[character_id] = [EntryId(e) for e in player.has]
            guilds[character_id] = [GuildId(g) for g in player.guilds]
        present.append(
            PresentPlayer(
                user_id=user_id,
                display_name=player.name,
                is_bot=player.bot,
                sitting_out_until=NOW + timedelta(hours=12) if player.sitout else None,
                character=character,
            )
        )
    return EngineInputs(present, roles, entries, guilds, names)


def run(players: Sequence[PlayerSpec], catalog: Catalog) -> tuple[PartyReport, EngineInputs]:
    inputs = build_inputs(players)
    report = compute(
        inputs.present_players,
        inputs.player_roles,
        inputs.character_entries,
        inputs.character_guilds,
        catalog,
    )
    return report, inputs


def expected_totals(expect: Mapping[str, int]) -> dict[StatId, int]:
    """Every stat's expected total, filling in the file's defaults (0, or CR for a subtype)."""
    totals: dict[StatId, int] = {}
    parents = stat_parents()
    for stat, parent in parents.items():
        if stat in expect:
            totals[stat] = expect[stat]
        elif parent is not None:
            totals[stat] = expect.get(parent, 0)
        else:
            totals[stat] = 0
    unknown = set(expect) - set(parents)
    assert not unknown, f"scenario expects unknown stats {unknown}"
    return totals


def actual_totals(report: PartyReport, name: str) -> dict[StatId, int]:
    recipient = report.recipient(name)
    return {stat: recipient.totals.get(stat, 0) for stat in stat_parents()}
