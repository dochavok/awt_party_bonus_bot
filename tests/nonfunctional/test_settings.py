"""Settings and secrets (AD-1, NF-9).

The settings file, config/settings.yaml, is written in M5; until then the AD-1
tests run as expected failures.
"""

import pytest
import yaml

from awt_bonus.settings import Environment, load_settings
from tests.support.traceability import ROOT

SETTINGS_FILE = ROOT / "config" / "settings.yaml"


@pytest.mark.milestone("M5")
@pytest.mark.req("AD-1", "SE-2", "CH-4", "CT-9")
def test_the_settings_file_holds_the_bot_settings() -> None:
    settings = load_settings(SETTINGS_FILE)
    assert settings.request_channel == "bonus-bot-support"
    assert settings.sitout_hours == 12
    assert settings.max_level == 75


@pytest.mark.milestone("M5")
@pytest.mark.req("AD-1")
def test_settings_are_loaded_from_the_default_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    assert load_settings() == load_settings(SETTINGS_FILE)


@pytest.mark.milestone("M5")
@pytest.mark.req("NF-9", "AD-1")
def test_the_settings_file_holds_no_secrets() -> None:
    load_settings(SETTINGS_FILE)
    with SETTINGS_FILE.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    keys = " ".join(str(key).casefold() for key in data)
    for word in ["token", "secret", "password", "credential", "key"]:
        assert word not in keys, f"{word!r} belongs in an environment variable (NF-9)"


@pytest.mark.milestone("M1")
@pytest.mark.req("NF-9")
def test_the_bot_token_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_TOKEN", "not-a-real-token")
    environment = Environment()

    assert environment.discord_token is not None
    assert environment.discord_token.get_secret_value() == "not-a-real-token"
    assert "not-a-real-token" not in repr(environment)
    assert "not-a-real-token" not in str(environment)
