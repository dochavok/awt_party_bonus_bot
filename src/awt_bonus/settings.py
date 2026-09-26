"""Bot settings (AD-1) and secrets (NF-9).

Settings live in ``config/settings.yaml`` in the repository. Secrets and the
database location come only from environment variables.
"""

from pathlib import Path

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseModel):
    """What ``config/settings.yaml`` holds (AD-1)."""

    request_channel: str
    """The text channel ``/request`` posts to (CT-9), e.g. "bonus-bot-support"."""
    sitout_hours: float
    """How long ``/sitout`` lasts (SE-2)."""
    max_level: int
    """The highest level a character can record (CH-4)."""


class Environment(BaseSettings):
    """Values read from environment variables only (DB-1, NF-9)."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    database_url: str = "sqlite+aiosqlite:///var/awt-bonus.db"
    """``DATABASE_URL`` (DB-1). The default is the project's own ``var/`` folder (12.1)."""
    discord_token: SecretStr | None = None
    """``DISCORD_TOKEN``: the bot token (NF-9)."""


def load_settings(path: Path = Path("config/settings.yaml")) -> Settings:
    """Load and validate the settings file with ``yaml.safe_load``."""
    raise NotImplementedError
