"""Database management CLI."""
import asyncio
import typer
from sqlalchemy import text
from app.db.session import engine, init_db
from app.db.base import Base
from app.config import settings

cli = typer.Typer()


@cli.command()
def init():
    """Create all tables defined in models (SQLAlchemy create_all)."""
    print(f"Creating tables on {settings.database_url}...")
    asyncio.run(init_db())
    print("Tables created successfully.")


@cli.command()
def drop():
    """Drop all tables."""
    if typer.confirm("Are you sure you want to delete all data?"):
        async def _drop():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

        asyncio.run(_drop())
        print("Tables dropped.")


@cli.command()
def reset():
    """Drop and recreate all tables."""
    drop()
    init()


if __name__ == "__main__":
    cli()