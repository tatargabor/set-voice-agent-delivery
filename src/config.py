"""Configuration loader — config.yaml for app settings, .env for secrets."""

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


# --- App settings from config.yaml ---

class ModelsConfig(BaseModel):
    fast: str = "claude-haiku-4-5"
    deep: str = "claude-sonnet-4-6"
    agent: str = "claude-sonnet-4-6"


class TTSConfig(BaseModel):
    voice_name: str = "hu-HU-Chirp3-HD-Achernar"
    language_code: str = "hu-HU"
    sample_rate: int = 8000


class VoiceConfig(BaseModel):
    max_sentences: int = 3
    max_tokens_tool_use: int = 150
    max_tokens_agent: int = 100
    max_tokens_stream: int = 300
    endpoint_delay_ms: int = 800
    interim_enabled: bool = True
    interim_min_words: int = 3
    interim_silence_ms: int = 500


class ResearchConfig(BaseModel):
    mode: Literal["tool_use", "local_agent", "auto"] = "tool_use"
    agent_timeout_sec: int = 10
    agent_max_iterations: int = 3
    tool_timeout_sec: int = 15


class AppSettings(BaseModel):
    """Application settings loaded from config.yaml."""
    language: Literal["hu", "en"] = "hu"
    company_name: str = "WebBuilder Kft."
    models: ModelsConfig = ModelsConfig()
    tts: TTSConfig = TTSConfig()
    voice: VoiceConfig = VoiceConfig()
    research: ResearchConfig = ResearchConfig()
    projects_dir: str = "."


_settings: AppSettings | None = None

# Language → TTS voice mapping
LANGUAGE_TTS_MAP = {
    "hu": {"voice_name": "hu-HU-Chirp3-HD-Achernar", "language_code": "hu-HU"},
    "en": {"voice_name": "en-US-Chirp3-HD-Achernar", "language_code": "en-US"},
}


def update_language(lang: str) -> AppSettings:
    """Switch language at runtime — mutates settings singleton and writes config.yaml.

    Args:
        lang: "hu" or "en"

    Returns:
        Updated AppSettings.

    Raises:
        ValueError: If lang is not a supported language.
    """
    if lang not in LANGUAGE_TTS_MAP:
        raise ValueError(f"Unsupported language: {lang}. Must be one of: {list(LANGUAGE_TTS_MAP.keys())}")

    settings = get_settings()
    tts_map = LANGUAGE_TTS_MAP[lang]

    # Mutate singleton
    settings.language = lang
    settings.tts.voice_name = tts_map["voice_name"]
    settings.tts.language_code = tts_map["language_code"]

    # Persist to config.yaml
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    data["language"] = lang
    if "tts" not in data:
        data["tts"] = {}
    data["tts"]["voice_name"] = tts_map["voice_name"]
    data["tts"]["language_code"] = tts_map["language_code"]

    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return settings


def load_app_settings(config_path: Path | None = None) -> AppSettings:
    """Load settings from config.yaml. Falls back to defaults if missing."""
    global _settings
    if _settings is not None:
        return _settings

    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"

    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        _settings = AppSettings(**data)
    else:
        _settings = AppSettings()

    return _settings


def get_settings() -> AppSettings:
    """Get cached settings (loads on first call)."""
    if _settings is None:
        return load_app_settings()
    return _settings


def reset_settings() -> None:
    """Reset cached settings (for testing)."""
    global _settings
    _settings = None


# --- Provider secrets from .env ---

PROVIDER_KEYS = {
    "anthropic": ["ANTHROPIC_API_KEY"],
    "soniox": ["SONIOX_API_KEY"],
    "google_tts": ["GOOGLE_APPLICATION_CREDENTIALS"],
    "twilio": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"],
}


class AppConfig(BaseModel):
    """Validated provider credentials from .env."""
    anthropic_api_key: str
    soniox_api_key: str | None = None
    google_application_credentials: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_phone_number: str | None = None


def load_env() -> None:
    """Load .env file from project root. Does not overwrite existing env vars."""
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path, override=False)


def validate_config(providers: list[str] | None = None, *, _load_dotenv: bool = True) -> AppConfig:
    """Validate required env vars for the given providers and return config.

    Args:
        providers: List of provider names to validate. If None, validates all.
                   Valid names: "anthropic", "soniox", "google_tts", "twilio"

    Returns:
        AppConfig with all loaded values.

    Raises:
        ValueError: If any required key is missing, lists all missing keys.
    """
    if _load_dotenv:
        load_env()

    if providers is None:
        providers = list(PROVIDER_KEYS.keys())

    # Always require anthropic
    if "anthropic" not in providers:
        providers = ["anthropic"] + providers

    missing = []
    for provider in providers:
        for key in PROVIDER_KEYS.get(provider, []):
            if not os.environ.get(key):
                missing.append(key)

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return AppConfig(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        soniox_api_key=os.environ.get("SONIOX_API_KEY"),
        google_application_credentials=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
        twilio_account_sid=os.environ.get("TWILIO_ACCOUNT_SID"),
        twilio_auth_token=os.environ.get("TWILIO_AUTH_TOKEN"),
        twilio_phone_number=os.environ.get("TWILIO_PHONE_NUMBER"),
    )
