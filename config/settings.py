"""Application Settings using Pydantic Settings."""
import os
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_ENV: str = Field(default="development")
    APP_DEBUG: bool = Field(default=True)
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    API_BASE_URL: str = Field(default="http://localhost:8000")
    DASHBOARD_BASE_URL: str = Field(default="http://localhost:8501")
    CORS_ORIGINS: str = Field(default="http://localhost:8501,http://127.0.0.1:8501")
    SEED_DEMO_DATA: bool = Field(default=False)

    # Dashboard & Tool Auth
    AUTH_USERNAME: str = Field(default="admin")
    AUTH_PASSWORD: str = Field(default="openclaw123")

    # Supabase
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(default=None)

    # AI - Xiaomi MiMo
    MIMO_API_KEY: Optional[str] = Field(default=None)
    MIMO_BASE_URL: str = Field(default="https://token-plan-sgp.xiaomimimo.com/v1")
    MIMO_MODEL: str = Field(default="mimo-v2.5-pro")

    # AI - Legacy / General OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_BASE_URL: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="mimo-v2.5-pro")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")

    # AI - DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None)
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat")

    # Gmail OAuth2
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None)
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None)
    GOOGLE_REDIRECT_URI: str = Field(default="http://localhost:8000/api/v1/auth/google/callback")

    # Scraping APIs
    NEWS_API_ORG_KEY: Optional[str] = Field(default=None)
    THE_NEWS_API_KEY: Optional[str] = Field(default=None)

    # Tracking
    TRACKING_BASE_URL: str = Field(default="http://localhost:8000/api/v1/outreach/track")

    @property
    def is_supabase_configured(self) -> bool:
        return bool(
            self.SUPABASE_URL
            and self.SUPABASE_KEY
            and "your-project-id" not in self.SUPABASE_URL
            and "your-supabase" not in self.SUPABASE_KEY
        )

    @property
    def is_mimo_configured(self) -> bool:
        key = self.MIMO_API_KEY or self.OPENAI_API_KEY
        return bool(key and len(key) > 5)

    @property
    def is_openai_configured(self) -> bool:
        return self.is_mimo_configured

    @property
    def is_deepseek_configured(self) -> bool:
        return bool(self.DEEPSEEK_API_KEY and len(self.DEEPSEEK_API_KEY) > 5)

    @property
    def is_gmail_configured(self) -> bool:
        return bool(
            self.GOOGLE_CLIENT_ID
            and self.GOOGLE_CLIENT_SECRET
            and "your-google" not in self.GOOGLE_CLIENT_ID
        )

    @property
    def cors_origins(self) -> list[str]:
        """Return a normalized allow-list for browser clients."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()
