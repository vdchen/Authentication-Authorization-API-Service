import logging
import json
import pytest
from unittest.mock import patch
from app.core.logging_config import setup_logging, JSONFormatter


def test_local_logging_level(monkeypatch):
    """Test that local environment defaults to INFO."""
    monkeypatch.setattr("app.config.settings.ENVIRONMENT", "local")
    setup_logging()

    assert logging.getLogger().getEffectiveLevel() == logging.INFO


def test_prod_logging_level(monkeypatch):
    """Test that prod environment sets level to ERROR."""
    monkeypatch.setattr("app.config.settings.ENVIRONMENT", "prod")
    setup_logging()

    assert logging.getLogger().getEffectiveLevel() == logging.ERROR


def test_dev_db_silencing(monkeypatch):
    """Test that dev mode silences SQLAlchemy logs."""
    monkeypatch.setattr("app.config.settings.ENVIRONMENT", "dev")
    setup_logging()

    db_logger = logging.getLogger("sqlalchemy.engine")
    assert db_logger.getEffectiveLevel() == logging.WARNING


def test_json_formatter_output():
    """Verify JSONFormatter actually produces valid JSON."""
    formatter = JSONFormatter()
    # Create a dummy log record
    record = logging.LogRecord(
        name="test_logger", level=logging.INFO, pathname="test.py",
        lineno=10, msg="Hello Vlad", args=None, exc_info=None
    )

    formatted_msg = formatter.format(record)
    parsed_json = json.loads(formatted_msg)

    assert parsed_json["message"] == "Hello Vlad"
    assert "timestamp" in parsed_json
    assert parsed_json["level"] == "INFO"