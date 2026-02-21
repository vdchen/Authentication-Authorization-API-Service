import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_admin_list_users_success(client: AsyncClient, admin_token: str):
    """Admin should see the user list in the specific {id: {data}} format."""
    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    # Check for the keyed dictionary format
    assert isinstance(data["users"], list)
    assert "user_id" in list(data["users"][0].values())[0]

@pytest.mark.asyncio
async def test_admin_route_hidden_from_user(client: AsyncClient, user_token: str):
    """CRITICAL: Regular users MUST get a 404 for admin routes."""
    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found" # Matching your dependency logic