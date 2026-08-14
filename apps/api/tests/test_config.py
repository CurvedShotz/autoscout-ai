import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_loads_auto_dev_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTO_DEV_API_KEY", "test-auto-dev-key")

    settings = Settings(_env_file=None)

    assert settings.auto_dev_api_key.get_secret_value() == "test-auto-dev-key"


def test_settings_require_auto_dev_api_key(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTO_DEV_API_KEY", raising=False)

    empty_env = tmp_path / ".env"
    empty_env.write_text("", encoding="utf-8")

    with pytest.raises(ValidationError, match="AUTO_DEV_API_KEY"):
        Settings(_env_file=empty_env)
