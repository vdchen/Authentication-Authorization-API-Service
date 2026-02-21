"""Authentication service with business logic."""
import uuid
from datetime import timedelta
from typing import Optional, Tuple

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import User
from app.schemas.auth import UserRegister, UserLogin, PasswordChange
from sqlalchemy.sql import func
# Import the password_hash object for the upgrade logic
from app.core.security import hash_password, verify_password, create_tokens, \
    password_hash, decode_access_token, create_token
from app.core.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidPasswordError,
    DatabaseError, SessionNotFoundError,
    AuthenticationError
)
from app.utils.redis_client import RedisClient


class AuthService:
    """Authentication service for handling user operations."""

    def __init__(self, db: AsyncSession, redis: RedisClient):
        self.db = db
        self.redis = redis

    async def register_user(self, user_data: UserRegister) -> User:
        """Register a new user with Argon2id hashing."""
        try:
            result = await self.db.execute(
                select(User).where(User.email == user_data.email)
            )
            if result.scalar_one_or_none():
                raise UserAlreadyExistsError()

            hashed_password = await hash_password(user_data.password)

            new_user = User(
                email=user_data.email,
                hashed_password=hashed_password
            )

            self.db.add(new_user)
            # Use commit() instead of flush()
            await self.db.commit()
            await self.db.refresh(new_user)

            return new_user

        except UserAlreadyExistsError:
            raise
        except Exception as e:
            await self.db.rollback() # Safety first!
            raise DatabaseError(f"Failed to register user: {str(e)}")

    async def login_user(self, credentials: UserLogin) -> Tuple[str, str, str, User]:
        """Authenticate user and perform automatic password hash upgrade."""
        try:
            result = await self.db.execute(
                select(User).where(User.email == credentials.email)
            )
            user = result.scalar_one_or_none()

            if not user:
                raise UserNotFoundError()

            # verify_and_update checks if password is correct AND if the hash is "old" (like Bcrypt)
            is_correct, new_hash = password_hash.verify_and_update(
                credentials.password,
                user.hashed_password
            )

            if not is_correct:
                raise InvalidPasswordError()

            # If the hash needs upgrading (e.g., from Bcrypt to Argon2id), save.
            if new_hash:
                user.hashed_password = new_hash

            # Add balance bonus (100 cents = 1.00)
            user.balance += 100

            # Update last activity timestamp
            user.last_activity_at = func.now()

            # Commit the hash upgrade, balance change, and timestamp
            await self.db.commit()

            session_id = str(uuid.uuid4())
            # Generate both tokens including session_id
            access_token, refresh_token = create_tokens(
                data={"sub": user.email, "session_id": session_id}
            )

            await self.redis.set_session(session_id, user.id)
            return access_token, refresh_token, session_id, user

        except (UserNotFoundError, InvalidPasswordError):
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to login user: {str(e)}")

    async def refresh_session(self, refresh_token: str) -> Tuple[str, str]:
        """Validates refresh token and issues a new access token."""
        try:
            payload = decode_access_token(refresh_token)

            # Security Check: Ensure this is actually a refresh token
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")

            session_id = payload.get("session_id")
            user_id = await self.redis.get_session(session_id)

            if not user_id:
                raise SessionNotFoundError()

            # Issue a new access token
            new_access_token = create_token(
                data={"sub": payload.get("sub"), "session_id": session_id},
                expires_delta=timedelta(
                    minutes=settings.access_token_expire_minutes),
                token_type="access"
            )

            return new_access_token, refresh_token  # Usually keep same refresh token
        except jwt.PyJWTError:
            raise AuthenticationError("Invalid or expired refresh token")


    async def logout_user(self, session_id: str) -> None:
        """Logout user by deleting session from Redis."""
        await self.redis.delete_session(session_id)

    async def change_password(self, user_id: int, password_data: PasswordChange) -> None:
        """Change user password and commit to DB."""
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                raise UserNotFoundError()

            # Use utility for consistency
            if not await verify_password(password_data.old_password, user.hashed_password):
                raise InvalidPasswordError("Old password is incorrect")

            user.hashed_password = await hash_password(password_data.new_password)

            await self.db.commit() # Save the change

        except (UserNotFoundError, InvalidPasswordError):
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to change password: {str(e)}")

    # Helper methods
    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()