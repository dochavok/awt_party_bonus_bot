# Restore runbook

How to put the bot's database back from a snapshot, on the same host or a new one
(requirement DB-7). It must be tried at least once before AWT goes live; record
each drill at the end.

**When to use it:** the database is lost or damaged, a bad change needs undoing,
or the bot is moving to a new host. Characters, entries, guilds, sit-outs and the
audit log are all in the database; the catalog and settings are in the repository
and need no restoring.

**What you lose:** changes since the snapshot, at most a day's. Players re-enter
them.

## What you need

- The Fly.io account (the GitHub login), with `flyctl` installed.
- Docker Desktop, to download a snapshot from Backblaze B2 (below). The B2 website
  won't download the snapshots, because they're stored with server-side encryption.
- The **read-only B2 key**, `awt-restore`. The bot's own key can only upload, on
  purpose. Craig keeps the current key in "Access". Keep it private: never in the
  repository, a chat or a plain file.

  **Last resort, if the key is lost:** in B2, **Application Keys**, delete
  `awt-restore` and add a new one with the same settings: name `awt-restore`, only
  the `awt-party-bonus-backups` bucket, **Read Only**, prefix `snapshots/`,
  list-all-bucket-names off. B2 shows the new key once; keep it where the old one
  was. Nothing else uses this key, so nothing else needs changing.
- For a new host: the Discord bot token (or reset it in the Discord developer
  portal) and a new B2 upload key. See [deployment.md](deployment.md).

Commands are for PowerShell, in the repository folder. `APP` is
`awt-party-bonus-bot`.

## 1. Pick a snapshot

Snapshots are named after the UTC time they were taken, e.g.
`awt-bonus-20260927T080000Z.db`. They're in two places:

