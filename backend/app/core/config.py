"""
Centralized application settings.

All configuration is loaded from environment variables (via a .env file in
development). Nothing here should ever be hard-coded with real secrets --
.env is gitignored, and .env.example documents what's required.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "MindPulse API"
    environment: str = "development"
    debug: bool = True

    # --- MongoDB ---
    mongo_uri: str
    mongo_db_name: str = "mindpulse"

    # --- Auth (wired up in Phase 2) ---
    jwt_secret: str = "placeholder_change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- AI ---
    chat_provider: Literal["openai", "gemini"] = "openai"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.5-flash"
    chat_rate_limit_per_minute: int = 20
    chat_rate_limit_per_day: int = 300

    # --- Sentiment analysis (Phase 6) ---
    # Set SENTIMENT_ENABLED=false to skip the local model entirely
    # (useful on a low-RAM machine or while developing other features).
    sentiment_enabled: bool = True
    sentiment_model_name: str = "j-hartmann/emotion-english-distilroberta-base"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Import this singleton everywhere instead of re-reading env vars.
settings = Settings()
