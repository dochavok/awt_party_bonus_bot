"""Structured logs (NF-8): JSON lines on standard output.

Every line is one JSON object with ``time`` (UTC, ISO 8601), ``level`` and ``event``.
Commands log ``command``, ``user_id``, ``outcome`` (ok, refused or error) and
``duration_ms``. Errors add the traceback as ``error``. Logs never contain the bot
token, storage credentials, reply text or message content.

Log with a short, fixed event name and put the details in ``extra``, e.g.
``log.info("snapshot taken", extra={"path": str(path)})``.
"""

import json
import logging
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, TextIO

from pydantic import ValidationError

from awt_bonus.settings import Environment

REDACTED = "[redacted]"

_STANDARD = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}
"""The attributes every log record has; anything else came from ``extra``."""

_QUIET = {
    "sqlalchemy": logging.WARNING,
    "aiosqlite": logging.WARNING,
    "alembic": logging.WARNING,  # startup logs "migrating" and "migrated" itself
    "botocore": logging.WARNING,
    "boto3": logging.WARNING,
}
"""Libraries that are too chatty at INFO."""


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with any secret values replaced (NF-8, NF-9)."""

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        super().__init__()
        self._secrets = sorted({s for s in secrets if s}, key=len, reverse=True)

    def format(self, record: logging.LogRecord) -> str:
        line: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
            "logger": record.name,
        }
        for key, value in vars(record).items():
            if key not in _STANDARD and not key.startswith("_"):
                line[key] = value
        if record.exc_info:
            line["error"] = self.formatException(record.exc_info)
        elif record.stack_info:
            line["error"] = self.formatStack(record.stack_info)
        return self._redact(json.dumps(line, default=str, ensure_ascii=False))

    def _redact(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, REDACTED)
        return text


def configure_logging(stream: TextIO = sys.stdout, level: int = logging.INFO) -> None:
    """Send the bot's logs to ``stream`` as JSON lines, replacing any earlier setup."""
    try:
        secrets = Environment().secrets()
    except ValidationError:
        secrets = []  # startup reports the bad variable once logging works
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter(secrets))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for name, quiet in _QUIET.items():
        logging.getLogger(name).setLevel(quiet)
