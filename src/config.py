"""Environment configuration loader with per-provider validation."""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel


PROVIDER_KEYS = {
    "anthropic": ["ANTHROPIC_API_KEY"],
    "soniox": ["SONIOX_API_KEY"],
    "google_tts": ["GOOGLE_APPLICATION_CREDENTIALS"],
    "twilio": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"],
}


class AppConfig(BaseModel):
    """Validated application configuration."""
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
