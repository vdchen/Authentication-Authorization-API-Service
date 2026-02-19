"""Pydantic schemas for authentication."""
import re
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict

def validate_password_complexity(v: str) -> str:
    """Reusable password complexity logic."""

    if any(char in v for char in ['@', '"', "'", '<', '>']):
        raise ValueError("Password cannot contain @, \", ', <, or >")

    if not re.search(r'\d', v):
        raise ValueError("Password must contain at least one digit")

    if not re.search(r'[a-z]', v):
        raise ValueError("Password must contain at least one lowercase letter")

    if not re.search(r'[A-Z]', v):
        raise ValueError("Password must contain at least one uppercase letter")

    if not re.search(r'[!#$%&()*+,\-./:;=?[\\\]^_`{|}~]', v):
        raise ValueError("Password must contain at least one special character")

    return v

class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, max_length=24)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_complexity(v)

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

class PasswordChange(BaseModel):
    """Schema for password change."""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=24)

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return validate_password_complexity(v)

class UserResponse(BaseModel):
    """Schema for user response (safe to return to frontend)."""
    id: int
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    # Handling ORM/SQLAlchemy models
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    token_type: str = "bearer"
    session_id: str

class MessageResponse(BaseModel):
    """Schema for generic message response."""
    message: str