"""The output commands' text (section 6.6), laid out as in section 9.

Each function turns a PartyReport into blocks of lines; ``messages.to_messages``
splits them into Discord messages. Tables sit in code blocks so they line up;
timestamps and channel mentions stay outside them, where Discord renders them.
"""

import textwrap
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from awt_bonus.catalog import Catalog, StatKind
from awt_bonus.engine import (
    AudienceKind,
    Give,
    PartyReport,
    Reason,
    RecipientReport,
    SourceKind,
)
from awt_bonus.ids import ChannelId, GuildId, StatId, UserId
from awt_bonus.output.describe import (
    amount,
    amounts,
    band,
    channel_mention,
    class_name,
    guild_name,
    item_counts,
    names,
    plural,
    timestamp,
    total,
)
from awt_bonus.output.messages import Block, code, text

RULE = "-" * 49
"""The line between sections."""

WIDTH = 72
"""Longer lines of prose in a code block are wrapped, so they read on a phone."""

SECRET = "secret guild bonus"
"""What a secret guild bonus is called when it can't be named (SG-4)."""

type RenderOne = Callable[[Party, RecipientReport, Sequence[str]], list[Block]]
"""/mybonus or /breakdown <character>: the party, the character, and any OUT-2a notice."""


@dataclass(frozen=True)
class Party:
    """What the output needs besides the report."""

    report: PartyReport
    catalog: Catalog
    channel: ChannelId | None
    """The voice channel; None when there's no party (OUT-4)."""
    level_updated: Mapping[str, datetime | None] = field(default_factory=dict)
    """When each counted character's level was last updated (CH-6), by name."""
    no_character_fix: Mapping[UserId, str] = field(default_factory=dict)
    """For each counted player with no character: the command that fixes it (SE-5)."""
    guilds: Mapping[UserId, frozenset[GuildId]] = field(default_factory=dict)
    """The guilds each counted character belongs to, by player."""
    detail_for: UserId | None = None
    """The player whose own character is being viewed by them (SG-5). That character's
    secret guild bonuses are shown in detail, for secret guilds it belongs to; every
    other secret guild bonus is shown unnamed, with no givers (SG-3, SG-4)."""

    def hidden(self, give: Give) -> bool:
        """Whether a give is from a secret guild and must be shown unnamed (SG-4)."""
        if give.secret_guild is None:
            return False
        if self.detail_for is None:
            return True
        return give.secret_guild not in self.guilds.get(self.detail_for, frozenset())

    def bonus_name(self, give: Give) -> str:
        return SECRET if self.hidden(give) else give.bonus

    def name_of(self, user_id: UserId) -> str:
        for recipient in self.report.recipients:
            if recipient.user_id == user_id:
                return recipient.name
        return "someone"

    def replaced(self) -> set[int]:
        """Gives replaced by another entry of the same giver (rule 4.5)."""
        return {
            n.give
            for r in self.report.recipients
            for n in r.not_applied
            if n.reason is Reason.REPLACED
        }

    def gives_by(self, user_id: UserId) -> list[Give]:
        """Everything this player gives, replaced entries and unnamed secret gives left out."""
        replaced = self.replaced()
        return [
            g
            for g in self.report.gives
            if g.giver == user_id and g.id not in replaced and not self.hidden(g)
        ]

    def display_name(self, recipient: RecipientReport) -> str:
        """The name in tables; a player with no character is marked with * (SE-5)."""
        return recipient.name + ("*" if recipient.character is None else "")


# ---------------------------------------------------------------- stats


def roll_columns(party: Party) -> list[StatId]:
    """CM, CR, and the CR subtypes that differ from CR for someone (OUT-1)."""
    catalog = party.catalog
    columns = []
    for stat in catalog.stat_order:
        info = catalog.stats[stat]
        if info.kind is not StatKind.ROLL:
            continue
        if info.parent is None or any(
            r.totals.get(stat, 0) != r.totals.get(info.parent, 0) for r in party.report.recipients
        ):
            columns.append(stat)
    return columns


def combat_notes(catalog: Catalog) -> list[StatId]:
    return [s for s in catalog.stat_order if catalog.stats[s].kind is StatKind.COMBAT_NOTE]


def _contributions(
    party: Party, recipient: RecipientReport, stat: StatId
) -> list[tuple[Give, int]]:
    """What adds up to a recipient's stat: Discord-role bonuses first, then in order."""
    lines = [
        (party.report.give(a.give), a.amounts[stat]) for a in recipient.applied if stat in a.amounts
    ]
    lines.sort(key=lambda pair: (pair[0].source.kind is not SourceKind.ROLE, pair[0].id))
    return lines


@dataclass(frozen=True)
class _Line:
    """One line of a recipient's working for one stat."""

    amount: int
    term: str
    """How it's written in the sum: "3", or "3s" for unnamed secret guild bonuses."""
    bonus: str
    source: str
    """Who gave it, e.g. "from <giver> (<Guild rank>)", "(1 other member present)"."""


