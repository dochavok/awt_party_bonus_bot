"""Splitting output into Discord messages (OUT-3b).

Output is built as blocks of lines. Code blocks keep tables lined up; lines with
Discord timestamps or channel mentions stay outside them, because Discord doesn't
render those inside a code block. Messages break only between lines, preferably
between blocks, and a code block split across messages is closed and reopened.
Nothing is ever cut off.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

LIMIT = 2000
"""Discord's limit on a message's length."""

FENCE = "```"


@dataclass
class Block:
    """Lines shown together: plain text, or a code block (``code=True``)."""

    lines: list[str] = field(default_factory=list)
    code: bool = False

    def add(self, *lines: str) -> None:
        self.lines.extend(lines)


def text(*lines: str) -> Block:
    return Block(list(lines))


def code(*lines: str) -> Block:
    return Block(list(lines), code=True)


def to_messages(blocks: Iterable[Block], limit: int = LIMIT) -> tuple[str, ...]:
    """Pack blocks into messages of at most ``limit`` characters."""
    packer = _Packer(limit)
    for block in blocks:
        lines = [
            piece
            for line in block.lines
            for piece in _wrap(line.rstrip(), limit - 2 * (len(FENCE) + 1) if block.code else limit)
        ]
        if lines:
            packer.add_block(lines, block.code)
    return packer.finish()


class _Packer:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.messages: list[str] = []
        self.lines: list[str] = []
        self.size = 0
        self.in_code = False

    def _fits(self, lines: Sequence[str], code: bool) -> bool:
        """Whether ``lines`` fit in the current message, with its closing fence."""
        size, count, in_code = self.size, len(self.lines), self.in_code
        for line in lines:
            if code != in_code:
                size += len(FENCE) + (1 if count else 0)
                count, in_code = count + 1, code
            size += len(line) + (1 if count else 0)
            count += 1
        return size + (len(FENCE) + 1 if in_code else 0) <= self.limit

    def add_block(self, lines: Sequence[str], code: bool) -> None:
        # Start a new message rather than split a block that would fit in one.
        fits_alone = _Packer(self.limit)._fits(lines, code)
        if self.lines and fits_alone and not self._fits(lines, code):
            self._flush()
        for line in lines:
            self._add_line(line, code)

    def _add_line(self, line: str, code: bool) -> None:
        if not self.lines and not code and not line.strip():
            return  # no blank lines at the start of a message
        if self.lines and not self._fits([line], code):
            self._flush()
        if code != self.in_code:
            self._append(FENCE)
            self.in_code = code
        self._append(line)

    def _append(self, line: str) -> None:
        self.size += len(line) + (1 if self.lines else 0)
        self.lines.append(line)

    def _flush(self) -> None:
        if self.in_code:
            self._append(FENCE)
            self.in_code = False
        if self.lines:
            self.messages.append("\n".join(self.lines))
        self.lines, self.size = [], 0

    def finish(self) -> tuple[str, ...]:
        self._flush()
        return tuple(self.messages)


def _wrap(line: str, width: int) -> list[str]:
    """A line longer than ``width`` split at spaces (or anywhere, as a last resort)."""
    if not line:
        return [line]
    pieces = []
    while len(line) > width:
        cut = line.rfind(" ", 0, width + 1)
        if cut <= 0:
            cut = width
        pieces.append(line[:cut].rstrip())
        line = line[cut:].lstrip()
    pieces.append(line)
    return pieces
