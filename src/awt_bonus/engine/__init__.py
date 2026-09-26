"""The calculation engine (requirements section 11)."""

from awt_bonus.engine.compute import compute
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

__all__ = [
    "Adjustment",
    "Applied",
    "Audience",
    "AudienceKind",
    "CharacterRef",
    "ConditionalBonus",
    "Give",
    "LevelRule",
    "NotApplied",
    "NotCounted",
    "PartyReport",
    "PresentPlayer",
    "Reason",
    "RecipientReport",
    "Source",
    "SourceKind",
    "compute",
]
