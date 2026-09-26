"""The test-change rule in CI (requirements TF-5, TF-6).

Fails if a change modifies or deletes an existing file under tests/ without also
changing party-bonus-bot-requirements.md. Adding new test files is always allowed.
A rename counts as deleting the old file.

tests/COVERAGE.md is exempt: it's documentation generated from the tests (TF-3),
and it changes whenever a test is added.

Usage: python scripts/check_test_changes.py --base <git ref>
Compares <base> with HEAD. Needs only the standard library and git.
"""

import argparse
import subprocess
import sys
from collections.abc import Iterable

REQUIREMENTS = "party-bonus-bot-requirements.md"
TESTS = "tests/"
EXEMPT = {"tests/COVERAGE.md"}

RULE = """\
The test-change rule (TF-5): a failing test means the code is wrong. A test may only
change after a human confirms it's wrong, and then only in this order:
  1. confirm with a human that the test is wrong;
  2. fix the requirements document ({requirements});
  3. fix the test to match (commit steps 2 and 3 together, naming the requirement);
  4. fix the code until the test passes.
Adding new test files is always allowed."""


def violations(changes: Iterable[tuple[str, str]]) -> list[str]:
    """Problems with a set of (git status letter, path) changes; empty if the rule holds."""
    changes = list(changes)
    touched_requirements = any(path == REQUIREMENTS for _, path in changes)
    if touched_requirements:
        return []
    return [
        f"{'deleted' if status.startswith('D') else 'modified'}: {path}"
        for status, path in changes
        if path.startswith(TESTS) and path not in EXEMPT and not status.startswith("A")
    ]


def changed_files(base: str) -> list[tuple[str, str]]:
    """(status letter, path) for every file changed between ``base`` and HEAD."""
    output = subprocess.run(
        ["git", "diff", "--name-status", "--no-renames", base, "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    changes = []
    for line in output.splitlines():
        status, _, path = line.partition("\t")
        changes.append((status, path))
    return changes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, help="git ref to compare HEAD with")
    args = parser.parse_args(argv)

    problems = violations(changed_files(args.base))
    if not problems:
        print(f"Test-change rule: OK (compared {args.base}..HEAD)")
        return 0
    print(f"Test-change rule broken: existing test files changed, but {REQUIREMENTS} didn't:")
    for problem in problems:
        print(f"  {problem}")
    print()
    print(RULE.format(requirements=REQUIREMENTS))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
