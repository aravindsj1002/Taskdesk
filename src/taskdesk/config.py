from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./taskdesk.db"
    log_level: str = "INFO"
    log_json: bool = False

    # AI step suggestions (Google Gemini). Without a key the endpoint answers 503.
    gemini_api_key: str | None = None
    ai_model: str = "gemini-3.8-flash-lite"


@lru_cache
def get_settings() -> Settings:
    return Settings()
