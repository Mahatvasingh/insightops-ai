import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.db.models import User
from app.core.security import create_access_token

@pytest.mark.asyncio
async def test_auth_deactivated_user_rejected(async_client: AsyncClient, db_session):
    result = await db_session.execute(select(User).where(User.email == "viewer@insightops.ai"))
    user = result.scalars().first()
    assert user is not None
    user.is_active = False
    await db_session.commit()

    token = create_access_token(subject="viewer@insightops.ai", role="Viewer")
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"]

@pytest.mark.asyncio
async def test_auth_demoted_user_loses_access(async_client: AsyncClient, db_session):
    result = await db_session.execute(select(User).where(User.email == "analyst@insightops.ai"))
    user = result.scalars().first()
    assert user is not None
    user.role = "Viewer"
    await db_session.commit()

    # Old token encoded with Analyst role
    token = create_access_token(subject="analyst@insightops.ai", role="Analyst")
    headers = {"Authorization": f"Bearer {token}"}

    comp_payload = {
        "name": "Test Domain Corp",
        "domain": "testdomain.com",
        "pricing_url": "https://testdomain.com/pricing"
    }
    res = await async_client.post("/api/v1/competitors", json=comp_payload, headers=headers)
    assert res.status_code == 403
    assert "does not have sufficient permissions" in res.json()["detail"]
