import pytest
from unittest.mock import AsyncMock
from app.utils.redis_client import RedisClient, redis_client
import asyncio


@pytest.mark.asyncio
async def test_set_session_with_expiration():
    """Test that setting a session passes the correct TTL to Redis."""
    # Arrange
    redis_client = RedisClient()
    redis_client.client = AsyncMock()  # Mock the actual redis-py client

    session_id = "test-session-123"
    user_id = 42
    expire_minutes = 60

    # Act
    await redis_client.set_session(session_id, user_id, expire_minutes)

    # Assert
    # Verify that the underlying redis set() was called with the right 'ex' (seconds)
    redis_client.client.set.assert_called_once_with(
        name=f"session:{session_id}",
        value=str(user_id),
        ex=expire_minutes * 60  # 3600 seconds
    )


@pytest.mark.asyncio
async def test_get_session_success():
    """Test retrieving a valid session."""
    redis_client = RedisClient()
    redis_client.client = AsyncMock()
    # Mock Redis returning string "42"
    redis_client.client.get.return_value = "42"

    user_id = await redis_client.get_session("valid-session")

    assert user_id == 42
    redis_client.client.get.assert_called_once_with("session:valid-session")


@pytest.mark.asyncio
async def test_extend_session_ttl():
    """Test the sliding window token expiration."""
    redis_client = RedisClient()
    redis_client.client = AsyncMock()

    session_id = "active-session"
    expire_minutes = 30

    await redis_client.extend_session(session_id, expire_minutes)

    # Verify the expire command was sent to Redis to reset the TTL
    redis_client.client.expire.assert_called_once_with(
        f"session:{session_id}",
        expire_minutes * 60
    )


@pytest.mark.asyncio
async def test_token_auto_expiration():
    """
    Verifies that Redis correctly expires a key after the TTL.
    This fulfills the 'automatic expiration' requirement.
    """
    # 1. Connect to Redis
    await redis_client.connect()

    session_id = "test-session-expire"
    user_id = 999
    short_ttl_seconds = 1  # We'll use 1 second for the test

    # 2. Manually set a session with a very short TTL (1 second)
    # We bypass the 'minutes' logic just for this test
    await redis_client.client.set(
        name=f"session:{session_id}",
        value=str(user_id),
        ex=short_ttl_seconds
    )

    # 3. Verify it exists initially
    val_before = await redis_client.get_session(session_id)
    assert val_before == user_id

    # 4. Wait for it to expire
    await asyncio.sleep(1.1)

    # 5. Verify it is gone
    val_after = await redis_client.get_session(session_id)
    assert val_after is None

    await redis_client.disconnect()