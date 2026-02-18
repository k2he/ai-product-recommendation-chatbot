"""Logging configuration."""

import logging
import sys
from pythonjsonlogger import jsonlogger

from app.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Configure application logging."""
    # Get log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Create formatter
    if settings.log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Set levels for third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger.info(f"Logging configured: level={settings.log_level}, format={settings.log_format}")
