"""Bot settings (AD-1) and secrets (NF-9).

Settings live in ``config/settings.yaml`` in the repository. Secrets and the
database location come only from environment variables.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from awt_bonus.catalog._files import read_yaml
from awt_bonus.startup import StartupError


class Settings(BaseModel):
    """What ``config/settings.yaml`` holds (AD-1)."""

    model_config = ConfigDict(extra="forbid")

    request_channel: str = Field(min_length=1, pattern=r"^[^#\s]")
    """The text channel ``/request`` posts to (CT-9), e.g. "bonus-bot-support"."""
    sitout_hours: float = Field(gt=0)
    """How long ``/sitout`` lasts (SE-2)."""
    max_level: int = Field(ge=1)
    """The highest level a character can record (CH-4)."""


class Environment(BaseSettings):
    """Values read from environment variables only (DB-1, NF-9)."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    database_url: str = "sqlite+aiosqlite:///var/awt-bonus.db"
    """``DATABASE_URL`` (DB-1). The default is the project's own ``var/`` folder (12.1)."""
    discord_token: SecretStr | None = None
    """``DISCORD_TOKEN``: the bot token (NF-9)."""
    discord_guild_id: int | None = None
    """``DISCORD_GUILD_ID``: the one server the bot serves (section 2)."""
    backup_bucket: str | None = None
    """``BACKUP_BUCKET``: the object storage bucket for nightly snapshots (DB-6)."""
    backup_endpoint_url: str | None = None
    """``BACKUP_ENDPOINT_URL``: the bucket's S3-compatible endpoint (DB-6)."""
    backup_key_id: SecretStr | None = None
    """``BACKUP_KEY_ID``: the storage key's ID (NF-9)."""
    backup_key: SecretStr | None = None
    """``BACKUP_KEY``: the storage key itself (NF-9)."""

    def secrets(self) -> list[str]:
        """Every secret value that's set, so the logs can leave them out (NF-8)."""
        values = [self.discord_token, self.backup_key_id, self.backup_key]
        return [v.get_secret_value() for v in values if v is not None and v.get_secret_value()]


def load_settings(path: Path = Path("config/settings.yaml")) -> Settings:
    """Load and validate the settings file with ``yaml.safe_load``.

    Raises StartupError, naming the file and each problem.
    """
    data, problems = read_yaml(path)
    if problems:
        raise StartupError("; ".join(problems))
    if not isinstance(data, dict):
        raise StartupError(f"{path.as_posix()}: must hold request_channel, sitout_hours, max_level")
    try:
        return Settings.model_validate(data)
    except ValidationError as error:
        details = "; ".join(
            f"{'.'.join(map(str, e['loc'])) or 'settings'}: {e['msg']}" for e in error.errors()
        )
        raise StartupError(f"{path.as_posix()}: {details}") from None
