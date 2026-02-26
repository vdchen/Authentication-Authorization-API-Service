"""Dependency injection for FastAPI."""
from typing import Annotated
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
from fastapi import HTTPException, status

from app.config import settings
from app.db.session import get_async_session
from app.utils.redis_client import get_redis_client, RedisClient
from app.services.auth_service import AuthService
from app.core.security import decode_access_token
from app.core.exceptions import AuthenticationError, SessionNotFoundError
from app.db.models import User, Role


# Adds the "Lock" icon to Swagger UI
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
        payload = decode_access_token(auth.credentials)
        if payload.get("type") != "access":
            raise AuthenticationError("Access token required")
        return payload
    except jwt.ExpiredSignatureError:
        # Per requirements: return 401 if token is not valid
        raise HTTPException(status_code=401, detail="Token has expired")
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
    await redis.extend_session(session_id, settings.access_token_expire_minutes)
    return user_id

async def get_session_id(
    payload: Annotated[dict, Depends(get_token_payload)]
) -> str:
    """Dependency for extracting session ID from token."""
    session_id = payload.get("session_id")
    if not session_id:
        raise AuthenticationError("Invalid token payload: missing session_id")
    return session_id

async def get_current_user_obj(
        user_id: Annotated[int, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_async_session)]
) -> User:
    """Fetches the user and checks if they are blocked or deleted."""

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found")

    if user.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Your account is blocked.")

    return user


async def get_current_admin(
        current_user: Annotated[User, Depends(get_current_user_obj)]
) -> User:
    """Dependency for Admin-only routes. Returns 404 for users to hide the route."""
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Not Found")
    return current_user