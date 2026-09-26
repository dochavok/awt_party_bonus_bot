"""Snapshot tests (requirements TS-5): the sample game's output, compared on every run.

Each view of the section 9 sample game is saved as a reference file in
tests/snapshots/sample-game/: a header line naming the command, who ran it and
whether the reply is private, then each Discord message after a
``--- message N of M ---`` line, so a change in how output splits shows too.

The layout was approved in M4. A mismatch means the output code is wrong, unless a
human confirms the layout should change; snapshots follow the test-change rule
(TF-5), like every other file under tests/.

To (re)write the files after an approved layout change:
    UPDATE_SNAPSHOTS=1 uv run pytest tests/commands/test_snapshots.py
Writing a file fails the test, so a run that rewrites snapshots never passes;
review the diff, then run again.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from awt_bonus.commands import Reply
from tests.support.world import MakeWorld

SNAPSHOTS = Path(__file__).resolve().parents[1] / "snapshots" / "sample-game"


@dataclass(frozen=True)
class View:
    file: str
    handle: str
    command: str
    character: str | None = None
    playing: str | None = None
    """Set the player's current character first (for the OUT-2a notice)."""
    about: str = ""


VIEWS = [
    View("partybonus", "isla", "partybonus"),
    View("breakdown", "isla", "breakdown", about="the same for members and non-members"),
    View("breakdown-Crateris", "cora", "breakdown", "Crateris"),
    View("mybonus-Mira-member", "maya", "mybonus", "Mira", about="the owner, a member"),
    View("mybonus-Mira-non-member", "isla", "mybonus", "Mira", about="not a member"),
    View(
        "mybonus-Crateris-not-current",
        "cora",
        "mybonus",
        "Crateris",
        playing="Elowen",
        about="while playing Elowen",
    ),
    View("breakdown-Chris-member", "cole", "breakdown", "Chris", about="the owner, a member"),
    View("breakdown-Chris-non-member", "isla", "breakdown", "Chris", about="not a member"),
]


def render(view: View, reply: Reply) -> str:
    command = f"/{view.command}" + (f" {view.character}" if view.character else "")
    about = f" ({view.about})" if view.about else ""
    lines = [
        f"# {command}, run by {view.handle}{about}: "
        f"{'private' if reply.private else 'public'}, {len(reply.messages)} message(s)"
    ]
    for number, message in enumerate(reply.messages, start=1):
        lines += [f"--- message {number} of {len(reply.messages)} ---", message]
    return "\n".join(lines) + "\n"


@pytest.mark.milestone("M4")
@pytest.mark.req("TS-5", "9.1", "SG-4", "SG-5")
@pytest.mark.dm("Q1", "Q2", "Q3", "Q6")
@pytest.mark.parametrize("view", VIEWS, ids=[v.file for v in VIEWS])
async def test_sample_game_output_matches_its_snapshot(make_world: MakeWorld, view: View) -> None:
    world = await make_world("sample-game")
    if view.playing is not None:
        await world.set_current(view.handle, view.playing)
    options = {"character": view.character} if view.character else {}
    actual = render(view, await world.run(view.handle, view.command, **options))

    path = SNAPSHOTS / f"{view.file}.txt"
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8", newline="\n")
        pytest.fail(f"wrote {path.name}: review the diff, then run again without UPDATE_SNAPSHOTS")
    assert path.exists(), f"no snapshot {path.name} (see this module's docstring)"
    assert actual == path.read_text(encoding="utf-8"), f"/{view.command} differs from {path.name}"
