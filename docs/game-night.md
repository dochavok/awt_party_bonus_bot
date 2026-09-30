---
reviewed: 2026-09-29
---

# Game night

There's nothing to start or end. The bot counts **everyone in the voice channel** at
the moment a command runs.

## Before the game

- **Join the voice channel.** You're counted with the character you're playing.
- **More than one character?** Choose tonight's with `/play character:<name>`. It stays
  chosen until you change it.
- **Running the game, or just listening in?** Use `/sitout`, so your character's bonuses
  aren't counted and you don't appear in the table. It lasts 12 hours; `/sitin` ends it
  early. Remembering to sit out is up to you: the bot doesn't guess.

## During the game

| To see… | Use | Who sees it |
|---|---|---|
| Everyone's totals | `/partybonus` | Everyone in the channel |
| Everyone's totals, quietly | `/partybonus private:true` | Only you |
| Your own totals | `/mybonus` | Only you |
| How the totals were worked out | `/breakdown` | Only you |
| One character's working | `/breakdown character:Wren` | Only you |
| Your bonuses for Bogsy's dice bot | `/bogsy` | Only you |

**People joining or leaving? Just run the command again.** The answer is always worked
out fresh from who's in the channel right now.

The bot's totals are **party bonuses only**: what other characters give yours. Add them
to your character's own bonuses, which you track yourself as usual.

See [Reading the results](results.md) for what each reply means.

## Who is counted

- Everyone in the voice channel, with the character they're playing.
- **Not** anyone who has used `/sitout` in the last 12 hours. They're listed at the end
  of `/partybonus` as *not counted*, with the time their sit-out ends.
- **Not** bots, such as a music bot.
- Someone **without a character** is still counted, under their Discord name. They
  receive bonuses, and give Support if their Discord role includes it, and they're
  listed under *NO CHARACTER SET UP* with how to fix it.

Using a voice channel other than the one you're in? Add `channel:` to `/partybonus` or
`/breakdown`.
