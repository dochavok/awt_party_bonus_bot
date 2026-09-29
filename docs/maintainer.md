# Maintainer guide

Every recurring maintenance task, with its steps or a link to where they're written
down (requirements DOC-3). This page is in the repository only; it isn't on the
documentation site.

Most tasks are a change on a branch, a pull request, and a merge to `main`. CI checks
the change, and a merge deploys the bot and republishes the site automatically
(DP-1, DOC-1). Commands below run in PowerShell from the repository folder.

## Answering `/request`

Players' requests arrive in `#bonus-bot-support`, with the player's name.

| The request | What to do |
|---|---|
| A **missing entry**: a skill, rank, boon, item or title that gives a party bonus | Add it to the catalog: see [Changing the catalog](#changing-the-catalog). Ask for the card text if it isn't in the request. Tell the player to `/add` it once it's deployed. |
| A **wrong entry**: a value, name or card text | Correct it in the catalog: see [Changing the catalog](#changing-the-catalog). The change applies to every character that has it (CT-3). If it's a rule question rather than a typo, ask the DMs first ([Applying a DM's answer](#applying-a-dms-answer)). |
| **Remove a character** | `awt-admin remove-character`: see [Maintainer tasks in deployment.md](deployment.md#maintainer-tasks). |
| **Move a character to another Discord account**, e.g. a player's new account | `awt-admin transfer`: same place. |
| **Free a one-holder title** whose holder can't or won't `/remove` it | `awt-admin remove-entry`: same place. |
| A **dispute** about who changed a character | `awt-admin history` shows every change, who made it and when. |
| Anything else | Reply on Discord. If it's a new feature, it starts as a requirements change. |

The `awt-admin` commands that change something show what they'd do first, and take a
snapshot before they change anything. Tell the players involved when it's done.

## Changing the catalog

The catalog is the YAML in `catalog/`. The rules and every field are in
[catalog/README.md](../catalog/README.md). In short:

1. Edit the entry on a branch. **Never delete an entry or change its ID**: to take one
   out of the game, set `retired: true` (CT-6).
2. Check it: `uv run python -m awt_bonus.catalog check catalog`
3. If it changes a value or rule described in the requirements (section 8), update the
   requirements in the same pull request.
4. Regenerate the documentation examples if the sample party uses the entry:
   `uv run python scripts/generate_docs.py` (CI tells you if you forget).
5. Open a pull request, and merge once CI passes. It deploys in a few minutes.

Before changing or retiring an entry, `awt-admin holders <entry>` shows which
characters have it.

## Changing settings

The `/request` channel, how long `/sitout` lasts, and the highest level are in
[config/settings.yaml](../config/settings.yaml) (AD-1). Change it on a branch and merge;
the deploy restarts the bot with the new value. Never put a secret in it.

If you change the sit-out length, also update the pages that mention "12 hours".

## Applying a DM's answer

Open rule questions are in [dm-rule-questions.md](../dm-rule-questions.md). When a DM
answers one, follow the test-change rule in [CLAUDE.md](../CLAUDE.md), starting at
step 2:

1. Update the requirements so they say how the bot should behave, and mark the question
   answered.
2. Update the tests to match, in the same commit; the commit message names the
   requirement.
3. Fix the code until the tests pass.
4. Update the documentation pages that describe the rule, in the same pull request
   (DOC-7), and set their `reviewed:` dates once you've read them through.

## Reviewing Dependabot pull requests

Dependabot opens pull requests to update dependencies and GitHub Actions (NF-12).

- **CI passes:** read the title for anything surprising (a major version jump), then
  merge. Merging deploys.
- **CI fails:** don't merge. Look at what broke; usually it's a change in the library,
  and the fix is in our code. A test failing means the code is wrong, never the test
  (TF-5).
- **MkDocs 2.0:** stay on MkDocs 1.x. Material for MkDocs doesn't support 2.0, which
  drops the plugins and theme overrides the site uses, so `pyproject.toml` keeps MkDocs
  below 2.0. Close any pull request that tries to move past it.

## Checking the bot is running

- **The logs:** `fly logs --app awt-party-bonus-bot`. Look for `ready` after a deploy,
  and `command` lines with `"outcome": "error"`.
- **The machine:** `fly status --app awt-party-bonus-bot`.
- **Restart it:** `fly apps restart awt-party-bonus-bot`.
- **Undo a bad release:** revert the commit on `main` by pull request.

The full list, and what each log event means:
[Everyday tasks in deployment.md](deployment.md#everyday-tasks).

## Backups and restoring

A snapshot of the database goes to Backblaze B2 every night and is kept for 30 days
(DB-6). Nothing to do day to day; check the logs for `snapshot uploaded` now and then.

To restore, or to start again with an empty database:
[restore-runbook.md](restore-runbook.md). Try the drill in it once in a while, so it's
familiar when it matters.

## Renewing secrets

The Fly deploy token expires a year after it's made: the Deploy workflow fails with an
authentication error. If the bot token or the storage key leaks, replace it at once.
The steps for each: [Renewing and changing secrets in
deployment.md](deployment.md#renewing-and-changing-secrets).

Paste secrets in a separate PowerShell window, not VS Code's terminal, which can add
invisible characters.

## Updating the documentation

The documentation site is built from `docs/` (DOC-1). Preview it with
`uv run mkdocs serve`, at <http://127.0.0.1:8000>.

- **When the bot's behaviour or a rule changes**, update the pages that describe it in
  the same pull request (DOC-7).
- **After reading a page through** and checking it against the bot, set its
  `reviewed:` date in the front matter. Changing a page isn't the same as reviewing it.
- **Examples and the command reference are generated** (DOC-4, DOC-5). After changing
  a command, the sample party (`docs/_sample/party.yaml`) or the catalog, run
  `uv run python scripts/generate_docs.py`. CI fails if they're out of date.
- **A new command** gets a block at the end of `docs/commands.md` when you regenerate:
  move it to the right section and add a line on who sees the reply and an example.
- **A new page** needs a `reviewed:` date and an entry under `nav:` in `mkdocs.yml`.
- **Maintainer-only pages**, like this one, are listed under `exclude_docs:` in
  `mkdocs.yml`, so they stay off the site.

## Testing on the private server

Before a change that affects how the bot behaves in Discord, try it with the test bot:
[test-server.md](test-server.md), including the TS-15 checklist.
