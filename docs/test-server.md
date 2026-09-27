# The private test server

How to set up and use the private Discord server for trying the bot by hand
(requirements TS-13 to TS-16). The automated tests use a fake Discord; this is
where the Discord-specific parts are checked for real. Run the checklist before
merging a milestone that changes Discord behaviour.

## Set up once

1. **Create the server.** In Discord, click **+** in the server list, then
   **Create My Own**. Call it something like "AWT Bot Test".
2. **Copy AWT's setup (TS-14):**
   - the five Guild rank roles: Junior Adventurer, Guild Veteran, Guild Vanguard,
     Guild Champion, Guild Legend;
   - a voice channel (a second one helps for the `channel:` option);
   - a text channel called `bonus-bot-support` (for `/request`);
     if it's private, as AWT's is likely to be, add the bot to it after inviting
     it (step 4): **Edit Channel → Permissions → +**, pick the bot, and allow
     **View Channel** and **Send Messages**. Otherwise `/request` replies that it
     couldn't be posted, and the log shows `403 Forbidden ... Missing Access`.
     Allow these on the channel only: never give the bot a role with server-wide
     powers such as Administrator (NF-11);
   - optionally, a music bot, to check bots are ignored.
3. **Create the test bot (TS-13).** It has its own token and database, so testing
   never touches AWT's data.
   - At <https://discord.com/developers/applications>, click **New Application**.
   - Give it the name, icon and description in [discord/](../discord/README.md).
   - Open **Bot** and click **Reset Token**. Copy the token and keep it private:
     never commit it or paste it into a chat (NF-9).
   - No privileged intents are needed; leave them all off (NF-6).
4. **Invite the bot with only the permissions it needs (NF-11).** Under
   **OAuth2 → URL Generator**, tick:
   - scopes: `bot` and `applications.commands`;
   - permissions: View Channels, Send Messages, Embed Links, Use Application
     Commands. Never Administrator.

   Both the scopes and the permissions are ticked on this **URL Generator** page.
   The **Bot** page has a "Bot Permissions" box too, but the invite URL doesn't use
   it. If `bot` isn't ticked here, the slash commands still appear, but the bot
   never joins the server, and every command fails with "the bot isn't in
   server …". Check the bot is in the server's member list.

   Open the generated URL and add the bot to the test server.
5. **Get the server ID.** Turn on **User Settings → Advanced → Developer Mode**,
   then right-click the server and choose **Copy Server ID**.

## Run the bot

From the repository folder, in PowerShell:

```
$env:DISCORD_TOKEN = "<test bot token>"
$env:DISCORD_GUILD_ID = "<test server ID>"
uv run python -m awt_bonus
```

The slash commands appear in the server within a few seconds. The test data goes
to `var/awt-bonus.db` (git-ignored); delete that file for a fresh start.
Stop the bot with Ctrl+C.

## Who tests

Two or three people, or alt accounts you operate by hand (TS-14). Many checks
need someone else in voice, or someone who isn't in a guild. **Never automate a
real user account** (TS-16): that breaks Discord's Terms of Service.

## Checklist (TS-15)

Tick each item for the milestone being checked, and note anything odd. A wrong
number is a bug, a rule modelled wrong or a catalog error: it becomes a new
scenario or catalog fix.

### Voice and presence

- [ ] Joining and leaving the voice channel: rerunning `/partybonus` shows the
      change.
- [ ] Bots in the channel (e.g. the music bot) are ignored and never listed.
- [ ] `/sitout` leaves you out, with the time it ends; `/sitin` counts you again.
- [ ] Someone in voice with no character is listed under NO CHARACTER SET UP.
- [ ] `channel:` picks another voice channel.

### Replies

- [ ] A plain `/partybonus` is public; `/partybonus private:true` only you see.
- [ ] Every other reply is private: `/mybonus`, `/breakdown`, `/catalog`, and every
      setup command.
- [ ] Long output (a big party's `/breakdown`) is split across messages, with
      nothing cut off and code blocks closed and reopened.
- [ ] Autocomplete works for characters, entries and guilds.
- [ ] `/help` is private and fits in one message, and its last line gives the
      right next step: try it with no character, then after registering one,
      then after `/add` (M6).
- [ ] `/mybonus <character>` for a character that isn't current shows the
      not-current notice, with the `/play` hint only for its own player.

### Roles and guilds (M4)

- [ ] Give yourself a Guild rank role: `/breakdown` shows Support from you, with
      the role name. With two rank roles, both names are shown and Support
      counts once.
- [ ] Role changes: remove the role, and within about a minute Support is gone
      (roles are cached for about 60 s, NF-6).
- [ ] `/guild join <character> Patreon Bonuses` is refused and shows the Patreon link.
- [ ] `/catalog Patreon Bonuses` shows Support, the Support Tiers and the Patreon link.
- [ ] `/add` autocomplete offers a guild's ranks and boons only after
      `/guild join`; typing one in anyway is refused with the join command.
- [ ] `/guild leave` removes that guild's ranks and boons and lists them.

### Secret guild privacy (M4)

- [ ] `/guild join` and `/add` or `/remove` of a Guild of Thieves rank reply
      privately.
- [ ] With two thieves in voice, someone who isn't a member sees only the unnamed
      "secret guild bonus" block in the party `/breakdown`, and no thief's name
      next to it.
- [ ] Each thief's own `/mybonus` shows Rat Pack and Leadership with a count, not
      names; one thief's `/breakdown` of the other thief's character shows the
      unnamed view.
- [ ] `/catalog Guild of Thieves` shows its ranks only to a member.

### Operations

- [ ] A restart mid-game loses nothing: stop and start the bot, and the characters
      and sit-outs are still there.
- [ ] `/request` posts to `#bonus-bot-support` with the player's name (M5). If the
      channel is private, the bot has been added to it (see "Set up once").
- [ ] A catalog change pushed to `main` is deployed automatically (M5).
