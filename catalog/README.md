# The catalog

Every stat, skill, guild, rank, boon, item, title and item class the bot knows about
(requirements 6.2 and 8). Characters store only the IDs, so a change here applies to
every character at once (CT-3). A push to `main` deploys it (DP-3).

Every `*.yaml` file in this folder is part of the catalog. Each file can hold any of
four sections: `stats`, `entries`, `guilds` and `item_classes`. By convention:

| File | Holds |
|---|---|
| `stats.yaml` | stats |
| `skills.yaml` | skills |
| `guilds.yaml` | guilds, and their rank and boon entries |
| `items.yaml` | items and titles, and item classes |

Check your change before pushing (CI runs the same check, CT-7):

```
uv run python -m awt_bonus.catalog check catalog
```

## Rules that keep characters working

- **IDs are permanent** (CT-2). The key of each stat, entry, guild and item class is
  its ID. Never change or remove one; change `name` instead.
- **Retire, don't delete** (CT-6, CT-10). To take an entry or an item class out of the
  game, add `retired: true`. CI refuses a catalog that loses an ID from the previous
  version.
- IDs are unique across entries and guilds. Names are unique too, ignoring case,
  across entry names, guild short and full names, and item class names and other
  names.

## Stats

```yaml
stats:
  CR vs fear: {kind: roll, parent: CR}
  Damage: {kind: combat_note, unit: hearts, description: "extra hearts dealt when attacking"}
```

| Field | Meaning |
|---|---|
| `kind` | `roll` (CM, CR and CR subtypes) or `combat_note` |
| `parent` | For a subtype: its parent's total is added to it (rule 4.7) |
| `unit`, `description` | Shown with combat notes |

## Entries

```yaml
entries:
  holy_aura:
    name: Holy Aura            # display name; defaults to the ID
    kind: skill                # skill, boon, rank, item or title
    tree: Holy Knight          # skills only, and required for them
    tags: [aura]
    gives: {CR vs fear: 2}
    card: "Allies in your aura gain +2 vs. fear effects"
```

| Field | Meaning | Default |
|---|---|---|
| `name` | Display name | the ID |
| `kind` | `skill`, `boon`, `rank`, `item` or `title` | required |
| `tree` | Skill tree (skills only) | required for skills |
| `guild` | The guild's ID (boons and ranks) | required for boons and ranks |
| `gives` | Stat ID → whole number above zero | nothing |
| `effect` | Text-only benefit | none |
| `audience` | `party`, `guild` (members of the entry's guild) or `holders` (other holders of this entry) | `party` |
| `includes_giver` | The giver receives it too | `false` |
| `stacks` | `false`: counted once per recipient, the highest giver's (rule 4.4) | `true` |
| `condition` | Makes it a conditional bonus, never added to totals (rule 4.12) | none |
| `level_rules` | Amounts by the **recipient's** level, instead of `gives` (see below) | none |
| `needs_item_class` | An item class ID: only recipients with at least one item of it in use receive it (rule 4.14) | none |
| `per_item_class` | An item class ID: goes **only to the holder**, with each amount in `gives` multiplied by the class's count in use across the counted party, the holder's own included (rule 4.15). Can't be combined with `audience`, `includes_giver`, `stacks`, `condition`, `level_rules` or `needs_item_class` | none |
| `modifies` | `{tag: aura, add: 1}` or `{all: true, add: 1}`: adds to each number of the same character's other bonuses (rule 4.6) | none |
| `tags` | Labels modifiers can target, e.g. `aura` | none |
| `replaces` | IDs this entry replaces; a character with both gives only this one (rule 4.5) | none |
| `unique` | Only one character may hold it at a time (HV-6) | `false` |
| `retired` | Can't be added any more; existing holders keep it (CT-6) | `false` |
| `card` | Card text **quoted from the source**. Leave it out until it's been copied; never write it from memory. | none |

An entry with nothing to give (e.g. a title with no party bonus) needs only `kind`.

### Abilities

The bonus is named after the entry, unless it's given a name with `ability`:

```yaml
  captain:
    kind: rank
    guild: pirates
    ability: King of the Pirates
    audience: guild
    gives: {CM: 2}
```

A rank that grants several abilities lists them, each with its own `name`, `gives`,
`effect`, `audience`, `includes_giver`, `stacks`, `condition`, `level_rules`,
`needs_item_class`, `per_item_class`, `tags` and `card` (CT-5):

```yaml
  guild_thief:
    kind: rank
    guild: thieves
    replaces: [footpad, burglar]
    abilities:
      - {name: Rat Pack, audience: guild, gives: {CM: 1, CR escape: 1}}
      - {name: Leadership, audience: guild, includes_giver: true, stacks: false,
         gives: {CM: 2, CR stealth: 2}}
```

Abilities with the same name are the same bonus: that's what "doesn't stack" counts once.

### Level rules

```yaml
    level_rules:
      - {when: "< 10", gives: {Damage: 1}}
      - {when: ">= 10", gives: {CM: 10}}
```

`when` is one of `< n`, `<= n`, `> n`, `>= n`, `= n` or a range `a-b` (inclusive).
Bands can't overlap. A recipient with no level recorded doesn't receive it (rule 4.10).

## Item classes

A family of items with a common theme (CT-10). Characters record how many items of
each class they have in use with `/character items` (IC-2); the individual items
aren't catalogued, unless they give a party bonus of their own.

```yaml
item_classes:
  passion:
    name: passion              # display name; defaults to the ID
    other_names: [Will Passion]
    description: Items made by Will Passion or through the Path of Passion quest
```

| Field | Meaning | Default |
|---|---|---|
| `name` | Display name | the ID |
| `other_names` | Other names players use; `/catalog` and autocomplete find the class by these too | none |
| `description` | What belongs to the class | required |
| `retired` | Counts can't be set any more; existing counts are kept (CT-6). An entry that depends on a retired class must be retired too | `false` |

An entry uses a class with `needs_item_class` or `per_item_class`:

```yaml
  will_passions_pendant:
    name: Will Passion's Pendant
    kind: item
    ability: Aura of Passion
    gives: {Damage: 2}
    needs_item_class: passion
  will_passions_adventure_token:
    name: Will Passions Adventure Token
    kind: item
    gives: {CM: 2, Damage: 1}
    per_item_class: passion
```

## Guilds

```yaml
guilds:
  thieves:
    short_name: Thieves        # defaults to the ID
    full_name: Guild of Thieves
    membership: open           # players join with /guild join
    secret: true               # members are never revealed (SG-1)
  the_guild:
    short_name: Patreon
    full_name: Patreon Bonuses
    membership: roles          # membership comes from Discord roles
    roles: [Junior Adventurer, Guild Veteran]   # lowest first
    from_roles:                # given once by a player with any of the roles (HV-3)
      - {name: Support, gives: {CM: 2}}
    how_to_join: "Guild tiers are derived from the AWT Patreon: <https://...>"   # optional (CT-5)
```

`roles` are listed lowest first: `/catalog` says a bonus is given by the first
role "or above", then lists them all (e.g. "Support Tiers: Junior Adventurer, ...").
`how_to_join` is optional text telling players how to join. For a guild whose
membership comes from roles, `/catalog` and `/guild join` show it instead of the
join command. `<...>` around a link stops Discord showing a preview.
