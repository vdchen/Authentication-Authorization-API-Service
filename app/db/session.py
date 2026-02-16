"""Database session management."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.db.base import Base

# 1. Create async engine (echo=True for debugging)
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

# 2. Create async session factory
# autocommit=False is the default in SQLAlchemy 2.0
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        # models.py User table gets created
        await conn.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.
    The session is automatically closed when the request is finished.
    """
    async with AsyncSessionLocal() as session:
        yield session
        # Commit is in logic for better control.

async def close_db() -> None:
    """Close database engine connections."""
    await engine.dispose()