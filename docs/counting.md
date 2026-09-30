---
reviewed: 2026-09-30
---

# How bonuses are counted

The bot follows the same rules you'd use adding bonuses up by hand. This page explains
each one. The examples use the sample party from [Reading the results](results.md).

## Every giver counts

If three characters each give +2 CM, the bonus counts three times, even when it's the
same skill. Two Holy Knights with Holy Aura give +4 CR vs fear.

## Bonuses go to allies, not the giver

A bonus never applies to the character who gives it. If three characters each give
+2 CM, each of them receives +4 (from the other two), and everyone else receives +6.

**Unless the ability says otherwise.** A few abilities say "all members" or "you and
your allies", so the giver benefits too: Leadership, King of the Pirates, Wilderness
Lore and Proper Seasoning, and some items and titles. `/catalog` shows who each entry
gives to.

## Some bonuses don't stack

A bonus marked *doesn't stack* counts **once** for each character, however many givers
are present. If the givers' amounts differ, the highest counts. Two Commanders with
Inspiring Presence give allies +5 CR, not +10.

## Better versions replace lesser ones

When a character has an entry and the entry that replaces it, only the replacement
counts. A GoTH member with Nuyaru's Love (+1 CM) and Seraph's Affection (+3 CM) gives
+3. A higher guild rank replaces the lower ones the same way.

## Modifiers change your own bonuses

A few entries don't give a bonus themselves; they change what the **same character**
gives. **Devotion III** adds +1 to each of that character's auras, from any skill tree
(Holy Aura, Bolstering Aura, Aura of Defense, Aura of Hope). Only skills named "Aura"
are auras: items aren't, even if their card mentions an aura.

**Helping Hands** doesn't change party bonuses. It raises the buffs and heals its holder
casts, which the bot doesn't track, not auras or other always-on bonuses.

## CR includes every kind of CR

A bonus to all challenge rolls also counts toward each kind of CR. With +5 CR and +3 CR
vs fear, you get CR +5 and CR vs fear +8. The same goes for *stealth*, *escape* and
*would hurt*.

## Who can receive a bonus

Most bonuses go to the whole party. Some go only to:

- **members of one guild**, e.g. Rat Pack goes only to Guild of Thieves members;
- **other holders of the same entry**, e.g. Hero of Passion goes only to other Hero of
  Passion holders.

## Some bonuses depend on level

A bonus can depend on the **receiving** character's level. The Cult of the Dragon's
High Inquisitor gives other Cult members +1 heart of damage below level 10, and +10 CM
at level 10 or higher. A character with no level recorded doesn't get it, and `/mybonus`
tells them.

## Some bonuses need an item of a class in use

Some items give a bonus only to characters **using** at least one item of a class
(what each character records with `/character items`). Will Passion's Pendant gives
Aura of Passion, +2 hearts of damage, to each ally with a passion item in use. Glizzy
from God gives +5 hearts of damage and +3 CM to each character with a glizzy item in
use, its holder included. A character with none in use doesn't get it, and
`/breakdown` says so, e.g. *no passion item in use*. More items of the class don't
multiply it: one is enough. Otherwise these follow every other rule.

## Some bonuses grow with the party's items of a class

Will Passions Adventure Token gives **its holder** +2 CM and +1 heart of damage for
each passion item in use across the party, the holder's own included. With the holder
using 1 and another character using 2, the holder gets +6 CM and +3 hearts of damage.
Only counted characters add to the count: anyone sitting out, or not in the voice
channel, adds nothing. With no passion items in use in the party, the holder gets
nothing, and `/breakdown` says so.

## Conditional bonuses are never in the totals

The bot doesn't know who is in melee or ranged. A bonus that depends on that, like
Commanding Presence's "allies in the same range", is listed separately, under
*CONDITIONAL BONUSES*, and never added to the totals, so the totals are never too high.
Add it yourself when it applies.

## Only people who are counted give or receive

Anyone sitting out, like the DM running the game, gives and receives nothing. Someone
in the channel without a character still receives bonuses, but gives only Support from
their Discord role.

## Totals first, detail on request

`/partybonus` and `/mybonus` show totals only. `/breakdown` shows every contribution and
how each total adds up.

## A worked example: Support

Every player with Junior Adventurer or above gives +2 CM to allies. With five of them
present, the other characters get +10, and each of the five gets +8 (from the other
four).
