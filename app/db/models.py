"""Database models."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, CheckConstraint
from sqlalchemy.sql import func
from app.db.base import Base


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Balance logic: Integer (cents) is safer than Float for money
    # CheckConstraint ensures database rejects negative values
    balance = Column(Integer, default=0, nullable=False)

    is_blocked = Column(Boolean, default=False, nullable=False)

    last_activity_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Use func.now() to let the DB (Postgres) handle the timestamp
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # onupdate=func.now() keeps updated_at fresh automatically
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Database-level constraint to prevent negative balance
    __table_args__ = (
        CheckConstraint('balance >= 0', name='check_balance_positive'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, balance={self.balance})>"