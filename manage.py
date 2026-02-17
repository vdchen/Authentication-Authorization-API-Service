"""Database management CLI."""
import asyncio
import logging
import typer
from alembic.config import Config
from alembic import command
from app.db.session import engine
from app.db.base import Base
from app.config import settings

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cli = typer.Typer()

# Helper to load Alembic config
def get_alembic_config():
    return Config("alembic.ini")

@cli.command()
def make_migrations(message: str = "New migration"):
    """
    Generate a new migration file (Auto-generate).
    Equivalent to: django-admin makemigrations
    """
    logger.info(f"Generating migration: {message}")
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, message=message, autogenerate=True)
    logger.info("Migration file created.")

@cli.command()
def migrate():
    """
    Apply all pending migrations to the database.
    Equivalent to: django-admin migrate
    """
    logger.info("Applying migrations...")
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, "head")
    logger.info("Database upgraded to head.")

@cli.command()
def drop():
    """Drop all tables (Use with caution!)."""
    if typer.confirm(f"⚠️  DANGER: Drop ALL tables in {settings.database_url}?"):
        async def _drop():
            async with engine.begin() as conn:
                # This drops tables but doesn't clear Alembic history from the file system
                await conn.run_sync(Base.metadata.drop_all)

        asyncio.run(_drop())
        logger.warning("All tables dropped.")

@cli.command()
def reset():
    """Drop all tables and re-run migrations from scratch."""
    drop()
    migrate()

if __name__ == "__main__":
    cli()