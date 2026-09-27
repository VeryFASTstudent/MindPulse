"""
Centralized application settings.

All configuration is loaded from environment variables (via a .env file in
development). Nothing here should ever be hard-coded with real secrets --
.env is gitignored, and .env.example documents what's required.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # --- AI (wired up in Phase 4/6) ---
    openai_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Import this singleton everywhere instead of re-reading env vars.
settings = Settings()