def _lines(party: Party, recipient: RecipientReport, stat: StatId) -> list[_Line]:
    """The contributions to a stat. Secret guild bonuses come last: in detail, one line per
    bonus with a count of givers (SG-5); otherwise all together, unnamed (SG-4)."""
    lines: list[_Line] = []
    detailed: dict[str, list[tuple[Give, int]]] = {}
    hidden = 0
    not_stacked = _not_stacked(party, recipient)
    for give, n in _contributions(party, recipient, stat):
        if party.hidden(give):
            hidden += n
        elif give.secret_guild is not None:
            detailed.setdefault(give.bonus, []).append((give, n))
        else:
            givers = [party.name_of(give.giver), *not_stacked.get(give.id, [])]
            source = f"from {', '.join(givers)}{_rank(give) if len(givers) == 1 else ''}"
            if give.per_item_class is not None:
                source = f"({_per_item(party, give)})"
            source += adjusted(give, party.catalog)
            if len(givers) > 1:
                source += " (doesn't stack: counted once)"
            lines.append(_Line(n, str(n), give.bonus, source))
    for bonus, pairs in detailed.items():
        n = sum(amount for _, amount in pairs)
        lines.append(_Line(n, str(n), bonus, _count(recipient, [g for g, _ in pairs])))
    if hidden:
        lines.append(_Line(hidden, f"{hidden}s", SECRET, "(givers not shown)"))
    return lines


def _count(recipient: RecipientReport, gives: Sequence[Give]) -> str:
    """How many members gave a secret guild bonus, never who (SG-5)."""
    first = gives[0]
    if not first.stacks:
        rank = first.giver_rank[0] if first.giver_rank else None
        if rank is None:
            return "(from a member present)"
        article = "an" if rank[0].lower() in "aeiou" else "a"
        return f"({article} {rank} is present)"
    others = len({g.giver for g in gives if g.giver != recipient.user_id})
    included = any(g.giver == recipient.user_id for g in gives)
    return f"({plural(others, 'other member')} present" + (
        f", {recipient.name} included)" if included else ")"
    )


def _secret_note(party: Party, stats: Sequence[StatId]) -> list[str]:
    """The key for "s" in the working, if any is used."""
    for recipient in party.report.recipients:
        for stat in stats:
            if any(line.term.endswith("s") for line in _lines(party, recipient, stat)):
                return [f"(s = {SECRET})"]
    return []


def _working(party: Party, recipient: RecipientReport, stat: StatId) -> str:
    """E.g. "CM 2+3+5 = +10" or "CR vs fear 5+3 = +8" (OUT-3)."""
    catalog = party.catalog
    terms = [line.term for line in _lines(party, recipient, stat)]
    parent = catalog.stats[stat].parent
    if parent is not None and recipient.totals.get(parent, 0):
        terms.insert(0, str(recipient.totals[parent]))
    shown = total(stat, recipient.totals.get(stat, 0), catalog)
    if catalog.stats[stat].kind is StatKind.COMBAT_NOTE and len(terms) == 1:
        return f"{stat} {shown}"
    return f"{stat} {'+'.join(terms)} = {shown}" if terms else f"{stat} {shown}"


# ---------------------------------------------------------------- shared pieces


def heading(title: str, party: Party) -> Block:
    counted = len(party.report.recipients)
    where = channel_mention(party.channel) if party.channel is not None else "no party"
    return text(f"**{title}**: {where} ({counted} counted)")


def not_counted(party: Party) -> Block | None:
    """Everyone in the channel who is sitting out, with the time it ends (SE-4)."""
    if not party.report.not_counted:
        return None
    people = ", ".join(
        f"{n.name} (sitting out until {timestamp(n.until, 't')})" for n in party.report.not_counted
    )
    return text(f"Not counted: {people}")


def no_character(party: Party) -> list[str]:
    """The NO CHARACTER SET UP section (SE-5)."""
    if not party.report.no_character:
        return []
    lines = [RULE, "NO CHARACTER SET UP (* only bonuses from Discord roles are counted)"]
    width = max(len(party.name_of(u)) for u in party.report.no_character) + 4
    for user_id in party.report.no_character:
        fix = party.no_character_fix.get(
            user_id, "no character registered: use /character register"
        )
        lines.append(f"  {party.name_of(user_id):<{width}}{fix}")
    return lines


def who(party: Party, receiving: Sequence[RecipientReport]) -> str:
    """ "All", "All but Crateris", or the names (for effects and conditional bonuses)."""
    everyone = party.report.recipients
    names_in = [r.name for r in receiving]
    missing = [r.name for r in everyone if r not in receiving]
    if not missing:
        return "All"
    if len(missing) < len(names_in):
        return f"All but {names(missing)}"
    return names(names_in)


