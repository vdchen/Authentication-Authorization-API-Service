import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_get_balance_optimized(client, auth_headers):
    """Verify the new optimized balance endpoint."""
    response = await client.get("/api/v1/users/me/balance",
                                headers=auth_headers)
    assert response.status_code == 200
    assert "balance" in response.json()
    assert isinstance(response.json()["balance"], int)


@pytest.mark.asyncio
async def test_login_increments_balance(client, registered_user):
    """Verify business rule: Each login adds 100 cents."""
    # First login
    res1 = await client.post("/api/v1/auth/login", json=registered_user)
    token = res1.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Check balance via the NEW optimized endpoint
    bal_res = await client.get("/api/v1/users/me/balance",
                               headers=auth_headers)

    assert bal_res.json()["balance"] == 100

    # Second login
    await client.post("/api/v1/auth/login", json=registered_user)

    # Check balance again
    bal_res = await client.get("/api/v1/users/me/balance",
                               headers=auth_headers)

    assert bal_res.json()["balance"] == 200


@pytest.mark.asyncio
async def test_withdraw_logic(client, auth_headers,
                              authenticated_user_profile):
    """Verify withdrawal: Requires names and sufficient funds."""
    # Ensure balance is at 100 first (via one login)
    # authenticated_user_profile should have first_name/last_name set

    withdraw_data = {"amount": 50}
    response = await client.post(
        "/api/v1/users/me/withdraw",
        json=withdraw_data,
        headers=auth_headers
    )

    assert response.status_code == 200
    # If it was 100, it is now exactly 50
    assert response.json()["balance"] == 50


@pytest.mark.asyncio
async def test_withdraw_fails_without_names(client, auth_headers):
    """Verify safety rule: Withdrawal blocked if names are missing (403 Forbidden)."""
    # Use a user that has NO first_name/last_name set
    response = await client.post(
        "/api/v1/users/me/withdraw",
        json={"amount": 10},
        headers=auth_headers
    )

    # Based on your users.py, this returns 403 Forbidden
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "first and last name" in response.json()["detail"]


@pytest.mark.asyncio
async def test_withdraw_insufficient_funds(client, auth_headers,
                                           authenticated_user_profile):
    """Verify it fails if the user tries to withdraw more than they have."""
    # Attempt to withdraw 1,000,000 cents

    response = await client.post(
        "/api/v1/users/me/withdraw",
        json={"amount": 1000000},
        headers=auth_headers
    )
    # The service raises ValueError -> Router catches and raises 400
    assert response.status_code == 400
    assert "Insufficient funds" in response.json()["detail"]


@pytest.mark.asyncio
async def test_user_soft_delete(client, user_token: str):
    # 1. Perform deletion
    response = await client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 204

    # 2. Try to login again (should fail because user is_deleted)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@test.com", "password": "..."}
    )
    assert login_response.status_code == 404



