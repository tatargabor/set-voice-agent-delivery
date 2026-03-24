"""Tests for environment configuration loading and validation."""

import os
import pytest
from src.config import validate_config, AppConfig


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure a clean environment for each test."""
    for key in [
        "ANTHROPIC_API_KEY", "SONIOX_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS",
        "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_missing_anthropic_key_raises(monkeypatch):
    """Missing ANTHROPIC_API_KEY should raise with clear message."""
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        validate_config(providers=["anthropic"], _load_dotenv=False)


def test_missing_multiple_keys_lists_all(monkeypatch):
    """Error should list ALL missing keys, not just the first."""
    with pytest.raises(ValueError) as exc_info:
        validate_config(providers=["anthropic", "twilio"], _load_dotenv=False)
    msg = str(exc_info.value)
    assert "ANTHROPIC_API_KEY" in msg
    assert "TWILIO_ACCOUNT_SID" in msg
    assert "TWILIO_AUTH_TOKEN" in msg
    assert "TWILIO_PHONE_NUMBER" in msg


def test_valid_config_returns_appconfig(monkeypatch):
    """All keys present should return AppConfig."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("SONIOX_API_KEY", "test-soniox")
    config = validate_config(providers=["anthropic", "soniox"], _load_dotenv=False)
    assert isinstance(config, AppConfig)
    assert config.anthropic_api_key == "test-key"
    assert config.soniox_api_key == "test-soniox"


def test_provider_specific_validation(monkeypatch):
    """Only requested provider keys should be validated."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # Should NOT fail even though TWILIO keys are missing
    config = validate_config(providers=["anthropic"], _load_dotenv=False)
    assert config.anthropic_api_key == "test-key"
    assert config.twilio_account_sid is None