def source(give: Give, catalog: Catalog) -> str:
    """Where a give comes from, e.g. "Holy Knight", "GoTH boon", "title" (OUT-3)."""
    kind = give.source.kind
    if kind is SourceKind.SKILL:
        return give.source.tree or "skill"
    if kind is SourceKind.ROLE:
        return guild_name(give.source.guild, catalog)
    if kind in (SourceKind.BOON, SourceKind.RANK):
        guild = catalog.guilds.get(give.source.guild) if give.source.guild is not None else None
        short = guild.short_name if guild is not None else str(give.source.guild)
        return f"{short} {kind.value}"
    return kind.value


def adjusted(give: Give, catalog: Catalog) -> str:
    """How modifiers changed a give, e.g. " (2 + 1 Devotion III)" (OUT-3a)."""
    if not give.adjustments:
        return ""
    added = " + ".join(
        f"{a.amount} {catalog.entries[a.entry].name if a.entry in catalog.entries else a.entry}"
        for a in give.adjustments
    )
    bases = set(give.base.values())
    base = str(bases.pop()) if len(bases) == 1 else "each"
    return f" ({base} + {added})"


def audience(give: Give, catalog: Catalog) -> str:
    """Who receives a give, e.g. "to allies", "to other Cult of the Dragon members"."""
    target = give.audience
    if target.kind is AudienceKind.GUILD:
        name = guild_name(target.guild, catalog)
        return f"to all {name} members" if give.includes_giver else f"to other {name} members"
    if target.kind is AudienceKind.HOLDERS:
        entry = catalog.entries.get(target.entry) if target.entry is not None else None
        held = entry.name if entry is not None else give.bonus
        return f"to all {held} holders" if give.includes_giver else f"to other {held} holders"
    if target.kind is AudienceKind.HOLDER:
        return "to the holder"
    who = "to the giver and allies" if give.includes_giver else "to allies"
    if give.needs_item_class is not None:
        who += f" with a {class_name(give.needs_item_class, catalog)} item in use"
    return who


def gives_text(give: Give, catalog: Catalog) -> str:
    """What a give gives, e.g. "+3 CR vs fear (2 + 1 Devotion III)"."""
    parts = []
    if give.level_rules:
        rules = "; ".join(
            f"{band(r.min_level, r.max_level)}: {amounts(r.amounts, catalog)}"
            for r in give.level_rules
        )
        parts.append(f"by the recipient's level ({rules})")
    elif give.amounts:
        parts.append(amounts(give.amounts, catalog) + adjusted(give, catalog))
    if give.effect is not None:
        parts.append(f"effect: {give.effect}")
    return "; ".join(parts)


def conditional_line(party: Party, recipient_give: Give, values: Mapping[StatId, int]) -> str:
    """E.g. "+5 CM from Vex (Commanding Presence): allies in the same range" (rule 4.12)."""
    if recipient_give.secret_guild is not None:
        name = party.bonus_name(recipient_give)
        return f"{amounts(values, party.catalog)} ({name}): {recipient_give.condition}"
    giver = party.name_of(recipient_give.giver)
    return (
        f"{amounts(values, party.catalog)} from {giver} ({recipient_give.bonus}): "
        f"{recipient_give.condition}"
    )


def wrapped(line: str, indent: int = 4) -> list[str]:
    """A long line wrapped at ``WIDTH``, continuation lines indented further."""
    lead = len(line) - len(line.lstrip())
    return textwrap.wrap(
        line.strip(),
        WIDTH,
        initial_indent=" " * lead,
        subsequent_indent=" " * (lead + indent),
        break_on_hyphens=False,
    ) or [line]


def _rank(give: Give) -> str:
    return f" ({', '.join(give.giver_rank)})" if give.giver_rank else ""


# ---------------------------------------------------------------- /partybonus


def partybonus(party: Party) -> list[Block]:
    """OUT-1: totals only."""
    report = party.report
    blocks = [heading("PARTY BONUSES", party)]
    if not report.recipients:
        blocks.append(text("Nobody in the channel is counted."))
    else:
        columns = roll_columns(party)
        rows = [["CHARACTER", *columns]] + [
            [party.display_name(r), *(f"{r.totals.get(s, 0):+d}" for s in columns)]
            for r in report.recipients
        ]
        blocks.append(code(*_table(rows)))
        blocks.append(code(*_combat_notes(party)))
        blocks.append(code(*_effects(party)))
        blocks.append(code(*_conditional(party)))
        blocks.append(code(*no_character(party)))
    blocks.append(_optional(not_counted(party)))
    return [b for b in blocks if b.lines]


def _table(rows: Sequence[Sequence[str]]) -> list[str]:
    widths = [max(len(row[i]) for row in rows) + 3 for i in range(len(rows[0]))]
    return [
        "".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in rows
    ]


def _combat_notes(party: Party) -> list[str]:
    lines = []
    catalog = party.catalog
    width = max(len(r.name) for r in party.report.recipients) + 4
    for recipient in party.report.recipients:
        for stat in combat_notes(catalog):
            n = recipient.totals.get(stat, 0)
            if n:
                description = catalog.stats[stat].description
                about = f" ({description})" if description else ""
                name = party.display_name(recipient)
                lines.append(f"{name:<{width}}{stat} {total(stat, n, catalog)}{about}")
    return [RULE, "COMBAT NOTES", *lines] if lines else []


