"""What the engine is given (requirements section 11)."""

from dataclasses import dataclass
from datetime import datetime

from awt_bonus.ids import CharacterId, UserId


@dataclass(frozen=True)
class CharacterRef:
    """The character a present player is counted with."""

    id: CharacterId
    name: str
    level: int | None
    """None when no level is recorded (CH-4, CH-5)."""


@dataclass(frozen=True)
class PresentPlayer:
    """One member in the voice channel, as ``compute`` sees them (section 11).

    The caller has already checked sit-outs against the clock and applied the
    OUT-2a substitution, so the engine needs no clock, Discord or database.
    """

    user_id: UserId
    display_name: str
    """The Discord name, used for a player with no character set up (SE-5)."""
    is_bot: bool = False
    """Bots are ignored and never listed (SE-6)."""
    sitting_out_until: datetime | None = None
    """End of an **active** sit-out (UTC), or None. A player sitting out isn't counted (SE-2)."""
    character: CharacterRef | None = None
    """The current character (or the OUT-2a substitute); None means no character set up."""
