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

## Maintainer tasks

Some changes players can't make themselves, by design; they ask with `/request`
and the maintainer makes them in the database (AD-2). The `awt-admin` command in
the bot's image does this safely, while the bot keeps running:

| Task | Command | Changes anything? |
|---|---|---|
| See a character's history, e.g. for a dispute (HV-5): every change, who made it and when. Finds a removed character too | `awt-admin history <character>` | No |
| See who has an entry, e.g. before changing or retiring it in the catalog | `awt-admin holders <entry>` | No |
| Move a character to another Discord account (only the owner can change a character, CH-1), e.g. a player's new account | `awt-admin transfer <character> <new owner's Discord user ID>` | Yes |
| Remove a character (CH-2): players can rename but not delete | `awt-admin remove-character <character>` | Yes |
| Free a one-holder title (HV-6) whose holder can't or won't `/remove` it, e.g. they've left | `awt-admin remove-entry <character> <entry>` | Yes |

To find a Discord user ID, turn on **User Settings → Advanced → Developer Mode**,
then right-click the person and choose **Copy User ID**.

Run it on the Fly machine. For the commands that change something, run it first
without `--yes` to see what it would change, then with `--yes` to make the change:

```
fly ssh console --app awt-party-bonus-bot -C "awt-admin remove-character Pip"
fly ssh console --app awt-party-bonus-bot -C "awt-admin remove-character Pip --yes"
```

Names ignore case; put a name with spaces in single quotes, e.g.
`-C "awt-admin remove-entry Ioseph 'Champion of Power' --yes"`.

With `--yes` it:
- takes a snapshot first, in `/data/snapshots/`, so a mistake can be undone with
  [restore-runbook.md](restore-runbook.md);
- makes the change in one go, leaving nothing half done: a removed character's
  entries and guild memberships go with it; a transferred character keeps them;
- records the change in the audit log (HV-5) as made by the maintainer (actor `0`).

A removed character's name is free to register again. A character that was its
player's current one stops being current, removed or transferred: the bot tells
them to choose another with `/play`, or to register one if it was their only
character. A transferred character becomes its new owner's current one if they had
none. Tell the players involved on Discord when it's done.

Never edit the database by hand instead: a hand-written query skips the
safeguards above, and can leave a removed character's entries behind.

## Setting it up from scratch

Done once on 2026-09-26; repeat it for a new host, or to hand the bot over.

> **Secrets:** run these commands in a **separate PowerShell window**, not VS Code's
> terminal. Never pipe a secret into `fly` or `gh`: on Windows, PowerShell can add an
> invisible byte-order mark to piped text, even in its own window and with
> `$OutputEncoding` set, and Fly then refuses the secret's name
> (`"﻿DISCORD_TOKEN" is not a valid secret name`). Instead, read the value into a
> variable with `Read-Host`, pass the variable, then remove it, as the steps below do.
> `Read-Host` shows what you paste, but it isn't kept in PowerShell's history. Never
> put a secret's value in a command, a file or a chat.

### GitHub

- Two-factor authentication on the GitHub account (NF-12). Signing in to Fly.io with
  GitHub puts Fly behind the same two-factor.
- `main` protected by the "Protect main" ruleset: pull requests only, and the CI
  checks `lint`, `test`, `test-rule` and `catalog` must pass.
- Dependabot (`.github/dependabot.yml`) keeps Python packages, actions and the
  Docker base images current, with one pull request a week for each.

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
3. Set the bot's secrets (separate PowerShell window). Paste the token at the
   prompt:
   ```
   $t = Read-Host 'Bot token'
   fly secrets set "DISCORD_TOKEN=$t" --stage --app awt-party-bonus-bot
   Remove-Variable t
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
   $t = fly tokens create deploy --app awt-party-bonus-bot --expiry 175200h
   gh secret set FLY_API_TOKEN --env production --body "$t"
   Remove-Variable t
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
   $id = Read-Host 'keyID'
   $key = Read-Host 'applicationKey'
   fly secrets set "BACKUP_KEY_ID=$id" "BACKUP_KEY=$key" --stage --app awt-party-bonus-bot
   Remove-Variable id, key
   ```
6. The bucket name and endpoint (`https://s3.us-east-005.backblazeb2.com`) are in
   `fly.toml`.
7. Restores download with a separate **read-only** key (`awt-restore`), made when
   needed: see [restore-runbook.md](restore-runbook.md). The B2 website won't
   download the snapshots, because they're stored encrypted.

### The first deploy

The Deploy workflow only exists once it's on `main`, so the first deploy is the
merge of the pull request that adds it. Check it with `fly logs`: you should see
`startup`, `snapshot taken`, `migrating` and `migrated` (a new, empty database),
`snapshot uploaded`, `commands synced` and `ready`.

