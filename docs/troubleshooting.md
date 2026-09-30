---
reviewed: 2026-09-30
---

# Troubleshooting

## The bot said no

### "The name … is taken"

--8<-- "refused-name-taken.md"

Character names are unique on the whole server, ignoring upper and lower case, so a
name always means one character. Pick a variant.

### "… isn't a member. Join first"

--8<-- "refused-join-first.md"

Guild ranks and boons need the character to be in the guild. Run the `/guild join`
command the bot gives you, then `/add` again.

### "… is held by …"

--8<-- "refused-one-holder.md"

Some ranks and titles can only be held by one character at a time. The holder can
`/remove` it; if they can't or won't, ask with `/request`. See
[Guilds and Support](guilds.md#one-holder-at-a-time).

### "There's no item class called …"

The class isn't in the catalog. The reply lists the classes there are, with their
other names (*hotdog* finds glizzy). If your item belongs to a class that isn't listed,
ask for it with `/request`.

### "Give a count from 0 to 30"

`/character items` takes how many items of the class your character is **using**,
from 0 to 30. 0 clears it.

### A warning about Devotion III

Devotion III adds +1 to your character's auras. If your character has no auras, it does
nothing, and the bot warns you. It's still added.

## My numbers look wrong

Start with `/breakdown character:<your character>`. It lists every bonus your character
receives and who from, and everything they **don't** receive, with the reason.

### My character isn't in `/partybonus`

- **Are you in the voice channel?** Only people in it are counted.
- **Are you sitting out?** Check the *Not counted* line. `/sitin` ends it.
- **Are you under *NO CHARACTER SET UP*?** Register a character, or choose one with
  `/play`.
- **Is a different character of yours in the table?** Choose tonight's with `/play`.

### A bonus I give isn't in my own totals

Bonuses go to allies, not the giver, unless the ability says otherwise. See
[How bonuses are counted](counting.md#bonuses-go-to-allies-not-the-giver).

### A bonus I expected is missing

- **Conditional bonuses** ("allies in the same range") are listed separately, never in
  the totals. Add them yourself when they apply.
- **It may not be tracked**: your own bonuses, once-per-combat abilities, summons. See
  [What the bot doesn't track](not-tracked.md).
- **It may be for guild members, or other holders, only.** `/breakdown` says so under
  *NOT APPLIED*.
- **It may depend on your level.** If `/mybonus` says *level not recorded*, set it with
  `/character level`.
- **It may need an item of a class in use.** See the next section.
- **It may not stack**, so two givers count once.

### "… needs a passion item in use"

--8<-- "mybonus-item-class.md"

Some bonuses go only to characters using an item of a class, such as passion items for
Aura of Passion. Your character has none recorded, so it doesn't get the bonus. If
you're using one, set how many with the `/character items` command in the note. If
you aren't, there's nothing to do. A bonus that grows with the party's count says
*has no … items in use in the party* instead. See
[How bonuses are counted](counting.md#some-bonuses-need-an-item-of-a-class-in-use).

### The totals show a character I'm not playing

--8<-- "mybonus-not-current.md"

Looking at a character who isn't being played shows them **in place of** the character
that is. Use `/play` to switch.

### I can't find something in `/add`

- **Guild ranks and boons** only appear once your character has joined the guild.
- **Not in the catalog?** Ask for it with `/request`. See
  [Setting up your character](setup.md#something-missing-or-wrong).

### The numbers are still wrong

Ask your DM to look at the party `/breakdown` with you. If an entry's value is wrong in
the catalog, report it with `/request`.

## Other questions

### Can I delete a character?

No: characters can't be deleted, so nothing is lost by accident. Rename it, or simply
don't play it. If it really needs removing, ask with `/request`.

### Can someone else change my character?

No. Only the player who registered a character can change it. Anyone can **look** at
any character's totals.
