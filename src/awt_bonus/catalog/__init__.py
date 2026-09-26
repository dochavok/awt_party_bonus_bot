"""The fixed catalog: stats, skills, guilds, items and titles (requirements 6.2).

The catalog is loaded from YAML with ``yaml.safe_load`` and validated with pydantic.
Its file format is the one used by ``tests/scenarios/engine-scenarios.yaml``:
a mapping of ``stats``, ``entries`` and ``guilds``, where each key is the permanent
ID (CT-2) and ``name`` defaults to the key.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class CatalogError(Exception):
    """The catalog is invalid. ``problems`` lists every problem found (CT-7)."""

    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems: list[str] = list(problems)


class Catalog:
    """A loaded, validated catalog. Its structure is defined in M2."""


def parse_catalog(data: Mapping[str, Any]) -> Catalog:
    """Validate one catalog mapping (``stats``, ``entries``, ``guilds``).

    Raises CatalogError listing every problem.
    """
    raise NotImplementedError


def load_catalog_file(path: Path) -> Catalog:
    """Load a single-file catalog, such as a test catalog.

    Rejects duplicate keys, which ``yaml.safe_load`` would otherwise silently
    overwrite. Raises CatalogError.
    """
    raise NotImplementedError


def load_catalog(directory: Path) -> Catalog:
    """Load the real catalog from ``directory`` (``catalog/*.yaml``).

    IDs and names must be unique across all the files. Raises CatalogError.
    """
    raise NotImplementedError


def check_no_removed(previous: Catalog, current: Catalog) -> list[str]:
    """Problems if any entry, guild or stat in ``previous`` is missing from ``current`` (CT-7).

    Retired entries are still present, so retiring is allowed (CT-6).
    """
    raise NotImplementedError
