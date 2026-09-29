---
reviewed: 2026-09-29
---

# Guilds and Support

## Joining a guild

A guild here means any group a character can belong to: a guild, order, cult or
coalition.

```
/guild join character:Thessaly guild:Cult of the Dragon
```

Joining **records membership and nothing else**. It decides which guild-only bonuses
your character can receive. The bonuses your character **gives** come from the rank or
boons they've earned, which you add by name:

```
/add character:Thessaly entry:High Inquisitor
```

- **Ranks and boons need membership.** The bot refuses a guild's rank or boon for a
  character who isn't in the guild, and tells you how to join.
- **Your rank isn't checked.** Add the rank you've earned; the DMs can see it in
  `/breakdown`.
- **A higher rank replaces the lower ones**, so only the highest counts.
- **Some ranks give several abilities**, each with its own rules.
- **Only ranks that give a party bonus are in the catalog.** Ranks that don't aren't
  listed, and there's no need to record them.
- **Leaving a guild removes its ranks and boons** from your character, and the bot tells
  you what it removed.

`/catalog` shows a guild's ranks and boons once your character has joined it. Other
guilds are listed by name with the command to join.

## One holder at a time

Some ranks and titles can only be held by **one character on the server at a time**,
such as High Inquisitor and Champion of Power. If someone else holds it, the bot says
who:

--8<-- "refused-one-holder.md"

The title passes on when its holder removes it, or leaves the guild for a guild rank.
If the holder can't or won't, ask with `/request`, and the maintainer will sort it out.

## Support from your Discord role

**Support** comes from your Discord role, not from joining a guild. If you have any of
the Guild rank roles, **Junior Adventurer, Guild Veteran, Guild Vanguard, Guild
Champion or Guild Legend**, you give +2 CM to your allies, once, whichever role you
have. There's nothing to add.

Support counts for whichever character you're playing. It counts even if you haven't
set up a character yet. Guild rank roles come from the AWT Patreon; `/catalog Patreon
Bonuses` shows the details.

## Secret guilds { #secret-guilds }

The Guild of Thieves' rules say never to reveal another member, so the bot keeps it
secret, in a tongue-in-cheek way:

- Joining or leaving, and adding or removing its ranks, **always reply privately**.
- The bot **never names a secret guild's members**, anywhere.
- Secret guild bonuses **are still in everyone's totals**, including the public
  `/partybonus`.
- In `/breakdown`, they're shown as one unnamed *secret guild bonus*, with no givers.

Members looking at **their own** character see the secret bonuses in detail, with how
many members contributed, but still not who:

--8<-- "mybonus-secret-member.md"

Looking at anyone else's character, even a fellow member's, shows the unnamed view, so
members don't learn who the other members are.

The secrecy isn't airtight: sharp-eyed players may spot members from their stealth
totals. That's part of the joke.
