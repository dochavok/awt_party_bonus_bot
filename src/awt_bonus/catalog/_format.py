"""The catalog file format (CT-4, CT-5, CT-10), as pydantic models of the YAML.

These describe one stat, entry, guild or item class exactly as written in the files. Checks
that need the whole catalog (references, duplicates) are in ``_parse``.
"""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, model_validator

Amount = Annotated[int, Field(strict=True, gt=0)]
"""A bonus amount: a whole number above zero."""

Gives = dict[StrictStr, Amount]
"""Stat ID -> amount."""


class _Spec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StatSpec(_Spec):
    kind: Literal["roll", "combat_note"]
    parent: StrictStr | None = None
    """For CR subtypes: the stat whose total flows into this one (rule 4.7)."""
    unit: StrictStr | None = None
    description: StrictStr | None = None


class LevelRuleSpec(_Spec):
    when: StrictStr
    """The recipient's levels it covers: "< 10", "<= 9", "> 9", ">= 10", "= 10" or "10-19"."""
    gives: Gives


class ModifierSpec(_Spec):
    """Changes the numbers of the character's other gives (rule 4.6)."""

    tag: StrictStr | None = None
    """Only gives with this tag, e.g. ``aura``."""
    all: StrictBool = False
    """Every give with numbers."""
    add: Amount

    @model_validator(mode="after")
    def _one_scope(self) -> Self:
        if (self.tag is None) == (not self.all):
            raise ValueError("a modifier needs exactly one of `tag` or `all: true`")
        return self


class BonusFields(_Spec):
    """What one ability gives, and to whom (CT-4)."""

    gives: Gives | None = None
    effect: StrictStr | None = None
    condition: StrictStr | None = None
    """Makes it a conditional bonus, never added to totals (rule 4.12)."""
    audience: Literal["party", "guild", "holders"] | None = None
    """Default party. ``guild``: members of the entry's guild; ``holders``: other holders."""
    includes_giver: StrictBool | None = None
    stacks: StrictBool | None = None
    level_rules: list[LevelRuleSpec] | None = None
    """Amounts that depend on the recipient's level (rule 4.10)."""
    needs_item_class: StrictStr | None = None
    """Only recipients with an item of this class in use receive it (rule 4.14)."""
    per_item_class: StrictStr | None = None
    """Goes to the holder only, once per item of this class in use in the party (rule 4.15)."""

    def bonus_problems(self) -> list[str]:
        problems = []
        if self.gives is not None and self.level_rules is not None:
            problems.append("has both `gives` and `level_rules`; use one")
        if self.per_item_class is not None:
            if self.needs_item_class is not None:
                problems.append("has both `needs_item_class` and `per_item_class`; use one")
            if not self.gives:
                problems.append("`per_item_class` needs `gives`")
            holder_only = [
                name
                for name in ("condition", "audience", "includes_giver", "stacks", "level_rules")
                if getattr(self, name) is not None
            ]
            if holder_only:
                problems.append(
                    "`per_item_class` goes only to the holder, so it can't set "
                    + ", ".join(holder_only)
                )
        gives_something = self.gives or self.level_rules or self.effect
        if not gives_something:
            settings = [
                name
                for name in (
                    "condition",
                    "audience",
                    "includes_giver",
                    "stacks",
                    "needs_item_class",
                )
                if getattr(self, name) is not None
            ]
            if settings:
                problems.append(f"sets {', '.join(settings)} but gives nothing")
        elif self.condition is not None and not (self.gives or self.level_rules):
            problems.append("has a `condition` but no amounts")
        return problems


class AbilitySpec(BonusFields):
    """One ability of a rank, or a guild's bonus from Discord roles (CT-5)."""

    name: StrictStr
    tags: list[StrictStr] = []
    card: StrictStr | None = None

    @model_validator(mode="after")
    def _gives_something(self) -> Self:
        problems = self.bonus_problems()
        if not (self.gives or self.level_rules or self.effect):
            problems.append("gives nothing")
        if problems:
            raise ValueError("; ".join(problems))
        return self


