"""Custom exceptions for the application."""
from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class UserAlreadyExistsError(HTTPException):
    """Raised when attempting to register with existing email."""

    def __init__(self, detail: str = "User with this email already exists"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class UserNotFoundError(HTTPException):
    """Raised when user is not found."""

    def __init__(self, detail: str = "User not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class InvalidPasswordError(HTTPException):
    """Raised when password is invalid."""

    def __init__(self, detail: str = "Invalid password"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class SessionNotFoundError(HTTPException):
    """Raised when session is not found or expired."""

    def __init__(self, detail: str = "Session not found or expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class DatabaseError(Exception):
    """Raised when database operations fail."""

    pass


class RedisError(Exception):
    """Raised when Redis operations fail."""

    pass

class BlockedUserError(Exception):
    pass