- **Backblaze B2** (off-site, 30 days). Use this if the Fly volume is lost.
  Download one with the bot's image. From the repository folder, on an
  up-to-date `main`, type the read-only key at the prompts (it isn't kept in
  PowerShell's history, and the last line clears it from the window):
  ```
  docker build -t awt-bonus .
  $env:BACKUP_KEY_ID = Read-Host 'Read-only keyID'
  $env:BACKUP_KEY = Read-Host 'Read-only applicationKey'
  docker run --rm -e BACKUP_KEY_ID -e BACKUP_KEY -e BACKUP_BUCKET=awt-party-bonus-backups -e BACKUP_ENDPOINT_URL=https://s3.us-east-005.backblazeb2.com -v "$HOME\Downloads:/out" awt-bonus python -m awt_bonus.download list
  docker run --rm -e BACKUP_KEY_ID -e BACKUP_KEY -e BACKUP_BUCKET=awt-party-bonus-backups -e BACKUP_ENDPOINT_URL=https://s3.us-east-005.backblazeb2.com -v "$HOME\Downloads:/out" awt-bonus python -m awt_bonus.download get newest --to /out
  Remove-Item Env:BACKUP_KEY_ID, Env:BACKUP_KEY
  ```
  `list` shows the snapshots, newest first; `get` takes `newest` or a name from the
  list, and saves it in your Downloads folder. (`-e BACKUP_KEY` with no value
  passes the key from the window's environment, so it never appears in the
  command.)
- **On the volume** (`/data/snapshots/`, 30 days): the nightly snapshots, and the
  one taken before each migration (DB-4). List them with
  `fly ssh console --app awt-party-bonus-bot -C "ls -l /data/snapshots"`.

## 2. Maintenance mode: stop the bot, keep the machine

The restore refuses while the bot is running (DB-3). Maintenance mode restarts the
machine without starting the bot, so the volume can still be reached:

```
fly machine list --app awt-party-bonus-bot
fly machine update <machine ID> --env MAINTENANCE=1 --app awt-party-bonus-bot --yes
```

`fly logs` then shows `maintenance mode: the bot is not running`, and the bot shows
as offline in Discord.

## 3. Restore

**A snapshot already on the volume:**

```
fly ssh console --app awt-party-bonus-bot -C "/app/.venv/bin/python -m awt_bonus.restore /data/snapshots/<snapshot file> --database /data/awt-bonus.db"
```

**A snapshot downloaded from B2** (step 1): copy it onto the volume first, then restore it:

```
fly ssh sftp shell --app awt-party-bonus-bot
» put C:\Users\<you>\Downloads\<snapshot file> /data/restore.db
» (Ctrl+D to leave)
fly ssh console --app awt-party-bonus-bot -C "/app/.venv/bin/python -m awt_bonus.restore /data/restore.db --database /data/awt-bonus.db"
```

The restore command checks the snapshot (SQLite's integrity check, and that it's a
bot database), keeps the current database as `awt-bonus.db.before-restore-<time>`,
and prints how many characters the snapshot holds. If it says *Not restored*, read
the reason: most likely the bot is still running (go back to step 2) or the file
isn't a snapshot.

## 4. Start the bot again

```
fly machine update <machine ID> --env MAINTENANCE=0 --app awt-party-bonus-bot --yes
fly logs --app awt-party-bonus-bot
```

Wait for `ready`. If the snapshot is from before a schema change, you'll first see
`snapshot taken`, `migrating` and `migrated`: the bot brings it up to date (DB-4).
The next deploy also clears `MAINTENANCE`.

## 5. Check it on Discord

- `/character list` for your own characters, and `/breakdown` for someone else's
  character: they match what they were at the snapshot's time.
- In a voice channel, `/partybonus private:true` gives sensible totals.
- Tell the players that changes after the snapshot's time need re-entering.

When all is well, delete the leftovers:
`fly ssh console --app awt-party-bonus-bot -C "rm /data/restore.db /data/awt-bonus.db.before-restore-<time>"`.

## Restoring onto a new host

If the Fly app or its volume is gone:

1. Set up Fly again as in [deployment.md](deployment.md), "Setting it up from
   scratch": the app, the volume, the secrets and, if the app's name changed, the
   deploy token and the name in `fly.toml` and `deploy.yml`.
2. Deploy once from `main`: re-run the last Deploy workflow in GitHub
   (**Actions → Deploy → Re-run jobs**), or run
   `fly deploy --app awt-party-bonus-bot --build-arg GIT_SHA=$(git rev-parse HEAD)`
   on an up-to-date `main`. The bot starts with an empty database.
3. Download the newest snapshot from B2 (step 1), then follow steps 2 to 5.

## Starting with an empty database

E.g. to clear the test data before AWT goes live: in maintenance mode (step 2),
`fly ssh console --app awt-party-bonus-bot -C "mv /data/awt-bonus.db /data/awt-bonus.db.old"`,
then step 4. The bot creates a new, empty database as it starts.

## The drill on a PC (Docker Desktop)

Restoring into a fresh Docker volume on a PC tries the "new host" path without
touching Fly. Only one bot may run with a token, so put the Fly bot in maintenance
mode (step 2) first, and take it out afterwards (step 4).

First download a snapshot from B2 into your Downloads folder, as in step 1. Then:

```
docker volume create awt-bonus-drill
docker run --rm -v awt-bonus-drill:/data -v "$HOME\Downloads:/restore:ro" awt-bonus python -m awt_bonus.restore /restore/<snapshot file> --database /data/awt-bonus.db
$env:DISCORD_TOKEN = Read-Host 'Bot token'
docker run --rm -it -v awt-bonus-drill:/data -e DISCORD_TOKEN -e DISCORD_GUILD_ID=<server ID> awt-bonus
```

Check it as in step 5, then stop it with Ctrl+C and remove the volume with
`docker volume rm awt-bonus-drill`. (`-e DISCORD_TOKEN` with no value passes the
token from the environment, so it never appears in the command.)

## Drills

| Date | Who | Snapshot | Where to | Time taken | Notes |
|---|---|---|---|---|---|
| 2026-09-26 | Craig | `awt-bonus-20260926T221141Z.db` from B2 (2 characters, 1 entry, 1 guild membership, 4 audit records) | A fresh Docker volume on a PC, run as the test bot on the test server (the "new host" path) | Not timed end to end; the Fly bot was offline about 8 minutes (22:21–22:29 UTC), including fixing the runbook as we went | Everything checked on the test server was restored. Found and fixed: the B2 website won't download encrypted snapshots (now `python -m awt_bonus.download`), and hidden key prompts inside Docker looked frozen (the key now comes from `Read-Host`). A timed run before AWT goes live would give a clean figure. |
