"""Tests for SecretSettings environment variable configuration."""

from __future__ import annotations

import pytest

from autopilot.core.secret_settings import SecretSettings


class TestSecretSettings:
    """Tests for pydantic-settings based secret configuration."""

    def test_defaults_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SecretSettings fields default to empty strings when env vars are unset."""
        monkeypatch.delenv("RENDER_API_KEY", raising=False)
        settings = SecretSettings()
        assert settings.render_api_key == ""

    def test_reads_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SecretSettings reads values from environment variables."""
        monkeypatch.setenv("RENDER_API_KEY", "test-key-123")
        settings = SecretSettings()
        assert settings.render_api_key == "test-key-123"

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables override default values."""
        monkeypatch.setenv("RENDER_API_KEY", "override-key")
        settings = SecretSettings()
        assert settings.render_api_key == "override-key"

    def test_model_is_frozen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SecretSettings instances are immutable."""
        monkeypatch.delenv("RENDER_API_KEY", raising=False)
        settings = SecretSettings()
        with pytest.raises(Exception):  # noqa: B017
            settings.render_api_key = "new-value"  # type: ignore[misc]
