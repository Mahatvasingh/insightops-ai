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

@pytest.mark.asyncio
async def test_auth_login_json_and_form(async_client: AsyncClient):
    # Test JSON login
    res_json = await async_client.post("/api/v1/auth/login", json={
        "username": "admin@insightops.ai",
        "password": "admin123"
    })
    assert res_json.status_code == 200
    data_json = res_json.json()
    assert "access_token" in data_json
    assert data_json["role"] == "Admin"

    # Test Form login
    res_form = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "analyst@insightops.ai", "password": "analyst123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert res_form.status_code == 200
    data_form = res_form.json()
    assert "access_token" in data_form
    assert data_form["role"] == "Analyst"

@pytest.mark.asyncio
async def test_auth_login_invalid_credentials(async_client: AsyncClient):
    res = await async_client.post("/api/v1/auth/login", json={
        "username": "admin@insightops.ai",
        "password": "wrongpassword"
    })
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]

@pytest.mark.asyncio
async def test_auth_register_with_role_requires_invite_code(async_client: AsyncClient):
    # Attempting to register as Analyst without invite code must fail with 403
    unauthorized_payload = {
        "email": "hacker@insightops.ai",
        "password": "securepassword123",
        "full_name": "Unverified Actor",
        "role": "Analyst"
    }
    res_fail = await async_client.post("/api/v1/auth/register", json=unauthorized_payload)
    assert res_fail.status_code == 403
    assert "Invalid or missing Organization Invite Code" in res_fail.json()["detail"]

    # Attempting to register with invalid invite code must fail with 403
    invalid_code_payload = {
        "email": "hacker2@insightops.ai",
        "password": "securepassword123",
        "full_name": "Unverified Actor 2",
        "role": "Admin",
        "invite_code": "WRONG-CODE"
    }
    res_invalid = await async_client.post("/api/v1/auth/register", json=invalid_code_payload)
    assert res_invalid.status_code == 403

    # Viewer registration succeeds without any invite code
    viewer_payload = {
        "email": "publicuser@insightops.ai",
        "password": "securepassword123",
        "full_name": "Public Viewer",
        "role": "Viewer"
    }
    res_viewer = await async_client.post("/api/v1/auth/register", json=viewer_payload)
    assert res_viewer.status_code == 200
    assert res_viewer.json()["role"] == "Viewer"

    # Registering as Analyst with valid invite code succeeds
    analyst_payload = {
        "email": "newanalyst@insightops.ai",
        "password": "securepassword123",
        "full_name": "Test New Analyst",
        "role": "Analyst",
        "invite_code": "INSIGHTOPS-2026"
    }
    res_analyst = await async_client.post("/api/v1/auth/register", json=analyst_payload)
    assert res_analyst.status_code == 200
    data = res_analyst.json()
    assert "access_token" in data
    assert data["role"] == "Analyst"
    assert data["full_name"] == "Test New Analyst"

    # Test duplicate register
    res_dup = await async_client.post("/api/v1/auth/register", json=analyst_payload)
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["detail"]

