"""
Logging configuration for the A/B Testing Platform.
"""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    # Configure logging for the entire application.

    # Define a clear, parseable log format
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Log to stdout so Docker and CloudWatch can capture it
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    WHY __name__: Automatically uses the module's full path as the logger name,
    so logs show exactly which file generated them.
    """
    return logging.getLogger(name)