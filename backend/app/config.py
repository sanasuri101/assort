"""Application settings via pydantic-settings."""

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

    # External Services (used in later phases)
    daily_api_key: str = ""
    deepgram_api_key: str = ""
    openai_api_key: str = ""
    cartesia_api_key: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Logging
    log_level: str = "INFO"
    hipaa_audit_log: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
