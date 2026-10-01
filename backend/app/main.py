import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core.limiter import limiter
from app.db.init_db import init_db
from app.api.auth import router as auth_router
from app.api.competitors import router as competitors_router
from app.api.alerts import router as alerts_router
from app.api.agent import router as agent_router
from app.api.analytics import router as analytics_router
from app.api.reports import router as reports_router
from app.api.health import router as health_router
from app.scheduler import start_scheduler, shutdown_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("insightops")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database and starting APScheduler...")
    init_db()
    start_scheduler()
    yield
    logger.info("Shutting down APScheduler...")
    shutdown_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="InsightOps AI: Autonomous Market Intelligence & Competitor War-Room Backend API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# SlowAPI Rate Limiting State
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware setup using configured ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API V1 Routers
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(competitors_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)
app.include_router(agent_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "status": "online",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
