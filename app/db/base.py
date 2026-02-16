"""Database base configuration."""
from app.db.models import Base

# Export Base for use in other modules
__all__ = ["Base"]