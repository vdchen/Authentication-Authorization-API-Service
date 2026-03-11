import logging
import json
import sys
from datetime import datetime, timezone
from app.config import settings


class JSONFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format for production."""

    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def setup_logging():
    # 1. Determine Levels
    if settings.ENVIRONMENT == "prod":
        base_level = logging.ERROR
    else:
        base_level = logging.INFO

    # 2. Choose Formatter
    if settings.ENVIRONMENT == "prod":
        formatter = JSONFormatter()
    else:
        # Standard readable format for local/dev
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # 3. Setup Handler (Standard Output)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # 4. Configure Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(base_level)

    # Remove existing handlers to avoid duplicate logs in FastAPI
    root_logger.handlers = []
    root_logger.addHandler(handler)

    # 5. Environment-Specific Overrides
    if settings.ENVIRONMENT == "dev":
        # Specifically silence database logs even if global is INFO
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        # If using 'databases' or other libs:
        logging.getLogger("databases").setLevel(logging.WARNING)

    # Ensure Uvicorn logs follow our new level/format
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers = []
        uv_logger.addHandler(handler)
        uv_logger.propagate = False  # Prevent double logging