## Renewing and changing secrets

| When | Do |
|---|---|
| The deploy token expires (20 years after it was made, chosen to outlive the bot; `fly tokens list --app awt-party-bonus-bot` shows the date), or leaks (the Deploy workflow fails with an authentication error) | Repeat the `fly tokens create deploy` and `gh secret set` step (Fly.io step 4). Then revoke the old one, and any extra tokens left by failed attempts: `fly tokens list --app awt-party-bonus-bot`, then `fly tokens revoke <ID>`. Only one deploy token should be active. |
| AWT goes live | Follow "Going live at AWT" below. |
| The bot token leaks | Discord developer portal → the bot → **Reset Token**, then set the new one (step 3, without `--stage`). |
| The storage key leaks or is lost | Delete it in B2, make a new one (B2 step 4) and set it (B2 step 5, without `--stage`). |

## Going live at AWT

Done on 2026-10-17 and 18. Repeat it to move the bot to another server.

Before launch, Fly ran the **test bot** on the test server. Production is a second,
separate bot, so the test bot keeps its own token and database for trying changes
(TS-13). Nothing in the code or the repository changes.

The Fly steps can be done before the server's admin has invited the bot: the bot
waits in maintenance mode until step 7. Don't start it earlier. A bot that isn't on
the server yet can't register its commands, so it exits, and Fly restarts it over and
over until the invite happens.

1. **Create the production bot.** Discord developer portal → **New Application**.
   Give it the name, icon and description in [discord/](../discord/README.md). On
   the **Bot** page, leave every privileged intent off (NF-6), and click **Reset
   Token**. Keep the token for step 6; never paste it into a chat or a file. Leave
   **Public Bot** on for now: when it's off, only the application's owner can add
   the bot to a server, so an admin who isn't the owner can't use the invite link.
2. **Invite it to AWT with only the four permissions (NF-11).** **OAuth2 → URL
   Generator**: scopes `bot` and `applications.commands`; permissions View
   Channels, Send Messages, Embed Links and Use Application Commands. The link ends
   with `permissions=2147503104`; any other number means an extra box is ticked.
   Whoever opens the link needs **Manage Server** on AWT; the link itself isn't
   secret.
3. **Let it into `#bonus-bot-support`.** Create the channel if it doesn't exist
   (named exactly as `request_channel` in `config/settings.yaml`; private, since
   requests name the player), and give whoever answers requests access to it. Then
   the channel's **Permissions → +**, pick the bot, and allow View Channel and Send
   Messages. On the channel only, never through a role.
4. **Park the bot** (separate PowerShell window, as for the rest of these steps):
   ```
   fly machine update <machine ID> --env MAINTENANCE=1 --app awt-party-bonus-bot --yes
   ```
   `fly logs` shows `maintenance mode: the bot is not running`, and the bot stays
   parked through the secret changes below.
5. **Start AWT with an empty database.** Move the test data aside; the bot creates
   a new, empty database when it starts:
   ```
   fly ssh console --app awt-party-bonus-bot -C "mv /data/awt-bonus.db /data/awt-bonus.db.old"
   fly ssh console --app awt-party-bonus-bot -C "ls -la /data"
   ```
   The listing should show `awt-bonus.db.old` and no `awt-bonus.db`, `-wal` or
   `-shm` file. Move any of those aside too, or SQLite may bring the test data back.
6. **Point Fly at AWT.** Paste the token at the prompt:
   ```
   $t = Read-Host 'AWT bot token'
   fly secrets set "DISCORD_TOKEN=$t" --app awt-party-bonus-bot
   Remove-Variable t
   fly secrets set DISCORD_GUILD_ID=<AWT server ID> --app awt-party-bonus-bot
   ```
   Each command restarts the machine, still in maintenance mode.
7. **Start it**, once the admin has done steps 2 and 3:
   ```
   fly machine update <machine ID> --env MAINTENANCE=0 --app awt-party-bonus-bot --yes
   ```
   `fly logs` shows `migrating` and `migrated` (the new database), then `commands
   synced` and `ready`, both with the AWT server's ID as `guild_id`.
8. **Check it.** On AWT, the bot is online; try `/catalog` and a test `/request`
   (it should arrive in `#bonus-bot-support`), and run the
   [TS-15 checklist](test-server.md) where it makes sense.
9. **Make it private.** On the **Installation** page, set **Install Link** to
   **None** (Discord won't make an application private while it has one), then turn
   **Public Bot** off on the **Bot** page. Worth doing for the test bot too.

From then on the test bot only runs when started by hand on a PC, with its own
`var/` database; it can't clash with production, because its token is different.

## Costs

About $3–4 a month on Fly.io (a shared-CPU machine with 512 MB and a 1 GB volume).
B2 is free under 10 GB; the database is well under 10 MB.
