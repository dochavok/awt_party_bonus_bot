---
reviewed: 2026-09-29
---

# Using Bogsy's dice bot

The bonus bot doesn't roll dice, but `/bogsy` turns your **current character's** party
bonuses into commands for Bogsy's dice bot, so your rolls include them.

## Each game

Run `/bogsy` once the party's in the voice channel, then **paste each line into Discord
one at a time** (Discord runs one command per message):

--8<-- "bogsy.md"

- **CM and CR** are your party bonus totals.
- **Each kind of CR** (`bonus_fear`, `bonus_stealth`…) holds only the **extra on top of
  CR**, because Bogsy adds modifiers together when rolling.
- **Every stat is always listed**, even at 0, so nothing is left over from an earlier
  game.
- Only roll stats are included. Combat notes (hearts), effects and conditional bonuses
  aren't: apply those as usual.

Run it again if people join or leave. Sitting out, or not in a voice channel? Every
value is 0, and the reply says why.

To use another of your characters, choose it with `/play` first.

## Set up once

The reply ends with the quickroll commands to set up once. Your own bonuses stay in
your own Bogsy modifiers (such as `my_cm` and `my_fear`); `/bogsy` never touches those,
so a roll adds both.

For one kind of CR, add its modifiers when you roll, e.g.
`/roll command:challenge+my_fear+bonus_fear`. Bogsy's quickrolls can't include other
quickrolls, so that part is typed each time.
