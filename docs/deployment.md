# Deployment

How the bot runs in production, how a push to `main` reaches it, and how to set it
up again from scratch (requirements 12.1, 12.2, NF-8, NF-9, NF-12). Restoring the
database is in [restore-runbook.md](restore-runbook.md).

## What runs where

| Where | What | Notes |
|---|---|---|
| **GitHub** | The code; CI (`.github/workflows/ci.yml`); the deploy workflow (`.github/workflows/deploy.yml`) | `main` is protected: changes arrive by pull request, and all four CI checks must pass (NF-12). |
| **GitHub `production` environment** | The `FLY_API_TOKEN` secret | Only `main` may use it. A deploy-only token for the one Fly app. |
| **Fly.io**, app `awt-party-bonus-bot`, region `iad` | One machine running the Docker image; the volume `awt_bonus_data` mounted at `/data` | `/data` holds the database (`awt-bonus.db`), its lock file and `snapshots/`. Fly restarts the bot if it crashes (NF-3) and keeps its logs. |
| **Fly secrets** | `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `BACKUP_KEY_ID`, `BACKUP_KEY` | Never in the repository (NF-9). `fly secrets list` shows names only. |
| **`fly.toml`** (committed) | The app name, the volume, `DATABASE_URL`, `BACKUP_BUCKET`, `BACKUP_ENDPOINT_URL` | Nothing secret. |
| **Backblaze B2**, bucket `awt-party-bonus-backups` | Nightly snapshots under `snapshots/` | A lifecycle rule deletes them after 30 days (DB-6). The bot's key can only write. |
| **Discord** | The bot application and its token | Invited with only View Channels, Send Messages, Embed Links and Use Application Commands (NF-11). |

## From a push to a running bot

1. A pull request is merged into `main`.
2. CI runs on `main`: lint, types, tests, the test-change rule and the catalog check.
3. When CI succeeds, the **Deploy** workflow starts. It checks the commit is still the
   newest on `main` (so a slow, older run never deploys over a newer one), then runs
   `flyctl deploy`.
4. Fly builds the image from the `Dockerfile` and replaces the machine: it sends the
   bot SIGTERM, the bot closes cleanly and releases its lock, and the new version
   starts on the same volume (DP-4). If the schema changed, the bot snapshots the
   database and migrates it as it starts (DB-4).
5. The workflow waits until the new version logs `ready`. If it doesn't within 90
   seconds, the deploy fails in GitHub with the last log lines.

A catalog or settings change is the same: edit, pull request, merge, and a few
minutes later the bot has it (DP-3, AD-1).

## Everyday tasks

In PowerShell, from the repository folder. Use `flyctl` in place of `fly` if `fly`
isn't found.

| To… | Run |
|---|---|
| Watch the logs (JSON lines, NF-8) | `fly logs --app awt-party-bonus-bot` |
| See the machine and the release | `fly status --app awt-party-bonus-bot` |
| Restart the bot | `fly apps restart awt-party-bonus-bot` |
| See past releases | `fly releases --app awt-party-bonus-bot` |
| Undo a bad release | Revert the commit on `main` by pull request; the revert deploys like any change. In a hurry: `fly deploy --app awt-party-bonus-bot --image <image of the previous release>` (images are listed by `fly releases --image`). |
| List snapshots on the volume | `fly ssh console --app awt-party-bonus-bot -C "ls -l /data/snapshots"` |

Useful log events: `startup`, `ready`, `command` (one per command, with `outcome`
and `duration_ms`), `gateway disconnected` / `gateway resumed`, `migrating` /
`migrated`, `snapshot taken` / `snapshot uploaded` / `snapshot upload failed`,
`startup refused` (with the reason) and `shutdown`.

**Only one copy of a bot may run with a token.** If you run the bot on your PC with
the same token as Fly (e.g. the test bot), stop the Fly one first:
see "Maintenance mode" in [restore-runbook.md](restore-runbook.md).

## Setting it up from scratch

Done once on 2026-09-26; repeat it for a new host, or to hand the bot over.

> **Piping secrets:** run any command that pipes a secret (`... | fly secrets import`,
> `... | gh secret set`) in a **separate PowerShell window**, not VS Code's terminal.
> VS Code's terminal adds an invisible byte-order mark to piped text, and Fly then
> refuses the secret's name (`"﻿DISCORD_TOKEN" is not a valid secret name`).
> Type secret values at the prompts; never put them in a command, a file or a chat.

### GitHub

- Two-factor authentication on the GitHub account (NF-12). Signing in to Fly.io with
  GitHub puts Fly behind the same two-factor.
- `main` protected by the "Protect main" ruleset: pull requests only, and the CI
  checks `lint`, `test`, `test-rule` and `catalog` must pass.
- Dependabot (`.github/dependabot.yml`) keeps Python packages, actions and the
  Docker base images current.

### Fly.io

1. Log in and create the app:
   ```
   fly auth login
   fly apps create awt-party-bonus-bot
   ```
   A new app name must also go in `fly.toml` and `deploy.yml`.
2. Create the volume (1 GB, in the app's region). Answer yes to the warning about a
   single volume: the bot must run as one machine (DB-3), and the nightly snapshots
   are the backup.
   ```
   fly volumes create awt_bonus_data --size 1 --region iad --app awt-party-bonus-bot
   ```
3. Set the bot's secrets (separate PowerShell window). The token is typed at the
   prompt, so it isn't kept in PowerShell's history:
   ```
   "DISCORD_TOKEN=$(Read-Host 'Bot token')" | fly secrets import --stage --app awt-party-bonus-bot
   fly secrets set DISCORD_GUILD_ID=<server ID> --stage --app awt-party-bonus-bot
   ```
   The token and server ID must belong together: the test bot and test server
   before launch, the AWT bot and AWT server after.
4. Give GitHub a deploy token. First create the `production` environment and allow
   only `main` to use it:
   ```
   gh api -X PUT repos/dochavok/awt_party_bonus_bot/environments/production -F "deployment_branch_policy[protected_branches]=false" -F "deployment_branch_policy[custom_branch_policies]=true"
   gh api -X POST repos/dochavok/awt_party_bonus_bot/environments/production/deployment-branch-policies -f name=main -f type=branch
   ```
   Then, in a separate PowerShell window, create the token and store it without it
   ever appearing on screen:
   ```
   fly tokens create deploy --app awt-party-bonus-bot --expiry 8760h | gh secret set FLY_API_TOKEN --env production
   ```
   Check with `gh secret list --env production`.

### Backblaze B2

1. Sign up for B2 (US region) and turn on two-factor authentication under
   **My Settings**.
2. **Create a Bucket**: `awt-party-bonus-backups`, Private, default encryption on,
   object lock off.
3. **Lifecycle Settings** → custom rule: prefix `snapshots/`, hide after 30 days,
   delete 1 day after hiding (DB-6).
4. **Application Keys** → new key `awt-bot-upload`: only this bucket, **Write Only**,
   prefix `snapshots/`, list-all-bucket-names off. The page shows the key once.
5. Give it to Fly (separate PowerShell window), pasting at the prompts:
   ```
   "BACKUP_KEY_ID=$(Read-Host 'keyID')`nBACKUP_KEY=$(Read-Host 'applicationKey')" | fly secrets import --stage --app awt-party-bonus-bot
   ```
6. The bucket name and endpoint (`https://s3.us-east-005.backblazeb2.com`) are in
   `fly.toml`.

