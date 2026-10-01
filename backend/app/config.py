import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "InsightOps AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "c8a9f3e4b1d720516b7e820c4519fa9012e3456789abcdef0123456789abcdef"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Demo & System Modes
    DEMO_MODE: bool = False
    SCRAPER_MODE: str = "demo"  # demo | live

    # Database & Checkpointer
    DATABASE_URL: str = "sqlite+aiosqlite:///./insightops.db"
    SYNC_DATABASE_URL: str = "sqlite:///./insightops.db"
    SQLITE_CHECKPOINT_DB: str = "./checkpointer.db"

    # LLM Settings
    LLM_PROVIDER: str = "mock"  # mock | openai | gemini
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"
    LLM_TOKEN_BUDGET: int = 50000

    # CORS & Security
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Quantitative Anomaly Thresholds (%)
    CRITICAL_PCT_THRESHOLD: float = 15.0
    HIGH_PCT_THRESHOLD: float = 5.0

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_AGENT_RUN: str = "10/minute"

    # Cache TTL (in seconds)
    CACHE_TTL_SCRAPE: int = 3600  # 1 hour
    CACHE_TTL_LLM: int = 1800     # 30 mins

    @field_validator("SECRET_KEY", mode="after")
    def validate_secret_key(cls, v: str, info) -> str:
        # Require non-default secret key outside demo mode
        demo_mode = info.data.get("DEMO_MODE", False)
        if not demo_mode and v == "c8a9f3e4b1d720516b7e820c4519fa9012e3456789abcdef0123456789abcdef":
            raise ValueError("SECRET_KEY must be explicitly set in production mode (.env)")
        return v

settings = Settings()
