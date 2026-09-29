"""Regenerate the generated parts of the documentation (requirements DOC-4, DOC-5).

    uv run python scripts/generate_docs.py            # rewrite what's out of date
    uv run python scripts/generate_docs.py --check    # CI: report it, write nothing

Two kinds of generated content:

- **Examples** (DOC-4): ``docs/_generated/<name>.md``, one per example in the sample
  party (``docs/_sample/party.yaml``). The sample party is set up by running the
  bot's own commands on a fresh database with the real catalog, then each example
  command is run and its reply rendered as Discord shows it. Pages include them
  with ``--8<-- "<name>.md"``.
- **The command reference** (DOC-5): in ``docs/commands.md``, each command's block
  between ``<!-- BEGIN GENERATED: /name -->`` and ``<!-- END GENERATED: /name -->``,
  built from the bot's command definitions. The text around the blocks is written
  by hand. A new command gets a block at the end of the page; a removed one loses
  its block.

``--check`` exits 1 and names each file that's out of date.
"""

import argparse
import asyncio
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import discord
import yaml
from discord import app_commands
from pydantic import BaseModel, ConfigDict, Field

from awt_bonus.bot import build_tree, intents
from awt_bonus.catalog import load_catalog
from awt_bonus.commands import App, OptionValue, Reply
from awt_bonus.ids import ChannelId, UserId
from awt_bonus.ports import Member, VoiceChannel
from awt_bonus.settings import Settings, load_settings
from awt_bonus.store import Store

ROOT = Path(__file__).resolve().parents[1]
VOICE = ChannelId(1)
GUILD = discord.Object(id=1)

# ---------------------------------------------------------------- the sample party


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SampleCharacter(_Model):
    name: str
    level: int | None = None
    guilds: list[str] = Field(default_factory=list)
    has: list[str] = Field(default_factory=list)


class SamplePlayer(_Model):
    name: str
    roles: list[str] = Field(default_factory=list)
    voice: bool = False
    sitout: bool = False
    current: str | None = None
    characters: list[SampleCharacter] = Field(default_factory=list)


class Step(_Model):
    command: str
    options: dict[str, OptionValue] = Field(default_factory=dict)


class Example(Step):
    file: str
    player: str
    before: list[Step] = Field(default_factory=list)


class SampleParty(_Model):
    time: datetime
    voice_channel: str
    players: list[SamplePlayer]
    examples: list[Example]


def load_sample(path: Path) -> SampleParty:
    with path.open(encoding="utf-8") as f:
        return SampleParty.model_validate(yaml.safe_load(f))


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now.astimezone(UTC)

    def now(self) -> datetime:
        return self._now


class SampleServer:
    """The sample server, as the bot's Discord gateway sees it (ports.DiscordGateway)."""

    def __init__(self, sample: SampleParty) -> None:
        self.channel = VoiceChannel(id=VOICE, name=sample.voice_channel)
        self.members: dict[UserId, Member] = {}
        self.in_voice: list[UserId] = []
        for number, player in enumerate(sample.players, start=1):
            user = UserId(1000 + number)
            self.members[user] = Member(user, player.name, frozenset(player.roles))
            if player.voice:
                self.in_voice.append(user)

    def user(self, name: str) -> UserId:
        for user, member in self.members.items():
            if member.display_name == name:
                return user
        raise KeyError(f"no sample player {name!r}")

    async def voice_channel_of(self, user_id: UserId) -> VoiceChannel | None:
        return self.channel if user_id in self.in_voice else None

    async def voice_channel(self, channel_id: ChannelId) -> VoiceChannel | None:
        return self.channel if channel_id == VOICE else None

    async def voice_members(self, channel_id: ChannelId) -> list[Member]:
        return [self.members[u] for u in self.in_voice] if channel_id == VOICE else []

    async def member(self, user_id: UserId) -> Member | None:
        return self.members.get(user_id)

    async def post(self, channel_name: str, text: str) -> None:
        pass


@dataclass
class Bot:
    app: App
    server: SampleServer
    store: Store
    settings: Settings


