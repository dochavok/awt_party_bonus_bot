# AWT Party Bonus Bot: Requirements

**Version:** 1.1 (baseline for development; changes from here follow the test-change rule, section 13.0)
**Date:** 2026-09-25
**Owner:** Craig
**Server:** Adventures from the Wizards Tower (AWT)
**Related:** [dm-rule-questions.md](dm-rule-questions.md) (rule questions waiting on the DMs)

---

## 1. Purpose

Working out party bonuses by hand is slow and easy to get wrong. Someone has to know every character's bonuses, drop the ones whose characters aren't in the game, and add up the rest for each character.

This bot does that work. Every skill, guild ability, item and title that gives a party bonus is defined once, in a **fixed catalog** kept in the bot's repository. Players record what their characters **have** (their skills, guilds, ranks, boons, items and titles) by picking from the catalog. When someone asks, the bot works out totals from the characters who are present:

- `/partybonus`: the totals every present character receives.
- `/mybonus [character]`: the totals for one of your characters.
- `/breakdown [character]`: every bonus in play, who contributes it, and how each total adds up.

Games happen in a Discord voice channel. There's no session to start or end: the bot counts everyone who is in the voice channel when the command runs. Anyone running the game or just watching uses `/sitout`, which lasts 12 hours, to be left out. When someone joins or leaves, running the command again gives an up-to-date answer.

## 2. Scope

### Goals

- Any player can see their character's current totals, and how they were calculated if they want the detail.
- The game's rules are applied correctly: every giver counts, bonuses go to **allies** (not the giver) unless the catalog says otherwise, and stacking, guild and level conditions are respected.
- Players enter their own data by picking from the catalog. Nobody else enters or approves anything.
- The catalog is uniform: one definition of each skill, guild, rank, boon, item and title, so there are no duplicates or typos.

### Non-Goals

- **No dice rolling.** At most, the bot hands CM/CR values to an existing dice bot (section 14).
- **No character sheets.** Each character has a name, an optional level, guild memberships, and catalog entries. Nothing more. The bot doesn't track class.
- **Only always-on bonuses to others.** Abilities used once per combat, day or weekend, Tasks, and repeatable one-off abilities (e.g. Bard Inspiration) aren't tracked.
- **No self-only bonuses.** A bonus that only helps its own character is part of that character's own CM or CR, which the player tracks. The bot's totals are added on top.
- **No bonuses typed in by players.** Everything comes from the catalog. Anything missing is requested with `/request` and added to the catalog.
- **Characters only.** Minions, summons, animal companions and allied NPCs (e.g. a Worldshaper's golem made an ally by Endowment) neither give nor receive party bonuses in the bot.
- **No position tracking.** The bot doesn't know who is in melee or ranged. Bonuses that depend on position (e.g. Commanding Presence: "allies in the same range") are **shown separately as conditional bonuses and left out of totals**, so totals are never overstated. All other bonuses apply to every counted character in the audience.
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
| **Stat** | What a bonus adds to. **Roll stats:** CM (combat modifier, attack and defence combined), CR (challenge roll) and CR subtypes (*vs fear*, *stealth*, *escape*, *would hurt*). **Combat notes:** damage, damage reduction, healing, measured in hearts. |
| **Catalog** | The fixed list of stats, skills, guilds, items and titles, kept as data files in the repository (section 6.2). |
| **Entry** | One thing in the catalog that a character can have: a **skill** (from a skill tree), a **boon** (e.g. a GoTH quest boon), a **rank** (e.g. Guild Thief), an **item** (e.g. Wills ward stone) or a **title** (e.g. Champion of Power, Hero of Passion). |
| **Guild** | Any group a character can belong to: a guild, order, cult or coalition. Membership decides guild-only audiences and secrecy. Joining grants nothing by itself: a guild's bonuses come from the rank and boon entries a member adds. |
| **Rank entry** | A guild rank that grants one or more abilities, added by name like a skill, e.g. *Footpad* (grants Rat Pack) or *Guild Thief* (grants Rat Pack and Leadership). Ranks that grant nothing aren't in the catalog. A higher rank replaces the lower ones (Guild Thief replaces Burglar and Footpad; Master Ranger replaces Ranger Captain). |
| **Secret guild** | A guild whose members are never revealed by the bot (the Guild of Thieves). |
| **Party** | Every counted character in the voice channel. |
| **Giver** | The character who provides a bonus. |
| **Recipient** | A present character who receives a bonus. |
| **Allies** | Everyone in a bonus's audience **except the giver**. All bonuses go to allies unless the catalog says the giver is included. |
| **Audience** | Who can receive a bonus: the whole **party**, only members of one **guild**, or only other **holders** of the same entry (e.g. Hero of Passion goes only to other HoP holders). |
| **Stacks / doesn't stack** | A bonus that stacks is counted once per giver. One that doesn't stack is counted once per recipient, however many givers are present. |
| **Replaces** | A catalog entry that supersedes another: a character with both gives only the better one (e.g. Seraph's Affection replaces Nuyaru's Love). |
| **Modifier** | An entry that changes the character's other entries instead of giving a bonus itself (e.g. Devotion III: +1 to each of the character's auras). |
| **Conditional bonus** | A bonus that only applies in a situation the bot doesn't track, e.g. "allies in the same range". It's listed separately, with its condition, and never included in totals. Players add it themselves when it applies. |
| **Effect** | A text-only benefit, e.g. *Resistance to damage from an Evil source*. |
| **Counted / sitting out** | Players in the voice channel are *counted*, with their current character, unless they have used `/sitout`. |

## 4. How Bonuses Are Counted

1. **Every giver counts.** Three present characters each giving +2 means the bonus counts three times, including the same skill from different characters. Two Holy Knights with Holy Aura give +4 CR vs fear.
2. **Bonuses go to allies.** A bonus never applies to its giver. Three characters each giving +2 CM: each of them receives +4, and everyone else receives +6. The same holds for CR and combat notes.
3. **Unless the catalog includes the giver.** A catalog entry can say the giver benefits too. Today that's Leadership, King of the Pirates, Wilderness Lore and Proper Seasoning, whose text says "all members" or "you and your allies".
4. **Some bonuses don't stack.** An entry marked *doesn't stack* is counted once per recipient, however many givers are present. If the givers' amounts differ, the highest counts. Two Commanders with Inspiring Presence give allies +5 CR, not +10.
5. **Replacements.** If a character has an entry and the entry that replaces it, they give only the replacement. A GoTH member with Nuyaru's Love (+1) and Seraph's Affection (+3) gives +3.
6. **Modifiers.** A modifier changes the bonuses **that same character** gives, and nobody else's. Numbers only; effects with no number are unchanged.
   - **Devotion III:** +1 to each aura, from any tree (Holy Aura, Bolstering Aura, Aura of Defense, Aura of Hope). Only skills named "Aura" are auras.
   - **Helping Hands / v2.0:** +1 / +2 to each numerical value of every bonus the character gives allies (pending Q7). Modifiers add together: a Holy Knight with Devotion III and Helping Hands gives Holy Aura +4.
