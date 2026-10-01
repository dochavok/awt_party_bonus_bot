---
reviewed: 2026-09-30
---

# Setting up your character

You do this once per character. After that, the bot remembers everything, and you only
update it when something changes: a new skill, a lost item, a level-up.

!!! tip "Not sure what to do next?"
    Type `/help` in Discord. It ends with your own next step, worked out from what
    you've set up so far.

## 1. Register your character

```
/character register name:Thessaly level:18
```

- **Names are unique on the server**, ignoring upper and lower case. If the name is
  taken, the bot suggests a variant.
- **The level is optional.** Only level-based bonuses use it; today that's the Cult of
  the Dragon. If your character is in the Cult, add the level, or they'll miss the
  bonus. You can set it later with `/character level`.
- **Your first character is chosen automatically** as the one you're playing. If you
  have more than one, choose with `/play` before the game.

Only you can change your characters. Nobody else can edit them, and nobody needs to
approve them.

## 2. Join your guilds

If your character belongs to a guild, order, cult or coalition, record it:

```
/guild join character:Thessaly guild:Cult of the Dragon
```

**Joining gives nothing by itself.** A guild's bonuses come from the rank or boons your
character has earned, which you add in the next step. The bot tells you when a guild
has ranks to add:

--8<-- "guild-join.md"

**Support comes from your Discord role, not from a guild.** If you have Junior
Adventurer or above, the bot counts your Support automatically; there's nothing to add.
See [Guilds and Support](guilds.md).

## 3. Add what your character has

Add each skill, guild rank, boon, item and title that gives a party bonus:

```
/add character:Thessaly entry:High Inquisitor
/add character:Thessaly entry:Will's Ward Stone
```

- **Autocomplete shows what's available**, labeled with where it comes from, e.g.
  *Holy Aura (Holy Knight skill)*.
- **Guild ranks and boons only appear once your character has joined the guild.**
- **Add your rank, not every rank below it.** A higher rank replaces the lower ones, so
  adding both does no harm, but only the higher one counts.
- **Missing a title? It may have no party bonus.** To keep the catalog trim, we've
  chosen not to list titles that never change anyone's totals. There's nothing to add
  for them.

To see what an entry gives before adding it, and the exact `/add` command for it:

```
/catalog entry:Holy Aura
```

`/catalog` on its own lists everything you can add.

## 4. Record the item classes you're using

Some items give a bonus only to characters **using** an item of a class, such as
Will Passion's Pendant for passion items, or one that grows with how many the party is
using, such as Will Passions Adventure Token. The bot doesn't track which items you
have, only **how many items of each class your character has in use**:

```
/character items character:Brannoc class:passion count:2
```

--8<-- "character-items.md"

- **Count what you're using, not what you own.** An item in your bag doesn't count.
- **You decide what belongs to a class.** An item's class isn't always in its name or
  card. `/catalog entry:passion` describes each class and lists the bonuses that depend
  on it.
- **Other names work too:** *hotdog* finds the glizzy class.
- **0 clears a count.** A class you haven't set counts as 0.
- **Keep it current.** Change it whenever you stop or start using one.

Skip this step if your character doesn't use items of a class. If you miss a bonus
because of a count of 0, `/mybonus` tells you.

## Something missing or wrong?

The catalog is a fixed list kept by the maintainer, so every character uses the same
names and values. If your character has something that isn't there, or an entry's value
is wrong, **ask for it with `/request`**:

```
/request text:Thessaly has the Amulet of Ember (+2 CR vs fear to allies), card attached in #loot
```

Your request is posted, with your name, to the channel the maintainer watches. Say
which character has it and what the card says; a link to the card helps. Once it's
added to the catalog, you add it to your character with `/add` as usual.

Use `/request` for anything else the bot can't do itself, too, such as removing a
character you no longer need.

## Keeping it up to date

| When… | Use |
|---|---|
| Your character levels up | `/character level character:Thessaly level:19` |
| You lose or give away an item | `/remove character:Thessaly entry:Will's Ward Stone` |
| You start or stop using an item of a class | `/character items character:Thessaly class:passion count:1` |
| You leave a guild (its ranks and boons go too) | `/guild leave character:Thessaly guild:Cult of the Dragon` |
| You spot a typo in a name | `/character rename character:Thesaly new:Thessaly` |
| You want to play another of your characters | `/play character:Ysolde` |
| You want to see your characters | `/character list` |

Characters can't be deleted, so nothing is lost by accident. One you no longer play
simply isn't chosen with `/play`, and counts for nothing.
