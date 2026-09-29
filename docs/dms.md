---
reviewed: 2026-09-29
---

# Running a game with the bot

To the bot, a DM is a player like any other: there are no DM or admin commands, and
nobody can change another player's characters. Here's how the bot fits into running a
game.

## Before the game

- **Use `/sitout`** once you're in the voice channel, so your own character isn't
  counted. It lasts 12 hours. Anyone just listening in should do the same.
- **Ask the players to check they're playing the right character**, with `/play` if they
  have more than one.
- **Post the totals** with `/partybonus` once everyone's in, so the whole party sees
  them. Run it again when people join or leave.

## During the game

- **Conditional bonuses aren't in the totals.** The bot doesn't know who is in melee or
  ranged, so bonuses like Commanding Presence's "allies in the same range" are listed
  separately. Rule on them as usual.
- **Some things aren't tracked at all**: once-per-combat and daily abilities, buffs and
  heals, summons and companions, and each character's own bonuses. See
  [What the bot doesn't track](not-tracked.md).

## Checking the numbers

`/breakdown` shows every bonus in play, who gives it, and how each character's totals
add up. Only you see the reply, so you can check it quietly during the game.

Things worth a glance:

- **Ranks and titles**: the bot doesn't check which rank a player has earned, only
  that the character is in the guild.
- **Levels**, for level-based bonuses: the breakdown for one character shows when the
  level was last updated.
- **Anything unexpected**: an item nobody mentioned, or a bonus that seems too high.

Secret guild bonuses show as one unnamed block. The bot never names a secret guild's
members, not even to the DM.

## Fixing mistakes

- **A player's character is wrong?** Ask the player to fix it: only they can change it,
  with `/add`, `/remove`, `/guild` or `/character level`.
- **The catalog is wrong or missing something?** Report it with `/request`, or ask the
  player to.
- **A rule looks wrong?** Tell the maintainer. The bot's rules come from the DMs'
  rulings, and a new ruling can change them.
