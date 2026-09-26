"""The command layer (requirements TF-2): a user, a command and its options in;
the reply text and whether it's private out.

Command names are as in section 7, e.g. "partybonus", "character register",
"guild join". Option names: ``character``, ``entry``, ``guild``, ``name``,
``level`` (a number, or "clear" for ``/character level``), ``new``, ``channel``
(a voice channel ID), ``private``, ``export`` and ``text``.

Command logic runs against the ports (the clock and Discord), never discord.py
directly (TS-8). Every reply is private except ``/partybonus`` (OUT-5).
"""

from collections.abc import Mapping

from awt_bonus.catalog import Catalog
from awt_bonus.commands import _catalog, _characters, _entries, _output, _presence
from awt_bonus.commands._autocomplete import suggest
from awt_bonus.commands._base import Context, Handler, Refused, Services, private
from awt_bonus.commands._types import Choice, OptionValue, Reply
from awt_bonus.ids import UserId
from awt_bonus.ports import Clock, DiscordGateway
from awt_bonus.settings import Settings
from awt_bonus.store import Store

__all__ = ["App", "Choice", "OptionValue", "Reply"]


async def _later(ctx: Context) -> Reply:
    """Commands that arrive in a later milestone (section 17)."""
    raise NotImplementedError


HANDLERS: Mapping[str, Handler] = {
    "character register": _characters.register,
    "character list": _characters.list_characters,
    "character rename": _characters.rename,
    "character level": _characters.level,
    "play": _characters.play,
    "add": _entries.add,
    "remove": _entries.remove,
    "sitout": _presence.sitout,
    "sitin": _presence.sitin,
    "catalog": _catalog.catalog,
    "partybonus": _output.partybonus,
    "mybonus": _output.mybonus,
    "breakdown": _output.breakdown,
    "guild join": _later,
    "guild leave": _later,
    "request": _later,
}


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
        self._services = Services(
            store=store, discord=discord, clock=clock, catalog=catalog, settings=settings
        )

    async def run(
        self,
        user_id: UserId,
        command: str,
        options: Mapping[str, OptionValue] | None = None,
    ) -> Reply:
        """Run a command as ``user_id``."""
        handler = HANDLERS.get(command)
        if handler is None:
            return private(f"There's no /{command} command.")
        ctx = Context(
            services=self._services,
            user=user_id,
            options=dict(options or {}),
            now=self._services.clock.now(),
        )
        try:
            return await handler(ctx)
        except Refused as refused:
            return private(*refused.lines)

    async def autocomplete(
        self,
        user_id: UserId,
        command: str,
        option: str,
        typed: str,
        options: Mapping[str, OptionValue] | None = None,
    ) -> list[Choice]:
        """Suggestions for ``option``, given what's ``typed`` and the other options filled in."""
        services = self._services
        return await suggest(
            services.store, services.catalog, user_id, command, option, typed, options or {}
        )