async def _setup(sample: SampleParty, bot: Bot) -> None:
    """Set the sample party up with the bot's own commands, checking each one worked."""

    async def run(player: str, command: str, **options: OptionValue) -> None:
        await bot.app.run(bot.server.user(player), command, options)

    for player in sample.players:
        for character in player.characters:
            options: dict[str, OptionValue] = {"name": character.name}
            if character.level is not None:
                options["level"] = character.level
            await run(player.name, "character register", **options)
            for guild in character.guilds:
                await run(player.name, "guild join", character=character.name, guild=guild)
            for entry in character.has:
                await run(player.name, "add", character=character.name, entry=entry)
            record = await bot.store.character_by_name(character.name)
            if record is None or (len(record.entries), len(record.guilds)) != (
                len(character.has),
                len(character.guilds),
            ):
                raise SystemExit(
                    f"docs/_sample/party.yaml: {character.name} wasn't set up as written "
                    "(a name that isn't in the catalog, or an entry the bot refused?)"
                )
        if player.current is not None:
            await run(player.name, "play", character=player.current)
        if player.sitout:
            await run(player.name, "sitout")


async def _open_bot(sample: SampleParty, folder: Path) -> Bot:
    store = await Store.open(f"sqlite+aiosqlite:///{(folder / 'sample.db').as_posix()}")
    server = SampleServer(sample)
    settings = load_settings(ROOT / "config" / "settings.yaml")
    app = App(
        store=store,
        discord=server,
        clock=FixedClock(sample.time),
        catalog=load_catalog(ROOT / "catalog"),
        settings=settings,
    )
    return Bot(app=app, server=server, store=store, settings=settings)


# ---------------------------------------------------------------- rendering replies

_TIMESTAMP = re.compile(r"<t:(\d+):([tTdDfFR])>")
_CHANNEL = re.compile(r"<#(\d+)>")
_USER = re.compile(r"<@(\d+)>")


def _twelve_hour(moment: datetime) -> str:
    hour = moment.hour % 12 or 12
    return f"{hour}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'}"


def _shown_time(match: re.Match[str], now: datetime) -> str:
    """A Discord timestamp as Discord shows it (to a reader in GMT)."""
    moment = datetime.fromtimestamp(int(match.group(1)), UTC)
    date = f"{moment:%B} {moment.day}, {moment.year}"
    match match.group(2):
        case "t":
            return _twelve_hour(moment)
        case "T":
            return f"{_twelve_hour(moment)[:-3]}:{moment.second:02d} {_twelve_hour(moment)[-2:]}"
        case "d":
            return f"{moment.month}/{moment.day}/{moment.year}"
        case "D":
            return date
        case "F":
            return f"{moment:%A}, {date} {_twelve_hour(moment)}"
        case "R":
            hours = round((moment - now).total_seconds() / 3600)
            return f"in {hours} hours" if hours >= 0 else f"{-hours} hours ago"
        case _:
            return f"{date} {_twelve_hour(moment)}"


def _markdown(message: str) -> str:
    """Discord's line breaks as Markdown: hard breaks outside code blocks, and blank
    lines around code blocks so they're never read as part of a paragraph."""
    lines: list[str] = []
    in_code = False
    for line in message.split("\n"):
        if line.startswith("```"):
            if not in_code and lines and lines[-1]:
                lines.append("")
            lines.append(line)
            in_code = not in_code
            if not in_code:
                lines.append("")
        elif in_code or not line:
            lines.append(line)
        else:
            lines.append(line + "  ")
    return "\n".join(lines).strip("\n")


def render(reply: Reply, sample: SampleParty, server: SampleServer) -> str:
    """A reply as a Markdown fragment for the site: one box per Discord message."""
    now = sample.time.astimezone(UTC)
    names = {str(user): member.display_name for user, member in server.members.items()}
    parts = ["<!-- Generated by scripts/generate_docs.py from docs/_sample/party.yaml. -->"]
    for message in reply.messages:
        shown = _TIMESTAMP.sub(lambda m: _shown_time(m, now), message)
        shown = _CHANNEL.sub(lambda m: f"#{sample.voice_channel}", shown)
        shown = _USER.sub(lambda m: f"@{names.get(m.group(1), 'someone')}", shown)
        seen_by = "Only you can see this" if reply.private else "Everyone in the channel sees this"
        parts.append(
            f'<div class="discord-reply" markdown>\n<div class="seen-by">{seen_by}</div>\n\n'
            f"{_markdown(shown)}\n\n</div>"
        )
    return "\n\n".join(parts) + "\n"


