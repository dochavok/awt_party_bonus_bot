"""The calculation engine (requirements section 11): a pure function.

No Discord, database or clock code belongs in this package.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from awt_bonus.catalog import Ability, Catalog, Entry, EntryKind, LevelBand, Membership
from awt_bonus.catalog import AudienceKind as CatalogAudience
from awt_bonus.catalog import Guild as CatalogGuild
from awt_bonus.engine.inputs import CharacterRef, PresentPlayer
from awt_bonus.engine.report import (
    Adjustment,
    Applied,
    Audience,
    AudienceKind,
    ConditionalBonus,
    Give,
    LevelRule,
    NotApplied,
    NotCounted,
    PartyReport,
    Reason,
    RecipientReport,
    Source,
    SourceKind,
)
from awt_bonus.ids import CharacterId, EntryId, GuildId, ItemClassId, StatId, UserId


def compute(
    present_players: Sequence[PresentPlayer],
    player_roles: Mapping[UserId, frozenset[str]],
    character_entries: Mapping[CharacterId, Sequence[EntryId]],
    character_guilds: Mapping[CharacterId, Sequence[GuildId]],
    catalog: Catalog,
    character_item_counts: Mapping[CharacterId, Mapping[ItemClassId, int]] | None = None,
) -> PartyReport:
    """Work out every counted player's bonuses (section 11, steps 0-6).

    ``character_item_counts`` holds each character's item class counts (IC-1); a
    character or class left out has 0.
    """
    # Step 0: who is counted. Bots are ignored entirely (SE-6); anyone with an
    # active sit-out is listed, but gives and receives nothing (SE-2, SE-4).
    people = [p for p in present_players if not p.is_bot]
    not_counted = tuple(
        NotCounted(p.user_id, p.display_name, p.sitting_out_until)
        for p in people
        if p.sitting_out_until is not None
    )
    counted = [p for p in people if p.sitting_out_until is None]

    # Step 1: memberships and what each character has.
    players = [
        _player(
            p,
            player_roles.get(p.user_id, frozenset()),
            character_entries,
            character_guilds,
            character_item_counts or {},
            catalog,
        )
        for p in counted
    ]
    # The party's count of each class, for bonuses counted across the party (rule 4.15).
    class_counts: dict[ItemClassId, list[tuple[UserId, int]]] = {}
    for player in players:
        for item_class, count in player.item_counts.items():
            class_counts.setdefault(item_class, []).append((player.user_id, count))

    # Step 2: every give, with replacements marked and modifiers applied.
    candidates: list[_Candidate] = []
    for player in players:
        candidates += _gives(player, catalog, class_counts, first_id=len(candidates) + 1)

    # Steps 3-5: apply each give to each recipient, keep one of each bonus that
    # doesn't stack, and add up.
    recipients = tuple(_receive(player, candidates, catalog) for player in players)

    # Step 6: the report holds everything; the output layer applies secrecy (6.4).
    return PartyReport(
        gives=tuple(c.give for c in candidates),
        recipients=recipients,
        not_counted=not_counted,
        no_character=tuple(p.user_id for p in counted if p.character is None),
    )


# ---------------------------------------------------------------- step 1


@dataclass(frozen=True)
class _Player:
    """A counted player, with what the engine needs to know about them."""

    user_id: UserId
    name: str
    character: CharacterRef | None
    roles: frozenset[str]
    held: tuple[Entry, ...]
    """The character's catalog entries, in order, each once."""
    guilds: frozenset[GuildId]
    """Open guilds joined, plus guilds from Discord roles; none without a character (SE-5)."""
    item_counts: Mapping[ItemClassId, int]
    """Item class counts above 0 (IC-1); none without a character."""

    @property
    def level(self) -> int | None:
        return self.character.level if self.character is not None else None


def _player(
    player: PresentPlayer,
    roles: frozenset[str],
    character_entries: Mapping[CharacterId, Sequence[EntryId]],
    character_guilds: Mapping[CharacterId, Sequence[GuildId]],
    character_item_counts: Mapping[CharacterId, Mapping[ItemClassId, int]],
    catalog: Catalog,
) -> _Player:
    character = player.character
    if character is None:
        return _Player(player.user_id, player.display_name, None, roles, (), frozenset(), {})
    # IDs the catalog doesn't know are ignored (CT-7 stops entries disappearing).
    entry_ids = dict.fromkeys(character_entries.get(character.id, ()))
    held = tuple(catalog.entries[e] for e in entry_ids if e in catalog.entries)
    joined = {
        g
        for g in character_guilds.get(character.id, ())
        if g in catalog.guilds and catalog.guilds[g].membership is Membership.OPEN
    }
    joined |= {g.id for g in catalog.role_guilds(roles)}
    counts = {
        c: n
        for c, n in character_item_counts.get(character.id, {}).items()
        if c in catalog.item_classes and n > 0
    }
    return _Player(
        player.user_id, character.name, character, roles, held, frozenset(joined), counts
    )


