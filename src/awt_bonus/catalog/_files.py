"""Reading catalog files (6.2, CT-7).

YAML is read with ``yaml.safe_load`` only (section 12). ``safe_load`` silently keeps
the last of two duplicate keys, so each file is also composed into YAML nodes (which
constructs nothing) and checked for duplicate keys first.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from awt_bonus.catalog._model import Catalog, CatalogError
from awt_bonus.catalog._parse import SECTIONS, parse_catalog


def read_yaml(path: Path) -> tuple[Any, list[str]]:
    """A YAML file's data, and any problems (duplicate keys, bad YAML)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return None, [f"{path.name}: can't be read ({error.strerror})"]
    try:
        problems = [
            f"{path.name}: {p}" for p in _duplicate_keys(yaml.compose(text, yaml.SafeLoader))
        ]
        return yaml.safe_load(text), problems
    except yaml.YAMLError as error:
        return None, [f"{path.name}: isn't valid YAML ({error})"]


def _duplicate_keys(node: yaml.Node | None) -> list[str]:
    problems: list[str] = []
    if isinstance(node, yaml.MappingNode):
        seen: set[str] = set()
        for key, value in node.value:
            if isinstance(key, yaml.ScalarNode):
                if key.value in seen:
                    line = key.start_mark.line + 1
                    problems.append(f"line {line}: duplicate key {key.value!r}")
                seen.add(key.value)
            problems += _duplicate_keys(value)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            problems += _duplicate_keys(item)
    return problems


def load_catalog_file(path: Path) -> Catalog:
    """Load a single-file catalog, such as a test catalog.

    Rejects duplicate keys, which ``yaml.safe_load`` would otherwise silently
    overwrite. Raises CatalogError.
    """
    data, problems = read_yaml(path)
    return _parse(data if data is not None else {}, problems)


def load_catalog(directory: Path) -> Catalog:
    """Load the real catalog from ``directory`` (``catalog/*.yaml``).

    Every ``*.yaml`` file in the folder is part of the catalog, and may hold any of
    ``stats``, ``entries``, ``guilds`` and ``item_classes``. IDs and names must be unique across all
    the files. Raises CatalogError.
    """
    merged, problems = _merge(directory)
    return _parse(merged, problems)


def _merge(directory: Path) -> tuple[dict[str, dict[Any, Any]], list[str]]:
    if not directory.is_dir():
        return {}, [f"{directory}: no such folder"]
    merged: dict[str, dict[Any, Any]] = {section: {} for section in SECTIONS}
    where: dict[tuple[str, Any], str] = {}
    problems: list[str] = []
    for path in sorted(directory.glob("*.yaml")):
        data, found = read_yaml(path)
        problems += found
        if data is None:
            continue
        if not isinstance(data, Mapping):
            problems.append(f"{path.name}: must be a mapping of catalog sections")
            continue
        for section, items in data.items():
            if section not in SECTIONS:
                problems.append(f"{path.name}: unknown section {section!r}")
                continue
            if items is None:
                continue
            if not isinstance(items, Mapping):
                problems.append(f"{path.name}: `{section}` must be a mapping of IDs")
                continue
            for key, value in items.items():
                if (section, key) in where:
                    problems.append(
                        f"ID {key!r} is defined in both {where[section, key]} and {path.name}"
                    )
                where[section, key] = path.name
                merged[section][key] = value
    return merged, problems


def _parse(data: Mapping[str, Any], problems: list[str]) -> Catalog:
    try:
        catalog = parse_catalog(data)
    except CatalogError as error:
        raise CatalogError(problems + error.problems) from None
    if problems:
        raise CatalogError(problems)
    return catalog


def catalog_ids(directory: Path) -> dict[str, set[str]]:
    """The IDs in each section of a catalog folder, read without validating it.

    For comparing with a previous version that today's rules might not accept.
    """
    merged, _ = _merge(directory)
    return {
        section: {str(key) for key in items} if isinstance(items, Mapping) else set()
        for section, items in merged.items()
        if section in SECTIONS
    }


def ids_of(catalog: Catalog) -> dict[str, set[str]]:
    return {
        "stats": set(catalog.stats),
        "entries": set(catalog.entries),
        "guilds": set(catalog.guilds),
        "item_classes": set(catalog.item_classes),
    }


def removed(previous: Mapping[str, set[str]], current: Mapping[str, set[str]]) -> list[str]:
    """Problems for every ID in ``previous`` that isn't in ``current`` (CT-7)."""
    what = {"stats": "stat", "entries": "entry", "guilds": "guild", "item_classes": "item class"}
    return [
        f"{what[section]} {key!r} was in the previous catalog and has disappeared; "
        "mark it `retired: true` instead of removing it (CT-6)"
        for section in SECTIONS
        for key in sorted(previous.get(section, set()) - current.get(section, set()))
    ]


def check_no_removed(previous: Catalog, current: Catalog) -> list[str]:
    """Problems if any entry, guild, stat or item class in ``previous`` is missing from
    ``current`` (CT-7, CT-10).

    Retired entries and classes are still present, so retiring is allowed (CT-6).
    """
    return removed(ids_of(previous), ids_of(current))
