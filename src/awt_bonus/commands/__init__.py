"""The command layer (requirements TF-2): a user, a command and its options in;
the reply text and whether it's private out.

Command names are as in section 7, e.g. "partybonus", "character register",
"guild join". Option names: ``character``, ``entry``, ``guild``, ``name``,
``level`` (a number, or "clear" for ``/character level``), ``new``, ``channel``
(a voice channel ID), ``private``, ``export`` and ``text``.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from awt_bonus.catalog import Catalog
from awt_bonus.engine import PartyReport
from awt_bonus.ids import UserId
from awt_bonus.ports import Clock, DiscordGateway
from awt_bonus.settings import Settings
from awt_bonus.store import Store

type OptionValue = str | int | bool | None


@dataclass(frozen=True)
class Reply:
    messages: tuple[str, ...]
    """The reply, split into messages of at most 2,000 characters (OUT-3b)."""
    private: bool
    """True if only the person who ran the command sees it (OUT-5)."""
    report: PartyReport | None = None
    """The calculation the reply was made from, for output commands; None otherwise."""

    @property
    def text(self) -> str:
        """All the messages, joined by newlines."""
        return "\n".join(self.messages)


@dataclass(frozen=True)
class Choice:
    """One autocomplete suggestion."""

    label: str
    """What the player sees, e.g. "Holy Aura (Holy Knight skill)" (HV-1)."""
    value: str
    """What's filled in."""


class App:
    """Runs commands against the database, Discord and the catalog."""

    def __init__(
        self,
        *,
        store: Store,
        discord: DiscordGateway,
        clock: Clock,
        catalog: Catalog,
        settings: Settings,
    ) -> None:
        raise NotImplementedError

    async def run(
        self,
        user_id: UserId,
        command: str,
        options: Mapping[str, OptionValue] | None = None,
    ) -> Reply:
        """Run a command as ``user_id``."""
        raise NotImplementedError

    async def autocomplete(
        self,
        user_id: UserId,
        command: str,
        option: str,
        typed: str,
        options: Mapping[str, OptionValue] | None = None,
    ) -> list[Choice]:
        """Suggestions for ``option``, given what's ``typed`` and the other options filled in."""
        raise NotImplementedError
