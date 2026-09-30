---
reviewed: 2026-09-30
---

# Commands

Every command the bot has. Everyone has the same commands: there are no DM or admin
commands. You can only change your own characters.

Type `/` in Discord and start typing a command's name; Discord shows its options, and
autocomplete suggests your characters, catalog entries and guilds as you type.

**Who sees the reply:** `/partybonus` posts for everyone in the channel, unless you add
`private:true`. Every other command replies privately: only you see it.

The command names, options and descriptions on this page are generated from the bot
itself, so they always match what Discord shows.

## Game night

<!-- BEGIN GENERATED: /partybonus -->
### `/partybonus`

Party bonus totals for your voice channel

| Option | Required | What it's for |
|---|---|---|
| `channel` | no | Another voice channel |
| `private` | no | Only you see the reply |

<!-- END GENERATED: /partybonus -->

Everyone's totals, for the voice channel you're in. **Everyone sees the reply**, unless
you add `private:true`. People joining or leaving? Just run it again.

```
/partybonus
/partybonus private:true
```
See [Reading the results](results.md#partybonus) for what each part means.

<!-- BEGIN GENERATED: /mybonus -->
### `/mybonus`

The totals for one of your characters

| Option | Required | What it's for |
|---|---|---|
| `character` | no | Any character (your current one if left out) |

<!-- END GENERATED: /mybonus -->

Your totals, or any character's. **Only you see the reply.**

```
/mybonus
/mybonus character:Wren
```

<!-- BEGIN GENERATED: /breakdown -->
### `/breakdown`

How the totals are worked out

| Option | Required | What it's for |
|---|---|---|
| `character` | no | One character (the whole party if left out) |
| `channel` | no | Another voice channel |

<!-- END GENERATED: /breakdown -->

How every total was worked out: who gives what, and to whom. With a character, just
that character's totals, what they don't receive and why, and what they give.
**Only you see the reply.**

```
/breakdown
/breakdown character:Thessaly
```

<!-- BEGIN GENERATED: /play -->
### `/play`

Choose the character you're playing

| Option | Required | What it's for |
|---|---|---|
| `character` | yes | One of your characters |

<!-- END GENERATED: /play -->

Choose which of your characters you're playing. It stays until you change it. Your
first character is chosen automatically, so you only need this if you have more than
one. **Only you see the reply.**

```
/play character:Ysolde
```

<!-- BEGIN GENERATED: /sitout -->
### `/sitout`

Don't count me for 12 hours

No options.

<!-- END GENERATED: /sitout -->

Running the game, or just watching? Sit out so you're not counted. It ends by itself
after 12 hours. **Only you see the reply.**

```
/sitout
```

<!-- BEGIN GENERATED: /sitin -->
### `/sitin`

Count me again

No options.

<!-- END GENERATED: /sitin -->

Ends your sit-out early. **Only you see the reply.**

```
/sitin
```

<!-- BEGIN GENERATED: /bogsy -->
### `/bogsy`

Your party bonuses as Bogsy dice-bot modifiers

No options.

<!-- END GENERATED: /bogsy -->

Your current character's party bonuses as commands for Bogsy's dice bot, ready to paste.
See [Using Bogsy's dice bot](bogsy.md). **Only you see the reply.**

```
/bogsy
```

## Setting up your characters

<!-- BEGIN GENERATED: /character register -->
### `/character register`

Register a new character

| Option | Required | What it's for |
|---|---|---|
| `name` | yes | Unique on the server |
| `level` | no | Optional: only level-based bonuses use it |

<!-- END GENERATED: /character register -->

Adds a character. Names are unique on the server, ignoring case. The level is
optional: only level-based bonuses (the Cult of the Dragon) use it.
**Only you see the reply.**

```
/character register name:Thessaly level:18
```

<!-- BEGIN GENERATED: /character list -->
### `/character list`

Your characters

No options.

<!-- END GENERATED: /character list -->

Your characters, which one you're playing, and the item classes each has in use.
**Only you see the reply.**

```
/character list
```

<!-- BEGIN GENERATED: /character rename -->
### `/character rename`

Rename one of your characters

| Option | Required | What it's for |
|---|---|---|
| `character` | yes | One of your characters |
| `new` | yes | The new name |

<!-- END GENERATED: /character rename -->

Fixes a typo or changes a name. Characters can't be deleted; if one really needs
removing, ask with `/request`. **Only you see the reply.**

```
/character rename character:Thesaly new:Thessaly
```

<!-- BEGIN GENERATED: /character level -->
### `/character level`

Set a character's level, or clear it

| Option | Required | What it's for |
|---|---|---|
| `character` | yes | One of your characters |
| `level` | yes | A level, or clear |

<!-- END GENERATED: /character level -->

Sets a character's level, or `clear` to remove it. **Only you see the reply.**

```
/character level character:Thessaly level:19
/character level character:Thessaly level:clear
```

<!-- BEGIN GENERATED: /character items -->
### `/character items`

How many items of a class a character has in use

| Option | Required | What it's for |
|---|---|---|
| `character` | yes | One of your characters |
| `item_class` | yes | An item class, e.g. passion or glizzy |
| `count` | yes | How many are in use, from 0 to 30 (0 clears it) |

<!-- END GENERATED: /character items -->

Sets how many items of a class (e.g. passion or glizzy) the character is **using**, not
how many it owns, from 0 to 30; 0 clears it. Some items give a bonus only to characters
using an item of a class, or one that grows with how many the party is using. Change it
whenever you stop or start using one. The class autocompletes, and other names work too
(*hotdog* finds glizzy). **Only you see the reply.**

```
/character items character:Thessaly class:passion count:2
/character items character:Thessaly class:passion count:0
```

<!-- BEGIN GENERATED: /guild join -->
### `/guild join`

A character joins a guild

| Option | Required | What it's for |
|---|---|---|
| `character` | yes | One of your characters |
| `guild` | yes | The guild to join |

<!-- END GENERATED: /guild join -->

Records that a character is in a guild. Joining gives nothing by itself: add the
character's rank or boons next, with `/add`. **Only you see the reply.**

```
/guild join character:Thessaly guild:Cult of the Dragon
```

<!-- BEGIN GENERATED: /guild leave -->
### `/guild leave`

A character leaves a guild

| Option | Required | What it's for |
|---|---|---|
| `character` | yes | One of your characters |
| `guild` | yes | The guild to leave (removes its ranks and boons) |

<!-- END GENERATED: /guild leave -->

Takes a character out of a guild, and removes their ranks and boons from it.
**Only you see the reply.**

```
/guild leave character:Thessaly guild:Cult of the Dragon
```

<!-- BEGIN GENERATED: /add -->
### `/add`

Give your character a skill, boon, rank, item or title

| Option | Required | What it's for |
|---|---|---|
| `character` | yes | One of your characters |
| `entry` | yes | What it has, from the catalog |

<!-- END GENERATED: /add -->

Gives a character a skill, boon, rank, item or title from the catalog. Autocomplete
shows what's available; guild ranks and boons appear once the character has joined the
guild. **Only you see the reply.**

```
/add character:Thessaly entry:Will's Ward Stone
```

<!-- BEGIN GENERATED: /remove -->
### `/remove`

Take something away from your character

| Option | Required | What it's for |
|---|---|---|
| `character` | yes | One of your characters |
| `entry` | yes | Something it has |

<!-- END GENERATED: /remove -->

Takes something away from a character, e.g. an item that was lost or given away.
**Only you see the reply.**

```
/remove character:Thessaly entry:Will's Ward Stone
```

<!-- BEGIN GENERATED: /catalog -->
### `/catalog`

What an entry, guild or item class gives, or everything

| Option | Required | What it's for |
|---|---|---|
| `entry` | no | An entry, guild or item class (everything if left out) |

<!-- END GENERATED: /catalog -->

What an entry or guild gives, with its card text and the `/add` command for it. For an
item class, what belongs to it, its other names, and the bonuses that depend on it. On
its own, lists everything you can add. **Only you see the reply.**

```
/catalog
/catalog entry:Holy Aura
/catalog entry:passion
```

<!-- BEGIN GENERATED: /request -->
### `/request`

Ask the maintainer to add or fix something

| Option | Required | What it's for |
|---|---|---|
| `text` | yes | What's missing or wrong, or what you need |

<!-- END GENERATED: /request -->

Something your character has isn't in the catalog, or something's wrong? Ask for it
here. Your request is posted to the maintainer's channel, with your name.
**Only you see the reply.**

```
/request text:Thessaly has the Amulet of Ember (+2 CR vs fear to allies), card attached in #loot
```

## Getting started

<!-- BEGIN GENERATED: /help -->
### `/help`

How to set up and play, and your next step

No options.

<!-- END GENERATED: /help -->

A short guide to getting started, ending with your own next step. **Only you see the
reply.**

```
/help
```