async def examples(sample: SampleParty) -> dict[str, str]:
    """Every example, rendered: {file name: Markdown}."""
    with tempfile.TemporaryDirectory() as folder:
        bot = await _open_bot(sample, Path(folder))
        try:
            await _setup(sample, bot)
            rendered: dict[str, str] = {}
            for example in sample.examples:
                user = bot.server.user(example.player)
                for step in example.before:
                    await bot.app.run(user, step.command, step.options)
                reply = await bot.app.run(user, example.command, example.options)
                rendered[f"{example.file}.md"] = render(reply, sample, bot.server)
            return rendered
        finally:
            await bot.store.close()


# ---------------------------------------------------------------- the command reference

_BLOCK = re.compile(
    r"<!-- BEGIN GENERATED: (?P<name>/[^>]+?) -->\n.*?<!-- END GENERATED: (?P=name) -->\n",
    re.DOTALL,
)


def _leaf_commands(
    tree: app_commands.CommandTree[Any],
) -> list[app_commands.Command[Any, ..., Any]]:
    found: list[app_commands.Command[Any, ..., Any]] = []
    for command in tree.get_commands(guild=GUILD):
        if isinstance(command, app_commands.Group):
            found.extend(c for c in command.walk_commands() if isinstance(c, app_commands.Command))
        elif isinstance(command, app_commands.Command):
            found.append(command)
    return found


def command_block(command: app_commands.Command[Any, ..., Any]) -> str:
    name = f"/{command.qualified_name}"
    lines = [f"<!-- BEGIN GENERATED: {name} -->", f"### `{name}`", "", command.description, ""]
    if command.parameters:
        lines += ["| Option | Required | What it's for |", "|---|---|---|"]
        for parameter in command.parameters:
            description = "" if parameter.description == "…" else parameter.description
            required = "yes" if parameter.required else "no"
            lines.append(f"| `{parameter.name}` | {required} | {description} |")
    else:
        lines.append("No options.")
    lines += ["", f"<!-- END GENERATED: {name} -->"]
    return "\n".join(lines) + "\n"


async def command_blocks(sample: SampleParty) -> dict[str, str]:
    """Every command's generated block, in the bot's order: {"/name": Markdown}."""
    with tempfile.TemporaryDirectory() as folder:
        bot = await _open_bot(sample, Path(folder))
        try:
            client = discord.Client(intents=intents())
            tree = build_tree(client, bot.app, GUILD, bot.settings)
            return {f"/{c.qualified_name}": command_block(c) for c in _leaf_commands(tree)}
        finally:
            await bot.store.close()


def updated_reference(text: str, blocks: Mapping[str, str]) -> str:
    """The command reference with every block replaced, stale ones dropped, new ones added."""
    present = {m.group("name") for m in _BLOCK.finditer(text)}
    text = _BLOCK.sub(lambda m: blocks.get(m.group("name"), ""), text)
    missing = [block for name, block in blocks.items() if name not in present]
    if missing:
        text = text.rstrip("\n") + "\n\n" + "\n".join(missing)
    return text


# ---------------------------------------------------------------- main


async def expected_files(docs: Path) -> dict[Path, str]:
    """Every generated file's full expected text."""
    sample = load_sample(docs / "_sample" / "party.yaml")
    files = {docs / "_generated" / name: text for name, text in (await examples(sample)).items()}
    reference = docs / "commands.md"
    current = reference.read_text(encoding="utf-8") if reference.exists() else "# Commands\n"
    files[reference] = updated_reference(current, await command_blocks(sample))
    return files


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report what's out of date")
    parser.add_argument("--docs", type=Path, default=ROOT / "docs", help="the docs folder")
    args = parser.parse_args(argv)
    docs: Path = args.docs.resolve()

    expected = asyncio.run(expected_files(docs))
    generated = docs / "_generated"
    stale = [p for p in sorted(generated.glob("*.md")) if p not in expected]
    changed = [
        path
        for path, text in expected.items()
        if not path.exists() or path.read_text(encoding="utf-8") != text
    ]

    def shown(path: Path) -> str:
        return path.relative_to(docs.parent).as_posix()

    if args.check:
        for path in changed:
            print(f"out of date: {shown(path)}")
        for path in stale:
            print(f"no longer generated: {shown(path)}")
        if changed or stale:
            print("Run: uv run python scripts/generate_docs.py")
            return 1
        print("Generated docs: up to date")
        return 0

    generated.mkdir(exist_ok=True)
    for path in changed:
        path.write_text(expected[path], encoding="utf-8", newline="\n")
        print(f"wrote {shown(path)}")
    for path in stale:
        path.unlink()
        print(f"removed {shown(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
