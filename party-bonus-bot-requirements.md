# AWT Party Bonus Bot: Requirements

**Version:** 0.4 (draft)
**Date:** 2026-09-24
**Owner:** Craig
**Server:** Adventures from the Wizards Tower (AWT)

---

## 1. Purpose

Right now, one player keeps a master list of every party bonus. Each session they strike out the bonuses of players who aren't there, then share the list.

This bot replaces that list. Players record the bonuses their characters **give**. The GM defines the bonuses that come from orgs (guilds and other groups). When someone asks, the bot works out totals from the characters who are present:

- `/partybonus`: the totals every present character receives.
- `/mybonus [character]`: the totals for one of your characters.
- `/breakdown [character]`: every bonus in play, who contributes it, and how each total adds up.

Games happen in a Discord voice channel. There's no session to start or end: the bot counts everyone who is in the voice channel when the command runs. Anyone running the game or just watching uses `/sitout`, which lasts 12 hours, to be left out. When someone joins or leaves, running the command again gives an up-to-date answer.

## 2. Scope

### Goals

- Any player can see their character's current totals, and how they were calculated if they want the detail.
- The game's rules are applied correctly: every giver counts; CM bonuses don't apply to the giver, CR bonuses do; org, rank and level conditions are respected.
- Players manage their own characters, levels and personal bonuses. The GM manages stats, orgs, ranks and org bonuses.

### Non-Goals

- **No dice rolling.** At most, the bot hands CM/CR values to an existing dice bot (section 13).
- **No character sheets.** Each character has a name, an optional level, org memberships, and the bonuses it gives. Nothing more.
- **One server only** (AWT).
- No web dashboard.

## 3. Glossary

| Term | Meaning |
|---|---|
| **Player** | A Discord member. Can have several characters. |
| **Character** | One of a player's AWT characters. Levels, guild memberships and personal bonuses are recorded per character. |
| **Level** | Optional, per character. Only used for level-based bonuses. |
| **Stat** | What a bonus adds to. **Roll stats:** CM (combat modifier), CR (challenge roll) and CR subtypes such as *CR vs fear*. **Combat notes:** damage, damage reduction, healing, measured in hearts. Combat notes are shown for information only. |
| **Giver** | The character who provides a bonus. |
| **Recipient** | A present character who receives a bonus. |
| **Giver rule** | Whether a bonus also applies to its giver. **CM: no. CR, damage, damage reduction and healing: yes.** Set per stat. |
| **Org (group)** | A guild, order or faction, recorded with a full name and an abbreviation, e.g. *Guild of the Timeless Heroes* / *GoTH*. Current orgs: the Guild, GoTH, HoP, Cult of the Dragon. More will be added later. |
| **Rank / standing** | A character's standing in an org. It decides what they give. May come from Discord roles. |
| **Org bonus** | A bonus the GM defines once, given by each qualifying member of an org, e.g. *Support: +2 CM*. |
| **Counted / sitting out** | Players in the voice channel are *counted*, with their active character (they give and receive bonuses), unless they have used `/sitout`. The DM running the game sits out the same way. |
| **Personal bonus** | A bonus from one character's own abilities or items, e.g. *Holy auras*. |
| **Effect** | A text-only benefit, e.g. *Effects of extreme cold are negated around Chris the holy baker.* |

## 4. How Bonuses Are Counted

1. **Every giver counts.** Three present characters each giving +2 means the bonus counts three times. This includes the same skill from different characters, e.g. two Holy Knights with Holy Aura give +4 CR vs fear.
2. **CM excludes the giver.** Three characters each giving +2 CM: each of them receives +4, and everyone else receives +6.
3. **CR includes the giver.** Three characters each giving +2 CR: everyone receives +6.
4. **Org bonuses follow the same rules.** Support, GoTH, HoP, the Cult of the Dragon and any future orgs: each qualifying member present gives the bonus. For CM it goes to everyone in the audience **except the giver**. For CR it goes to **everyone** in the audience.
5. **Parent stats flow down to subtypes.** "+5 to all challenge rolls" plus "+3 CR vs fear" means CR +5 and CR vs fear +8.
6. **Audience.** Everyone present (e.g. Support, GoTH) or only members of certain orgs (e.g. Cult of the Dragon: cult members only).
7. **Only counted players give or receive.** Anyone sitting out (the DM running the game, observers) is left out entirely. A player in the channel with no character set up still gives bonuses that come from their Discord roles (e.g. Support), but nothing that needs a character.
8. **Level conditions.** A bonus can depend on the recipient character's level. A character with no level recorded doesn't receive level-based bonuses. `/mybonus` notes this.
9. **Only totals are shown by default.** `/partybonus` and `/mybonus` show totals only. `/breakdown` shows every contributor and the working.

Worked example (Support): each character whose player has one of the Guild rank roles (Junior Adventurer, Guild Veteran, Guild Vanguard, Guild Champion, Guild Legend) gives +2 CM. With five of them present, other characters get +10 and each of the five gets +8.

## 5. Users and Roles

