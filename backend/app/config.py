import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "InsightOps AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "c8a9f3e4b1d720516b7e820c4519fa9012e3456789abcdef0123456789abcdef")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Demo & Scraper Control
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "t")
    SCRAPER_MODE: str = os.getenv("SCRAPER_MODE", "demo")  # demo | live

    # Database & Checkpointer
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./insightops.db")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "sqlite:///./insightops.db")
    SQLITE_CHECKPOINT_DB: str = os.getenv("SQLITE_CHECKPOINT_DB", "./checkpointer.db")

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")  # mock | openai | gemini
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    LLM_TOKEN_BUDGET: int = int(os.getenv("LLM_TOKEN_BUDGET", "50000"))

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_AGENT_RUN: str = "10/minute"

    # Cache TTL (in seconds)
    CACHE_TTL_SCRAPE: int = 3600  # 1 hour
    CACHE_TTL_LLM: int = 1800     # 30 mins

    class Config:
        case_sensitive = True

settings = Settings()

