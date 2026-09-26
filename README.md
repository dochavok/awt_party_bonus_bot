# awt_party_bonus_bot
Discord bot to track bonuses to the party for AWT raids

> **Status:** in development. Every command in the requirements works, including `/guild`, Support from Discord roles, secret guilds and `/request`; automatic deployment is being set up (milestone M5). See the [requirements](party-bonus-bot-requirements.md) for the full design.

The bot works out the party bonuses (CM, CR, and more) that each character receives from everyone else in the voice channel. You record what your character **has**; the bot does the math.

## First-time setup (once per character)

1. **Register your character.** The level is optional; it's only used for the Cult of the Dragon's bonus, so add it if your character is in the Cult:
   ```
   /character register name:Crateris level:22
   ```
2. **Join your guilds**, if any:
   ```
   /guild join character:Crateris guild:Cult of the Dragon
   ```
3. **Add what your character has**: skills, guild ranks, boons, items and titles. Autocomplete shows what's available:
   ```
   /add character:Crateris entry:Holy Aura
   /add character:Crateris entry:High Priest
   /add character:Crateris entry:Wills ward stone
   ```
   Not sure what's available or what it gives? Use `/catalog`.

Your Guild rank role on Discord (Junior Adventurer through Guild Legend) gives **Support** automatically; you don't add it.

## On game night

- **Join the voice channel.** Everyone in it is counted automatically.
- **Running the game or just listening?** Use `/sitout` so your bonuses aren't counted. It lasts 12 hours; `/sitin` ends it early.
- **Show the party's bonuses:** `/partybonus` posts the table for everyone. Add `private:true` to just check it yourself.
- **See your own totals:** `/mybonus`
- **See how a total was worked out:** `/breakdown` for the whole party, or `/breakdown Crateris` for one character.

Everything except `/partybonus` replies privately: only you see it.

People joining or leaving? Just run the command again.

## Other things you might need

| To… | Use |
|---|---|
| Play a different character of yours | `/play <character>` (it stays until you switch again) |
| Update your level | `/character level <character> <n>` |
| Rename a character (e.g. fix a typo) | `/character rename <character> <new name>` |
| Remove something | `/remove <character> <entry>` |
| Leave a guild (also removes its ranks and boons) | `/guild leave <character> <guild>` |
| Look up what a skill, item or guild gives | `/catalog <name>` |
| Report something missing or wrong in the catalog, or ask for anything the bot can't do (e.g. removing a character) | `/request <text>` |

Characters can't be deleted. Rename one instead, or use `/request` if it really needs removing.

## Good to know

- **Bonuses go to your allies, not to you,** unless the ability says otherwise (e.g. Leadership, King of the Pirates).
- **"If in the same range" bonuses** (Commanding Presence) are listed separately and aren't included in totals. Add them yourself when they apply.
- **Only always-on bonuses are tracked.** Once-per-combat or daily abilities aren't.
- You can only change your own characters.

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
