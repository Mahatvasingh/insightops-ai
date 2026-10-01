from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.database import get_db
from app.config import settings
from app.core.cache import cache_manager

router = APIRouter(prefix="/health", tags=["System Health"])

@router.get("")
async def get_health_status(db: AsyncSession = Depends(get_db)):
    """Health check endpoint checking Database, Cache, and System configuration."""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {e}"

    cache_stats = cache_manager.stats()

    return {
        "status": "online" if db_status == "healthy" else "degraded",
        "service": settings.PROJECT_NAME,
        "database": db_status,
        "demo_mode": settings.DEMO_MODE,
        "scraper_mode": settings.SCRAPER_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "cache": cache_stats
    }