7. **Parent stats flow down to subtypes.** "+5 to all challenge rolls" plus "+3 CR vs fear" means CR +5 and CR vs fear +8. The same applies to *stealth*, *escape* and *would hurt*.
8. **Audience.** The whole party, only members of one guild (e.g. Rat Pack: Guild of Thieves members only), or only other holders of the same entry (e.g. Hero of Passion: other HoP holders only).
9. **Guilds and ranks.** Joining a guild only records membership. Bonuses from rank or service are entries the player adds by name: a rank (Footpad, Guild Thief, Captain, High Inquisitor, Ranger Captain, Chef…) or a boon (Seraph's Affection). A rank can grant several abilities, each following its own rules (e.g. Guild Thief grants Rat Pack, which stacks, and Leadership, which doesn't). Support is the exception: it comes from Discord roles.
10. **Level conditions.** A bonus can depend on the **recipient's** level (the Cult of the Dragon). A character with no level recorded doesn't receive level-based bonuses, and `/mybonus` notes this.
11. **Only counted players give or receive.** Anyone sitting out (the DM running the game, observers) is left out entirely. A player in the channel with no character set up still gives bonuses that come from their Discord roles (Support), but nothing that needs a character.
12. **Conditional bonuses stay out of totals.** A bonus whose catalog entry has a condition the bot can't check (e.g. "allies in the same range") is listed separately for each recipient it could apply to, e.g. `+5 CM if in the same range as Chris (Commanding Presence)`. It follows every other rule (allies, stacking, audience) but is never added to totals or exported.
13. **Only totals are shown by default.** `/partybonus` and `/mybonus` show totals only. `/breakdown` shows every contributor and the working.

Worked example (Support): each character whose player has Junior Adventurer or above (Junior Adventurer, Guild Veteran, Guild Vanguard, Guild Champion, Guild Legend) gives +2 CM to allies. With five of them present, other characters get +10 and each of the five gets +8.

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
| CH-1 | A player can register several characters, each with a name that is unique on the server (ignoring case), so a name always means one character. A name that's taken is refused with a suggestion to pick a variant. Each character records the Discord user who registered it, and only that user can change it. Names autocomplete in commands. | M |
| CH-2 | A player can **rename** their own characters, e.g. to fix a typo or free a name. Characters **can't be deleted**: a character that's no longer played simply isn't made current, and counts for nothing. A player who really needs one removed asks with `/request` (CT-9), and the maintainer removes it from the database. | M |
| CH-3 | **Current character:** each player has one **current** character, set with `/play <character>`. It stays until changed. A player's first registered character becomes current automatically, so most players (one character each) never need `/play`. Commands with no character named use the current character. | M |
| CH-4 | **Optional level per character:** 1 up to a configurable maximum (currently 75). It can be left blank. | M |
| CH-5 | Level-based bonuses only apply to characters with a recorded level. `/mybonus` notes any bonus missed because the level is missing. The note appears only when recording a level would get the character the bonus: a character outside the bonus's audience is told they're not in the audience, not that their level is missing. | M |
| CH-6 | The date each level was last updated is stored and shown in `/breakdown`. It's shown as a date-only Discord timestamp (NF-10), which Discord displays as an ordinary date in each reader's own format and time zone. | S |

### 6.2 The Catalog

The catalog lives in the repository as data files: `catalog/stats.yaml`, `catalog/skills.yaml`, `catalog/guilds.yaml` (guilds and their rank and boon entries) and `catalog/items.yaml` (items and titles). Section 8 lists the starting catalog.

