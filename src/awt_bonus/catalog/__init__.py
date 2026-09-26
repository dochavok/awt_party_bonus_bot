"""The fixed catalog: stats, skills, guilds, items and titles (requirements 6.2).

The catalog is loaded from YAML with ``yaml.safe_load`` and validated with pydantic.
Its file format is the one used by ``tests/scenarios/engine-scenarios.yaml``:
a mapping of ``stats``, ``entries`` and ``guilds``, where each key is the permanent
ID (CT-2) and ``name`` defaults to the key. ``catalog/README.md`` describes it.
"""

from awt_bonus.catalog._files import check_no_removed, load_catalog, load_catalog_file
from awt_bonus.catalog._model import (
    Ability,
    AudienceKind,
    Catalog,
    CatalogError,
    Entry,
    EntryKind,
    Guild,
    LevelBand,
    Membership,
    Modifier,
    Stat,
    StatKind,
)
from awt_bonus.catalog._parse import parse_catalog

__all__ = [
    "Ability",
    "AudienceKind",
    "Catalog",
    "CatalogError",
    "Entry",
    "EntryKind",
    "Guild",
    "LevelBand",
    "Membership",
    "Modifier",
    "Stat",
    "StatKind",
    "check_no_removed",
    "load_catalog",
    "load_catalog_file",
    "parse_catalog",
]