def _effects(party: Party) -> list[str]:
    """Each effect and who receives it (OUT-1)."""
    grouped: dict[tuple[str, str], list[RecipientReport]] = {}
    for recipient in party.report.recipients:
        for give_id in recipient.effects:
            give = party.report.give(give_id)
            key = (give.effect or "", party.bonus_name(give))
            if recipient not in grouped.setdefault(key, []):
                grouped[key].append(recipient)
    if not grouped:
        return []
    labels = {key: _who(party, receiving, key[1] == SECRET) for key, receiving in grouped.items()}
    width = max(len(label) for label in labels.values()) + 3
    lines = [f"{labels[key]:<{width}}{key[0]} ({key[1]})" for key in grouped]
    return [RULE, "EFFECTS", *lines]


def _conditional(party: Party) -> list[str]:
    """Conditional bonuses, with their conditions, never in totals (rule 4.12)."""
    grouped: dict[tuple[int, str], list[RecipientReport]] = {}
    lines_for: dict[tuple[int, str], str] = {}
    for recipient in party.report.recipients:
        for bonus in recipient.conditional:
            give = party.report.give(bonus.give)
            line = conditional_line(party, give, bonus.amounts)
            key = (bonus.give, line)
            grouped.setdefault(key, []).append(recipient)
            lines_for[key] = line
    if not grouped:
        return []
    labels = {
        key: _who(party, receiving, party.report.give(key[0]).secret_guild is not None)
        for key, receiving in grouped.items()
    }
    width = max(len(label) for label in labels.values()) + 3
    lines = [f"{labels[key]:<{width}}{lines_for[key]}" for key in grouped]
    return [RULE, "CONDITIONAL BONUSES (not in totals: add them when they apply)", *lines]


def _who(party: Party, receiving: Sequence[RecipientReport], secret: bool) -> str:
    """Who receives something; for a secret guild bonus, never who the members are (SG-3)."""
    label = who(party, receiving)
    return label if not secret or label == "All" else "Each member present"


def _optional(block: Block | None) -> Block:
    return block if block is not None else Block()


# ---------------------------------------------------------------- party /breakdown


def party_breakdown(party: Party) -> list[Block]:
    """OUT-3: every bonus in play, its contributors, and the working."""
    report = party.report
    blocks = [heading("PARTY BREAKDOWN", party)]
    if not report.recipients:
        blocks.append(text("Nobody in the channel is counted."))
        blocks.append(_optional(not_counted(party)))
        return [b for b in blocks if b.lines]
    groups = _groups(party)
    for group in groups:
        if group.gives[0].effect is None or group.gives[0].amounts or group.gives[0].level_rules:
            blocks.append(code(*_group_lines(party, group), ""))
    blocks.append(code(*_secret_block(party)))
    for group in groups:
        if group.gives[0].effect is not None and not (
            group.gives[0].amounts or group.gives[0].level_rules
        ):
            blocks.append(code(*_effect_group_lines(party, group), ""))
    blocks.append(code(RULE, "TOTALS", *_totals(party)))
    blocks.append(code(*no_character(party)))
    blocks.append(_optional(not_counted(party)))
    return [b for b in blocks if b.lines]


def _secret_block(party: Party) -> list[str]:
    """Every secret guild bonus in play as one unnamed block, givers never shown (SG-4)."""
    received: list[tuple[tuple[StatId, int], ...]] = []
    effects: dict[str, None] = {}
    conditional: dict[str, None] = {}
    for recipient in party.report.recipients:
        totals: dict[StatId, int] = {}
        for applied in recipient.applied:
            if party.hidden(party.report.give(applied.give)):
                for stat, n in applied.amounts.items():
                    totals[stat] = totals.get(stat, 0) + n
        if totals:
            received.append(tuple((s, totals[s]) for s in party.catalog.stat_order if s in totals))
        for give_id in recipient.effects:
            give = party.report.give(give_id)
            if party.hidden(give) and give.effect is not None:
                effects[give.effect] = None
        for bonus in recipient.conditional:
            give = party.report.give(bonus.give)
            if party.hidden(give):
                conditional[f"{amounts(bonus.amounts, party.catalog)}: {bonus.condition}"] = None
    if not (received or effects or conditional):
        return []
    header = SECRET[0].upper() + SECRET[1:]
    lines = []
    if received and len(set(received)) == 1:
        each = names(amount(stat, n, party.catalog) for stat, n in received[0])
        lines += wrapped(f"{header}: {each} to each member present", indent=2)
    elif received:
        lines.append(f"{header}: amounts vary by member (see the working)")
    lines += [f"{header}, effect: {effect}" for effect in effects]
    lines += [f"{header}, only for {c} (not in totals)" for c in conditional]
    return [*lines, "    (givers not shown)", ""]