### The first deploy

The Deploy workflow only exists once it's on `main`, so the first deploy is the
merge of the pull request that adds it. Check it with `fly logs`: you should see
`startup`, `snapshot taken`, `migrating` and `migrated` (a new, empty database),
`snapshot uploaded`, `commands synced` and `ready`.

## Renewing and changing secrets

| When | Do |
|---|---|
| The deploy token expires (a year after it was made; the Deploy workflow fails with an authentication error) | Repeat the `fly tokens create deploy ... \| gh secret set ...` step. Revoke the old one: `fly tokens list --app awt-party-bonus-bot`, then `fly tokens revoke <ID>`. |
| AWT goes live | Set `DISCORD_TOKEN` and `DISCORD_GUILD_ID` to the AWT bot's token and AWT's server ID (step 3, without `--stage`: the bot restarts with them). Invite the AWT bot with only the four permissions in NF-11, as in [test-server.md](test-server.md). If AWT's `#bonus-bot-support` is private, add the bot to it with View Channel and Send Messages on that channel only. The test data stays in the database; if AWT should start empty, see [restore-runbook.md](restore-runbook.md) "Starting with an empty database". |
| The bot token leaks | Discord developer portal → the bot → **Reset Token**, then set the new one (step 3, without `--stage`). |
| The storage key leaks or is lost | Delete it in B2, make a new one (B2 step 4) and set it (B2 step 5, without `--stage`). |

## Costs

About $3–4 a month on Fly.io (a shared-CPU machine with 512 MB and a 1 GB volume).
B2 is free under 10 GB; the database is well under 10 MB.
