---
reviewed: 2026-09-29
---

# Reading the results

Every example on this page is real output from the bot, for a sample party of six
players in the *Game Night* voice channel: Brannoc, Wren, Thessaly, Osk and Pell, plus
Quinn, who hasn't set up a character yet. Sam is running the game and has used
`/sitout`.

!!! note "Times"
    Discord shows times in your own time zone. The examples show them in GMT.

## `/partybonus` { #partybonus }

Everyone's totals, posted for the whole party:

--8<-- "partybonus.md"

Reading it from the top:

- **The table** has each counted character's totals for the roll stats: **CM** (combat
  modifier) and **CR** (challenge roll), plus the kinds of CR that some character gets
  extra for, like *CR vs fear*. A kind of CR always includes the plain CR bonus: Osk's
  CR vs fear of +8 is the +5 CR plus +3 more for fear.
- **COMBAT NOTES** are bonuses measured in hearts: extra damage, damage reduction and
  healing.
- **EFFECTS** (when there are any) are benefits without a number, such as a resistance.
- **CONDITIONAL BONUSES** only apply in a situation the bot can't see, such as "allies
  in the same range". They're **never included in the totals**: add them yourself when
  they apply.
- **NO CHARACTER SET UP** lists anyone in the channel without a character, with how to
  fix it. They still receive bonuses, but the `*` means the only bonus they give is
  Support from their Discord role, if they have it.
- **Not counted** lists who in the channel is sitting out, and until when.

## `/mybonus` { #mybonus }

Your own totals, just for you. Only the kinds of CR that differ from your CR are shown.

--8<-- "mybonus.md"

### If your level isn't recorded

A character without a level misses level-based bonuses, and `/mybonus` says so. Pell is
in the Cult of the Dragon but has no level recorded:

--8<-- "mybonus-no-level.md"

### If you're looking at a character you're not playing

The totals show that character **in place of** the one you're playing, as if you'd
switched. Casey is playing Thessaly and looks at Ysolde:

--8<-- "mybonus-not-current.md"

### If you're not in a voice channel

There's no party, so there are no totals, but you still see what your character gives:

--8<-- "mybonus-not-in-voice.md"

## `/breakdown` { #breakdown }

How every total was worked out. For each bonus in play: what it gives, to whom, and who
gives it. Then each character's working, e.g. `CM 2+5 = +7`.

--8<-- "breakdown-party.md"

A few things to notice:

- **Seraph's Affection replaces Nuyaru's Love.** Brannoc has both, but only the better
  one counts.
- **Inspiring Presence doesn't stack.** However many characters have it, allies get +5
  CR once.
- **Holy Aura is +3, not +2.** Brannoc's Devotion III adds +1 to each of Brannoc's
  auras.
- **The secret guild bonus** has no names. The bot never reveals who is in a secret
  guild. An `s` in the working marks the secret amounts. See
  [Guilds and Support](guilds.md#secret-guilds).

## `/breakdown` for one character { #breakdown-character }

Every bonus that character receives, and who from; what they **don't** receive, and
why; and what they give.

--8<-- "breakdown-character.md"

Thessaly doesn't receive the Cult of the Dragon bonus or Will's Ward Stone, because
Thessaly is the one giving them: bonuses go to **allies**, not to the giver. See
[How bonuses are counted](counting.md).