@dataclass
class _Group:
    """Gives shown together: the same bonus, giving the same thing."""

    header: str
    gives: list[Give]


def _groups(party: Party) -> list[_Group]:
    catalog = party.catalog
    replaced = party.replaced()
    groups: dict[str, _Group] = {}
    ordered = sorted(
        (g for g in party.report.gives if g.id not in replaced and not party.hidden(g)),
        key=lambda g: (g.source.kind is not SourceKind.ROLE, g.id),
    )
    for give in ordered:
        header = _group_header(give, catalog)
        groups.setdefault(header, _Group(header, [])).gives.append(give)
    return list(groups.values())


def _group_header(give: Give, catalog: Catalog) -> str:
    what = gives_text(give, catalog) if not give.level_rules else ""
    parts = [f"{give.bonus} ({source(give, catalog)}):"]
    if give.effect is not None and not (give.amounts or give.level_rules):
        return f"Effect: {give.effect} ({give.bonus}), {audience(give, catalog)}"
    if give.level_rules:
        parts.append("by the recipient's level,")
    if what:
        parts.append(what.replace(adjusted(give, catalog), ""))
    parts.append(audience(give, catalog))
    header = " ".join(parts) + adjusted(give, catalog)
    if give.source.kind is SourceKind.ROLE:
        header += " from each giver"
    if not give.stacks:
        header += ", doesn't stack"
    if give.condition is not None:
        header += f", only for {give.condition} (not in totals)"
    if give.retired:
        header += " (retired)"
    return header


def _per_item(party: Party, give: Give) -> str:
    """Who a bonus counted across the party counts, e.g. "per passion item: Chris 1, Elizor 2"."""
    counted = ", ".join(f"{party.name_of(user)} {n}" for user, n in give.class_counts)
    return f"per {class_name(give.per_item_class, party.catalog)} item: {counted}"


def _per_item_lines(party: Party, group: _Group) -> list[str]:
    """One line for each holder of a bonus counted across the party, with its working
    (rule 4.15), e.g. "Will Passions Adventure Token (Chris): +6 CM (per passion item: ...)"."""
    lines = []
    for give in group.gives:
        holder = next(r for r in party.report.recipients if r.user_id == give.giver)
        applied = next((a for a in holder.applied if a.give == give.id), None)
        if applied is None:
            item = class_name(give.per_item_class, party.catalog)
            working = f"nothing: no {item} items in use in the party"
        else:
            working = f"{amounts(applied.amounts, party.catalog)} ({_per_item(party, give)})"
        retired = " (retired)" if give.retired else ""
        # One line, never wrapped: the working reads as one sum.
        lines.append(f"{give.bonus} ({holder.name}): {working}{retired}")
    return lines


def _group_lines(party: Party, group: _Group) -> list[str]:
    if group.gives[0].per_item_class is not None:
        return _per_item_lines(party, group)
    lines = wrapped(group.header, indent=2)
    if group.gives[0].level_rules:
        for give in group.gives:
            lines += _level_lines(party, give)
        return lines
    ranked = any(g.giver_rank for g in group.gives)
    notes = [_replaces(party, g) for g in group.gives]
    if ranked or any(notes):
        width = max(len(party.name_of(g.giver)) for g in group.gives) + 3
        for give, note in zip(group.gives, notes, strict=True):
            rank = ", ".join(give.giver_rank)
            line = f"    {party.name_of(give.giver):<{width}}{rank:<22}{note}"
            lines.append(line.rstrip())
    else:
        lines.append("    " + ", ".join(party.name_of(g.giver) for g in group.gives))
    return lines


def _replaces(party: Party, give: Give) -> str:
    entry = party.catalog.entries.get(give.entry)
    if entry is None or not entry.replaces:
        return ""
    replaced = party.replaced()
    names_replaced = [
        g.bonus
        for g in party.report.gives
        if g.giver == give.giver and g.id in replaced and g.entry in entry.replaces
    ]
    return f"(replaces {names(dict.fromkeys(names_replaced))})" if names_replaced else ""


def _level_lines(party: Party, give: Give) -> list[str]:
    """A level-based give: what each recipient gets, by level (rule 4.10)."""
    received = []
    for recipient in party.report.recipients:
        for applied in recipient.applied:
            if applied.give == give.id:
                level = recipient.character.level if recipient.character else None
                received.append(
                    f"{amounts(applied.amounts, party.catalog)} to {recipient.name} (level {level})"
                )
    giver = f"    {party.name_of(give.giver):<11}{', '.join(give.giver_rank):<22}"
    if not received:
        return [f"{giver}nobody present receives it".rstrip()]
    return [(giver if i == 0 else " " * len(giver)) + line for i, line in enumerate(received)]


def _effect_group_lines(party: Party, group: _Group) -> list[str]:
    return [
        *wrapped(group.header, indent=2),
        "    " + ", ".join(party.name_of(g.giver) for g in group.gives),
    ]


