"""Structured logs (NF-8): JSON lines on standard output.

Every line is one JSON object with ``time`` (UTC, ISO 8601), ``level`` and ``event``.
Commands log ``command``, ``user_id``, ``outcome`` (ok, refused or error) and
``duration_ms``. Errors add the traceback as ``error``. Logs never contain the bot
token, storage credentials, reply text or message content.
"""

import logging
import sys
from typing import TextIO


def configure_logging(stream: TextIO = sys.stdout, level: int = logging.INFO) -> None:
    """Send the bot's logs to ``stream`` as JSON lines, replacing any earlier setup."""
    raise NotImplementedError
