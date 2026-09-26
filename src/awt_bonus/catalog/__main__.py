"""Catalog check for CI (CT-7).

Usage: ``python -m awt_bonus.catalog check CATALOG_DIR [--previous PREVIOUS_DIR]``

Exits non-zero, printing every problem, if the catalog is invalid or if an entry
in the previous version has disappeared.
"""

import argparse
import sys
from pathlib import Path

from awt_bonus.catalog import CatalogError, load_catalog
from awt_bonus.catalog._files import catalog_ids, ids_of, removed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m awt_bonus.catalog")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check the catalog (CT-7)")
    check.add_argument("catalog", type=Path, help="the catalog folder, e.g. catalog")
    check.add_argument(
        "--previous", type=Path, help="the previous version's catalog folder, to compare with"
    )
    args = parser.parse_args(argv)
    problems = _check(args.catalog, args.previous)
    for problem in problems:
        print(f"catalog: {problem}", file=sys.stderr)
    if problems:
        print(f"The catalog has {len(problems)} problem(s).", file=sys.stderr)
        return 1
    print("The catalog is valid.")
    return 0


def _check(directory: Path, previous: Path | None) -> list[str]:
    try:
        catalog = load_catalog(directory)
    except CatalogError as error:
        return error.problems
    if not catalog.entries:
        return [f"{directory}: the catalog has no entries"]
    if previous is None:
        return []
    if not previous.is_dir():
        return [f"{previous}: no such folder"]
    # Read the previous version's IDs without validating it: it may predate a
    # change to the format.
    return removed(catalog_ids(previous), ids_of(catalog))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
