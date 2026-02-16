"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient
from fastapi import status

class TestRegistration:
    """Tests for user registration."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, test_user_data):
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user_data):
        # Arrange: Register once
        await client.post("/api/v1/auth/register", json=test_user_data)

        # Act: Register again
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()

    # --- DR Y IMPROVEMENT: Parametrization ---
    @pytest.mark.parametrize("invalid_payload, expected_error", [
        ({"email": "not-an-email", "password": "Valid1!"}, "value is not a valid email"),
        ({"email": "t@e.com", "password": "Short1!"}, "at least 8 characters"),
        ({"email": "t@e.com", "password": "A" * 26 + "1!"}, "at most 24 characters"),
        ({"email": "t@e.com", "password": "NoDigitPass!"}, "digit"),
        ({"email": "t@e.com", "password": "NOLOWER1!"}, "lowercase"),
        ({"email": "t@e.com", "password": "noupper1!"}, "uppercase"),
        ({"email": "t@e.com", "password": "NoSpecial1"}, "special"),
        ({"email": "t@e.com", "password": "BadChar<1!"}, "password"), # Forbidden char
    ])
    @pytest.mark.asyncio
    async def test_register_validation_errors(self, client: AsyncClient, invalid_payload, expected_error):
        """
        One single test to handle ALL validation scenarios.
        """
        response = await client.post("/api/v1/auth/register", json=invalid_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # Check that the error message contains the expected hint (e.g. "digit", "lowercase")
        assert expected_error.lower() in str(response.json()).lower()


class TestLogin:
    """Tests for user login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, registered_user):
        """Uses the 'registered_user' fixture to skip manual registration step."""
        response = await client.post("/api/v1/auth/login", json=registered_user)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, registered_user):
        wrong_credentials = {
            "email": registered_user["email"],
            "password": "WrongPassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=wrong_credentials)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        credentials = {"email": "ghost@ex.com", "password": "Pass123!"}
        response = await client.post("/api/v1/auth/login", json=credentials)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestLogout:
    """Tests for user logout."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers):
        """
        Uses 'auth_headers' fixture.
        The user is ALREADY registered and logged in before this test starts.
        """
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert "logged out" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordChange:
    """Tests for password change."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, auth_headers, test_user_data):
        new_pass = "NewSecurePass456#"

        # 1. Change Password
        response = await client.put(
            "/api/v1/auth/change-password",
            json={"old_password": test_user_data["password"], "new_password": new_pass},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK

        # 2. Verify login with NEW password
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user_data["email"], "password": new_pass}
        )
        assert login_res.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_change_password_failures(self, client: AsyncClient, auth_headers, test_user_data):
        """Combining failure cases for password change."""
        # Case A: Wrong old password
        res = await client.put(
            "/api/v1/auth/change-password",
            json={"old_password": "Wrong!", "new_password": "ValidPass1!"},
            headers=auth_headers
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

        # Case B: Weak new password
        res = await client.put(
            "/api/v1/auth/change-password",
            json={"old_password": test_user_data["password"], "new_password": "weak"},
            headers=auth_headers
        )
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSessionManagement:

    @pytest.mark.asyncio
    async def test_session_persists_clean(self, client: AsyncClient, auth_headers):
        """
        Verifies session validity by hitting a protected endpoint multiple times.
        Uses the clean logic we discussed.
        """
        for i in range(3):
            # We use /api/v1/auth/me if it exists, or /logout (but logout destroys session)
            # Assuming you added the /me endpoint. If not, we can use change-password dry run.
            response = await client.get("/api/v1/auth/me", headers=auth_headers)
            assert response.status_code == status.HTTP_200_OK, f"Request {i} failed"

    @pytest.mark.asyncio
    async def test_logout_invalidates_session(self, client: AsyncClient, auth_headers, test_user_data):
        # 1. Logout
        await client.post("/api/v1/auth/logout", headers=auth_headers)

        # 2. Try to perform action with OLD headers
        response = await client.put(
            "/api/v1/auth/change-password",
            json={"old_password": test_user_data["password"], "new_password": "New!"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED