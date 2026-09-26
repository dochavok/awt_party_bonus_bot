"""The calculation engine (requirements section 11): a pure function.

No Discord, database or clock code belongs in this package.
"""

from collections.abc import Mapping, Sequence

from awt_bonus.catalog import Catalog
from awt_bonus.engine.inputs import PresentPlayer
from awt_bonus.engine.report import PartyReport
from awt_bonus.ids import CharacterId, EntryId, GuildId, UserId


def compute(
    present_players: Sequence[PresentPlayer],
    player_roles: Mapping[UserId, frozenset[str]],
    character_entries: Mapping[CharacterId, Sequence[EntryId]],
    character_guilds: Mapping[CharacterId, Sequence[GuildId]],
    catalog: Catalog,
) -> PartyReport:
    """Work out every counted player's bonuses (section 11, steps 0-6)."""
    raise NotImplementedError
