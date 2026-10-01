import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_privilege_escalation_prevented(async_client: AsyncClient):
    """Verify that public signup IGNORES user-supplied role and enforces Viewer role."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "hacker@example.com",
            "password": "password123",
            "full_name": "Attacker",
            "role": "Admin"  # Attempt privilege escalation
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "Viewer"  # Must be enforced as Viewer

    # Verify user profile in /auth/me
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    me_resp = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "Viewer"

@pytest.mark.asyncio
async def test_admin_create_user_endpoint(async_client: AsyncClient, admin_token_headers, viewer_token_headers):
    """Verify admin-only user creation endpoint."""
    # Viewer attempting to create analyst should fail with 403
    forbidden_resp = await async_client.post(
        "/api/v1/auth/users",
        headers=viewer_token_headers,
        json={
            "email": "newanalyst@insightops.ai",
            "password": "password123",
            "full_name": "New Analyst",
            "role": "Analyst"
        }
    )
    assert forbidden_resp.status_code == 403

    # Admin creating analyst should succeed with 201
    success_resp = await async_client.post(
        "/api/v1/auth/users",
        headers=admin_token_headers,
        json={
            "email": "newanalyst@insightops.ai",
            "password": "password123",
            "full_name": "New Analyst",
            "role": "Analyst"
        }
    )
    assert success_resp.status_code == 201
    assert success_resp.json()["role"] == "Analyst"