def _totals(party: Party) -> list[str]:
    """The working for each counted player's totals (OUT-3)."""
    catalog = party.catalog
    stats = roll_columns(party) + combat_notes(catalog)
    rows: list[list[str]] = []
    for recipient in party.report.recipients:
        items = [
            _working(party, recipient, stat)
            for stat in stats
            if recipient.totals.get(stat, 0)
            and (catalog.stats[stat].parent is None or _differs(recipient, stat, catalog))
        ]
        rows.append([party.display_name(recipient), *(items or ["no bonuses"])])
    return _flow(rows, per_line=3) + _secret_note(party, stats)


def _differs(recipient: RecipientReport, stat: StatId, catalog: Catalog) -> bool:
    parent = catalog.stats[stat].parent
    return parent is None or recipient.totals.get(stat, 0) != recipient.totals.get(parent, 0)


def _flow(rows: Sequence[Sequence[str]], per_line: int) -> list[str]:
    """Each row's name, then its items, ``per_line`` to a line, in lined-up columns."""
    name_width = max((len(row[0]) for row in rows), default=0) + 3
    chunks = [
        [list(row[1 + i : 1 + i + per_line]) for i in range(0, max(len(row) - 1, 1), per_line)]
        for row in rows
    ]
    widths = [0] * per_line
    for row_chunks in chunks:
        for chunk in row_chunks:
            for i, item in enumerate(chunk):
                widths[i] = max(widths[i], len(item) + 3)
    lines = []
    for row, row_chunks in zip(rows, chunks, strict=True):
        for n, chunk in enumerate(row_chunks):
            label = row[0] if n == 0 else ""
            cells = "".join(item.ljust(widths[i]) for i, item in enumerate(chunk))
            lines.append(f"{label:<{name_width}}{cells}".rstrip())
    return lines


# ---------------------------------------------------------------- /mybonus


def notice_lines(notice: Sequence[str]) -> Block:
    return text(*notice)


def mybonus(party: Party, recipient: RecipientReport, notice: Sequence[str]) -> list[Block]:
    """OUT-2: one character's totals, and a note about any bonus missed for no level."""
    catalog = party.catalog
    blocks = [
        text(
            f"**{_title(recipient)}**: {channel_mention(party.channel)}"
            if party.channel
            else _title(recipient)
        )
    ]
    blocks.append(notice_lines(notice))
    stats = [s for s in roll_columns(party) if _differs(recipient, s, catalog)]
    rows = [[s, f"{recipient.totals.get(s, 0):+d}"] for s in stats]
    for stat in combat_notes(catalog):
        n = recipient.totals.get(stat, 0)
        if n:
            description = catalog.stats[stat].description
            rows.append(
                [stat, total(stat, n, catalog) + (f" ({description})" if description else "")]
            )
    width = max(len(row[0]) for row in rows) + 2
    lines = [f"{label:<{width}}{value}" for label, value in rows]
    effects = [
        f"{party.report.give(g).effect} ({party.bonus_name(party.report.give(g))})"
        for g in dict.fromkeys(recipient.effects)
    ]
    if effects:
        lines += [RULE, *dict.fromkeys(effects)]
    if recipient.conditional:
        lines += [RULE, "CONDITIONAL BONUSES (not in totals: add them when they apply)"]
        for c in recipient.conditional:
            lines += wrapped(conditional_line(party, party.report.give(c.give), c.amounts))
    lines += _secret_detail(party, recipient)
    blocks.append(code(*lines))
    footer = _class_notes(party, recipient)
    missed = _no_level(recipient)
    if missed:
        name = recipient.character.name if recipient.character else "<character>"
        footer.append(
            f"{plural(missed, 'bonus')} not applied: level not recorded. "
            f"Use `/character level {name} <n>`."
        )
    if recipient.character is None:
        footer.append(
            "You have no character set up, so you give only bonuses from Discord roles. "
            "Register one with `/character register <name>`."
        )
    else:
        footer.append(f"See how this was worked out: `/breakdown {recipient.name}`")
    blocks.append(text(*footer))
    return [b for b in blocks if b.lines]


def _secret_detail(party: Party, recipient: RecipientReport) -> list[str]:
    """A member's own secret guild bonuses, with how many gave them, not who (SG-5)."""
    by_guild: dict[GuildId, dict[str, list[tuple[Give, Mapping[StatId, int]]]]] = {}
    for applied in recipient.applied:
        give = party.report.give(applied.give)
        if give.secret_guild is not None and not party.hidden(give):
            bonuses = by_guild.setdefault(give.secret_guild, {})
            bonuses.setdefault(give.bonus, []).append((give, applied.amounts))
    lines: list[str] = []
    for guild, bonuses in by_guild.items():
        lines += [RULE, f"Secret guild ({guild_name(guild, party.catalog)}), included above:"]
        width = max(len(bonus) for bonus in bonuses) + 3
        for bonus, pairs in bonuses.items():
            summed: dict[StatId, int] = {}
            for _, values in pairs:
                for stat, n in values.items():
                    summed[stat] = summed.get(stat, 0) + n
            count = _count(recipient, [g for g, _ in pairs])
            lines += wrapped(f"  {bonus:<{width}}{amounts(summed, party.catalog)} {count}")
    return lines


