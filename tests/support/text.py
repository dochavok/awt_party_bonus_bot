"""Helpers for checking replies by behaviour, not layout (TF-1).

Numbers are checked on ``reply.report`` (the calculation behind the reply).
Text checks look only for what must, or must never, appear: names, notices,
timestamps, pronouns.
"""

import re
from datetime import datetime

from awt_bonus.commands import Reply
from awt_bonus.engine import RecipientReport
from awt_bonus.ids import StatId

PRONOUNS = re.compile(
    r"\b(he|she|him|her|his|hers|himself|herself|themself|themselves)\b", re.IGNORECASE
)
"""Pronouns that output must never use for a character (OUT-7)."""


def discord_timestamp(moment: datetime) -> str:
    """The start of a Discord timestamp for this moment, e.g. ``<t:1790380800`` (NF-10)."""
    return f"<t:{int(moment.timestamp())}"


def lines_with(text: str, *needles: str) -> list[str]:
    """The lines of ``text`` that contain every one of ``needles``."""
    return [line for line in text.splitlines() if all(n in line for n in needles)]


def mentions(text: str, needle: str) -> bool:
    return needle.casefold() in text.casefold()


def recipient(reply: Reply, name: str) -> RecipientReport:
    assert reply.report is not None, "an output command's reply must carry its report"
    return reply.report.recipient(name)


def stat(reply: Reply, name: str, stat_id: str) -> int:
    """One counted character's total for one stat, e.g. ``stat(reply, "Chris", "CM")``."""
    return recipient(reply, name).totals.get(StatId(stat_id), 0)


def totals(reply: Reply, name: str) -> dict[StatId, int]:
    """Every non-zero total for one counted character (or no-character player)."""
    return {stat: value for stat, value in recipient(reply, name).totals.items() if value}


def counted(reply: Reply) -> set[str]:
    assert reply.report is not None, "an output command's reply must carry its report"
    return {r.name for r in reply.report.recipients}
