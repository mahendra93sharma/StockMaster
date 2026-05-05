"""Application settings loaded from environment."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    env: str = "qa"  # qa | uat | production

    # Database
    database_url: str = "postgresql+asyncpg://stockmaster:stockmaster@localhost:5432/stockmaster"
    db_echo: bool = False

    # Auth
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Firebase
    firebase_project_id: str = ""

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    llm_daily_spend_cap_usd: float = 5.0

    # Admin
    admin_docs: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
