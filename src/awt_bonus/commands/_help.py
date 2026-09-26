"""/help (OUT-9): a short guide for players getting started, ending with their next step."""

from awt_bonus.commands._base import Context, private
from awt_bonus.commands._types import Reply
from awt_bonus.output.messages import text


async def help_(ctx: Context) -> Reply:
    """OUT-9: always private (OUT-5), and one message."""
    hours = f"{ctx.settings.sitout_hours:g}"
    return private(
        text(
            "**AWT Party Bonus Bot**",
            "Adds up the party bonuses each character gets from everyone in your voice "
            "channel. You record what your character has; the bot does the math.",
        ),
        text(
            "",
            "__Set up__ (once per character)",
            "- `/character register name:<name>`: the level is optional; only "
            "level-based bonuses (the Cult of the Dragon) use it",
            "- `/guild join <character> <guild>`: if your character is in a guild",
            "- `/add <character> <entry>`: each skill, rank, boon, item or title",
            "- `/catalog`: what's available and what it gives",
            "- `/request <text>`: something your character has isn't listed? "
            "Ask for it to be added",
            "A Guild rank role on Discord gives **Support** automatically: nothing to add.",
        ),
        text(
            "",
            "__Game night__",
            "- Join the voice channel: you're counted automatically, nothing to start.",
            f"- `/sitout`: running the game or just watching? (lasts {hours} hours; "
            "`/sitin` to undo)",
            "- `/partybonus`: everyone's totals, posted for the party",
            "- `/mybonus`: your totals, just for you",
            "- `/breakdown`: how the totals are worked out",
            "More than one character? `/play <character>` before the game.",
        ),
        text("", await _next_step(ctx)),
    )


async def _next_step(ctx: Context) -> str:
    """What this player should do next, from their data (OUT-9)."""
    characters = await ctx.store.characters_of(ctx.user)
    if not characters:
        return "**Your next step:** register a character with `/character register name:<name>`."
    current = await ctx.store.current_character(ctx.user)
    if current is None:
        names = ", ".join(c.name for c in characters)
        return (
            f"**Your next step:** choose the character you're playing with "
            f"`/play <character>` (yours: {names})."
        )
    if not current.entries and not current.guilds:
        return (
            f"**Your next step:** add what {current.name} has with "
            f"`/add {current.name} <entry>`. `/catalog` shows what's available."
        )
    return (
        f"**You're set up** with {current.name}. On game night, join the voice channel "
        "and run `/partybonus`."
    )
