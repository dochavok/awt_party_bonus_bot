"""Catalog check for CI (CT-7).

Usage: ``python -m awt_bonus.catalog check CATALOG_DIR [--previous PREVIOUS_DIR]``

Exits non-zero, printing every problem, if the catalog is invalid or if an entry
in the previous version has disappeared.
"""

import sys


def main(argv: list[str]) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