| Role | Can do |
|---|---|
| **Player** | Register and manage their characters; set levels; manage personal bonuses and effects; choose their active character; sit out (`/sitout`); join open orgs; run `/mybonus`, `/partybonus`, `/breakdown`. |
| **GM** | Everything a player can do, plus: manage stats, orgs, ranks and org bonuses; assign characters to orgs; sit any player out or back in; edit any bonus; configure the bot. |
| **Admin** | Set which Discord role counts as GM (default: *Manage Server*). |

## 6. Functional Requirements

Priority: **M** = must have (v1), **S** = should have, **C** = could have (later).

### 6.1 Characters and Level

| ID | Requirement | Pri |
|---|---|---|
| CH-1 | A player can register several characters, each with a unique name on the server. Names autocomplete in commands. | M |
| CH-2 | A player can rename or delete their own characters. Deletion asks for confirmation. | M |
| CH-3 | A player can mark one character as their **default**. Commands with no character named use the player's **active** character (see SE-3), or else their default. | M |
| CH-4 | **Optional level per character:** 1 up to a configurable maximum (currently 75). It can be left blank. | M |
| CH-5 | Level-based bonuses only apply to characters with a recorded level. `/mybonus` notes any bonus missed because the level is missing. | M |
| CH-6 | The date each level was last updated is stored and shown in `/breakdown`. | S |
| CH-7 | A GM can create or fix characters on a player's behalf, and take over characters of players who have left. | S |

### 6.2 Stats

| ID | Requirement | Pri |
|---|---|---|
| ST-1 | The GM manages stats, with aliases and autocomplete. | M |
| ST-2 | **Giver rule per stat:** CM excludes the giver. CR and all combat notes (damage, damage reduction, healing) include the giver. | M |
| ST-3 | **Subtypes:** e.g. *CR vs fear*. Bonuses to the parent stat count toward each subtype. | M |
| ST-4 | **Two kinds of stat:** *roll stats* (CM, CR and CR subtypes), which are totaled and can be exported; and *combat notes* (in hearts), which are totaled and shown but never exported. | M |
| ST-5 | **Each combat note has a description that is displayed with it.** Starting set: **Damage**: extra hearts dealt when attacking. **Damage reduction**: hearts mitigated when attacked. **Healing**: hearts healed at the end of each round. | M |
| ST-6 | **Starting catalog:** CM; CR, with subtype *CR vs fear*; Damage; Damage reduction; Healing. | M |

### 6.3 Orgs (Groups) and Standing

Membership comes from two levels:

- **Player level:** Discord roles. They apply to **every** character that player owns. Example: a player with the *Guild Vanguard* role gives Support with any of their characters.
- **Character level:** org membership recorded per character. One character can be in GoTH while the same player's other character is in the Cult.