def _class_notes(party: Party, recipient: RecipientReport) -> list[str]:
    """One note for each class bonus in play the character misses with a count of 0 (IC-3)."""
    if recipient.character is None:
        return []
    notes: dict[str, str] = {}
    for n in recipient.not_applied:
        give = party.report.give(n.give)
        if n.reason is not Reason.NO_ITEM_CLASS or give.secret_guild is not None:
            continue
        item = class_name(give.needs_item_class or give.per_item_class, party.catalog)
        what = amounts(give.amounts, party.catalog)
        fix = (
            f"If you're using one, set it with "
            f"`/character items {recipient.character.name} {item} 1`."
        )
        if give.per_item_class is not None:
            missed = f"({what} per {item} item) has no {item} items in use in the party."
        else:
            missed = f"({what}) needs a {item} item in use."
        notes.setdefault(give.bonus, f"{give.bonus} {missed} {fix}")
    return list(notes.values())


def _title(recipient: RecipientReport) -> str:
    character = recipient.character
    if character is None:
        return f"{recipient.name} (no character set up)"
    level = f"level {character.level}" if character.level is not None else "level not recorded"
    return f"{recipient.name} ({level})"


def _no_level(recipient: RecipientReport) -> int:
    """Bonuses missed only because no level is recorded (CH-5)."""
    return len({n.give for n in recipient.not_applied if n.reason is Reason.NO_LEVEL})


# ---------------------------------------------------------------- /breakdown <character>


def character_breakdown(
    party: Party, recipient: RecipientReport, notice: Sequence[str]
) -> list[Block]:
    """OUT-3a: each stat, the sum written out, every contribution; not applied; gives."""
    catalog = party.catalog
    blocks = [
        text(_breakdown_title(party, recipient), *_counts_line(party, recipient)),
        notice_lines(notice),
    ]
    lines: list[str] = []
    stats = [s for s in roll_columns(party) if recipient.totals.get(s, 0)] + [
        s for s in combat_notes(catalog) if recipient.totals.get(s, 0)
    ]
    for stat in stats:
        lines += _stat_lines(party, recipient, stat)
    if any(line.term.endswith("s") for stat in stats for line in _lines(party, recipient, stat)):
        lines.append(f"(s = {SECRET})")
    if not stats:
        lines.append("Receives no bonuses to totals.")
    effects = list(dict.fromkeys(recipient.effects))
    if effects:
        lines += [RULE, "EFFECTS"]
        for give_id in effects:
            give = party.report.give(give_id)
            if give.secret_guild is not None:
                lines.append(f"  {give.effect} ({party.bonus_name(give)})")
            else:
                lines.append(f"  {give.effect} ({give.bonus}) from {party.name_of(give.giver)}")
    if recipient.conditional:
        lines += [RULE, "CONDITIONAL BONUSES (not in totals: add them when they apply)"]
        for c in recipient.conditional:
            lines += wrapped("  " + conditional_line(party, party.report.give(c.give), c.amounts))
    lines += _not_applied(party, recipient)
    lines += [RULE, f"WHAT {recipient.name} GIVES", *_gives_lines(party, recipient.user_id)]
    blocks.append(code(*lines))
    return [b for b in blocks if b.lines]


def _counts_line(party: Party, recipient: RecipientReport) -> list[str]:
    """The character's item class counts and how to change them (IC-3). Shown when it
    has any, or when a class bonus in play wasn't applied for lack of one."""
    character = recipient.character
    missed = any(
        n.reason is Reason.NO_ITEM_CLASS and party.report.give(n.give).secret_guild is None
        for n in recipient.not_applied
    )
    if character is None or not (recipient.item_counts or missed):
        return []
    counts = item_counts(recipient.item_counts, party.catalog) or "none"
    return [
        f"Item classes in use: {counts}. "
        f"Change with `/character items {character.name} <class> <count>`."
    ]


def _breakdown_title(party: Party, recipient: RecipientReport) -> str:
    character = recipient.character
    where = f": {channel_mention(party.channel)}" if party.channel is not None else ""
    if character is None:
        return f"**BREAKDOWN**: {recipient.name} (no character set up){where}"
    if character.level is None:
        return f"**BREAKDOWN**: {recipient.name} (level not recorded){where}"
    updated = party.level_updated.get(recipient.name)
    when = f", updated {timestamp(updated, 'd')}" if updated is not None else ""
    return f"**BREAKDOWN**: {recipient.name} (level {character.level}{when}){where}"