| ID | Requirement | Pri |
|---|---|---|
| CT-1 | **Fixed catalog.** Stats, skills, guilds, ranks, boons, items and titles are defined only in the catalog files. There are no commands to create or change them. | M |
| CT-2 | **Permanent IDs.** Every catalog entry has a permanent ID separate from its display name. Characters store the ID, so renaming an entry never breaks a character. | M |
| CT-3 | **Linked, not copied.** Characters refer to catalog entries. Changing an entry's value in the catalog changes it for every character at once. | M |
| CT-4 | **Entry fields:** name, kind (skill, boon, rank, item, title), tree or guild, what it gives (one or more stats with amounts, effect text, or nothing), audience (party, one guild, or other holders of the same entry), whether the giver is included (default no), whether it stacks (default yes), whether only one character may hold it at a time (default no; HV-6), what it replaces, tags (e.g. `aura`), modifiers, a condition (which makes it a conditional bonus, rule 4.12), level rules, and the card text quoted from the source. | M |
| CT-5 | **Guild fields:** full name, short name, membership (Discord roles, or players join themselves), whether it's secret, and optional text telling players how to join (e.g. for Patreon Bonuses, "Guild tiers are derived from the AWT Patreon" with its link, shown instead of `/guild join`). A guild whose membership comes from Discord roles lists them lowest first. The guild's rank and boon entries name the guild they belong to. A rank entry can grant **several abilities**, each with its own entry fields (CT-4): what it gives, audience, whether the giver is included, whether it stacks. | M |
| CT-6 | **Retire, don't delete.** An entry that leaves the game is marked `retired`. It can't be added any more, but characters who have it keep it, and `/breakdown` marks it as retired. | M |
| CT-7 | **Validation in CI.** Every push checks the catalog: the format is valid, stat and entry references exist, and there are no duplicate IDs or names. CI also compares the catalog with its previous version in git: **no previously released entry may disappear**, whether or not any character uses it (CI can't see character data, which lives only in the production database). To take an entry out of the game, mark it `retired` (CT-6). An invalid catalog can't be deployed. | M |
| CT-8 | **`/catalog [entry or guild]`** shows what an entry gives, with its card text and the exact `/add` command to add it. With no argument it lists everything available, grouped by kind and tree or guild. **Guild entries are shown only for guilds the player's current character belongs to**: a character can't use them until it joins. A player with several characters uses `/play` first to browse for another one. Other guilds are listed by name with the command to join (`/guild join <character> <guild>`), but not their bonuses. For a guild whose membership comes from Discord roles, `/catalog` shows each bonus with the roles that give it (e.g. *Support Tiers: Junior Adventurer, Guild Veteran, …*) and the text on how to join. The full list ends with how to ask for a missing or wrong entry with `/request` (CT-9), and so do replies when `/catalog` or `/add` finds nothing by that name. Replies are always private. It doesn't show which characters have an entry; `/breakdown` does that. | M |
| CT-9 | **`/request <text>`** lets any player suggest a missing or wrong entry, or ask the maintainer for anything the bot can't do itself (e.g. removing a character, or freeing a one-holder title whose holder has left). The bot posts it, with the player's name, to a configured channel the maintainer watches. | M |

### 6.3 What Characters Have

| ID | Requirement | Pri |
|---|---|---|
| HV-1 | **`/add <character> <entry>`** gives a character a skill, boon, rank, item or title from the catalog. **`/remove`** takes away anything the character has, with no restrictions. In practice it's mostly used for items that are lost or given away. `/remove`'s autocomplete lists what the character has. Autocomplete for `/add` shows entries labeled with their kind and tree or guild, e.g. "Holy Aura (Holy Knight skill)". **Guild entries (ranks and boons) appear only for guilds the character belongs to.** If `entry` is filled in before `character`, autocomplete uses the player's current character. | M |
| HV-2 | **`/guild join <character> <guild>`** and **`/guild leave`** set a character's guild membership. Joining grants nothing by itself; ranks and boons are then added with `/add`, and the reply to `/guild join` says so for guilds with ranks (e.g. *"Now add your rank: `/add Chris Footpad`"*). Leaving **removes the character's ranks and boons from that guild**, and the reply lists what was removed. | M |
| HV-3 | **Support** comes from Discord roles, not from `/guild join`. A player with **Junior Adventurer or above** (any of the Guild rank roles: Junior Adventurer, Guild Veteran, Guild Vanguard, Guild Champion, Guild Legend) gives Support, **once**, whichever of these roles they have and however many. The role doesn't change the amount. Support applies to whichever character the player is counted with, or to the player with no character set up (SE-5). `/breakdown` shows the giver's Guild rank role next to their name; a player with more than one has them all shown. Roles are checked each time totals are calculated. | M |
| HV-4 | **Checks when adding.** Autocomplete isn't a lock (a player can type any text), so the bot checks when the command runs. Adding a rank or boon from a guild the character isn't in is **refused**, with the command to join, e.g. *"High Inquisitor is a Cult of the Dragon rank, and Crateris isn't a member. Join first: `/guild join Crateris Cult of the Dragon`"*. Adding Devotion III with no auras only **warns**. Rank itself is never checked: players add the ranks they've earned. | M |
| HV-5 | **Audit log.** Every change to a character (entries, guilds, level, name) is written to the audit log, with who made it and when. There's no command to read it; the maintainer can read it from the database if a dispute comes up. | M |
| HV-6 | **One holder at a time.** Some entries can be held by only **one character** on the server at a time: today **High Inquisitor** and **Champion of Power**. `/add` **refuses** such an entry while another character holds it, naming the holder, e.g. *"Champion of Power is held by Ioseph. Only one character can hold it at a time."* The title passes on when the current holder `/remove`s it (or leaves the guild, for a guild rank). If the holder can't or won't, the new holder asks with `/request` (CT-9), and the maintainer removes it in the database (AD-2). | M |

### 6.4 Secret Guilds

The Guild of Thieves' rules say "never reveal another member". Even thieves don't automatically know who the other thieves are.

| ID | Requirement | Pri |
|---|---|---|
| SG-1 | A guild can be marked **secret** in the catalog. Today only the Guild of Thieves is. | M |
| SG-2 | `/guild join` and `/guild leave` for a secret guild, and `/add` or `/remove` of its rank entries, reply privately. | M |
| SG-3 | The bot never lists a secret guild's members: not in the party `/breakdown`, or in anyone's *not applied* list. | M |
| SG-4 | Secret guild bonuses are **included in totals** everywhere, including the public `/partybonus`. The party `/breakdown`, for everyone (members included), and any `/breakdown <character>` except a member's own (SG-5), show them as one unnamed "secret guild bonus" block, and as unnamed amounts in the working. It never names a giver. This is deliberately light: the secrecy is tongue-in-cheek, and members are usually easy to work out (e.g. from the CR stealth column). Labeling it "secret guild" plays along with the joke; it isn't meant to be airtight. | M |
| SG-5 | A member's private `/mybonus` and `/breakdown <character>` **for their own character**, when that character is in the secret guild, show the secret bonuses in detail, with **how many** members contributed but not who (e.g. "Rat Pack +1 (1 other member present)"). Looking up anyone else's character, even a fellow member's, shows the unnamed view (SG-4), so members don't learn who the other members are. | M |

### 6.5 Presence (Voice Channel)

There are no sessions to start or end. Each time a command runs, the bot looks at who is in the voice channel and counts them, with these exceptions:

- **Sitting out:** anyone who has used `/sitout` in the last 12 hours. This covers the DM running the game and players who are only observing.
- **No character set up:** members with no usable character are still counted as players. They give only bonuses that come from their Discord roles, and are listed separately so they know to set up a character (SE-5).

| ID | Requirement | Pri |
|---|---|---|
| SE-1 | **Which channel:** `/partybonus` and the party `/breakdown` use the voice channel the caller is in. `/mybonus <character>` and `/breakdown <character>` use the voice channel the character's player is in. `channel:<voice channel>` picks one explicitly. | M |
| SE-2 | **`/sitout`** leaves the caller uncounted for **12 hours** (configurable). `/sitin` ends it early. Players only sit **themselves** out, e.g. because they're running the game or just listening in. Remembering to do it is each player's responsibility. | M |
| SE-3 | **One character per player:** each player is counted with their **current** character (CH-3). Players play one character per event; a player switching characters runs `/play` first. | M |
| SE-4 | `/partybonus` and `/breakdown` end with a *not counted* line listing everyone in the voice channel who is sitting out, with the time it ends. People sitting out who aren't in that voice channel aren't listed. | M |
| SE-5 | **No character set up:** a member in the voice channel with no usable character is still **counted as a player**, under their Discord name. They **give** only Support (from Discord roles). They **receive** bonuses like anyone else, except level-based, guild-only and holder-only ones (e.g. Hero of Passion). `/partybonus` and `/breakdown` list them in a **NO CHARACTER SET UP** section with the fix (`/character register` or `/play`). | M |
| SE-6 | Bots in the voice channel (e.g. music bots) are ignored and never listed. | M |

### 6.6 Output Commands

| ID | Requirement | Pri |
|---|---|---|
| OUT-1 | **`/partybonus`**: a table of the roll-stat totals each counted character receives (CM, CR, and only the CR subtypes that differ from CR for someone), then combat notes (with their descriptions), effects, conditional bonuses (with their conditions, not in totals), and the *not counted* line. Totals only. The heading names the voice channel as a Discord channel mention (`<#…>`), which Discord shows as the channel's name. | M |
| OUT-2 | **`/mybonus [character]`**: totals for one character (roll stats, combat notes, effects, and conditional bonuses listed separately), plus a single line about any bonus missed because the level is missing. Totals only. | M |
| OUT-2a | **Not-current character notice:** when `/mybonus <character>` or `/breakdown <character>` names a character who isn't its player's current character, the bot works out the totals **as if that character were playing in place of the current one**, and shows a notice at the top, e.g. *"Crateris isn't your current character (you're playing Chris). These totals show Crateris in Chris's place. Use `/play Crateris` to switch."* When someone other than the character's player runs the command, the totals are worked out the same way, and the notice reads e.g. *"Crateris isn't currently being played (Elowen is). These totals show Crateris in Elowen's place."* The `/play` hint is shown only to the character's own player. | M |
| OUT-3 | **`/breakdown`** (whole party): for **each bonus in play**, its name and source (skill tree, guild, boon, rank, item or title), what it gives and to whom, and **every contributing character** with their rank or level where it matters. Then: effects, the working for each character's totals (e.g. `CM 2+2+3+5 = +12`), and the *not counted* line. Secret guilds follow SG-4. | M |
| OUT-3a | **`/breakdown <character>`**: each stat that character receives, the sum written out, and every contribution with the bonus name, giver and value (including modifiers, e.g. "Holy Aura +3 (2 + 1 Devotion III)"). Then: bonuses **not applied** to them, with the reason (every bonus or effect shown in the party `/breakdown` that this character doesn't receive, e.g. not in the guild, doesn't hold the title, is the giver, or has no level recorded; replaced entries and not-stacked duplicates aren't listed, and secret guild bonuses follow SG-3), and what the character **gives**. | M |
| OUT-3b | Discord messages are limited to 2,000 characters (4,096 in an embed). Longer output is split across several messages or pages, never cut off. | M |
| OUT-4 | If the character's player isn't in a voice channel, or is sitting out, `/mybonus` and `/breakdown <character>` show what the character **gives**, and explain why there are no totals (no party present, or sitting out until when). | M |
| OUT-5 | **Who sees replies.** `/partybonus` posts **publicly** by default, so the whole party sees the table; `private:true` makes it a private check instead (e.g. when rerunning it as people join). Every other reply is **always private** (only the person who ran the command sees it), with no option: `/mybonus`, `/breakdown` (party or character), `/catalog`, and all setup commands. | M |
| OUT-6 | A player can look up anyone's character (subject to SG-3). | S |
| OUT-7 | Output never uses pronouns for characters ("to Kael", not "to himself"). | M |
| OUT-8 | **Live `/partybonus`:** a public `/partybonus` message that the bot keeps editing when people join or leave the voice channel, sit out or in, or change characters. Edits are batched over a few seconds (to stay within Discord's rate limits), and it stops updating once the channel has been empty for a while (e.g. 15 minutes). It isn't pinned, since pinning needs the *Manage Messages* permission (NF-11). | C |
| OUT-9 | **`/help`**: a short guide for players getting started, in one private message. **Set up** (once per character): `/character register` (the level is optional and only used for level-based bonuses), `/guild join`, `/add`, `/catalog`, and `/request` for anything the character has that isn't in the catalog; and that Support comes from the Guild rank roles automatically, with nothing to add. **Game night:** being in the voice channel is how players are counted, with nothing to start; `/sitout` and `/sitin` for anyone running the game or watching; `/partybonus` (posted for everyone), `/mybonus` (only for the player) and `/breakdown`. Then a note that a player with several characters uses `/play` before the game. It ends with **the player's next step**, worked out from their data: with no character, register one; with characters but none current, choose one with `/play`; with a current character that has nothing added, add what it has with `/add` (and see `/catalog`); otherwise, that they're set up, and how to see the party's bonuses on game night. | S |

### 6.7 Administration and Review

| ID | Requirement | Pri |
|---|---|---|
| AD-1 | **Settings live in the repository**, in `config/settings.yaml`, not in Discord commands: the `/request` channel (`#bonus-bot-support`), sit-out duration (default 12 h) and maximum level (75). Changing one is a commit and an automatic deploy, like a catalog change. Secrets (bot token, storage credentials) stay in environment variables (NF-9). | M |
| AD-2 | **Review:** anyone, typically the DM, can check the party `/breakdown` during a game to catch mistakes and abuse, and ask the owner to fix their character. The maintainer can correct data in the database as a last resort. | M |

## 7. Commands

```
Game night (players)
/partybonus [channel:<voice>] [private:<bool>]     public by default
/mybonus [character] [export:<bogsy>]              always private; export is for later (M6)
/breakdown [character] [channel:<voice>]           always private
/play <character>
/sitout   /sitin

Setup (players, for their own characters)
/character register name:<text> [level:<n>]
/character list | rename <character> <new>
           | level <character> <n|clear>
/add <character> <entry>              skill, boon, rank, item or title
/remove <character> <entry>
/guild join <character> <guild>
/guild leave <character> <guild>
/catalog [entry or guild]
/request <text>

Getting started
/help                                 how to set up and play, and your next step
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
| CR escape | Roll (CR subtype) | Challenge rolls to escape combat. |
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
| Commanding Presence | Commander | +5 CM | Conditional: allies in the same range, so shown separately and not in totals. Not an aura (DM question Q1). |
| Inspiring Presence | Commander | +5 CR | Doesn't stack. Not an aura (Q1). |

### 8.3 Guilds

| Guild | Membership | Entries added with `/add` |
|---|---|---|
| **Patreon Bonuses** | Discord roles: Junior Adventurer, Guild Veteran, Guild Vanguard, Guild Champion, Guild Legend | None. **Support** comes from the roles, Junior Adventurer and above: +2 CM to allies. Guild tiers are derived from the AWT Patreon. |
| **Guild of the Timeless Heroes** (GoTH) | `/guild join` | Boons: **Nuyaru's Love** +1 CM to allies; **Seraph's Affection** +3 CM to allies, replaces Nuyaru's Love (Q3). Length of service isn't tracked. |
| **Guild of Thieves** (secret) | `/guild join` | Ranks **Footpad**, **Burglar** (replaces Footpad) and **Guild Thief** (replaces both). Every rank grants **Rat Pack:** +1 CM and +1 CR escape to other members. Guild Thief also grants **Leadership:** +2 CM and +2 CR stealth to all members, the giver included; doesn't stack. (Q6) |
| **Pirate Coalition** | `/guild join` | Rank **Captain** (King of the Pirates): +2 CM to all members, the giver included; doesn't stack. |
| **Cult of the Dragon** | `/guild join` | Rank **High Inquisitor** (Cult of the Dragon): to other members, level under 10: +1 heart damage; level 10 or higher: +10 CM. **One holder at a time** (HV-6). Doesn't stack (Q2). |
| **Ranger's Guild** | `/guild join` | Ranks **Ranger Captain** and **Master Ranger** (replaces Ranger Captain), each with Wilderness Lore: effect: challenge rolls to resist natural effects are one roll category easier, for the giver and allies. |
| **Order of Cookery** | `/guild join` | Ranks **Chef** and **Cookery Master** (replaces Chef), each with Proper Seasoning: effect: +1 heart when Invigorated, for the giver and allies. |

Ranks that grant no party bonus (e.g. Journeyman, Swabbie) aren't in the catalog.

Guilds with no always-on bonuses to others (Bards, Monks, Fighters, Hunters, Physicians, Lorekeepers) aren't in the catalog. They can be added if one is needed as an audience.

### 8.4 Items and Titles

| Entry | Kind | Gives (to allies) | Status |
|---|---|---|---|
| Wills ward stone | Item | +5 CM | To confirm (Q4) |
| NF (nobuFest pin) | Item | +1 CM to **NF pin holders only**, the holder included; stacks (with three holders present, each gets +3) | Amount to confirm (Q4) |
| Champion of Power | Title | +5 CR, +5 CM. **One holder at a time** (HV-6). | To confirm (Q4) |
| Hero of Passion (HoP) | Title | +1 or more, to **other HoP holders only** | Amount to be defined (Q5) |
| Helping Hands | Title | Nothing itself. **Modifier:** +1 to each numerical value of every bonus this character gives allies. Card text: "Anytime you buff or heal an ally/allies the numerical value is increased by 1." | Scope to confirm (Q7) |
| Helping Hands v2.0 | Title | As Helping Hands, but +2; replaces Helping Hands | Scope to confirm (Q7) |
| Power Supporter | Title | No party bonus | Listed for completeness |
| Charitable Adventurer | Title | No party bonus | Listed for completeness |
| Element Savant | Title | No party bonus | Listed for completeness |
| Joy-Maker | Title | No party bonus | Listed for completeness |
| Story Teller | Title | No party bonus | Listed for completeness |
| Spook Survivor | Title | No party bonus (its +2 CR vs fear is for the holder only) | Listed for completeness |

Titles with no party bonus can still be added with `/add`; they show in `/catalog` and in what a character has, but never change totals.

Some bonuses players have been counting have no known source yet; see "Waiting on players" in section 16.

## 9. Example

The sample game uses the test catalog in `tests/fixtures/`, which keeps some older names: *the Guild* (now Patreon Bonuses) and *High Priest* (now High Inquisitor). Its output below matches the test snapshots.

### 9.1 Sample game

Voice channel: *AWT Voice*. DM Sam and Bob, an observer, are in the channel but have used `/sitout`. Dana has just joined the server, has no Guild rank role, and hasn't registered a character. Counted characters:

| Character | Level | Discord role | Guilds | Has |
|---|---|---|---|---|
| Ioseph | 34 | Guild Vanguard | GoTH | Nuyaru's Love, Seraph's Affection, Champion of Power |
| Kael | 8 | Junior Adventurer | Cult of the Dragon | |
| Crateris | 22 | | Cult of the Dragon | High Priest, Holy Aura, Bolstering Aura, Protective Aura, Devotion III, Wills ward stone |
| Chris | not recorded | | Guild of Thieves | Guild Thief, Inspiring Presence |
| Mira | 15 | | Guild of Thieves, Cult of the Dragon | Footpad, Inspiring Presence |

What's in play:
- **Support:** +2 CM each from Ioseph and Kael.
- **Seraph's Affection:** +3 CM from Ioseph. It replaces Nuyaru's Love.
- **Champion of Power:** +5 CR and +5 CM from Ioseph.
- **Crateris's auras, with Devotion III:** Holy Aura +3 CR vs fear, Bolstering Aura +3 CM, and the Protective Aura effect.
- **Wills ward stone:** +5 CM from Crateris.
- **Cult of the Dragon:** the High Priest (Crateris) gives Kael (level 8) +1 heart damage, and Mira (level 15) +10 CM.
- **Inspiring Presence:** Chris and Mira both have it. It doesn't stack, so allies get +5 CR once. Chris and Mira each still get +5 from the other.
- **Secret guild bonuses:**
  - Rat Pack (every Thieves rank): Chris and Mira each get +1 CM and +1 CR escape from the other.
  - Leadership: Chris is a Guild Thief, so both get +2 CM and +2 CR stealth, Chris included.

`/partybonus` (public):

```
PARTY BONUSES: AWT Voice (6 counted)
-------------------------------------------------
CHARACTER   CM    CR    CR vs fear   CR stealth   CR escape
Ioseph      +10   +5    +8           +5           +5
Kael        +18   +10   +13          +10          +10
Crateris    +12   +10   +10          +10          +10
Chris       +23   +10   +13          +12          +11
Mira        +33   +10   +13          +12          +11
Dana*       +20   +10   +13          +10          +10
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

`/breakdown` (whole party; private, as seen by someone who isn't a Guild of Thieves member):

```
PARTY BREAKDOWN: AWT Voice (6 counted)
-------------------------------------------------
Support (the Guild): +2 CM to allies from each giver
    Ioseph     Guild Vanguard
    Kael       Junior Adventurer

Seraph's Affection (GoTH boon): +3 CM to allies
    Ioseph                           (replaces Nuyaru's Love)

Champion of Power (title): +5 all CR, +5 CM to allies
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

Secret guild bonus: +3 CM, +2 CR stealth and +1 CR escape to each member present
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
           CR stealth 10+2s = +12       CR escape 10+1s = +11
Mira       CM 2+2+3+5+3+5+10+3s = +33   CR 5+5 = +10   CR vs fear 10+3 = +13
           CR stealth 10+2s = +12       CR escape 10+1s = +11
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
CR escape = 10 (all CR) = +10
-------------------------------------------------
NOT APPLIED
  Holy Aura, Bolstering Aura, Protective Aura, Wills ward stone    allies only (Crateris is the giver)
  Cult of the Dragon                                               allies only (Crateris is the giver)
-------------------------------------------------
CRATERIS GIVES
  Holy Aura +3 CR vs fear (2 + 1 Devotion III)
  Bolstering Aura +3 CM (2 + 1 Devotion III)
  Protective Aura: resistance to damage from an Evil source
  Wills ward stone +5 CM
  Cult of the Dragon (High Priest)
```

The "updated" date is a Discord timestamp (CH-6, NF-10), so each reader sees it as an ordinary date in their own format; it's shown here as 2026-09-20.

`/mybonus Mira` (private; Mira is a Guild of Thieves member):

```
MIRA (level 15): AWT Voice
-------------------------------------------------
CM          +33
CR          +10
CR vs fear  +13
CR stealth  +12
CR escape   +11
-------------------------------------------------
Resistance to damage from an Evil source (Protective Aura)
-------------------------------------------------
Secret guild (Guild of Thieves), included above:
  Rat Pack     +1 CM, +1 CR escape (1 other member present)
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
| NF-8 | **Operations:** structured logs, written to standard output as **JSON lines** (one JSON object per line) so the host collects them. Every line has `time` (UTC, ISO 8601), `level` and `event`. Each command logs one line with the command name, the Discord user ID, the outcome (`ok`, `refused` or `error`) and its duration; startup, shutdown, reconnects, migrations and snapshots are logged too, and errors include the traceback. Logs never contain the bot token, storage credentials, reply text or message content. Nightly off-site database snapshots (section 12.1). |
| NF-9 | **Security:** the bot token and storage credentials live only in environment variables or the host's secret store. |
| NF-10 | **Time zones:** every time the bot stores or checks (sit-out expiry, level "last updated", audit log, snapshots) is in **GMT (UTC)**, never the host's local time. Times shown to players use Discord timestamps (`<t:…>`), which Discord displays in each reader's own time zone. |
| NF-11 | **Least privilege:** the bot is invited with only View Channels, Send Messages, Embed Links and Use Application Commands. Never Administrator. |
| NF-12 | **Protecting automatic deployment:** because a push to `main` deploys to the server, the GitHub account uses two-factor authentication, `main` is protected (CI must pass), and deploy credentials live only in GitHub secrets. Dependencies are kept current with Dependabot. |

## 11. Data Model and Engine

The **catalog** and **settings** aren't stored in the database. They're loaded from `catalog/*.yaml` and `config/settings.yaml` at startup, and the database stores only catalog IDs. All timestamps are GMT (UTC).

```
Player          (discord_user_id, current_character_id NULL)
Character       (id, discord_user_id, name UNIQUE NOCASE, level NULL, level_updated_at)
CharacterEntry  (character_id, entry_id)                  -- skill, boon, rank, item or title (catalog ID)
CharacterGuild  (character_id, guild_id, joined_at)       -- catalog ID
SitOut          (discord_user_id, until)
AuditLog        (id, actor_user_id, character_id, action, before_json, after_json, at)
```

Support isn't stored. It's worked out on each calculation from the player's current Discord roles.

**Calculation engine:** a pure function with no Discord or database code:

```
compute(present_players, player_roles, character_entries, character_guilds, catalog) -> PartyReport
```

`present_players` lists every member in the voice channel: Discord user ID and name, whether it's a bot, the end of any **active** sit-out, and the character they're counted with (ID, name and level), or none. The caller checks sit-outs against the clock and applies the OUT-2a substitution before calling, so the engine never needs a clock, Discord or the database.

0. **Who is counted:** members in the voice channel (excluding bots), minus anyone with an active sit-out. Each counted player uses their current character, or a stand-in with no character if none is set up. For OUT-2a, the named character replaces its player's current character.
1. **Work out memberships:** each character's guilds, plus the Guild rank from their player's Discord roles.
2. **List the gives:** each counted character's entries (after replacements, and with modifiers such as Devotion III applied), each ability their rank entries grant, and Support.
3. **Apply them to recipients:** for each recipient, check each give against the audience, whether the giver is included, and any level rule. Record it as *applied* (with its amount) or *not applied* (with a reason: giver excluded, not in audience, no level, replaced, or not stacked).
4. **Stacking:** for gives that don't stack, keep one per recipient (the highest amount).
5. **Add up:** total each stat, then add parent-stat amounts into subtypes. Conditional gives are kept in a separate list and never added.
6. **Display:** `PartyReport` holds everything, including which gives come from secret guilds. The output layer applies the secrecy rules (section 6.4).

## 12. Technology, Storage and Deployment

| Layer | Choice | Why |
|---|---|---|
| Language | **Python 3.12+** | Readable, quick to iterate on with Claude Code. |
| Discord library | **discord.py 2.x** (`app_commands`) | Mature and maintained; slash commands and autocomplete. |
| Database | **SQLite** (WAL mode) | A single file, no database server to run. Plenty for one server. |
| ORM / migrations | **SQLAlchemy 2.0 (async)** + **aiosqlite**, **Alembic** | Typed models; versioned schema changes. |
| Catalog | **YAML** files validated with **pydantic** | Easy to edit by hand; checked in CI. |
| Config | **pydantic-settings** | Typed settings from `config/settings.yaml`; secrets from environment variables. |
| Testing | **pytest**, **pytest-asyncio**, **hypothesis** | Property tests fit the counting rules well. |
| Quality | **ruff**, **mypy**, **pytest-cov** | Lint, format, type-check; enforce 90% branch coverage on the engine. |
| Packaging | **uv** + `pyproject.toml` | Fast, reproducible. |
| Deploy | **Docker** on **Fly.io**: one machine with a persistent volume | Needs a process that's always running; the host restarts it and collects its logs. |
| CI/CD | **GitHub Actions** | Lint, type-check, test, validate the catalog, build and deploy. |
| Backups | Nightly `sqlite3 .backup` snapshots to **Backblaze B2** (S3-compatible) | Meets NF-8; off-site from the host; see 12.1. |

**Decided: Python.** It's the easiest to read and review, Hypothesis is the strongest fit for the property tests (TS-3) and the 90% coverage target, and its dependency tree is smaller than npm's. TypeScript + discord.js was the runner-up; C# and Go were ruled out as more code for the same bot.

**Python-specific security:** the catalog and settings are read with `yaml.safe_load` (never `yaml.load`, which can run code) and validated with pydantic. Dependencies are locked with hashes in `uv.lock`.

### 12.1 Storage and Backups

**Where the data lives:** a single **SQLite** file (by default `var/awt-bonus.db`) on the same machine as the bot. The `var/` folder is git-ignored; the catalog in `catalog/` is committed. Nothing is stored in Discord. Roles and voice presence are read live from Discord each time a command runs.

**Hosting:** Craig hosts the bot at launch on Fly.io: one machine, with a persistent volume mounted at `/data` (`DATABASE_URL=sqlite+aiosqlite:////data/awt-bonus.db`). Long-term hosting is an open question (section 16).

| Hosting | Location of the database file |
|---|---|
| Small VPS | The VPS's disk, mounted into the container as a Docker volume, e.g. `/srv/awt-bonus/var/` |
| Fly.io | A **persistent volume** mounted at `/data` |
| Local PC (development/testing) | A `var/` folder next to the code (git-ignored) |

| ID | Requirement | Pri |
|---|---|---|
| DB-1 | The database path is set by configuration (`DATABASE_URL`), never hard-coded. | M |
| DB-2 | The database must be on **persistent** storage. The bot refuses to start if the path is on a known temporary filesystem, or if it can't write a test file next to the database. Known temporary filesystems: on Linux, a tmpfs or ramfs mount, or a path under `/tmp`, `/var/tmp` or `/dev/shm`; on Windows, a path under `%TEMP%`. The default location, the project's own `var/` folder next to the code (section 12.1), is persistent and passes the check; only the system's `/var/tmp` is temporary. The check runs at bot startup, not whenever the database is opened, so tests can use temporary database files (TS-11). | M |
| DB-3 | SQLite runs in **WAL mode** with a busy timeout. Only **one** bot process uses the file at a time: the bot takes an exclusive lock on a file next to the database at startup and refuses to start if another process holds it. | M |
| DB-4 | **Schema changes** only happen through Alembic migrations. They run automatically at startup, after a snapshot is taken first. | M |
| DB-5 | **Continuous replication:** Litestream streams every change to object storage, so at most seconds of changes are lost instead of up to a day. Not needed at launch: losing a day of character changes costs players a few minutes of re-entering. | C |
| DB-6 | **Nightly snapshots:** a full `sqlite3 .backup` copy goes to the same object storage every night and is kept for 30 days. | M |
| DB-7 | **Restore is documented and tested:** a written runbook covers restoring onto a new host. It's tried at least once before AWT goes live. | M |

**Where snapshots go:** a private Backblaze B2 bucket. The bot uploads with a write-only application key limited to that bucket, set in `BACKUP_KEY_ID` and `BACKUP_KEY` (NF-9). The bucket's lifecycle rule deletes snapshots after 30 days.

**Expected size:** well under 10 MB. Storage costs are pennies a month.

### 12.2 Deployment

| ID | Requirement | Pri |
|---|---|---|
| DP-1 | **Automatic deployment:** every push to `main` that passes CI (tests, type checks, catalog validation) is deployed automatically. | M |
| DP-2 | **Branches:** experimental work happens on branches and reaches `main` by merge. Only `main` is deployed. | M |
| DP-3 | **Catalog changes are ordinary commits.** Adding a skill or title is an edit to a data file, a push, and an automatic deploy: a few minutes end to end. | M |
| DP-4 | **Safe restarts:** a deploy restarts the bot in a few seconds without losing data, so deploying during a game is harmless. | M |

**How a push reaches the bot:** when CI passes on a push to `main`, the deploy workflow (`.github/workflows/deploy.yml`) runs `flyctl deploy` with a deploy-only Fly token kept in a GitHub secret (NF-12). Fly builds the Docker image, stops the running bot, which shuts down cleanly and releases its lock (DB-3), and starts the new one on the same volume.

## 13. Testing Strategy

Most of the checking is done by fast automated tests that never touch Discord. Live testing in Discord only confirms the Discord-specific parts, and a trial at AWT, with DMs checking the numbers, proves the bot in real games.

### 13.0 Tests First, and the Test-Change Rule

The functional tests are written **before any bot code** (milestone M1), from this document alone. They are the executable form of the requirements: the code is built to pass them, not the other way round.

| ID | Requirement | Pri |
|---|---|---|
| TF-1 | **Tests first.** Milestone M1 writes the functional tests for every requirement, derived only from this document, before any bot logic exists. Tests check behaviour (e.g. "Chris's CM is +23", "the reply is private"), not exact layout. | M |
| TF-2 | **Test harness defined up front.** M1 fixes the interfaces the tests call, as stubs with no logic: the engine's `compute(...)` and its result; a command layer that takes a user, a command and its options and returns the reply text and whether it's private; a fake Discord (voice members, roles, bots); and a fake clock. Later milestones implement these interfaces without changing them. | M |
| TF-2a | **Mock data.** M1 also creates the test fixtures, as YAML in `tests/fixtures/`: players, characters, levels, guild memberships, entries and sit-outs (the section 9 sample game, plus small fixtures for edge cases); the fake Discord's voice channels, members, roles and bots; and a fixed GMT time for the fake clock. Each test loads its fixture into a fresh temporary database, so every run sees the same data. Fixtures are test files, covered by TF-5. | M |
| TF-3 | **Traceability.** Every test names the requirement ID(s) it checks (e.g. `HV-4`), and the rule questions it depends on (e.g. `Q7`). The DM rule questions ([dm-rule-questions.md](dm-rule-questions.md)) are documentation for the DMs, not requirements: no test checks their content or number. A coverage table lists every requirement and its tests; every *must have* requirement has at least one. **Requirement IDs are permanent from M1 onward:** they're never renumbered or reused. A removed requirement keeps its row, marked *removed*, so tests and past discussions never point at the wrong thing. | M |
| TF-4 | **Milestone markers.** Each test is marked with the milestone that implements it. CI treats tests for unfinished milestones as expected failures, and requires every test for a finished milestone to pass. The 90% coverage threshold applies from M2. | M |
| TF-5 | **The test-change rule.** A failing test means the **code** is wrong, unless a human confirms the **test** is wrong. A test is **never** changed to make code pass. When a test is believed to be wrong, the only allowed sequence is:<br>1. **Confirm with a human** that the test is wrong, explaining why (Claude Code must stop and ask; it never decides this alone).<br>2. **Fix the requirements document** so it states how the bot should behave.<br>3. **Fix the test** so it matches the corrected requirement.<br>4. **Fix the code** until the test passes.<br>Steps 2 and 3 are committed together, and the commit message names the requirement changed. The same sequence applies when a DM answer changes a rule, starting at step 2. | M |
| TF-6 | **Enforcement.** The rule is written into `CLAUDE.md`, which Claude Code reads in every session. Claude Code asks for permission before editing or overwriting any test file, the pytest settings, the CI workflows or the test-change check. CI fails any change that alters or removes an **existing** test, scenario, fixture or test-harness file, adds a `conftest.py`, removes a finished milestone, changes the pytest settings, or changes the test-change check or CI workflows (updating only the versions of the actions a workflow uses, as Dependabot does, is allowed), unless the same change also edits the requirements document. Adding new tests, new scenarios and new test files is allowed. CI also fails if the bot's code refers to the tests or the test data. The CI check is a required status check on `main`. | M |

### 13.1 Calculation Engine

| ID | Requirement | Pri |
|---|---|---|
| TS-1 | **Scenario files:** engine tests are written as YAML scenarios: who is in the channel, what they have, and the expected totals (and, where relevant, *not applied* lines). They use their own test catalog, so changing a real catalog value doesn't break them. `tests/scenarios/engine-scenarios.yaml` covers every rule in section 4 and the sample game in section 9. Every rules question that comes up becomes a permanent scenario. | M |
| TS-2 | **Edge cases** each get a scenario: no level recorded; level exactly 10; a player with no character but a Guild role; everyone sitting out; an empty channel; the same skill from two characters; bots in the channel; two givers of a bonus that doesn't stack; a replaced boon; a retired entry. | M |
| TS-3 | **Property tests (Hypothesis):** thousands of randomly generated parties check rules that must always hold:<br>• nobody receives their own bonus unless the entry includes the giver;<br>• a bonus that doesn't stack is counted at most once per recipient;<br>• every total equals the sum of the lines `/breakdown` shows for it;<br>• a subtype total is never lower than its parent's;<br>• the order of players doesn't change the result;<br>• removing a giver never increases anyone's total. | M |
| TS-4 | **Catalog validation tests:** the real catalog loads and passes every check in CT-7. | M |

### 13.2 Output

| ID | Requirement | Pri |
|---|---|---|
| TS-5 | **Snapshot tests:** the text of `/partybonus`, `/mybonus` and `/breakdown` for the sample game is saved as reference files and compared on every run. The snapshots are **created in M4**, once the output layout exists and has been approved, and Support (HV-3) and the secret-guild output rules (6.4) are in place; M1 covers the same output with behaviour tests (TF-1). From then on, snapshots follow the test-change rule (TF-5): a mismatch means the output code is wrong unless a human confirms the layout should change. | M |
| TS-6 | **Secrecy tests:** for the sample game, neither the public `/partybonus` nor any non-member's `/breakdown` or `/mybonus` contains a secret guild member's name next to a secret guild bonus, or lists secret guild members. | M |
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
| TS-14 | The test server **mirrors AWT's setup**: the five Guild rank roles, a voice channel, a `#bonus-bot-support` channel (for `/request`), and a music bot. Testing uses two or three people or alt accounts operated by hand. | M |
| TS-15 | A **manual checklist** covers: joining and leaving voice; role changes; bots ignored; autocomplete; public and `private:true` `/partybonus`, and every other reply private; long output splitting; a restart mid-game; `/sitout` / `/sitin`; a member with no character; the not-current character notice; `/request` posting to `#bonus-bot-support`; secret guild privacy; a catalog change deployed automatically. | M |
| TS-16 | **No self-bots:** real user accounts are never automated to drive tests. That breaks Discord's Terms of Service. | M |

### 13.5 Trial at AWT

| ID | Requirement | Pri |
|---|---|---|
| TS-17 | **DM-checked trial:** for the first few games, the DM checks the party `/breakdown` by hand against the rules. Every mismatch is a bug, a rule modeled wrong, or a catalog error. Each becomes a new scenario or catalog fix. | M |
| TS-18 | A few players try `/mybonus` and `/breakdown` and give feedback on how clear the output is before general rollout. | S |

## 14. Optional: Hand-off to Bogsy's Dice Bot

The bot doesn't roll dice. `/mybonus <character> export:bogsy` lists **roll stats only** (CM, CR, CR subtypes) as values for the player to enter with Bogsy's `/modifier`. Combat notes, effects and conditional bonuses are never exported. The exported values are party bonuses only; they add on top of the character's own CM and CR.

| ID | Requirement | Pri |
|---|---|---|
| BG-1 | The export lists each roll stat's modifier name and value, e.g. `awt_cm` = `+33`, `awt_cr` = `+10`, `awt_cr_fear` = `+13`, with copyable text lines (`.awt_cm = +33 "AWT CM"`). | C |
| BG-2 | Modifier names come from the catalog's stat definitions and avoid Bogsy's reserved words. | C |
| BG-3 | The export also lists modifiers to clear (`.awt_cm =`) for stats that are now zero. | C |

## 15. Future Enhancements

- A live `/partybonus` message that updates itself (OUT-8).
- Switching an item off temporarily without removing it (e.g. not equipped).
- Continuous database replication with Litestream (DB-5).
- Stricter type checking (`mypy --strict`).

## 16. Open Questions

**Waiting on the DMs:** see [dm-rule-questions.md](dm-rule-questions.md): Presence skills as auras (Q1), the Cult's level rule (Q2), GoTH boons (Q3), the full item and title list (Q4), the Hero of Passion amount (Q5), whether a Guild Thief keeps Rat Pack (Q6), what Helping Hands does and applies to (Q7), and whether a summoned character's bonuses count (Q8).

**Waiting on players:** these bonuses have been counted, but where they come from (skill, item, title, guild…) isn't known yet. Craig is following up with the players. Each becomes a catalog entry once its source is known:

| Character | What they've been giving | Notes |
|---|---|---|
| Elizor | +2 hearts of damage to allies who have a *passion item* equipped | Conditional on an item the bot doesn't track; likely a conditional bonus (rule 4.12). |
| Elizor | 1 heart of healing per round | |
| Chris the Holy Baker | 2 hearts of damage reduction per round | Once thought to come from Helping Hands. |
| Chris the Holy Baker | Effect: "Effects of extreme cold are negated around Chris the Holy Baker" | |

**For later consideration: long-term hosting.** Craig hosts the bot at launch. If it runs for the long term, decide who pays for hosting, who holds the bot token and backup credentials, who fixes it when it's down at game time, and how it's handed over if Craig steps away.

### Resolved

- **Allies only:** a bonus never applies to its giver, unless the catalog entry says so (Leadership, King of the Pirates, Wilderness Lore, Proper Seasoning).
- **Fixed catalog:** skills, guild abilities, boons, items and titles come from data files in the repository. Players pick from it and can't type in bonuses. Missing entries are requested with `/request`.
- **Catalog changes:** permanent IDs, retired instead of deleted, linked rather than copied, validated in CI, and deployed automatically on push to `main`.
- **Stacking:** every giver counts, except entries marked "doesn't stack", which count once. A replacing entry supersedes the one it replaces.
- **Devotion III** adds +1 to all of the character's own auras, from any tree. Only skills named "Aura" are auras (pending Q1).
- **Characters can't be deleted**, only renamed. This avoids losing data by accident and means a player's current character always exists. The rare removal goes through `/request`.
- **Character names are unique on the server**, not per player, so names are never ambiguous in commands or output. This can be revisited if duplicate names turn out to be common.
- **One `/add` command** (and `/remove`) for skills, boons, ranks, items and titles, rather than one command per kind. Players don't need to know an entry's kind, and `/catalog` shows the exact command for each entry. Guild ranks and boons are only shown (in `/catalog` and autocomplete) and only accepted for members of that guild; leaving a guild removes them.
- **Auras** (Holy Knight and Paladin) have no range limit: they reach the whole party.
- **Position-dependent bonuses** (Commanding Presence's "same range") are conditional bonuses: shown separately, never in totals. The bot doesn't track who is in melee or ranged. "Would hurt" is a CR subtype that players ask about.
- **CM** combines the old combat bonus and combat defence.
- **GoTH boons** are always on. **Bard Inspiration** is out of scope.
- **Guild of Thieves** is secret, tongue-in-cheek: the bot never names members, but public totals still include their bonuses, even though that makes them easy to spot. Leadership needs any Guild Thief present, and a stealth bonus counts toward both CM and stealth CRs. Rat Pack's escape bonus is tracked (escape is a CR subtype); street work and burglary rolls are ignored.
- **Bogsy hand-off** stays a *could have*.
- **Reply visibility:** only `/partybonus` is public (with `private:true` for a quiet check); every other reply is always private.
- **Tech stack:** Python 3.12+ with discord.py, SQLite and SQLAlchemy (section 12).
- **Tests first:** functional tests are written from the requirements before any code (M1). Tests change only when a human confirms they're wrong, and only after the requirements are corrected (TF-5).
- **Titles:** Champion of Power and Hero of Passion (HoP) are titles. HoP goes only to other HoP holders. Titles with no party bonus are listed anyway for completeness.
- **`/request`** posts to `#bonus-bot-support`.
- **The Cult bonus** comes only from the High Inquisitor. The rank entry is *High Inquisitor*; the bonus it gives is named *Cult of the Dragon*.
- **One holder at a time:** High Inquisitor and Champion of Power can each be held by only one character on the server. `/add` refuses a second holder (HV-6).
- **Guilds and ranks:** joining a guild only records membership; nothing is granted automatically. Ranks that grant bonuses and GoTH boons are entries the player adds by name, and a higher rank replaces a lower one. Every Thieves rank (Footpad, Burglar, Guild Thief) grants Rat Pack; Guild Thief also grants Leadership. Rangers and Cookery work the same way. **Rank isn't checked; guild membership is.** Adding a guild's rank or boon requires membership (HV-4); which rank a player has reached is up to them. Support comes from Discord roles.
- **Sit-outs:** players sit only themselves out (when running the game or just listening); the bot doesn't guess.
- **Characters only:** minions, summons, companions and allied NPCs aren't tracked; bonuses apply only to player characters.
- **No DM or admin role** in the bot: everyone has the same commands and changes only their own characters. DMs review informally with `/breakdown`.
- **Times** are stored in GMT (UTC).
- **No master list:** each player enters their own characters.

## 17. Milestones

| Milestone | Scope |
|---|---|
| **M1: Functional tests** | The test harness (interface stubs, fake Discord, fake clock, milestone markers); mock data fixtures (TF-2a); the scenario runner and property tests for the engine; command-level functional tests for sections 6.1–6.7; the requirement coverage table; CI that runs them as expected failures and enforces the test-change rule (section 13.0). No bot logic. |
| **M2: Engine and catalog** | Catalog format and loader with validation; stats; the calculation engine with every rule in section 4. Done when the engine scenario and property tests pass. |
| **M3: Characters and output** | `/character`, `/add`, `/remove`, voice presence, `/sitout` / `/sitin`, `/play`, `/partybonus`, `/mybonus`, `/breakdown`, `/catalog`, and the thin discord.py adapter (TS-8) for live testing on the private test server (TS-13). |
| **M4: Guilds** | `/guild join/leave`, rank entries with several abilities, Support from Discord roles, secret guilds. Once the output layout is approved, the snapshot tests (TS-5) are created. |
| **M5: Ops** | Docker, automatic deployment, persistent storage, nightly snapshots, restore runbook, settings file, `/request`. |
| **M6: Extras** | Bogsy hand-off, `/help` (OUT-9). |

Each milestone from M2 on is done when all of its M1 tests pass, with no test changed except through the test-change rule (TF-5).
