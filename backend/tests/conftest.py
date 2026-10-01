import os
import pytest
import asyncio
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Set environment for testing
os.environ["DEMO_MODE"] = "true"
os.environ["SCRAPER_MODE"] = "demo"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SQLITE_CHECKPOINT_DB"] = ":memory:"

from app.main import app
from app.db.database import Base, get_db
from app.db.models import User
from app.core.security import get_password_hash, create_access_token
from app.core.cache import cache_manager

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def reset_cache():
    cache_manager.clear()

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        # Seed test users into memory database
        admin_user = User(
            email="admin@insightops.ai",
            hashed_password=get_password_hash("admin123"),
            full_name="Chief Intelligence Officer (Admin)",
            role="Admin",
            is_active=True
        )
        analyst_user = User(
            email="analyst@insightops.ai",
            hashed_password=get_password_hash("analyst123"),
            full_name="Lead Market Analyst",
            role="Analyst",
            is_active=True
        )
        viewer_user = User(
            email="viewer@insightops.ai",
            hashed_password=get_password_hash("viewer123"),
            full_name="Executive Viewer",
            role="Viewer",
            is_active=True
        )
        session.add_all([admin_user, analyst_user, viewer_user])
        await session.commit()
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
def admin_token_headers():
    token = create_access_token(subject="admin@insightops.ai", role="Admin")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def analyst_token_headers():
    token = create_access_token(subject="analyst@insightops.ai", role="Analyst")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def viewer_token_headers():
    token = create_access_token(subject="viewer@insightops.ai", role="Viewer")
    return {"Authorization": f"Bearer {token}"}