| ID | Requirement | Pri |
|---|---|---|
| GR-1 | The GM manages a list of known orgs, each with a **full name** and an **abbreviation**, e.g. *Guild of the Timeless Heroes* / *GoTH*. Either one works in commands, with autocomplete. HoP's full name can be filled in later. | M |
| GR-1a | **`/orgs`** lists every org: full name, abbreviation, how membership works, rank names, and a one-line summary of its bonuses. `/orgs <org>` also shows its members. | M |
| GR-2 | **Membership source per org:** *Discord roles* (player level, applies to all of that player's characters), *GM-assigned* (per character), or *open* (players add or remove their own characters). | M |
| GR-3 | **Ranks:** an org can have ordered ranks. For role-based orgs, each rank maps to a Discord role, e.g. Junior Adventurer … Guild Legend, and the player's highest matching role sets the rank. For GM-assigned orgs, the GM sets each character's rank. | M |
| GR-4 | A character can belong to any number of orgs, and different characters of the same player can be in different orgs. | M |
| GR-5 | Discord roles are checked each time totals are calculated, so role changes on the server take effect straight away. | M |
| GR-6 | `/party` shows who is counted, with each character's orgs and ranks. | S |
| GR-7 | Changes to character-level membership are written to the audit log. | S |

### 6.4 Bonuses

| ID | Requirement | Pri |
|---|---|---|
| BN-1 | **Personal bonuses** belong to a character: a name, one or more stat values, and an optional note. | M |
| BN-2 | **Org bonuses** are defined by the GM: the org, the stat(s), the audience, optionally a minimum rank, and any level rules. The **amount** comes from one of two places: **fixed** by the GM, optionally varying by rank (e.g. Support: +2 CM from every Guild rank), or **set by each member** for their own character, because members of the same org can give different amounts (e.g. one GoTH member gives +1 CM and another +3 CM). | M |
| BN-2a | For member-set org bonuses, each character's `/breakdown` line shows their own amount, and the org's heading shows what they add up to. A member who hasn't entered an amount is flagged as "amount not set" and contributes nothing. | M |
| BN-4 | **Several stats per bonus**, e.g. *Holy auras: +3 CR vs fear, +3 CM*. | M |
| BN-5 | **Audience:** everyone present, or only members of listed orgs. | M |
| BN-6 | Each bonus follows its stat's giver rule, which can be overridden per bonus. | M |
| BN-7 | **Level rules:** the value depends on the recipient's level, and each level band can use a different stat, e.g. *Cult: level < 10: +1 heart damage; level ≥ 10: +10 CM*. | M |
| BN-8 | **Effects:** text-only bonuses, with the same audience options. | M |
| BN-9 | Players can list, edit and remove their characters' personal bonuses. The GM can edit any bonus. | M |
| BN-10 | A bonus can be switched off temporarily, e.g. an item that isn't equipped. Absent characters need no switching: the bot only counts characters who are present. | S |
| BN-11 | **No approval step:** players edit their own characters' bonuses, skills, org amounts and levels freely. Every change is written to the audit log. `/audit [character]` lets a GM review recent changes and undo any of them. | M |
| BN-13 | **Skill catalog:** the GM (or trusted players) can define common bonus-giving skills **once**, and players add them to their characters by name instead of typing the values. Examples from the Holy Knight tree: *Bolstering Aura* (+2 CM to allies, not self) and *Holy Aura* (+2 CR vs fear). A character can have one or several catalog skills. Players can still enter one-off personal bonuses by hand. | M |
| BN-14 | **Skill tree label:** catalog skills can be labeled with their tree (e.g. *Holy Knight*), so `/breakdown` shows "Holy Aura (Holy Knight)" and `/orgs`-style lists can group them. | S |
| BN-15 | **Prerequisites:** a catalog skill can list a prerequisite skill (e.g. Bolstering Aura requires Holy Aura). The bot warns when a character adds a skill without its prerequisite, but doesn't block it. | C |
| BN-12 | **Entering bonuses (v1: short slash commands).** Each command does one thing, with autocomplete for characters, skills, orgs and stats. Most entry is picking by name: `/skill add`, `/org join`. One-off bonuses use `/bonus add`, one stat per command; repeating the same name adds another stat to that bonus. Effects use `/effect add`. An interactive panel and a paste-in text format may come later. | M |

### 6.5 Presence (Voice Channel)

There are no sessions to start or end. Each time a command runs, the bot looks at who is in the voice channel and counts them, with these exceptions:

- **Sitting out:** anyone who has used `/sitout` in the last 12 hours. This covers the DM running the game and players who are only observing.
- **No character set up:** members with no registered character, or with characters but none active or default, are still counted as players. They give only bonuses that come from their Discord roles, and are listed separately so they know to set up a character (SE-6).

| ID | Requirement | Pri |
|---|---|---|
| SE-1 | **Which channel:** `/partybonus` and `/breakdown` use the voice channel the caller is in. `channel:<voice channel>` picks one explicitly, e.g. when the caller isn't in voice. `/mybonus` uses the voice channel the character's player is in. | M |
| SE-2 | **`/sitout`** leaves the caller uncounted for **12 hours** (configurable), long enough for one game but expiring before, say, a morning event. `/sitin` ends it early. A DM can sit other players out or back in. | M |
| SE-3 | **Active character:** each player is counted with their **active** character, which is their default unless they chose another with `/play <character>`. The choice stays until changed. Each player counts with one character. | M |
| SE-4 | `/partybonus` and `/breakdown` end with a *not counted* line listing everyone sitting out (with the time it ends), so nobody is left out silently. | M |
| SE-5 | `/party` lists who would be counted right now, with their active characters. It's a quick check before looking at bonuses. | S |
| SE-6 | **No character set up:** a member in the voice channel with no usable character (none registered, or none active or default) is still **counted as a player**, under their Discord name:<br>• They **give** only bonuses that come from their **Discord roles**. Today that means just **Support**, from the Guild rank roles. Bonuses that need a character (catalog skills, per-character org memberships, one-off bonuses, effects) can't be included.<br>• They **receive** bonuses like anyone else, except level-based ones, since they have no level. The CM giver rule still applies, so they don't receive their own Support.<br>• `/partybonus` and `/breakdown` (whole party and single character) list them in a **NO CHARACTER SET UP** section, with the reason and the fix (`/character register` or `/play`), and a note that bonuses from their character are missing. Members sitting out aren't listed here. | M |
| SE-7 | Bots in the voice channel (e.g. music bots) are ignored and never listed. | M |

### 6.6 Output Commands

| ID | Requirement | Pri |
|---|---|---|
| OUT-1 | **`/partybonus`**: a table of the roll-stat totals (CM, CR, CR subtypes) each counted character receives, then the combat notes (with their descriptions), the effects, and the *not counted* line. It shows totals only. | M |
| OUT-2 | **`/mybonus [character]`**: totals for one character (roll stats, combat notes, effects), plus a single line about any bonus missed because the level is missing. It shows totals only. | M |
| OUT-3 | **`/breakdown`** (whole party): a detailed version of the old master list. For **each bonus in play**, it shows its name and org, what it adds up to for each audience (e.g. "+4 CM to non-members, +2 CM to each giver"), and **every contributing character** on its own line with their rank or level where it matters. Then: effects, the working for each character's totals (e.g. `CM 2+2+4+5+10 = +23`), and the *not counted* line. | M |
| OUT-3a | **`/breakdown <character>`**: each stat that character receives, the sum written out, and every contribution with the bonus name, giver and value. Then: bonuses **not applied** to them, with the reason, and what the character **gives**. | M |
| OUT-3b | Discord messages are limited to 2,000 characters (4,096 in an embed). Longer breakdowns are split across several messages or pages, never cut off. | M |
| OUT-4 | If the player isn't in a voice channel, `/mybonus` and `/breakdown <character>` show what the character **gives**, and explain that no party is present. | M |
| OUT-5 | `/mybonus` and `/breakdown <character>` reply privately by default. `/partybonus` and `/breakdown` (whole party) post publicly by default. An option switches either way. | M |
| OUT-6 | A player can look up anyone's character. | S |
| OUT-7 | A pinned `/partybonus` message that updates itself when people join or leave the voice channel. | C |

### 6.7 Administration

| ID | Requirement | Pri |
|---|---|---|
| AD-1 | `/config` sets the GM role, default visibility, sit-out duration (default 12 h) and maximum level. | M |
| AD-2 | Export and import all data as JSON. | S |
| AD-3 | One-time import from the current master list. | C |

## 7. Commands

Entry follows BN-12: short, single-purpose commands with autocomplete.

```
/character register name:<text> [level:<n>] [default:<bool>]
/character list | rename <character> <new> | delete <character> | default <character>
/level set <character> <n> | clear <character>

/partybonus [channel:<voice>] [private:<bool>]
/mybonus [character] [public:<bool>] [export:<bogsy>]
/breakdown [character] [channel:<voice>] [public:<bool>]

/bonus add character:<c> name:<text> stat:<stat> amount:<n> [audience:<everyone|orgs>]
           [orgs:<o,...>] [giver_included:<default|yes|no>] [note:<text>]
/bonus add-stat <bonus> stat:<stat> amount:<n>
/bonus level-rule <bonus> when:<lt|gte> level:<n> stat:<stat> amount:<n>
/bonus list [character] | edit <bonus> | toggle <bonus> | remove <bonus>
/effect add character:<c> text:<text> [name:<text>] [audience:<everyone|org>] [org:<o>]
/effect list [character] | edit <effect> | remove <effect>
/skill add character:<c> skill:<skill> | remove
/org amount character:<c> org:<o> amount:<n>

/sitout | /sitin
/sitout member:<m> | /sitin member:<m>                       (GM)
/play <character>
/party [channel:<voice>]

/orgs [org]
/org add full_name:<text> abbrev:<text> membership:<roles|gm|open> | edit | remove   (GM)
/org rank add <org> name:<text> [role:<discord role>] [order:<n>]                  (GM)
/org assign <character> <org> [rank:<rank>] | unassign                             (GM)
/org join <character> <org> | leave <character> <org>                             (open orgs)
/org bonus add <org> name:<text> stat:<stat> amount:<n>
           [min_rank:<rank>] [audience:<everyone|org>]                              (GM)

/stats list | add | subtype | alias | describe | remove     (GM)
/config ...                                                 (Admin)
```

## 8. Example

### 8.1 Setup (from the current master list)

| Bonus | Type | Given by | Values | Audience |
|---|---|---|---|---|
| Support | Org (the Guild; player-level roles) | Each character of a player with a Guild rank role | +2 CM, **fixed** | Everyone |
| Guild of the Timeless Heroes | Org (GoTH; per character) | GoTH members | CM, **amount set by each member** (e.g. +1, +3, +4) | Everyone |
| HoP | Org (HoP; per character) | HoP members | CM, **amount set by each member** | HoP members only |
| Cult of the Dragon | Org (Cult; per character) | Cult members | Level < 10: +1 heart damage; level ≥ 10: +10 CM (fixed, to confirm) | Cult members only |
| Holy auras | Catalog skills (Holy Knight tree) | Holy Knight characters | *Holy Aura*: +2 CR vs fear. *Bolstering Aura*: +2 CM to allies. (The old list's +3 values are kept in the sample below.) | Everyone |
| Champion of power | Personal | (a character) | +5 CR (all), +5 CM | Everyone |
| Wills ward stone | Personal (item) | (a character) | +5 CM | Everyone |
| Healing | Personal | (a character) | 1 heart healing | Everyone |
| Damage reduction | Personal | (a character) | 2 hearts damage reduction | Everyone |
| Chris the holy baker | Effect | Chris | "Effects of extreme cold are negated around Chris" | Everyone |

### 8.2 Sample game

Voice channel: *AWT Voice*. DM Sam and Bob, an observer, are in the channel but have used `/sitout`. Dana has just joined the server, has no Guild rank role yet, and hasn't registered a character. She receives bonuses but gives none. Counted characters:

- **Ioseph:** level 34, player has the Guild Vanguard role, GoTH (gives +4), HoP (gives +2); gives *Champion of power*.
- **Kael:** level 8, player has the Junior Adventurer role, Cult.
- **Crateris:** level 22, Cult; gives *Holy auras* and *Wills ward stone*.
- **Chris:** no level recorded, HoP (gives +2); gives *Damage reduction* and the cold effect.

The healing giver isn't in the channel. Damage reduction also protects its giver, Chris.

`/partybonus`:

```
PARTY BONUSES: AWT Voice (5 counted)
------------------------------------------
CHARACTER   CM    CR   CR vs fear
Ioseph      +12   +5   +8
Kael        +19   +5   +8
Crateris    +23   +5   +8
Chris       +23   +5   +8
Dana*       +21   +5   +8
------------------------------------------
COMBAT NOTES
Kael        Damage +2 hearts (extra hearts dealt when attacking)
Everyone    Damage reduction 2 hearts (mitigated when attacked)
------------------------------------------
EFFECTS
Effects of extreme cold are negated around Chris the holy baker.
------------------------------------------
NO CHARACTER SET UP (* only bonuses from Discord roles are counted)
  Dana    no character registered: use /character register
------------------------------------------
Not counted: DM Sam (sitting out until 11:40 PM), Bob (sitting out until 10:15 PM)
```

`/breakdown` (whole party):

```
PARTY BREAKDOWN: AWT Voice (5 counted)
------------------------------------------
Support (the Guild): +4 CM to non-members, +2 CM to each giver
    Ioseph     Guild Vanguard        +2 CM to others
    Kael       Junior Adventurer     +2 CM to others

Guild of the Timeless Heroes (GoTH): +4 CM to all but Ioseph
    Ioseph                           +4 CM to others

HoP (HoP members only): +2 CM to Ioseph, +2 CM to Chris
    Ioseph                           +2 CM to other HoP members
    Chris                            +2 CM to other HoP members

Cult of the Dragon (cult members only): Kael +2 hearts damage, Crateris +10 CM
    Kael       level 8               +10 CM to Crateris (level 10+)
                                     +1 heart damage to Kael himself (damage includes the giver)
    Crateris   level 22              +1 heart damage to Kael (under level 10)

Champion of power: +5 all CR to everyone, +5 CM to all but Ioseph
    Ioseph

Holy auras: +3 CR vs fear to everyone, +3 CM to all but Crateris
    Crateris

Wills ward stone: +5 CM to all but Crateris
    Crateris

Damage reduction: 2 hearts to everyone (mitigated when attacked)
    Chris

Effect: Effects of extreme cold are negated around Chris the holy baker.
    Chris
------------------------------------------
TOTALS
Ioseph     CM 2+2+3+5 = +12           CR +5   CR vs fear 5+3 = +8
Kael       CM 2+4+5+3+5 = +19         CR +5   CR vs fear 5+3 = +8   Damage 1+1 = +2 hearts
Crateris   CM 2+2+4+5+10 = +23        CR +5   CR vs fear 5+3 = +8
Chris      CM 2+2+4+2+5+3+5 = +23     CR +5   CR vs fear 5+3 = +8
Dana*      CM 2+2+4+5+3+5 = +21       CR +5   CR vs fear 5+3 = +8
Everyone   Damage reduction 2 hearts
------------------------------------------
NO CHARACTER SET UP (* only bonuses from Discord roles are counted)
  Dana    no character registered: use /character register
------------------------------------------
Not counted: DM Sam (sitting out until 11:40 PM), Bob (sitting out until 10:15 PM)
```

If Dana did have a Guild rank role (e.g. Junior Adventurer), her Support would still count without a character. Every other counted character would get +2 CM more, and `/breakdown` would show:

```
Support (the Guild): +6 CM to non-members, +4 CM to each giver
    Ioseph     Guild Vanguard        +2 CM to others
    Kael       Junior Adventurer     +2 CM to others
    Dana       Junior Adventurer     +2 CM to others   (no character set up)
```

`/mybonus Crateris`:

```
CRATERIS (level 22): AWT Voice
------------------------------------------
CM          +23
CR          +5
CR vs fear  +8
------------------------------------------
Damage reduction 2 hearts (mitigated when attacked)
Effects of extreme cold are negated around Chris the holy baker.
------------------------------------------
See how this was worked out: /breakdown Crateris
```

`/breakdown Crateris`:

```
BREAKDOWN: Crateris (level 22, updated 2026-09-20)
------------------------------------------
CM = 2 + 2 + 4 + 5 + 10 = +23
   +2   Support               from Ioseph (Guild Vanguard)
   +2   Support               from Kael (Junior Adventurer)
   +4   Timeless Heroes       from Ioseph
   +5   Champion of power     from Ioseph
  +10   Cult of the Dragon    from Kael (Crateris is level 10+)
CR = 5 = +5
   +5   Champion of power     from Ioseph
CR vs fear = 5 (all CR) + 3 = +8
   +5   Champion of power     from Ioseph
   +3   Holy auras            from Crateris (CR includes giver)
Damage reduction = 2 hearts
    2   Damage reduction      from Chris
------------------------------------------
NOT APPLIED
  Holy auras +3 CM, Wills ward stone +5 CM    CM excludes the giver
  Cult of the Dragon (own)                    CM excludes the giver
  HoP +2 CM                                   HoP members only
------------------------------------------
CRATERIS GIVES: Holy auras, Wills ward stone, Cult of the Dragon
```

A character with no level recorded would see this in `/mybonus`:

```
1 bonus not applied: level not recorded. Use /level set <character> <n>.
```

## 9. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NF-1 | **Responsiveness:** replies within Discord's 3-second limit. Calculating a 20-character party takes under 200 ms. |
| NF-2 | **Scale:** one server (AWT), up to about 300 characters and about 20 present at once. |
| NF-3 | **Reliability:** reconnects automatically and restarts after a crash. All state lives in the database. |
| NF-4 | **Permissions:** players change only their own characters' data unless they are a GM. Checked in the bot on every command. |
| NF-5 | **Privacy:** Discord IDs, display names and game data only. Doesn't read message content. |
| NF-6 | **Intents:** `Guilds` and `GuildVoiceStates` (both non-privileged). Roles for present players are looked up individually, so no privileged intents are needed. Results are cached for about 60 s. |
| NF-7 | **Quality (see section 12):** type-checked; the calculation engine has at least 90% branch coverage, including every rule in section 4 and the numbers in section 8; CI on every push. |
| NF-8 | **Operations:** structured logs; continuous off-site database replication plus nightly snapshots (section 11.1). |
| NF-9 | **Security:** the bot token lives only in environment variables or secrets. |

## 10. Data Model and Engine

```
Settings        (server_id, gm_role_id, presence_mode, default_visibility,
                 sitout_hours, level_max)
Stat            (id, name, parent_stat_id NULL, kind[roll|combat_note], unit[number|hearts],
                 description, giver_included_default, export_name NULL, sort_order)
StatAlias       (stat_id, alias)
Player          (discord_user_id, default_character_id NULL, active_character_id NULL)
Character       (id, discord_user_id, name UNIQUE, level NULL, level_updated_at)
Org             (id, full_name UNIQUE, abbreviation UNIQUE, membership[roles|gm|open], description)
OrgRank         (id, org_id, name, rank_order, discord_role_id NULL)
OrgRole         (org_id, discord_role_id)                 -- role membership without ranks
CharacterOrg    (character_id, org_id, rank_id NULL, assigned_by, assigned_at)
Bonus           (id, name, kind[numeric|effect], effect_text NULL,
                 giver_character_id NULL, giver_org_id NULL, min_rank_id NULL,
                 audience[everyone|orgs],
                 giver_included[default|yes|no], is_enabled, note)
BonusValue      (bonus_id, stat_id, amount NULL, rank_id NULL, amount_source[fixed|member])
MemberAmount    (bonus_id, stat_id, character_id, amount)   -- member-set org bonus amounts
Skill           (id, name UNIQUE, tree NULL, prerequisite_skill_id NULL)  -- catalog; its bonus
                                                            -- lives in Bonus/BonusValue
CharacterSkill  (character_id, skill_id)
BonusLevelRule  (bonus_id, op[lt|gte], level, stat_id, amount)
BonusAudience   (bonus_id, org_id)
SitOut          (discord_user_id, until, set_by)
-- Player also holds active_character_id NULL. Presence comes from live voice
-- state, so no session records are kept.
AuditLog        (id, actor_user_id, entity, entity_id, action, before_json, after_json, at)
```

Role-based membership isn't stored. It's worked out on each calculation from the player's current Discord roles and applied to whichever character that player has present.

**Calculation engine:** a pure function with no Discord or database code:

```
compute(counted_characters, player_roles, memberships, bonuses, stats) -> PartyReport
```

0. **Who is counted:** members in the voice channel (excluding bots), minus anyone with an active sit-out. Each counted player uses their active character, or a stand-in with no character (Discord name, no level, no skills or per-character orgs) if none is set up.
1. **Work out memberships:** combine each counted character's own org memberships with those from their player's Discord roles.
2. **List the gives:** personal bonuses of counted characters, and org bonuses once for each qualifying counted member.
3. **Apply them to recipients:** for each recipient, check each give against the audience, the giver rule and any level rule. Record it as *applied* (with its amount) or *not applied* (with a reason).
4. **Add up:** total each stat, then add parent-stat amounts into subtypes.
5. **Display:** `PartyReport` holds everything. `/partybonus` and `/mybonus` display the totals; `/breakdown` groups the gives by bonus and lists every contributor.

## 11. Recommended Technology Stack

| Layer | Choice | Why |
|---|---|---|
| Language | **Python 3.12+** | Readable, quick to iterate on with Claude Code. |
| Discord library | **discord.py 2.x** (`app_commands`) | Mature and maintained; slash commands and autocomplete. |
| Database | **SQLite** (WAL mode) | A single file, no database server to run. Plenty for one server. |
| ORM / migrations | **SQLAlchemy 2.0 (async)** + **aiosqlite**, **Alembic** | Typed models; versioned schema changes. |
| Config | **pydantic-settings** | Typed config from the environment. |
| Testing | **pytest**, **pytest-asyncio**, **hypothesis** | Property tests fit the counting rules well. |
| Quality | **ruff**, **mypy --strict** | Lint, format, type-check. |
| Packaging | **uv** + `pyproject.toml` | Fast, reproducible. |
| Deploy | **Docker** on a small VPS (about $4–6/mo) or Fly.io / Railway with a volume | Needs a process that's always running. |
| CI | **GitHub Actions** | Lint, type-check, test, build. |
| Backups | **Litestream** replication plus nightly `sqlite3 .backup` snapshots to object storage | Meets NF-8; see 11.1. |

**Alternative:** Node.js 22 + discord.js v14 + Prisma + Vitest.

### 11.1 Storage and Backups

**Where the data lives:** a single **SQLite** file (e.g. `data/awt-bonus.db`) on the same machine as the bot. There's no separate database server; the bot reads and writes the file directly. Nothing is stored in Discord. Roles and voice presence are read live from Discord each time a command runs.

| Hosting | Location of the database file |
|---|---|
| Small VPS | The VPS's disk, mounted into the container as a Docker volume, e.g. `/srv/awt-bonus/data/` |
| Fly.io / Railway | A **persistent volume** attached to the bot's container |
| Local PC (development/testing) | A `data/` folder next to the code (git-ignored) |

| ID | Requirement | Pri |
|---|---|---|
| DB-1 | The database path is set by configuration (`DATABASE_URL`), never hard-coded. | M |
| DB-2 | The database must be on **persistent** storage. The bot refuses to start if the path is on a known temporary filesystem, or if it can't write a test file. | M |
| DB-3 | SQLite runs in **WAL mode** with a busy timeout, so reads never block writes. Only **one** bot process uses the file at a time. | M |
| DB-4 | **Schema changes** only happen through Alembic migrations. They run automatically at startup, after a snapshot is taken first. | M |
| DB-5 | **Continuous replication:** Litestream runs alongside the bot and streams every change to object storage (e.g. Backblaze B2 or Amazon S3). If the host fails, at most a few seconds of changes are lost. | S |
| DB-6 | **Nightly snapshots:** a full `sqlite3 .backup` copy goes to the same object storage every night and is kept for 30 days. | M |
| DB-7 | **Restore is documented and tested:** a written runbook covers restoring from Litestream or from a snapshot onto a new host. It's tried at least once before AWT goes live. | M |
| DB-8 | **Readable export:** `/admin export` (AD-2) produces a JSON copy a GM can download at any time, independent of the backups. | S |
| DB-9 | **Secrets:** storage credentials live only in environment variables or the host's secret store, like the bot token. | M |

**Expected size:** well under 10 MB, even with hundreds of characters and a long audit log. Storage costs are pennies a month.

**Alternative (not planned):** a managed **Postgres** database (e.g. Neon or Supabase) would keep the data separate from the bot's host. It adds another account and a network dependency, so it isn't needed at AWT's size. Because data access goes through SQLAlchemy, switching later is mainly a change to `DATABASE_URL` plus a one-time data copy.

## 12. Testing Strategy

Testing is layered. Most of the checking is done by fast automated tests that never touch Discord. Live testing in Discord only confirms the Discord-specific parts, and a trial alongside the current master list proves the bot at AWT.

### 12.1 Calculation Engine (most of the work)

The engine is a pure function (section 10), so it's the easiest part to test thoroughly. It's also where mistakes would hurt most.

| ID | Requirement | Pri |
|---|---|---|
| TS-1 | **Scenario files:** engine tests are written as YAML scenarios: who is in the channel, what they give, and the expected totals (and, where relevant, the expected *not applied* lines). They can be read and written without reading code. Every rules question that comes up becomes a permanent scenario. The first set, `engine-scenarios.yaml`, covers every rule in section 4 and the full sample game in section 8. | M |
| TS-2 | **Edge cases** each get a scenario: no level recorded; level exactly at a threshold (10); a player with no character but a Guild role; everyone sitting out; an empty channel; a member-set org amount that hasn't been entered; the same skill from two characters; bots in the channel. | M |
| TS-3 | **Property tests (Hypothesis):** thousands of randomly generated parties check rules that must always hold:<br>• nobody receives their own CM bonus;<br>• everyone receives their own CR and combat-note bonuses;<br>• every total equals the sum of the lines `/breakdown` shows for it;<br>• a subtype total is never lower than its parent's;<br>• the order of players doesn't change the result;<br>• removing a giver never increases anyone's total (with non-negative bonuses). | M |

### 12.2 Output

| ID | Requirement | Pri |
|---|---|---|
| TS-4 | **Snapshot tests:** the text of `/partybonus`, `/mybonus` and `/breakdown` for the sample game is saved as reference files and compared on every run, so layout changes are caught and reviewed on purpose. | M |
| TS-5 | **Message size:** a very large party must split across messages under Discord's 2,000-character limit and never cut off mid-line (OUT-3b). | M |

### 12.3 Commands and Database (no Discord needed)

| ID | Requirement | Pri |
|---|---|---|
| TS-6 | The Discord-specific code is kept thin: it reads voice members and roles, and sends replies. Command logic runs behind it against a **fake Discord** that supplies voice members, roles and bots from test data. | M |
| TS-7 | **Permission tests:** players can't change other players' characters; GMs can. Every GM-only command is checked. | M |
| TS-8 | **Fake clock:** time-based behavior (the 12-hour `/sitout`, level "last updated" dates, snapshot retention) is tested with a controllable clock, not real waiting. | M |
| TS-9 | **Database tests:** each test gets a fresh temporary SQLite file. Alembic migrations are tested from an empty database and from the previous release's schema. | M |
| TS-10 | **Backup and restore:** an automated test restores a snapshot into a new database and checks the data matches, in addition to the manual runbook in DB-7. | S |

### 12.4 Live Testing on a Private Server

| ID | Requirement | Pri |
|---|---|---|
| TS-11 | A **separate test bot** application (its own token and database) runs on a private test server, so testing never touches AWT data. | M |
| TS-12 | The test server **mirrors AWT's setup**: the five Guild rank roles, a voice channel, and a music bot. Testing uses two or three people or alt accounts operated by hand. | M |
| TS-13 | A **manual checklist** covers what automated tests can't:<br>• joining and leaving voice, then re-running commands;<br>• role changes showing up;<br>• bots ignored;<br>• autocomplete;<br>• private versus public replies;<br>• long `/breakdown` output splitting;<br>• the bot restarting mid-game without losing data;<br>• `/sitout` / `/sitin`;<br>• a member with no character. | M |
| TS-14 | **No self-bots:** real user accounts are never automated to drive tests. That breaks Discord's Terms of Service. | M |

### 12.5 Trial at AWT

| ID | Requirement | Pri |
|---|---|---|
| TS-15 | **Parallel run:** for the first few games, the bot runs alongside the existing master list and the numbers are compared. Every mismatch is either a bug or a rule modeled wrong, and becomes a new scenario. | M |
| TS-16 | A few players try `/mybonus` and `/breakdown` and give feedback on how clear the output is before general rollout. | S |

### 12.6 Continuous Integration

| ID | Requirement | Pri |
|---|---|---|
| TS-17 | Every push runs linting (ruff), type checks (mypy), all automated tests, and a coverage check (at least 90% branch coverage for the engine). A change that breaks a scenario or a snapshot can't be merged. | M |

**Fit with the milestones:** 12.1 is built together with the engine in M1, 12.2–12.3 grow with M2–M3, and 12.4–12.5 happen before and during launch.

## 13. Optional: Hand-off to Bogsy's Dice Bot

The bot doesn't roll dice. `/mybonus <character> export:bogsy` lists **roll stats only** (CM, CR, CR subtypes) as values for the player to enter with Bogsy's `/modifier`. Combat notes and effects are never exported.

Each character's totals are different, so these have to be personal Bogsy modifiers, and the player enters them. Another bot can't run Bogsy's slash commands.

| ID | Requirement | Pri |
|---|---|---|
| BG-1 | The export lists each roll stat's modifier name and value, e.g. `awt_cm` = `+23`, `awt_cr` = `+5`, `awt_cr_fear` = `+8`. It also gives copyable text lines (`.awt_cm = +23 "AWT CM"`). | C |
| BG-2 | The GM sets modifier names (`export_name`) per stat. The bot avoids names that clash with Bogsy's reserved words. | C |
| BG-3 | The export also lists modifiers to clear (`.awt_cm =`) for stats that are now zero. | C |

## 14. Future Enhancements

- Buttons on the `/partybonus` message (Join / Leave / Refresh).
- A pinned message that updates itself (OUT-7).
- A one-time import from the master list (AD-3).

## 15. Open Questions


**Resolved:** bonus entry starts with short slash commands (BN-12).

**Resolved:** there are no sessions. The bot counts whoever is in the voice channel. The DM and observers use `/sitout`, which lasts 12 hours (configurable), and `/sitin` ends it early.

**Resolved:** GoTH, HoP and the Cult of the Dragon are recorded per character in the bot. Only the Guild ranks come from Discord roles. Since players edit freely, these orgs default to *open* membership: players add their own characters.

**Resolved:** players edit their own characters' bonuses, skills, org amounts and levels freely. Every change is written to the audit log, and a GM can review or undo it.

**Resolved:** duplicates stack. Two Holy Knights with Holy Aura give +4 CR vs fear. Every giver counts, with no exceptions.

**Resolved:** all five Guild ranks give the same +2 CM Support. The ranks only decide who qualifies.

**Resolved:** org bonus amounts can be set by each member (e.g. GoTH +1 or +3); HoP is an ordinary org.

**Resolved:** combat notes (damage, damage reduction, healing) apply to the giver too, like CR.

## 16. Milestones

| Milestone | Scope |
|---|---|
| **M1: Engine** | Stats (giver rule, subtypes, combat notes), characters and level, personal bonuses, calculation engine with tests for section 4 and section 8. |
| **M2: Commands** | `/character`, `/level`, `/bonus`, `/effect`, voice presence, `/sitout` / `/sitin`, `/play`, `/partybonus`, `/mybonus`, `/breakdown`. |
| **M3: Orgs** | Org list (full name and abbreviation, `/orgs`), role-based and per-character membership, ranks, org bonuses, audiences, level rules. |
| **M4: Ops** | Docker, CI, hosting, persistent storage, Litestream and nightly snapshots, restore runbook, `/config`, JSON export/import. |
| **M5: Extras** | Bogsy hand-off, buttons, master-list import. |
