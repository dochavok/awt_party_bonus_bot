"""What the engine returns: ``PartyReport`` (requirements section 11, steps 2-6).

The report holds everything, including which gives come from secret guilds.
Secrecy (section 6.4) is applied by the output layer, not here.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from awt_bonus.engine.inputs import CharacterRef
from awt_bonus.ids import EntryId, GuildId, StatId, UserId


class Reason(StrEnum):
    """Why a give wasn't applied to a recipient (section 11, step 3)."""

    GIVER_EXCLUDED = "giver_excluded"
    """The recipient is the giver, and the entry doesn't include the giver."""
    NOT_IN_AUDIENCE = "not_in_audience"
    """Not a member of the guild, or doesn't hold the entry (holders audience)."""
    NO_LEVEL = "no_level"
    """In the audience, but a level rule applies and no level is recorded."""
    REPLACED = "replaced"
    """The giver also has the entry that replaces this one (rule 4.5)."""
    NOT_STACKED = "not_stacked"
    """Doesn't stack, and another give of the same bonus was counted instead (rule 4.4)."""


class SourceKind(StrEnum):
    SKILL = "skill"
    BOON = "boon"
    RANK = "rank"
    ITEM = "item"
    TITLE = "title"
    ROLE = "role"
    """Support, from Discord roles (HV-3)."""


@dataclass(frozen=True)
class Source:
    """Where a give comes from, for display (OUT-3)."""

    kind: SourceKind
    tree: str | None = None
    """The skill tree, for skills."""
    guild: GuildId | None = None
    """The guild, for boons, ranks and Support."""


class AudienceKind(StrEnum):
    PARTY = "party"
    GUILD = "guild"
    HOLDERS = "holders"


@dataclass(frozen=True)
class Audience:
    """Who can receive a give (rule 4.8)."""

    kind: AudienceKind
    guild: GuildId | None = None
    """For GUILD: the guild whose members receive it."""
    entry: EntryId | None = None
    """For HOLDERS: the entry the recipients must also hold."""


@dataclass(frozen=True)
class LevelRule:
    """A level band for a level-based give, checked against the recipient (rule 4.10)."""

    min_level: int | None
    """Lowest level in the band, inclusive; None for no lower bound."""
    max_level: int | None
    """Highest level in the band, inclusive; None for no upper bound."""
    amounts: Mapping[StatId, int]


@dataclass(frozen=True)
class Adjustment:
    """A modifier's change to each number of a give, e.g. +1 from Devotion III (rule 4.6)."""

    entry: EntryId
    amount: int


@dataclass(frozen=True)
class Give:
    """One bonus one counted character gives (section 11, step 2)."""

    id: int
    """Unique within the report."""
    giver: UserId
    entry: EntryId
    """What the giver has, e.g. "High Inquisitor"; for Support, the role guild's pseudo-entry."""
    bonus: str
    """The bonus's display name, e.g. "Cult of the Dragon", "Rat Pack", "Holy Aura"."""
    source: Source
    giver_rank: tuple[str, ...]
    """The giver's rank(s) to show next to them, e.g. ("Guild Vanguard",) for Support (HV-3)."""
    base: Mapping[StatId, int]
    """Amounts before modifiers. Empty for effects and level-based gives."""
    adjustments: tuple[Adjustment, ...]
    """Modifiers applied, e.g. Devotion III +1, for "2 + 1 Devotion III" (OUT-3a)."""
    amounts: Mapping[StatId, int]
    """Amounts after modifiers. Empty for effects and level-based gives."""
    level_rules: tuple[LevelRule, ...]
    """For level-based gives; the amounts then depend on the recipient."""
    effect: str | None
    """Effect text, for text-only benefits."""
    condition: str | None
    """For conditional bonuses (rule 4.12), which are never added to totals."""
    audience: Audience
    includes_giver: bool
    stacks: bool
    secret_guild: GuildId | None
    """Set when the give comes from a secret guild (SG-1)."""
    retired: bool
    """The catalog entry is retired (CT-6)."""


@dataclass(frozen=True)
class Applied:
    """A give applied to a recipient: one line of the working (OUT-3a)."""

    give: int
    """The Give's id."""
    amounts: Mapping[StatId, int]
    """What this recipient gets from it (after modifiers and level rules)."""


@dataclass(frozen=True)
class NotApplied:
    give: int
    reason: Reason


@dataclass(frozen=True)
class ConditionalBonus:
    """A conditional give this recipient could get; never in totals (rule 4.12)."""

    give: int
    amounts: Mapping[StatId, int]
    condition: str


@dataclass(frozen=True)
class RecipientReport:
    """Everything about one counted player."""

    user_id: UserId
    name: str
    """The character's name, or the Discord name if no character is set up."""
    character: CharacterRef | None
    totals: Mapping[StatId, int]
    """Total for each stat; a subtype's total includes its parent's (rule 4.7)."""
    applied: tuple[Applied, ...]
    """Direct contributions to the totals, before parent amounts flow into subtypes."""
    not_applied: tuple[NotApplied, ...]
    conditional: tuple[ConditionalBonus, ...]
    effects: tuple[int, ...]
    """Ids of the effect gives this recipient receives."""


@dataclass(frozen=True)
class NotCounted:
    """A present player who is sitting out (SE-4)."""

    user_id: UserId
    name: str
    until: datetime
    """When the sit-out ends (UTC)."""


@dataclass(frozen=True)
class PartyReport:
    gives: tuple[Give, ...]
    """Every give from a counted player, including replaced ones."""
    recipients: tuple[RecipientReport, ...]
    """Every counted player, in the order given. Bots never appear anywhere."""
    not_counted: tuple[NotCounted, ...]
    no_character: tuple[UserId, ...]
    """Counted players with no character set up (SE-5)."""

    def recipient(self, name: str) -> RecipientReport:
        """The counted player with this character name (or Discord name). KeyError if none."""
        for recipient in self.recipients:
            if recipient.name == name:
                return recipient
        raise KeyError(name)

    def give(self, give_id: int) -> Give:
        """The give with this id. KeyError if none."""
        for give in self.gives:
            if give.id == give_id:
                return give
        raise KeyError(give_id)
