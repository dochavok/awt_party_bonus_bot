# AWT Party Bonus Bot

Discord bot that works out party bonuses for AWT games. The source of truth is
[party-bonus-bot-requirements.md](party-bonus-bot-requirements.md). Open rule
questions for the DMs are in [dm-rule-questions.md](dm-rule-questions.md).

- Stack: Python 3.12+, discord.py, SQLite (SQLAlchemy + Alembic), pytest, Hypothesis, uv.
- Milestones: requirements section 17. M1 writes the functional tests only; later milestones implement code to pass them.

## The test-change rule (requirements TF-5): never break this

Tests are written from the requirements, before the code. **A failing test means
the code is wrong.** Never change, delete, skip, weaken or mark as expected-failure
a test to make code pass. That includes anything under `tests/`: the engine
scenarios (`tests/scenarios/engine-scenarios.yaml`) and their expected values,
the fixtures in `tests/fixtures/`, and snapshot files.

If you believe a test itself is wrong, stop and follow exactly this sequence:

1. **Ask the human.** Explain which test, what it expects, what you think is wrong,
   and which requirement it traces to. Do not continue until the human confirms
   the test is wrong. Never decide this yourself.
2. **Fix the requirements document** so it states how the bot should behave.
3. **Fix the test** so it matches the corrected requirement. Commit steps 2 and 3
   together; the commit message names the requirement changed.
4. **Fix the code** until the test passes.

If the human says the test is right, fix the code instead.

Adding **new** tests for existing requirements is fine without this sequence.
When a DM answers a question in `dm-rule-questions.md`, start at step 2.

## Where things live

- `catalog/`: the fixed catalog (stats, skills, guilds, items, titles) as YAML. Committed.
- `config/settings.yaml`: bot settings. Committed; **never** put secrets here.
- `var/`: the SQLite database and other runtime files. Git-ignored.
- `tests/`: `scenarios/` (engine scenarios), `fixtures/` (mock data), and snapshot files.
- Secrets (bot token, storage credentials) come only from environment variables.

## Running the checks

- `uv run pytest`: tests for milestones not in `finished_milestones` (pyproject.toml)
  run as expected failures (TF-4). Mark each test `milestone`, `req` and, where
  relevant, `dm`; untagged tests fail collection.
- `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`.
- After adding tests: `uv run pytest --collect-only -q --write-coverage` regenerates
  `tests/COVERAGE.md`.
- `uv run python scripts/check_test_changes.py --base main`: the TF-6 check CI runs.
  Without a requirements change it refuses any change to an existing test, scenario,
  fixture or harness file, a new `conftest.py`, removing a finished milestone,
  changing the pytest settings, and changes to the check or the CI workflows. It
  always refuses bot code that refers to the tests or names test characters. New
  tests, scenarios and test files are always fine.
- On this PC uv needs `--system-certs` to reach PyPI (e.g. `uv sync --system-certs`).

## Other conventions

- Every test names the requirement ID(s) it checks (e.g. `HV-4`) and any DM
  question it depends on (e.g. `Q7`).
- **Assertions must be able to fail** (TF-7): tie each value to the character and
  stat it belongs to, check a refusal is private and names what was refused, and
  never accept "any non-empty reply". Before trusting a new test, break the code it
  guards and watch it fail.
- **Requirement IDs are permanent** (TF-3): never renumber or reuse one. A removed
  requirement keeps its row, marked *removed*.
- **Catalog entries are retired, never deleted** (CT-6, CT-7): set `retired: true`
  instead of removing an entry from `catalog/`.
- Read YAML with `yaml.safe_load` only; validate the catalog with pydantic.
- Store and compare all times in GMT (UTC).
- Keep the calculation engine a pure function with no Discord or database code.
- When a requirement changes, update the documentation pages that describe it in
  the same pull request (requirements DOC-7).
