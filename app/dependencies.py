"""Dependency injection for FastAPI."""
from typing import Annotated
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.db.session import get_async_session
from app.utils.redis_client import get_redis_client, RedisClient
from app.services.auth_service import AuthService
from app.core.security import decode_access_token
from app.core.exceptions import AuthenticationError, SessionNotFoundError

# This adds the "Lock" icon to Swagger UI
security = HTTPBearer()

async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    redis: Annotated[RedisClient, Depends(get_redis_client)]
) -> AuthService:
    """Dependency for getting authentication service."""
    return AuthService(db, redis)

async def get_token_payload(
    auth: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """
    Helper dependency to decode the token.
    Consolidates error handling in one place.
    """
    try:
        # auth.credentials is the token string without 'Bearer '
        return decode_access_token(auth.credentials)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {str(e)}")

async def get_current_user(
    payload: Annotated[dict, Depends(get_token_payload)],
    redis: Annotated[RedisClient, Depends(get_redis_client)]
) -> int:
    """Dependency for getting current authenticated user ID."""
    session_id = payload.get("session_id")
    if not session_id:
        raise AuthenticationError("Invalid token payload: missing session_id")

    user_id = await redis.get_session(session_id)
    if not user_id:
        raise SessionNotFoundError()

    # Sliding window session: extend on every request
    await redis.extend_session(session_id)
    return user_id

async def get_session_id(
    payload: Annotated[dict, Depends(get_token_payload)]
) -> str:
    """Dependency for extracting session ID from token."""
    session_id = payload.get("session_id")
    if not session_id:
        raise AuthenticationError("Invalid token payload: missing session_id")
    return session_id