# ---------------------------------------------------------------- step 2


@dataclass(frozen=True)
class _Candidate:
    """A give, with what applying it needs that the report doesn't keep."""

    give: Give
    replaced: bool
    """The giver also has an entry that replaces this one (rule 4.5)."""
    bands: tuple[LevelBand, ...]
    extra: int
    """The give's adjustments added together; added to each number (rule 4.6)."""


@dataclass(frozen=True)
class _Origin:
    """Where a give comes from: the parts of a Give that depend on its entry or guild."""

    entry: EntryId
    source: Source
    giver_rank: tuple[str, ...]
    guild: GuildId | None
    secret_guild: GuildId | None
    retired: bool
    replaced: bool


def _gives(
    player: _Player,
    catalog: Catalog,
    class_counts: Mapping[ItemClassId, Sequence[tuple[UserId, int]]],
    first_id: int,
) -> list[_Candidate]:
    held = {e.id for e in player.held}
    replaced = {r for e in player.held for r in e.replaces} & held
    modifiers = [e for e in player.held if e.modifier is not None and e.id not in replaced]

    origins: list[tuple[_Origin, Ability]] = []
    for entry in player.held:
        guild = catalog.guilds.get(entry.guild) if entry.guild is not None else None
        origin = _Origin(
            entry=entry.id,
            source=Source(SourceKind(entry.kind.value), tree=entry.tree, guild=entry.guild),
            giver_rank=(entry.name,) if entry.kind is EntryKind.RANK else (),
            guild=entry.guild,
            secret_guild=guild.id if guild is not None and guild.secret else None,
            retired=entry.retired,
            replaced=entry.id in replaced,
        )
        origins += [(origin, ability) for ability in entry.abilities]
    # Bonuses from Discord roles, e.g. Support: once, however many roles (HV-3).
    for guild in catalog.role_guilds(player.roles):
        origins += [(_role_origin(guild, player.roles), a) for a in guild.role_abilities]

    candidates = []
    for number, (origin, ability) in enumerate(origins, start=first_id):
        adjustments = tuple(
            Adjustment(m.id, m.modifier.add)
            for m in modifiers
            if m.modifier is not None and ability.has_numbers and m.modifier.applies_to(ability)
        )
        extra = sum(a.amount for a in adjustments)
        give = Give(
            id=number,
            giver=player.user_id,
            entry=origin.entry,
            bonus=ability.name,
            source=origin.source,
            giver_rank=origin.giver_rank,
            base=dict(ability.gives),
            adjustments=adjustments,
            amounts={stat: n + extra for stat, n in ability.gives.items()},
            level_rules=tuple(
                LevelRule(b.min_level, b.max_level, dict(b.gives)) for b in ability.level_rules
            ),
            effect=ability.effect,
            condition=ability.condition,
            audience=_audience(ability, origin),
            includes_giver=ability.includes_giver,
            stacks=ability.stacks,
            secret_guild=origin.secret_guild,
            retired=origin.retired,
            needs_item_class=ability.needs_item_class,
            per_item_class=ability.per_item_class,
            class_counts=(
                tuple(class_counts.get(ability.per_item_class, ()))
                if ability.per_item_class is not None
                else ()
            ),
        )
        candidates.append(_Candidate(give, origin.replaced, ability.level_rules, extra))
    return candidates


def _role_origin(guild: CatalogGuild, roles: frozenset[str]) -> _Origin:
    return _Origin(
        # The guild stands in for an entry: role bonuses aren't added with /add.
        entry=EntryId(guild.id),
        source=Source(SourceKind.ROLE, guild=guild.id),
        giver_rank=tuple(r for r in guild.roles if r in roles),
        guild=guild.id,
        secret_guild=guild.id if guild.secret else None,
        retired=False,
        replaced=False,
    )


def _audience(ability: Ability, origin: _Origin) -> Audience:
    if ability.per_item_class is not None:
        return Audience(AudienceKind.HOLDER)
    if ability.audience is CatalogAudience.GUILD:
        return Audience(AudienceKind.GUILD, guild=origin.guild)
    if ability.audience is CatalogAudience.HOLDERS:
        return Audience(AudienceKind.HOLDERS, entry=origin.entry)
    return Audience(AudienceKind.PARTY)


