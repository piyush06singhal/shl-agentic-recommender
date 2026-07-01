"""Centralized logging configuration module supporting console, file rotating, and JSON-styled logs."""

import json
import logging
import os
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from app.configs.settings import get_settings


class JSONFormatter(logging.Formatter):
    """Structured JSON formatter to format logs as key-value JSON records."""

    def format(self, record: logging.LogRecord) -> str:
        """Formats a LogRecord as a JSON string."""
        log_payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
        }

        # Inject extra parameters (like correlation IDs) if available in record attributes
        if hasattr(record, "correlation_id"):
            log_payload["correlation_id"] = record.correlation_id

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


def setup_logging() -> None:
    """Configures system-wide logging with Console and Rotating File outputs.

    Log settings are retrieved dynamically from the global configurations instance.
    """
    settings = get_settings()
    log_level_str = settings.log_level.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Prevent duplicating logs if already configured
    if root_logger.handlers:
        return

    # 1. Console stream handler with structured formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Configure JSON styled logging by default, fallback to structured text for local dev checks
    if os.getenv("LOG_FORMAT", "").upper() == "JSON":
        console_formatter: logging.Formatter = JSONFormatter()
    else:
        console_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s"
        )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 2. Rotating File handler setup
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "app.log")

    try:
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB limit per log file
            backupCount=5,              # Keep up to 5 historical rotating backup files
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        # Fallback console warn if logging file creation fails (e.g., directory permission errors)
        sys.stderr.write(f"Warning: Failed to initialize file logger output: {e}\n")
