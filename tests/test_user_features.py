import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_login_increments_balance(client, registered_user):
    """Verify business rule: Each login adds 100 cents."""
    # First login
    res1 = await client.post("/api/v1/auth/login", json=registered_user)
    token = res1.json()["access_token"]

    # Check balance via the list endpoint (as /me requires names)
    user_res = await client.get("/api/v1/users/",
                                headers={"Authorization": f"Bearer {token}"})
    assert user_res.json()["users"][0]["balance"] == 100

    # Second login
    await client.post("/api/v1/auth/login", json=registered_user)
    user_res = await client.get("/api/v1/users/",
                                headers={"Authorization": f"Bearer {token}"})
    assert user_res.json()["users"][0]["balance"] == 200


@pytest.mark.asyncio
async def test_withdraw_logic(client, auth_headers,
                              authenticated_user_profile):
    """Verify withdrawal: Requires names and sufficient funds."""
    # 1. Withdraw within limits (after 1 login bonus + 1 registration, balance should be at least 100)
    # Note: If your registration also adds balance, adjust this number.
    withdraw_data = {"amount": 50}
    response = await client.post("/api/v1/users/me/withdraw",
                                 json=withdraw_data, headers=auth_headers)

    assert response.status_code == 200
    # If balance started at 100, it should now be 50
    assert response.json()["balance"] < 100


@pytest.mark.asyncio
async def test_withdraw_fails_without_names(client, auth_headers):
    """Verify safety rule: Withdrawal blocked if names are missing."""
    # We use auth_headers but NOT the authenticated_user_profile fixture here
    response = await client.post("/api/v1/users/me/withdraw",
                                 json={"amount": 10}, headers=auth_headers)
    assert response.status_code == 400
    assert "first and last name" in response.json()["detail"]


@pytest.mark.asyncio
async def test_user_sorting(client, auth_headers):
    # Register multiple users and set different balances manually in DB or via multiple logins
    # For this test, let's assume we have users with balances 100, 200, 300

    # Query sorted by balance descending
    res = await client.get(
        "/api/v1/users/?sort_by=balance&sort_order=desc",
        headers=auth_headers
    )

    # Debug check: if this fails, print(res.json()) to see the error
    assert res.status_code == 200

    data = res.json()
    users = data["users"]

    # Check if the first user has a higher or equal balance than the second
    if len(users) > 1:
        assert users[0]["balance"] >= users[1]["balance"]