"""Redis client utility."""
from typing import Optional
import redis.asyncio as redis
from app.config import settings
from app.core.exceptions import RedisError


class RedisClient:
    """Async Redis client wrapper."""

    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.pool: Optional[redis.ConnectionPool] = None

    async def connect(self) -> None:
        """"Initialize the Redis connection pool."""
        if self.pool is None:
            try:
                self.pool = redis.ConnectionPool.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=20
                )
                self.client = redis.Redis(connection_pool=self.pool)
                await self.client.ping()
            except Exception as e:
                self.client = None
                self.pool = None
                raise RedisError(f"Failed to connect to Redis: {str(e)}")

    async def disconnect(self) -> None:
        """Close the connection pool gracefully."""
        if self.pool:
            await self.pool.disconnect()
            self.client = None
            self.pool = None

    async def set_session(self, session_id: str, user_id: int,
                          expire_minutes: int) -> None:
        """
        Store session data in Redis.

        Args:
            session_id: Session identifier
            user_id: User ID

        Raises:
            RedisError: If operation fails
        """
        try:
            await self.client.set(
                name=f"session:{session_id}",
                value=str(user_id),
                ex=expire_minutes * 60
            )
        except Exception as e:
            raise RedisError(f"Failed to set session: {str(e)}")

    async def get_session(self, session_id: str) -> Optional[int]:
        """Retrieves user_id. Returns None if session is expired or missing."""
        try:
            val = await self.client.get(f"session:{session_id}")
            return int(val) if val else None
        except Exception as e:
            raise RedisError(f"Failed to get session: {str(e)}")

    async def delete_session(self, session_id: str) -> None:
        """Manual logout."""
        try:
            await self.client.delete(f"session:{session_id}")
        except Exception as e:
            raise RedisError(f"Failed to delete session: {str(e)}")

    async def extend_session(self, session_id: str, expire_minutes: int) -> None:
        """Sliding window: resets the TTL on activity."""
        try:
            await self.client.expire(f"session:{session_id}",
                                     expire_minutes * 60)
        except Exception as e:
            raise RedisError(f"Failed to extend session: {str(e)}")

    async def invalidate_admin_cache(self) -> None:
        """
        Finds and deletes all Redis keys associated with the 'admin_list' namespace.
        This ensures that when a user is blocked or registered, the admin list is refreshed.
        """
        if not self.client:
            return

        # aiocache often stores keys as ':admin_list:<hash>' or 'admin_list:<hash>'
        # Using *admin_list* ensures we catch both formats.
        match_pattern = "*admin_list*"
        cursor = 0

        try:
            while True:
                # SCAN returns a cursor and a list of keys found
                cursor, keys = await self.client.scan(
                    cursor=cursor,
                    match=match_pattern,
                    count=100
                )
                if keys:
                    await self.client.delete(*keys)

                # If cursor is 0, the iteration is complete
                if cursor == 0:
                    break
        except Exception as e:
            # We raise a custom error or log it so it doesn't crash the main DB transaction
            raise RedisError(f"Failed to invalidate admin cache: {str(e)}")


# Global Redis client instance
redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """
    Dependency for getting Redis client.

    Returns:
        RedisClient: Redis client instance
    """
    return redis_client