# ---------------------------------------------------------------- steps 3-5


def _receive(
    player: _Player, candidates: Sequence[_Candidate], catalog: Catalog
) -> RecipientReport:
    held = {e.id for e in player.held}
    not_applied: list[NotApplied] = []
    received: list[tuple[_Candidate, dict[StatId, int]]] = []

    # Step 3: check each give against this recipient.
    for candidate in candidates:
        give = candidate.give
        amounts: dict[StatId, int] = dict(give.amounts)
        reason: Reason | None = None
        if candidate.replaced:
            reason = Reason.REPLACED
        elif give.audience.kind is AudienceKind.HOLDER:
            # Counted across the party: only to the holder (rule 4.15).
            if give.giver != player.user_id:
                reason = Reason.NOT_IN_AUDIENCE
            elif give.class_total == 0:
                reason = Reason.NO_ITEM_CLASS
            else:
                amounts = {stat: n * give.class_total for stat, n in amounts.items()}
        elif give.giver == player.user_id and not give.includes_giver:
            reason = Reason.GIVER_EXCLUDED
        elif not _in_audience(give.audience, player, held):
            reason = Reason.NOT_IN_AUDIENCE
        elif give.needs_item_class is not None and give.needs_item_class not in player.item_counts:
            reason = Reason.NO_ITEM_CLASS  # rule 4.14
        elif candidate.bands:
            band = _band(candidate.bands, player.level)
            if player.level is None:
                reason = Reason.NO_LEVEL
            elif band is None:
                reason = Reason.NOT_IN_AUDIENCE  # no band covers this level
            else:
                amounts = {stat: n + candidate.extra for stat, n in band.gives.items()}
        if reason is None:
            received.append((candidate, amounts))
        else:
            not_applied.append(NotApplied(give.id, reason))

    # Step 4: a bonus that doesn't stack counts once per recipient: the highest.
    best: dict[tuple[str, bool], tuple[_Candidate, dict[StatId, int]]] = {}
    for candidate, amounts in received:
        give = candidate.give
        if not give.stacks:
            key = (give.bonus, give.condition is not None)
            if key not in best or _rank(amounts) > _rank(best[key][1]):
                best[key] = (candidate, amounts)

    # Step 5: sort into totals, conditional bonuses and effects.
    applied: list[Applied] = []
    conditional: list[ConditionalBonus] = []
    effects: list[int] = []
    for candidate, amounts in received:
        give = candidate.give
        if not give.stacks and best[(give.bonus, give.condition is not None)][0] is not candidate:
            not_applied.append(NotApplied(give.id, Reason.NOT_STACKED))
        elif give.condition is not None:
            conditional.append(ConditionalBonus(give.id, amounts, give.condition))
        else:
            if amounts:
                applied.append(Applied(give.id, amounts))
            if give.effect is not None:
                effects.append(give.id)

    return RecipientReport(
        user_id=player.user_id,
        name=player.name,
        character=player.character,
        totals=_totals(applied, catalog),
        applied=tuple(applied),
        not_applied=tuple(sorted(not_applied, key=lambda n: n.give)),
        conditional=tuple(conditional),
        effects=tuple(effects),
        item_counts=player.item_counts,
    )


def _in_audience(audience: Audience, player: _Player, held: set[EntryId]) -> bool:
    if audience.kind is AudienceKind.GUILD:
        return audience.guild in player.guilds
    if audience.kind is AudienceKind.HOLDERS:
        return audience.entry in held
    return True


def _band(bands: Sequence[LevelBand], level: int | None) -> LevelBand | None:
    """The band covering the recipient's level (rule 4.10)."""
    if level is None:
        return None
    return next((b for b in bands if b.covers(level)), None)


def _rank(amounts: Mapping[StatId, int]) -> tuple[int, tuple[tuple[StatId, int], ...]]:
    """Orders the gives of a bonus that doesn't stack: the highest total counts (rule 4.4).

    Ties are broken by the amounts themselves, never by who gives them, so the
    order of players can't change the result.
    """
    return sum(amounts.values()), tuple(sorted(amounts.items()))


def _totals(applied: Sequence[Applied], catalog: Catalog) -> dict[StatId, int]:
    """Each stat's total; a subtype's includes its parent's (rule 4.7)."""
    direct: dict[StatId, int] = {}
    for line in applied:
        for stat, n in line.amounts.items():
            direct[stat] = direct.get(stat, 0) + n
    totals: dict[StatId, int] = {}
    for stat in catalog.stat_order:
        parent = catalog.stats[stat].parent
        totals[stat] = direct.get(stat, 0) + (totals[parent] if parent is not None else 0)
    return totals
