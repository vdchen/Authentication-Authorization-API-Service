"""Pytest configuration and fixtures."""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_async_session
from app.utils.redis_client import get_redis_client, RedisClient
from app.config import settings
import logging

# Setup logging for tests
logger = logging.getLogger(__name__)

# Force tests to use Redis DB 9 (Safety measure)
settings.redis_url = "redis://127.0.0.1:6379/9"

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

TestAsyncSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with isolated tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def redis_client() -> AsyncGenerator[RedisClient, None]:
    """Create test Redis client on a safe DB."""
    client = RedisClient()
    await client.connect()

    # Check we are definitely on a test DB before flushing!
    connection_kwargs = client.client.connection_pool.connection_kwargs
    db_index = connection_kwargs.get("db", 0)

    if db_index == 0:
        logger.warning(
            "Running tests on Redis DB 0! Data loss risk for production/local data.")
    else:
        logger.info("Test Redis connected to DB %s", db_index)

    yield client

    # Clean up after test
    if client.client:
        await client.client.flushdb()
    await client.disconnect()

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, redis_client: RedisClient) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden dependencies."""
    app.dependency_overrides[get_async_session] = lambda: db_session
    app.dependency_overrides[get_redis_client] = lambda: redis_client

    # Use ASGITransport for modern httpx versions
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def registered_user(client: AsyncClient, test_user_data):
    """
    Fixture that registers a user and returns the user data.
    """
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    return test_user_data

@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, registered_user):
    """
    Fixture that logs in the registered user and returns headers with the token.
    Now your tests don't need to manually login!
    """
    response = await client.post("/api/v1/auth/login", json=registered_user)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def authenticated_user_profile(client: AsyncClient, auth_headers):
    """
    Fixture that completes the profile (names) for tests that require it.
    """
    profile_data = {"first_name": "Vlad", "last_name": "Cottbus"}
    await client.patch("/api/v1/users/me", json=profile_data, headers=auth_headers)
    return profile_data


@pytest.fixture
def test_user_data():
    """Test user registration data."""
    return {
        "email": "test@example.com",
        "password": "TestPass123!",
    }


@pytest.fixture
def test_user_data_2():
    """Second test user registration data."""
    return {
        "email": "test2@example.com",
        "password": "SecurePass456#",
    }
