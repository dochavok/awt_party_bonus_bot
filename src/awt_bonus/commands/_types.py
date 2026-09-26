"""The command layer's values: options in, replies and suggestions out (TF-2)."""

from dataclasses import dataclass

from awt_bonus.engine import PartyReport

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
