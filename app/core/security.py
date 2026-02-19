"""Security utilities for password hashing and JWT tokens."""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from app.config import settings

# Password hashing (automatically handles bcrypt/argon2)
password_hash = PasswordHash((
    Argon2Hasher(),
    BcryptHasher(),
))


async def hash_password(password: str) -> str:
    """
    Hash a password.
    Hashing is CPU-intensive, so we offload it to a thread to keep
    the FastAPI event loop free to handle other requests.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, password_hash.hash, password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash asynchronously."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        password_hash.verify,
        plain_password,
        hashed_password
    )


def create_access_token(data: dict,
                        expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with proper UTC awareness."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    expire = now + (expires_delta or timedelta(
        minutes=settings.access_token_expire_minutes))

    to_encode.update({"exp": expire, "iat": now})

    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm]
    )