# AWT Party Bonus Bot: Requirements

**Version:** 0.6 (draft)
**Date:** 2026-09-25
**Owner:** Craig
**Server:** Adventures from the Wizards Tower (AWT)
**Related:** [dm-rule-questions.md](dm-rule-questions.md) (rule questions waiting on the DMs)

---

## 1. Purpose

Working out party bonuses by hand is slow and easy to get wrong. Someone has to know every character's bonuses, drop the ones whose characters aren't in the game, and add up the rest for each character.

This bot does that work. Every skill, guild ability, item and award that gives a party bonus is defined once, in a **fixed catalog** kept in the bot's repository. Players record what their characters **have** (their skills, guilds and items) by picking from the catalog. When someone asks, the bot works out totals from the characters who are present:

- `/partybonus`: the totals every present character receives.
- `/mybonus [character]`: the totals for one of your characters.
- `/breakdown [character]`: every bonus in play, who contributes it, and how each total adds up.

Games happen in a Discord voice channel. There's no session to start or end: the bot counts everyone who is in the voice channel when the command runs. Anyone running the game or just watching uses `/sitout`, which lasts 12 hours, to be left out. When someone joins or leaves, running the command again gives an up-to-date answer.

## 2. Scope

### Goals

- Any player can see their character's current totals, and how they were calculated if they want the detail.
- The game's rules are applied correctly: every giver counts, bonuses go to **allies** (not the giver) unless the catalog says otherwise, and stacking, rank and level conditions are respected.
- Players enter their own data by picking from the catalog. Nobody else enters or approves anything.
- The catalog is uniform: one definition of each skill, guild and item, so there are no duplicates or typos.

### Non-Goals

- **No dice rolling.** At most, the bot hands CM/CR values to an existing dice bot (section 14).
- **No character sheets.** Each character has a name, an optional level, guild memberships with rank, and catalog entries. Nothing more. The bot doesn't track class.
- **Only always-on bonuses to others.** Abilities used once per combat, day or weekend, Tasks, and repeatable one-off abilities (e.g. Bard Inspiration) aren't tracked.
- **No self-only bonuses.** A bonus that only helps its own character is part of that character's own CM or CR, which the player tracks. The bot's totals are added on top.
- **No bonuses typed in by players.** Everything comes from the catalog. Anything missing is requested with `/request` and added to the catalog.
- **Characters only.** Minions, summons, animal companions and allied NPCs (e.g. a Worldshaper's golem made an ally by Endowment) neither give nor receive party bonuses in the bot.
- **No positioning or range.** If a character is present, their bonuses apply. Distance and positioning are up to the DM.
- **One server only** (AWT).
- No web dashboard.

## 3. Glossary

| Term | Meaning |
|---|---|
| **Player** | A Discord member. Can have several characters. |
| **DM** | Dungeon Master. Runs games and rules on conditions. Has no special permissions in the bot. |
| **Maintainer** | Whoever edits the catalog in the repository (Craig at launch). |
| **Character** | One of a player's AWT characters. |
| **Level** | Optional, per character. Only used for level-based bonuses (today, just the Cult of the Dragon). |
| **Stat** | What a bonus adds to. **Roll stats:** CM (combat modifier, attack and defence combined), CR (challenge roll) and CR subtypes (*vs fear*, *stealth*, *would hurt*). **Combat notes:** damage, damage reduction, healing, measured in hearts. |
| **Catalog** | The fixed list of stats, skills, guilds and items/awards, kept as data files in the repository (section 6.2). |
| **Entry** | One thing in the catalog that a character can have: a **skill** (from a skill tree), a **boon** (e.g. a GoTH quest boon), an **item** (e.g. Wills ward stone) or an **award** (e.g. Champion of Power). |
| **Guild** | Any group a character can belong to: a guild, order, cult or coalition. Each has ranks (optional) and guild abilities. |
| **Guild ability** | A bonus that comes from being in a guild at or above a certain rank, e.g. *Rat Pack* (any Guild of Thieves member). |
| **Secret guild** | A guild whose members are never revealed by the bot (the Guild of Thieves). |
| **Party** | Every counted character in the voice channel. |
| **Giver** | The character who provides a bonus. |
| **Recipient** | A present character who receives a bonus. |
| **Allies** | Everyone in a bonus's audience **except the giver**. All bonuses go to allies unless the catalog says the giver is included. |
| **Audience** | Who can receive a bonus: the whole **party**, or only members of one **guild**. |
| **Stacks / doesn't stack** | A bonus that stacks is counted once per giver. One that doesn't stack is counted once per recipient, however many givers are present. |
| **Replaces** | A catalog entry that supersedes another: a character with both gives only the better one (e.g. Seraph's Affection replaces Nuyaru's Love). |
| **Modifier** | An entry that changes the character's other entries instead of giving a bonus itself (e.g. Devotion III: +1 to each of the character's auras). |
| **Condition note** | A condition the bot shows but doesn't enforce, e.g. "allies in the same range". The DM rules on it. |
| **Effect** | A text-only benefit, e.g. *Resistance to damage from an Evil source*. |
| **Counted / sitting out** | Players in the voice channel are *counted*, with their current character, unless they have used `/sitout`. |

## 4. How Bonuses Are Counted

