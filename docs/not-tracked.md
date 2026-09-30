---
reviewed: 2026-09-30
---

# What the bot doesn't track

The bot only adds up **always-on bonuses that one character gives to others**. If a
bonus you expected isn't in your totals, it's probably one of these.

## Your own bonuses

A bonus that only helps its own character, like a title's bonus to its holder, is part
of **your character's own** CM or CR, which you track yourself. The bot's totals are
party bonuses to add on top.

Some cards give both: Hero of Passion gives its holder +3 CM (yours to track) and other
Hero of Passion holders +1 CM (tracked by the bot).

The exception is a bonus to its holder that grows with how many items of a class the
**party** is using, like Will Passions Adventure Token. It depends on who else is
present, so the bot counts it. See
[How bonuses are counted](counting.md#some-bonuses-grow-with-the-partys-items-of-a-class).

## Which items you're wearing

The bot doesn't know what your character owns or wears. For item classes, like
passion items, it only knows **how many** your character is using, which you set with
`/character items`. Whether an item belongs to a class, and whether it's in use, is
your call.

## Abilities you use, rather than always-on bonuses

Abilities used once per combat, per day or per weekend, Tasks, and one-off abilities
like Bard Inspiration aren't tracked. Nor are the buffs and heals a character casts,
so Helping Hands doesn't change the bot's numbers.

## Position

The bot doesn't know who is in melee or ranged. Bonuses that depend on position, like
Commanding Presence's "allies in the same range", are listed as **conditional
bonuses**, never in the totals. Add them yourself when they apply.

## Minions, summons and companions

Only player characters give or receive bonuses. Minions, summons, animal companions and
allied NPCs aren't counted.

## Anything not in the catalog

Players can't type in their own bonuses: everything comes from the catalog, so everyone
uses the same names and values. If your character has something that isn't there, ask
for it with `/request`. See
[Setting up your character](setup.md#something-missing-or-wrong).

## Dice

The bot doesn't roll dice. It can hand your party bonuses to Bogsy's dice bot, though:
see [Using Bogsy's dice bot](bogsy.md).
