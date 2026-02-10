"""Application settings via pydantic-settings."""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Aggressive Sentry Hub monkeypatch for Sentry 2.x compatibility during pytest discovery
if "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST"):
    try:
        import sentry_sdk
        if not hasattr(sentry_sdk, "Hub"):
            sentry_sdk.Hub = MagicMock()
        sys.modules['sentry_sdk.hub'] = MagicMock()
        sys.modules['sentry_sdk.Hub'] = MagicMock()
    except ImportError:
        pass

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Assort Health application configuration.

    All settings can be overridden via environment variables or .env file.
    """

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_key: str = "dev-key-change-me"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # External Services
    gemini_api_key: str = ""
    embedding_model: str = "models/gemini-embedding-001"
    voice_model: str = "gemini-2.0-flash"
    
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    deepgram_api_key: str = ""
    cartesia_api_key: str = ""
    daily_api_key: str = ""
    
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    
    # Phase 5: Learning Engine
    wandb_api_key: str = ""
    redis_stream_analysis: str = "call:analysis"

    # Logging
    log_level: str = "INFO"
    hipaa_audit_log: bool = True

    # Practice Info
    practice_name: str = "Valley Family Medicine"
    practice_location: str = "123 Valley Blvd, Suite 200"

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8"
    }


settings = Settings()