class EntrySpec(BonusFields):
    """A skill, boon, rank, item or title (CT-4).

    What it gives is written in one of three ways: bonus fields at the top level
    (the bonus is named after the entry); ``ability: <name>`` plus bonus fields at
    the top level; or a list of ``abilities``.
    """

    name: StrictStr | None = None
    """Display name; defaults to the ID."""
    kind: Literal["skill", "boon", "rank", "item", "title"]
    tree: StrictStr | None = None
    guild: StrictStr | None = None
    tags: list[StrictStr] = []
    unique: StrictBool = False
    """Only one character may hold it at a time (HV-6)."""
    retired: StrictBool = False
    replaces: list[StrictStr] = []
    modifies: ModifierSpec | None = None
    card: StrictStr | None = None
    """Card text quoted from the source."""
    ability: StrictStr | None = None
    abilities: list[AbilitySpec] | None = None

    @model_validator(mode="after")
    def _shape(self) -> Self:
        problems = []
        if self.kind == "skill" and self.tree is None:
            problems.append("a skill needs a `tree`")
        if self.kind != "skill" and self.tree is not None:
            problems.append("only skills have a `tree`")
        if self.kind in ("boon", "rank") and self.guild is None:
            problems.append(f"a {self.kind} needs a `guild`")
        top_level = [name for name in BonusFields.model_fields if getattr(self, name) is not None]
        if self.abilities is not None:
            if self.ability is not None or top_level:
                problems.append(
                    "`abilities` can't be combined with `ability` or top-level bonus fields"
                )
            if not self.abilities:
                problems.append("`abilities` is empty")
            names = [a.name for a in self.abilities]
            if len(set(names)) != len(names):
                problems.append("two abilities share a name")
            audiences = [a.audience for a in self.abilities]
        else:
            problems += self.bonus_problems()
            if self.ability is not None and not (self.gives or self.level_rules or self.effect):
                problems.append(f"ability {self.ability!r} gives nothing")
            audiences = [self.audience]
        if "guild" in audiences and self.guild is None:
            problems.append("`audience: guild` needs the entry to have a `guild`")
        if problems:
            raise ValueError("; ".join(problems))
        return self


class ItemClassSpec(_Spec):
    """An item class (CT-10), e.g. passion items."""

    name: StrictStr | None = None
    """Display name; defaults to the ID."""
    other_names: list[StrictStr] = []
    """Other names players use, e.g. "Will Passion" for passion."""
    description: StrictStr
    """What belongs to the class."""
    retired: StrictBool = False
    """Counts can't be set any more; existing counts are kept (CT-6)."""


class GuildSpec(_Spec):
    """A guild, order, cult or coalition (CT-5)."""

    full_name: StrictStr
    short_name: StrictStr | None = None
    """Defaults to the ID."""
    membership: Literal["open", "roles"]
    """``open``: players join with /guild join; ``roles``: from Discord roles (HV-3)."""
    roles: list[StrictStr] = []
    from_roles: list[AbilitySpec] = []
    """Bonuses a player gives once for having any of the roles, e.g. Support (HV-3)."""
    secret: StrictBool = False
    """Members are never revealed (SG-1)."""
    how_to_join: StrictStr | None = None
    """What to tell players about joining, shown instead of /guild join (CT-5)."""

    @model_validator(mode="after")
    def _membership(self) -> Self:
        if self.membership == "roles" and not self.roles:
            raise ValueError("`membership: roles` needs a list of `roles`")
        if self.membership == "open" and (self.roles or self.from_roles):
            raise ValueError("`roles` and `from_roles` are only for `membership: roles`")
        if any(a.audience == "holders" for a in self.from_roles):
            raise ValueError("a bonus from roles can't have `audience: holders`")
        return self