1. **Every giver counts.** Three present characters each giving +2 means the bonus counts three times, including the same skill from different characters. Two Holy Knights with Holy Aura give +4 CR vs fear.
2. **Bonuses go to allies.** A bonus never applies to its giver. Three characters each giving +2 CM: each of them receives +4, and everyone else receives +6. The same holds for CR and combat notes.
3. **Unless the catalog includes the giver.** A catalog entry can say the giver benefits too. Today that's Leadership, King of the Pirates, Wilderness Lore and Proper Seasoning, whose text says "all members" or "you and your allies".
4. **Some bonuses don't stack.** An entry marked *doesn't stack* is counted once per recipient, however many givers are present. If the givers' amounts differ, the highest counts. Two Commanders with Inspiring Presence give allies +5 CR, not +10.
5. **Replacements.** If a character has an entry and the entry that replaces it, they give only the replacement. A GoTH member with Nuyaru's Love (+1) and Seraph's Affection (+3) gives +3.
6. **Modifiers.** Devotion III adds +1 to each aura **that same character** gives, from any tree (Holy Aura, Bolstering Aura, Aura of Defense, Aura of Hope). Only skills named "Aura" are auras. Auras with no number (Protective Aura) are unchanged.
7. **Parent stats flow down to subtypes.** "+5 to all challenge rolls" plus "+3 CR vs fear" means CR +5 and CR vs fear +8. The same applies to *stealth* and *would hurt*.
8. **Audience.** The whole party, or only members of one guild (e.g. Rat Pack: Guild of Thieves members only).
9. **Rank.** Guild abilities can require a minimum rank (e.g. Leadership needs a Guild Thief). Players set their own rank. Support is the exception: it comes from Discord roles.
10. **Level conditions.** A bonus can depend on the **recipient's** level (the Cult of the Dragon). A character with no level recorded doesn't receive level-based bonuses, and `/mybonus` notes this.
11. **Only counted players give or receive.** Anyone sitting out (the DM running the game, observers) is left out entirely. A player in the channel with no character set up still gives bonuses that come from their Discord roles (Support), but nothing that needs a character.
12. **Present means in range.** Every counted character's bonuses apply to the whole audience. Conditions such as "allies in the same range" are shown as notes, and the DM rules on them.
13. **Only totals are shown by default.** `/partybonus` and `/mybonus` show totals only. `/breakdown` shows every contributor and the working.

Worked example (Support): each character whose player has one of the Guild rank roles (Junior Adventurer, Guild Veteran, Guild Vanguard, Guild Champion, Guild Legend) gives +2 CM to allies. With five of them present, other characters get +10 and each of the five gets +8.

## 5. Users and Roles

| Role | Can do |
|---|---|
| **Player** | Every Discord member, DMs included. Register and manage **their own** characters; set levels; add catalog entries and guild memberships to their characters; choose their current character; sit themselves out; run `/partybonus`, `/mybonus`, `/breakdown`; request catalog additions. |
| **Maintainer** | Edits the catalog and settings files in the repository (sections 6.2 and 6.7), and fixes data in the database if ever needed. This is a repository role, not a Discord role. |

The bot has **no DM or admin role**. A DM is an ordinary player to the bot: a DM running a game uses `/sitout`, and may check the party `/breakdown` and ask players to fix mistakes.

## 6. Functional Requirements

Priority: **M** = must have (v1), **S** = should have, **C** = could have (later).

### 6.1 Characters and Level

| ID | Requirement | Pri |
|---|---|---|
| CH-1 | A player can register several characters, each with a name that is unique on the server (ignoring case). Names autocomplete in commands. | M |
| CH-2 | A player can rename or delete their own characters. Deletion asks for confirmation. | M |
| CH-3 | **Current character:** each player has one **current** character, set with `/play <character>`. It stays until changed. A player's first registered character becomes current automatically, so most players (one character each) never need `/play`. Commands with no character named use the current character. | M |
| CH-4 | **Optional level per character:** 1 up to a configurable maximum (currently 75). It can be left blank. | M |
| CH-5 | Level-based bonuses only apply to characters with a recorded level. `/mybonus` notes any bonus missed because the level is missing. | M |
| CH-6 | The date each level was last updated is stored and shown in `/breakdown`. | S |

### 6.2 The Catalog

The catalog lives in the repository as data files: `data/stats.yaml`, `data/skills.yaml`, `data/guilds.yaml` (guilds, ranks, guild abilities and boons) and `data/items.yaml` (items and awards). Section 8 lists the starting catalog.

| ID | Requirement | Pri |
|---|---|---|
| CT-1 | **Fixed catalog.** Stats, skills, guilds, ranks, guild abilities, boons, items and awards are defined only in the catalog files. There are no commands to create or change them. | M |
| CT-2 | **Permanent IDs.** Every catalog entry has a permanent ID separate from its display name. Characters store the ID, so renaming an entry never breaks a character. | M |
| CT-3 | **Linked, not copied.** Characters refer to catalog entries. Changing an entry's value in the catalog changes it for every character at once. | M |
| CT-4 | **Entry fields:** name, kind (skill, boon, item, award), tree or guild, what it gives (one or more stats with amounts, or effect text), audience (party or one guild), whether the giver is included (default no), whether it stacks (default yes), what it replaces, tags (e.g. `aura`), modifiers, a condition note, level rules, and the card text quoted from the source. | M |
| CT-5 | **Guild fields:** full name, short name, membership (Discord roles, or players join themselves), ordered ranks, whether it's secret, and its abilities, each with a minimum rank. | M |
| CT-6 | **Retire, don't delete.** An entry that leaves the game is marked `retired`. It can't be added any more, but characters who have it keep it, and `/breakdown` marks it as retired. | M |
| CT-7 | **Validation in CI.** Every push checks the catalog: the format is valid, stat and entry references exist, there are no duplicate IDs or names, and no entry used by a character has been deleted. An invalid catalog can't be deployed. | M |
| CT-8 | **`/catalog [entry or guild]`** shows what an entry gives, with its card text, or a guild's ranks and abilities. With no argument it lists everything, grouped by kind and tree or guild. | S |
| CT-9 | **`/request <text>`** lets any player suggest a missing or wrong entry. The bot posts it, with the player's name, to a configured channel the maintainer watches. | S |

### 6.3 What Characters Have

