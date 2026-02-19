"""Redis client utility."""
from typing import Optional
import redis.asyncio as redis
from app.config import settings
from app.core.exceptions import RedisError


class RedisClient:
    """Async Redis client wrapper."""

    def __init__(self):
        """Initialize Redis client."""
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        # If we already have an active client, don't create a new one
        if self.client:
            return

        try:
            self.client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30
            )
            await self.client.ping()
        except Exception as e:
            # Reset to None if the connection attempt failed
            self.client = None
            raise RedisError(f"Failed to connect to Redis: {str(e)}")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.client:
            await self.client.aclose()
            self.client = None #reset to None after closing

    async def set_session(self, session_id: str, user_id: int) -> None:
        """
        Store session data in Redis.

        Args:
            session_id: Session identifier
            user_id: User ID

        Raises:
            RedisError: If operation fails
        """
        try:
            key = f"{settings.redis_session_prefix}{session_id}"
            await self.client.setex(
                key,
                settings.redis_session_expire_seconds,
                str(user_id)
            )
        except Exception as e:
            raise RedisError(f"Failed to set session: {str(e)}")

    async def get_session(self, session_id: str) -> Optional[int]:
        """
        Get session data from Redis.

        Args:
            session_id: Session identifier

        Returns:
            User ID if session exists, None otherwise

        Raises:
            RedisError: If operation fails
        """
        try:
            key = f"{settings.redis_session_prefix}{session_id}"
            user_id = await self.client.get(key)
            return int(user_id) if user_id else None
        except Exception as e:
            raise RedisError(f"Failed to get session: {str(e)}")

    async def delete_session(self, session_id: str) -> None:
        """
        Delete session from Redis.

        Args:
            session_id: Session identifier

        Raises:
            RedisError: If operation fails
        """
        try:
            key = f"{settings.redis_session_prefix}{session_id}"
            await self.client.delete(key)
        except Exception as e:
            raise RedisError(f"Failed to delete session: {str(e)}")

    async def extend_session(self, session_id: str) -> None:
        """
        Extend session expiration time.

        Args:
            session_id: Session identifier

        Raises:
            RedisError: If operation fails
        """
        try:
            key = f"{settings.redis_session_prefix}{session_id}"
            await self.client.expire(key,
                                     settings.redis_session_expire_seconds)
        except Exception as e:
            raise RedisError(f"Failed to extend session: {str(e)}")


# Global Redis client instance
redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """
    Dependency for getting Redis client.

    Returns:
        RedisClient: Redis client instance
    """
    return redis_client