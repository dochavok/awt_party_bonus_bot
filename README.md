# awt_party_bonus_bot
Discord bot to track bonuses to the party for AWT raids

The bot works out the party bonuses (CM, CR, and more) that each character receives from
everyone else in the voice channel. Players record what their characters **have**; the
bot does the math.

## Using the bot

**The player and DM guide is at <https://dochavok.github.io/awt_party_bonus_bot/>.**
In Discord, `/help` shows how to get started and your own next step.

## For the maintainer

- [party-bonus-bot-requirements.md](party-bonus-bot-requirements.md): the requirements,
  the source of truth for how the bot behaves.
- [docs/maintainer.md](docs/maintainer.md): every recurring maintenance task, e.g.
  answering `/request`, changing the catalog, and updating the documentation.
- [docs/deployment.md](docs/deployment.md), [docs/restore-runbook.md](docs/restore-runbook.md)
  and [docs/test-server.md](docs/test-server.md): running the bot in production,
  restoring its database, and the private test server.
- [catalog/README.md](catalog/README.md): how the catalog files work.
- [dm-rule-questions.md](dm-rule-questions.md): rule questions waiting on the DMs.

## Running the bot (for testing)

On the private test server (TS-13), with the test bot's own token:

```
$env:DISCORD_TOKEN = "<test bot token>"
$env:DISCORD_GUILD_ID = "<test server ID>"
uv run python -m awt_bonus
```

The database goes to `var/awt-bonus.db` unless `DATABASE_URL` says otherwise, and snapshots of it to `var/snapshots/`. Settings (the `/request` channel, sit-out hours, maximum level) are in [config/settings.yaml](config/settings.yaml). The bot logs one JSON object per line.

To restore a snapshot, with the bot stopped: `uv run python -m awt_bonus.restore var/snapshots/<file>`.

Setting up the test server, and the checklist to run on it: [docs/test-server.md](docs/test-server.md).

## Working on the documentation

The site is built from `docs/` with MkDocs, and published by the Docs workflow when CI
passes on `main`.

```
uv run mkdocs serve                       # preview at http://127.0.0.1:8000
uv run python scripts/generate_docs.py    # regenerate the examples and command reference
```