| ID | Requirement | Pri |
|---|---|---|
| HV-1 | **`/add <character> <entry>`** gives a character a skill, boon, item or award from the catalog; **`/remove`** takes it away. Autocomplete shows entries labeled with their kind and tree or guild, e.g. "Holy Aura (Holy Knight skill)". | M |
| HV-2 | **`/guild join <character> <guild> [rank]`**, **`/guild rank`** and **`/guild leave`** set a character's guild membership and rank. A guild with ranks requires one. Players choose their own rank; nothing is checked. | M |
| HV-3 | **Support** comes from Discord roles, not from `/guild join`. The player's highest Guild rank role sets the rank, and it applies to every character that player owns. Roles are checked each time totals are calculated. | M |
| HV-4 | **Warnings, not blocks.** The bot warns, but still accepts the change, when a character adds a boon without being in its guild (e.g. Seraph's Affection without GoTH), or adds Devotion III with no auras. | S |
| HV-5 | **Audit log.** Every change to a character (entries, guilds, ranks, level, name) is written to the audit log, with who made it and when. There's no command to read it; the maintainer can read it from the database if a dispute comes up. | M |

### 6.4 Secret Guilds

The Guild of Thieves' rules say "never reveal another member". Even thieves don't automatically know who the other thieves are.

| ID | Requirement | Pri |
|---|---|---|
| SG-1 | A guild can be marked **secret** in the catalog. Today only the Guild of Thieves is. | M |
| SG-2 | `/guild join`, `/guild rank` and `/guild leave` for a secret guild reply privately. | M |
| SG-3 | The bot never lists a secret guild's members: not in `/catalog`, the party `/breakdown`, or anyone's *not applied* list. | M |
| SG-4 | In public output, secret guild bonuses are **included in totals**. The party `/breakdown` shows them as one unnamed "secret guild bonus" block, and as unnamed amounts in the working. It never names a giver. This is deliberately light: the secrecy is tongue-in-cheek, and members are usually easy to work out (e.g. from the CR stealth column). Labeling it "secret guild" plays along with the joke; it isn't meant to be airtight. | M |
| SG-5 | A member's private `/mybonus` and `/breakdown` show the secret bonuses in detail, with **how many** members contributed but not who (e.g. "Rat Pack +1 (1 other member present)"). | M |

### 6.5 Presence (Voice Channel)

There are no sessions to start or end. Each time a command runs, the bot looks at who is in the voice channel and counts them, with these exceptions:

- **Sitting out:** anyone who has used `/sitout` in the last 12 hours. This covers the DM running the game and players who are only observing.
- **No character set up:** members with no usable character are still counted as players. They give only bonuses that come from their Discord roles, and are listed separately so they know to set up a character (SE-6).

| ID | Requirement | Pri |
|---|---|---|
| SE-1 | **Which channel:** `/partybonus` and `/breakdown` use the voice channel the caller is in. `channel:<voice channel>` picks one explicitly. `/mybonus` uses the voice channel the character's player is in. | M |
| SE-2 | **`/sitout`** leaves the caller uncounted for **12 hours** (configurable). `/sitin` ends it early. Players only sit **themselves** out, e.g. because they're running the game or just listening in. Remembering to do it is each player's responsibility. | M |
| SE-3 | **One character per player:** each player is counted with their **current** character (CH-3). Players play one character per event; a player switching characters runs `/play` first. | M |
| SE-4 | `/partybonus` and `/breakdown` end with a *not counted* line listing everyone sitting out, with the time it ends. | M |
| SE-6 | **No character set up:** a member in the voice channel with no usable character is still **counted as a player**, under their Discord name. They **give** only Support (from Discord roles). They **receive** bonuses like anyone else, except level-based ones and guild-only ones. `/partybonus` and `/breakdown` list them in a **NO CHARACTER SET UP** section with the fix (`/character register` or `/play`). | M |
| SE-7 | Bots in the voice channel (e.g. music bots) are ignored and never listed. | M |

### 6.6 Output Commands

| ID | Requirement | Pri |
|---|---|---|
| OUT-1 | **`/partybonus`**: a table of the roll-stat totals each counted character receives (CM, CR, and only the CR subtypes that differ from CR for someone), then combat notes (with their descriptions), effects, condition notes, and the *not counted* line. Totals only. | M |
| OUT-2 | **`/mybonus [character]`**: totals for one character (roll stats, combat notes, effects, condition notes), plus a single line about any bonus missed because the level is missing. Totals only. | M |
| OUT-2a | **Not-current character notice:** when `/mybonus <character>` or `/breakdown <character>` names a character who isn't its player's current character, the bot works out the totals **as if that character were playing in place of the current one**, and shows a notice at the top, e.g. *"Crateris isn't your current character (you're playing Chris). These totals show Crateris in Chris's place. Use `/play Crateris` to switch."* | M |
| OUT-3 | **`/breakdown`** (whole party): for **each bonus in play**, its name and source (tree, guild or item), what it gives and to whom, and **every contributing character** with their rank or level where it matters. Then: effects, the working for each character's totals (e.g. `CM 2+2+3+5 = +12`), and the *not counted* line. Secret guilds follow SG-4. | M |
| OUT-3a | **`/breakdown <character>`**: each stat that character receives, the sum written out, and every contribution with the bonus name, giver and value (including modifiers, e.g. "Holy Aura +3 (2 + 1 Devotion III)"). Then: bonuses **not applied** to them, with the reason, and what the character **gives**. | M |
| OUT-3b | Discord messages are limited to 2,000 characters (4,096 in an embed). Longer output is split across several messages or pages, never cut off. | M |
| OUT-4 | If the player isn't in a voice channel, `/mybonus` and `/breakdown <character>` show what the character **gives**, and explain that no party is present. | M |
| OUT-5 | `/mybonus` and `/breakdown <character>` reply privately by default. `/partybonus` and `/breakdown` (whole party) post publicly by default. An option switches either way. | M |
| OUT-6 | A player can look up anyone's character (subject to SG-3). | S |
| OUT-7 | Output never uses pronouns for characters ("to Kael", not "to himself"). | M |
| OUT-8 | A pinned `/partybonus` message that updates itself when people join or leave the voice channel. | C |

### 6.7 Administration and Review

| ID | Requirement | Pri |
|---|---|---|
| AD-1 | **Settings live in the repository**, in `config/settings.yaml`, not in Discord commands: the `/request` channel, default reply visibility, sit-out duration (default 12 h) and maximum level (75). Changing one is a commit and an automatic deploy, like a catalog change. Secrets (bot token, storage credentials) stay in environment variables (NF-9). | M |
| AD-2 | **Review:** anyone, typically the DM, can check the party `/breakdown` during a game to catch mistakes and abuse, and ask the owner to fix their character. The maintainer can correct data in the database as a last resort. | M |

## 7. Commands

```
Game night (players)
/partybonus [channel:<voice>] [private:<bool>]
/mybonus [character] [public:<bool>] [export:<bogsy>]
/breakdown [character] [channel:<voice>] [public:<bool>]
/play <character>
/sitout   /sitin

Setup (players, for their own characters)
/character register name:<text> [level:<n>]
/character list | rename <character> <new> | delete <character>
           | level <character> <n|clear>
/add <character> <entry>              skill, boon, item or award
/remove <character> <entry>
/guild join <character> <guild> [rank]
/guild rank <character> <guild> <rank>
/guild leave <character> <guild>
/catalog [entry or guild]
/request <text>
```

Everyone has the same commands. There are no DM or admin commands: settings and the catalog live in the repository.

## 8. Starting Catalog

Values come from the skill-tree images and guild write-ups in the Diceknights drive. Items marked *to confirm* wait on the DMs ([dm-rule-questions.md](dm-rule-questions.md)).

### 8.1 Stats

| Stat | Kind | Notes |
|---|---|---|
| CM | Roll | Combat modifier; attack and defence combined. |
| CR | Roll | Challenge roll. |
| CR vs fear | Roll (CR subtype) | |
| CR stealth | Roll (CR subtype) | |
| CR would hurt | Roll (CR subtype) | Applies when a failed CR would cause damage; players ask the DM. |
| Damage | Combat note (hearts) | Extra hearts dealt when attacking. |
| Damage reduction | Combat note (hearts) | Hearts mitigated when attacked. |
| Healing | Combat note (hearts) | Hearts healed at the end of each round. |

### 8.2 Skills

| Skill | Tree | Gives (to allies) | Notes |
|---|---|---|---|
| Holy Aura | Holy Knight | +2 CR vs fear | Aura |
| Bolstering Aura | Holy Knight | +2 CM | Aura |
| Protective Aura | Holy Knight | Effect: resistance to damage from an Evil source | Aura |
| Devotion III | Holy Knight | Nothing itself | Modifier: +1 to each of this character's auras |
| Aura of Defense | Paladin | +5 CR would hurt | Aura |
| Aura of Hope | Paladin | +10 CM | Aura |
| Commanding Presence | Commander | +5 CM | Condition: allies in the same range. Not an aura (DM question Q1). |
| Inspiring Presence | Commander | +5 CR | Doesn't stack. Not an aura (Q1). |

### 8.3 Guilds

| Guild | Membership and ranks | Abilities |
|---|---|---|
| **The Guild** | Discord roles: Junior Adventurer, Guild Veteran, Guild Vanguard, Guild Champion, Guild Legend | **Support** (any rank): +2 CM to allies. |
| **Guild of the Timeless Heroes** (GoTH) | Players join; no ranks | Boons (added with `/add`): **Nuyaru's Love** +1 CM to allies; **Seraph's Affection** +3 CM to allies, replaces Nuyaru's Love (Q3). |
| **Guild of Thieves** (secret) | Footpad, Burglar, Guild Thief | **Rat Pack** (any rank): +1 CM to other members. **Leadership** (Guild Thief): +2 CM and +2 CR stealth to all members, the giver included; doesn't stack. |
| **Pirate Coalition** | Swabbie, Crew Mate, First Mate, Captain | **King of the Pirates** (Captain): +2 CM to all members, the giver included; doesn't stack. |
| **Cult of the Dragon** | Member, High Priest | **High Priest's blessing** (High Priest): to other members, level under 10: +1 heart damage; level 10 or higher: +10 CM. Doesn't stack (Q2). |
| **Ranger's Guild** | Apprentice, Journeyman, Ranger Captain, Master Ranger | **Wilderness Lore** (Ranger Captain): effect: challenge rolls to resist natural effects are one roll category easier, for the giver and allies. |
| **Order of Cookery** | Scullery Servant, Sous Chef, Chef, Cookery Master | **Proper Seasoning** (Chef): effect: +1 heart when Invigorated, for the giver and allies. |
| **HoP** | To be defined (Q5) | To be defined. |

Guilds with no always-on bonuses to others (Bards, Monks, Fighters, Hunters, Physicians, Lorekeepers) aren't in the catalog. They can be added if one is needed as an audience.

### 8.4 Items and Awards

| Entry | Kind | Gives (to allies) | Status |
|---|---|---|---|
| Wills ward stone | Item | +5 CM | To confirm (Q4) |
| NF (nobuFest pin) | Item | +1 CM | To confirm (Q4) |
| Champion of Power | Award | +5 CR, +5 CM | To confirm (Q4) |

The sources of the healing and damage reduction bonuses from the original sample are still unknown (Q4).

## 9. Example

### 9.1 Sample game

Voice channel: *AWT Voice*. DM Sam and Bob, an observer, are in the channel but have used `/sitout`. Dana has just joined the server, has no Guild rank role, and hasn't registered a character. Counted characters:

| Character | Level | Discord role | Guilds (rank) | Has |
|---|---|---|---|---|
| Ioseph | 34 | Guild Vanguard | GoTH | Nuyaru's Love, Seraph's Affection, Champion of Power |
| Kael | 8 | Junior Adventurer | Cult of the Dragon (Member) | |
| Crateris | 22 | | Cult of the Dragon (High Priest) | Holy Aura, Bolstering Aura, Protective Aura, Devotion III, Wills ward stone |
| Chris | not recorded | | Guild of Thieves (Guild Thief) | Inspiring Presence |
| Mira | 15 | | Guild of Thieves (Footpad), Cult of the Dragon (Member) | Inspiring Presence |

What's in play:
- **Support:** +2 CM each from Ioseph and Kael.
- **Seraph's Affection:** +3 CM from Ioseph. It replaces Nuyaru's Love.
- **Champion of Power:** +5 CR and +5 CM from Ioseph.
- **Crateris's auras, with Devotion III:** Holy Aura +3 CR vs fear, Bolstering Aura +3 CM, and the Protective Aura effect.
- **Wills ward stone:** +5 CM from Crateris.
- **Cult of the Dragon:** the High Priest (Crateris) gives Kael (level 8) +1 heart damage, and Mira (level 15) +10 CM.
- **Inspiring Presence:** Chris and Mira both have it. It doesn't stack, so allies get +5 CR once. Chris and Mira each still get +5 from the other.
- **Secret guild bonuses:**
  - Rat Pack: Chris and Mira each get +1 CM from the other.
  - Leadership: Chris is a Guild Thief, so both get +2 CM and +2 CR stealth, Chris included.

`/partybonus`:

```
PARTY BONUSES: AWT Voice (6 counted)
-------------------------------------------------
CHARACTER   CM    CR    CR vs fear   CR stealth
Ioseph      +10   +5    +8           +5
Kael        +18   +10   +13          +10
Crateris    +12   +10   +10          +10
Chris       +23   +10   +13          +12
Mira        +33   +10   +13          +12
Dana*       +20   +10   +13          +10
-------------------------------------------------
COMBAT NOTES
Kael        Damage +1 heart (extra hearts dealt when attacking)
-------------------------------------------------
EFFECTS
All but Crateris   Resistance to damage from an Evil source (Protective Aura)
-------------------------------------------------
NO CHARACTER SET UP (* only bonuses from Discord roles are counted)
  Dana    no character registered: use /character register
-------------------------------------------------
Not counted: DM Sam (sitting out until 11:40 PM), Bob (sitting out until 10:15 PM)
```

`/breakdown` (whole party):

```
PARTY BREAKDOWN: AWT Voice (6 counted)
-------------------------------------------------
Support (the Guild): +2 CM to allies from each giver
    Ioseph     Guild Vanguard
    Kael       Junior Adventurer

Seraph's Affection (GoTH boon): +3 CM to allies
    Ioseph                           (replaces Nuyaru's Love)

Champion of Power (award): +5 all CR, +5 CM to allies
    Ioseph

Cult of the Dragon (Cult members only)
    Crateris   High Priest           +1 heart damage to Kael (level 8)
                                     +10 CM to Mira (level 15)

Holy Aura (Holy Knight): +3 CR vs fear to allies (2 + 1 Devotion III)
    Crateris

Bolstering Aura (Holy Knight): +3 CM to allies (2 + 1 Devotion III)
    Crateris

Wills ward stone (item): +5 CM to allies
    Crateris

Inspiring Presence (Commander): +5 all CR to allies, doesn't stack
    Chris, Mira

Secret guild bonus: +3 CM and +2 CR stealth to each member present
    (givers not shown)

Effect: Resistance to damage from an Evil source (Protective Aura), to allies
    Crateris
-------------------------------------------------
TOTALS
Ioseph     CM 2+3+5 = +10               CR 5 = +5      CR vs fear 5+3 = +8
Kael       CM 2+3+5+3+5 = +18           CR 5+5 = +10   CR vs fear 10+3 = +13
           Damage +1 heart
Crateris   CM 2+2+3+5 = +12             CR 5+5 = +10   CR vs fear +10
Chris      CM 2+2+3+5+3+5+3s = +23      CR 5+5 = +10   CR vs fear 10+3 = +13
           CR stealth 10+2s = +12
Mira       CM 2+2+3+5+3+5+10+3s = +33   CR 5+5 = +10   CR vs fear 10+3 = +13
           CR stealth 10+2s = +12
Dana*      CM 2+2+3+5+3+5 = +20         CR 5+5 = +10   CR vs fear 10+3 = +13
(s = secret guild bonus)
-------------------------------------------------
NO CHARACTER SET UP (* only bonuses from Discord roles are counted)
  Dana    no character registered: use /character register
-------------------------------------------------
Not counted: DM Sam (sitting out until 11:40 PM), Bob (sitting out until 10:15 PM)
```

`/breakdown Crateris` (private):

```
BREAKDOWN: Crateris (level 22, updated 2026-09-20)
-------------------------------------------------
CM = 2 + 2 + 3 + 5 = +12
   +2   Support               from Ioseph (Guild Vanguard)
   +2   Support               from Kael (Junior Adventurer)
   +3   Seraph's Affection    from Ioseph
   +5   Champion of Power     from Ioseph
CR = 5 + 5 = +10
   +5   Champion of Power     from Ioseph
   +5   Inspiring Presence    from Chris, Mira (doesn't stack: counted once)
CR vs fear = 10 (all CR) = +10
CR stealth = 10 (all CR) = +10
-------------------------------------------------
NOT APPLIED
  Holy Aura, Bolstering Aura, Wills ward stone    allies only (Crateris is the giver)
  Cult of the Dragon                              allies only (Crateris is the giver)
-------------------------------------------------
CRATERIS GIVES
  Holy Aura +3 CR vs fear (2 + 1 Devotion III)
  Bolstering Aura +3 CM (2 + 1 Devotion III)
  Protective Aura: resistance to damage from an Evil source
  Wills ward stone +5 CM
  Cult of the Dragon (High Priest)
```

`/mybonus Mira` (private; Mira is a Guild of Thieves member):

```
MIRA (level 15): AWT Voice
-------------------------------------------------
CM          +33
CR          +10
CR vs fear  +13
CR stealth  +12
-------------------------------------------------
Resistance to damage from an Evil source (Protective Aura)
-------------------------------------------------
Secret guild (Guild of Thieves), included above:
  Rat Pack     +1 CM (1 other member present)
  Leadership   +2 CM, +2 CR stealth (a Guild Thief is present)
-------------------------------------------------
See how this was worked out: /breakdown Mira
```

A character with no level recorded would see this in `/mybonus`:

```
1 bonus not applied: level not recorded. Use /character level <character> <n>.
```

If Crateris's player were actually playing another character, `/mybonus Crateris` would start with the OUT-2a notice:

```
NOTE: Crateris isn't your current character (you're playing Elowen).
These totals show Crateris in Elowen's place. Use /play Crateris to switch.
```

## 10. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NF-1 | **Responsiveness:** commands acknowledge within Discord's 3-second limit (deferring the reply if needed). Calculating a 20-character party takes under 200 ms. |
| NF-2 | **Scale:** one server (AWT), up to about 300 characters and about 20 present at once. |
| NF-3 | **Reliability:** reconnects automatically and restarts after a crash. All character data lives in the database; the catalog lives in the repository. A restart mid-game loses nothing. |
| NF-4 | **Permissions:** players change only their own characters, and sit out only themselves. Checked in the bot on every command. There are no elevated roles. |
| NF-5 | **Privacy:** Discord IDs, display names and game data only. Doesn't read message content. Secret guild membership is protected as in section 6.4. |
| NF-6 | **Intents:** `Guilds` and `GuildVoiceStates` (both non-privileged). Roles for present players are looked up individually, so no privileged intents are needed. Results are cached for about 60 s. |
| NF-7 | **Quality (see section 13):** type-checked; the calculation engine has at least 90% branch coverage, including every rule in section 4 and the numbers in section 9; CI on every push. |
| NF-8 | **Operations:** structured logs; nightly off-site database snapshots (section 12.1). |
| NF-9 | **Security:** the bot token and storage credentials live only in environment variables or the host's secret store. |
| NF-10 | **Time zones:** every time the bot stores or checks (sit-out expiry, level "last updated", audit log, snapshots) is in **GMT (UTC)**, never the host's local time. Times shown to players use Discord timestamps (`<t:…>`), which Discord displays in each reader's own time zone. |

## 11. Data Model and Engine

The **catalog** and **settings** aren't stored in the database. They're loaded from `data/*.yaml` and `config/settings.yaml` at startup, and the database stores only catalog IDs. All timestamps are GMT (UTC).

```
Player          (discord_user_id, current_character_id NULL)
Character       (id, discord_user_id, name UNIQUE NOCASE, level NULL, level_updated_at)
CharacterEntry  (character_id, entry_id)                  -- skill, boon, item or award (catalog ID)
CharacterGuild  (character_id, guild_id, rank_id NULL, joined_at)   -- catalog IDs
SitOut          (discord_user_id, until, set_by)
AuditLog        (id, actor_user_id, character_id, action, before_json, after_json, at)
```

Support isn't stored. It's worked out on each calculation from the player's current Discord roles.

**Calculation engine:** a pure function with no Discord or database code:

```
compute(counted_players, player_roles, character_entries, character_guilds, catalog) -> PartyReport
```

0. **Who is counted:** members in the voice channel (excluding bots), minus anyone with an active sit-out. Each counted player uses their current character, or a stand-in with no character if none is set up. For OUT-2a, the named character replaces its player's current character.
1. **Work out memberships:** each character's guilds and ranks, plus the Guild rank from their player's Discord roles.
2. **List the gives:** each counted character's entries (after replacements, and with modifiers such as Devotion III applied), and each guild ability they qualify for by rank.
3. **Apply them to recipients:** for each recipient, check each give against the audience, whether the giver is included, and any level rule. Record it as *applied* (with its amount) or *not applied* (with a reason: giver excluded, not in audience, no level, replaced, or not stacked).
4. **Stacking:** for gives that don't stack, keep one per recipient (the highest amount).
5. **Add up:** total each stat, then add parent-stat amounts into subtypes.
6. **Display:** `PartyReport` holds everything, including which gives come from secret guilds. The output layer applies the secrecy rules (section 6.4).

## 12. Technology, Storage and Deployment

| Layer | Choice | Why |
|---|---|---|
| Language | **Python 3.12+** | Readable, quick to iterate on with Claude Code. |
| Discord library | **discord.py 2.x** (`app_commands`) | Mature and maintained; slash commands and autocomplete. |
| Database | **SQLite** (WAL mode) | A single file, no database server to run. Plenty for one server. |
| ORM / migrations | **SQLAlchemy 2.0 (async)** + **aiosqlite**, **Alembic** | Typed models; versioned schema changes. |
| Catalog | **YAML** files validated with **pydantic** | Easy to edit by hand; checked in CI. |
| Config | **pydantic-settings** | Typed config from the environment. |
| Testing | **pytest**, **pytest-asyncio**, **hypothesis** | Property tests fit the counting rules well. |
| Quality | **ruff**, **mypy**, **pytest-cov** | Lint, format, type-check; enforce 90% branch coverage on the engine. |
| Packaging | **uv** + `pyproject.toml` | Fast, reproducible. |
| Deploy | **Docker** on a small VPS (about $4–6/mo) or Fly.io / Railway with a volume | Needs a process that's always running. |
| CI/CD | **GitHub Actions** | Lint, type-check, test, validate the catalog, build and deploy. |
| Backups | Nightly `sqlite3 .backup` snapshots to object storage | Meets NF-8; see 12.1. |

**Alternative:** Node.js 22 + discord.js v14 + Prisma + Vitest.

### 12.1 Storage and Backups

**Where the data lives:** a single **SQLite** file (e.g. `data/awt-bonus.db`) on the same machine as the bot. Nothing is stored in Discord. Roles and voice presence are read live from Discord each time a command runs.

**Hosting:** Craig hosts the bot at launch. Long-term hosting is an open question (section 16).

| Hosting | Location of the database file |
|---|---|
| Small VPS | The VPS's disk, mounted into the container as a Docker volume, e.g. `/srv/awt-bonus/data/` |
| Fly.io / Railway | A **persistent volume** attached to the bot's container |
| Local PC (development/testing) | A `data/` folder next to the code (git-ignored) |

| ID | Requirement | Pri |
|---|---|---|
| DB-1 | The database path is set by configuration (`DATABASE_URL`), never hard-coded. | M |
| DB-2 | The database must be on **persistent** storage. The bot refuses to start if the path is on a known temporary filesystem, or if it can't write a test file. | M |
| DB-3 | SQLite runs in **WAL mode** with a busy timeout. Only **one** bot process uses the file at a time. | M |
| DB-4 | **Schema changes** only happen through Alembic migrations. They run automatically at startup, after a snapshot is taken first. | M |
| DB-5 | **Continuous replication:** Litestream streams every change to object storage, so at most seconds of changes are lost instead of up to a day. Not needed at launch: losing a day of character changes costs players a few minutes of re-entering. | C |
| DB-6 | **Nightly snapshots:** a full `sqlite3 .backup` copy goes to the same object storage every night and is kept for 30 days. | M |
| DB-7 | **Restore is documented and tested:** a written runbook covers restoring onto a new host. It's tried at least once before AWT goes live. | M |

**Expected size:** well under 10 MB. Storage costs are pennies a month.

### 12.2 Deployment

| ID | Requirement | Pri |
|---|---|---|
| DP-1 | **Automatic deployment:** every push to `main` that passes CI (tests, type checks, catalog validation) is deployed automatically. | M |
| DP-2 | **Branches:** experimental work happens on branches and reaches `main` by merge. Only `main` is deployed. | M |
| DP-3 | **Catalog changes are ordinary commits.** Adding a skill or award is an edit to a data file, a push, and an automatic deploy: a few minutes end to end. | M |
| DP-4 | **Safe restarts:** a deploy restarts the bot in a few seconds without losing data, so deploying during a game is harmless. | M |

## 13. Testing Strategy

Most of the checking is done by fast automated tests that never touch Discord. Live testing in Discord only confirms the Discord-specific parts, and a trial at AWT, with DMs checking the numbers, proves the bot in real games.

### 13.1 Calculation Engine

| ID | Requirement | Pri |
|---|---|---|
| TS-1 | **Scenario files:** engine tests are written as YAML scenarios: who is in the channel, what they have, and the expected totals (and, where relevant, *not applied* lines). They use their own test catalog, so changing a real catalog value doesn't break them. `engine-scenarios.yaml` covers every rule in section 4 and the sample game in section 9. Every rules question that comes up becomes a permanent scenario. | M |
| TS-2 | **Edge cases** each get a scenario: no level recorded; level exactly 10; a player with no character but a Guild role; everyone sitting out; an empty channel; the same skill from two characters; bots in the channel; two givers of a bonus that doesn't stack; a replaced boon; a retired entry. | M |
| TS-3 | **Property tests (Hypothesis):** thousands of randomly generated parties check rules that must always hold:<br>• nobody receives their own bonus unless the entry includes the giver;<br>• a bonus that doesn't stack is counted at most once per recipient;<br>• every total equals the sum of the lines `/breakdown` shows for it;<br>• a subtype total is never lower than its parent's;<br>• the order of players doesn't change the result;<br>• removing a giver never increases anyone's total. | M |
| TS-4 | **Catalog validation tests:** the real catalog loads and passes every check in CT-7. | M |

### 13.2 Output

| ID | Requirement | Pri |
|---|---|---|
| TS-5 | **Snapshot tests:** the text of `/partybonus`, `/mybonus` and `/breakdown` for the sample game is saved as reference files and compared on every run. | M |
| TS-6 | **Secrecy tests:** for the sample game, no public output and no non-member's output contains a secret guild member's name next to a secret guild bonus, or lists secret guild members. | M |
| TS-7 | **Message size:** a very large party splits across messages under Discord's 2,000-character limit and never cuts off mid-line (OUT-3b). | M |

### 13.3 Commands and Database (no Discord needed)

| ID | Requirement | Pri |
|---|---|---|
| TS-8 | The Discord-specific code is kept thin. Command logic runs against a **fake Discord** that supplies voice members, roles and bots from test data. | M |
| TS-9 | **Permission tests:** no player can change another player's characters, whatever Discord roles they have. Every command that acts on a character is checked. | M |
| TS-10 | **Fake clock:** time-based behavior is tested with a controllable clock in GMT (UTC), including a host set to a different time zone. | M |
| TS-11 | **Database tests:** each test gets a fresh temporary SQLite file. Migrations are tested from empty and from the previous release's schema. | M |
| TS-12 | **Backup and restore:** an automated test restores a snapshot into a new database and checks the data matches. At launch, the manual restore in DB-7 is enough. | C |

### 13.4 Live Testing on a Private Server

| ID | Requirement | Pri |
|---|---|---|
| TS-13 | A **separate test bot** (its own token and database) runs on a private test server, so testing never touches AWT data. | M |
| TS-14 | The test server **mirrors AWT's setup**: the five Guild rank roles, a voice channel, and a music bot. Testing uses two or three people or alt accounts operated by hand. | M |
| TS-15 | A **manual checklist** covers: joining and leaving voice; role changes; bots ignored; autocomplete; private versus public replies; long output splitting; a restart mid-game; `/sitout` / `/sitin`; a member with no character; the not-current character notice; secret guild privacy; a catalog change deployed automatically. | M |
| TS-16 | **No self-bots:** real user accounts are never automated to drive tests. That breaks Discord's Terms of Service. | M |

### 13.5 Trial at AWT

| ID | Requirement | Pri |
|---|---|---|
| TS-17 | **DM-checked trial:** for the first few games, the DM checks the party `/breakdown` by hand against the rules. Every mismatch is a bug, a rule modeled wrong, or a catalog error. Each becomes a new scenario or catalog fix. | M |
| TS-18 | A few players try `/mybonus` and `/breakdown` and give feedback on how clear the output is before general rollout. | S |

## 14. Optional: Hand-off to Bogsy's Dice Bot

The bot doesn't roll dice. `/mybonus <character> export:bogsy` lists **roll stats only** (CM, CR, CR subtypes) as values for the player to enter with Bogsy's `/modifier`. Combat notes and effects are never exported. The exported values are party bonuses only; they add on top of the character's own CM and CR.

| ID | Requirement | Pri |
|---|---|---|
| BG-1 | The export lists each roll stat's modifier name and value, e.g. `awt_cm` = `+33`, `awt_cr` = `+10`, `awt_cr_fear` = `+13`, with copyable text lines (`.awt_cm = +33 "AWT CM"`). | C |
| BG-2 | Modifier names come from the catalog's stat definitions and avoid Bogsy's reserved words. | C |
| BG-3 | The export also lists modifiers to clear (`.awt_cm =`) for stats that are now zero. | C |

## 15. Future Enhancements

- Buttons on the `/partybonus` message (Join / Leave / Refresh).
- A pinned message that updates itself (OUT-8).
- Switching an item off temporarily without removing it (e.g. not equipped).
- Continuous database replication with Litestream (DB-5) and an automated restore test (TS-12).
- Stricter type checking (`mypy --strict`).

## 16. Open Questions

**Waiting on the DMs:** see [dm-rule-questions.md](dm-rule-questions.md): Presence skills as auras (Q1), the Cult's level rule (Q2), GoTH boons (Q3), the full item and award list (Q4), and HoP (Q5).

**Not tracked yet:** Rat Pack also gives +1 to escape, street work and burglary rolls, and Leadership to burglary and street work. These are left out until it's clear whether escape counts as a combat-time CR.

**Design question for later: one `/add` or several commands?** The document uses a single `/add <character> <entry>` (and `/remove`) for skills, boons, items and awards, with autocomplete labeling each entry's kind. The alternative is separate commands such as `/addskill` and `/additem`. One command means less to learn; separate commands make it clearer what's being added.

**For later consideration: long-term hosting.** Craig hosts the bot at launch. If it runs for the long term, decide who pays for hosting, who holds the bot token and backup credentials, who fixes it when it's down at game time, and how it's handed over if Craig steps away.

### Resolved

- **Allies only:** a bonus never applies to its giver, unless the catalog entry says so (Leadership, King of the Pirates, Wilderness Lore, Proper Seasoning).
- **Fixed catalog:** skills, guild abilities, boons, items and awards come from data files in the repository. Players pick from it and can't type in bonuses. Missing entries are requested with `/request`.
- **Catalog changes:** permanent IDs, retired instead of deleted, linked rather than copied, validated in CI, and deployed automatically on push to `main`.
- **Stacking:** every giver counts, except entries marked "doesn't stack", which count once. A replacing entry supersedes the one it replaces.
- **Devotion III** adds +1 to all of the character's own auras, from any tree. Only skills named "Aura" are auras (pending Q1).
- **Conditions** such as "same range" are notes; the DM rules. "Would hurt" is a CR subtype that players ask about.
- **CM** combines the old combat bonus and combat defence.
- **GoTH boons** are always on. **Bard Inspiration** is out of scope.
- **Guild of Thieves** is secret, tongue-in-cheek: the bot never names members, but public totals still include their bonuses, even though that makes them easy to spot. Leadership needs any Guild Thief present, and a stealth bonus counts toward both CM and stealth CRs.
- **The Cult bonus** comes only from the High Priest.
- **Guild rank** is chosen by the player. Support comes from Discord roles.
- **Sit-outs:** players sit only themselves out (when running the game or just listening); the bot doesn't guess.
- **Characters only:** minions, summons, companions and allied NPCs aren't tracked; bonuses apply only to player characters.
- **No DM or admin role** in the bot: everyone has the same commands and changes only their own characters. DMs review informally with `/breakdown`.
- **Times** are stored in GMT (UTC).
- **No master list:** each player enters their own characters.

## 17. Milestones

| Milestone | Scope |
|---|---|
| **M1: Engine and catalog** | Catalog format and loader with validation; stats; the calculation engine with every rule in section 4; scenario and property tests. |
| **M2: Characters and output** | `/character`, `/add`, `/remove`, voice presence, `/sitout` / `/sitin`, `/play`, `/partybonus`, `/mybonus`, `/breakdown`, `/catalog`. |
| **M3: Guilds** | `/guild join/rank/leave`, Support from Discord roles, secret guilds. |
| **M4: Ops** | Docker, CI with catalog validation, automatic deployment, persistent storage, nightly snapshots, restore runbook, settings file, `/request`. |
| **M5: Extras** | Bogsy hand-off, buttons. |