def _stat_lines(party: Party, recipient: RecipientReport, stat: StatId) -> list[str]:
    catalog = party.catalog
    contributions = _lines(party, recipient, stat)
    terms = [line.term for line in contributions]
    parent = catalog.stats[stat].parent
    if parent is not None and recipient.totals.get(parent, 0):
        terms.insert(0, f"{recipient.totals[parent]} (all {parent})")
    shown = total(stat, recipient.totals.get(stat, 0), catalog)
    lines = [f"{stat} = {' + '.join(terms)} = {shown}"]
    for line in contributions:
        lines.append(f"   {line.amount:+d}   {line.bonus:<22}{line.source}")
    return lines


def _not_stacked(party: Party, recipient: RecipientReport) -> dict[int, list[str]]:
    """For each counted give that doesn't stack, the other givers of the same bonus."""
    counted = {a.give for a in recipient.applied}
    others: dict[int, list[str]] = {}
    for n in recipient.not_applied:
        if n.reason is not Reason.NOT_STACKED:
            continue
        skipped = party.report.give(n.give)
        for give_id in counted:
            give = party.report.give(give_id)
            if give.bonus == skipped.bonus and not give.stacks:
                others.setdefault(give_id, []).append(party.name_of(skipped.giver))
    return others


def _not_applied(party: Party, recipient: RecipientReport) -> list[str]:
    """Bonuses in play this character doesn't receive, and why (OUT-3a).

    Replaced entries, not-stacked duplicates and other holders' bonuses counted
    across the party aren't listed. A class bonus gets a line of its own, with its
    reason (IC-3).
    """
    reasons: dict[str, list[str]] = {}
    by_class: dict[str, None] = {}
    for n in recipient.not_applied:
        give = party.report.give(n.give)
        if n.reason in (Reason.REPLACED, Reason.NOT_STACKED) or give.secret_guild is not None:
            continue  # secret guild bonuses are never listed here (SG-3)
        if give.audience.kind is AudienceKind.HOLDER and n.reason is Reason.NOT_IN_AUDIENCE:
            continue  # another character's own bonus (rule 4.15)
        why = _reason(party, recipient, give, n.reason)
        if n.reason is Reason.NO_ITEM_CLASS:
            by_class[f"  {give.bonus}: {why}"] = None
        elif give.bonus not in reasons.setdefault(why, []):
            reasons[why].append(give.bonus)
    if not (reasons or by_class):
        return []
    lines = [RULE, "NOT APPLIED"]
    for why, bonuses in reasons.items():
        lines += [f"  {why}:", *wrapped(f"    {', '.join(bonuses)}", indent=0)]
    return lines + list(by_class)


def _reason(party: Party, recipient: RecipientReport, give: Give, reason: Reason) -> str:
    name = recipient.name
    if reason is Reason.GIVER_EXCLUDED:
        return f"allies only ({name} is the giver)"
    if reason is Reason.NO_LEVEL:
        return f"level not recorded: use /character level {name} <n>"
    if reason is Reason.NO_ITEM_CLASS:
        item = class_name(give.needs_item_class or give.per_item_class, party.catalog)
        if give.per_item_class is not None:
            return f"no {item} items in use in the party"  # rule 4.15
        return f"no {item} item in use"  # rule 4.14
    target = give.audience
    if target.kind is AudienceKind.GUILD:
        guild = guild_name(target.guild, party.catalog)
        if recipient.character is not None and target.guild in party.guilds.get(
            recipient.user_id, frozenset()
        ):
            return f"not for level {recipient.character.level}"
        return f"{guild} members only ({name} isn't one)"
    if target.kind is AudienceKind.HOLDERS:
        return f"other {give.bonus} holders only"
    return "not in the audience"


def _gives_lines(party: Party, user_id: UserId) -> list[str]:
    """What a character gives the party (OUT-3a, OUT-4)."""
    catalog = party.catalog
    lines = []
    for give in party.gives_by(user_id):
        rank = _rank(give) if give.source.kind is SourceKind.RANK else ""
        line = f"  {give.bonus}{rank}"
        if give.amounts:
            line += f" {amounts(give.amounts, catalog)}{adjusted(give, catalog)}"
        if give.per_item_class is not None:
            item = class_name(give.per_item_class, catalog)
            line += f" per {item} item in use in the party"
        if give.level_rules:
            line += f": {gives_text(give, catalog)}"
        if give.effect is not None:
            line += f": {give.effect}" if not give.amounts else f"; effect: {give.effect}"
        if (
            give.audience.kind is not AudienceKind.PARTY
            or give.includes_giver
            or give.needs_item_class is not None
        ):
            line += f", {audience(give, catalog)}"
        if not give.stacks:
            line += ", doesn't stack"
        if give.condition is not None:
            line += f", only for {give.condition} (not in totals)"
        if give.retired:
            line += " (retired)"
        lines += wrapped(line)
    return lines or ["  No party bonuses."]


def gives_only(party: Party, recipient: RecipientReport, why: str) -> list[Block]:
    """OUT-4: no totals (no party, or sitting out), so only what the character gives."""
    return [
        text(f"**{_title(recipient)}**: no totals", why),
        code(f"WHAT {recipient.name} GIVES", *_gives_lines(party, recipient.user_id)),
    ]
