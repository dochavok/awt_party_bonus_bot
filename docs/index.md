---
reviewed: 2026-09-29
---

# AWT Party Bonus Bot

Working out party bonuses by hand is slow and easy to get wrong. This Discord bot does
it for games at **Adventures from the Wizards Tower**.

You record what your character **has**: skills, guilds, ranks, boons, items and titles,
picked from a fixed catalog. On game night, the bot looks at who's in the voice channel
and adds up the bonuses each character receives from everyone else.

## Get set up in three steps

You only do this once per character. In Discord, `/help` shows the same steps and tells
you your own next step.

1. **Register your character.** The level is optional; only level-based bonuses use it.

    ```
    /character register name:Thessaly level:18
    ```

2. **Join your guilds**, if your character is in any.

    ```
    /guild join character:Thessaly guild:Cult of the Dragon
    ```

3. **Add what your character has.** Autocomplete shows what's available.

    ```
    /add character:Thessaly entry:High Inquisitor
    /add character:Thessaly entry:Will's Ward Stone
    ```

Something your character has isn't in the list? Ask for it with `/request`. See
[Setting up your character](setup.md) for the details.

## On game night

Join the voice channel: that's all. Everyone in it is counted.

- `/partybonus` posts everyone's totals for the party.
- `/mybonus` shows your own totals, just to you.
- `/breakdown` shows how the totals were worked out.

Running the game or just watching? Use `/sitout` so you're not counted. See
[Game night](game-night.md).

## Need help?

- Something missing or wrong in the catalog, or something the bot can't do itself?
  Use `/request` in Discord.
- Numbers look wrong? Check [Troubleshooting](troubleshooting.md), then ask your DM to
  look at the `/breakdown`.
