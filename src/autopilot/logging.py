"""Structured logging configuration using structlog.

Provides a ``configure_logging`` function that sets up structlog with
ISO timestamps, log level injection, and JSON rendering for
machine-parsable output.
"""

from __future__ import annotations

import logging

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging for the CLI.

    Sets up structlog with ISO timestamps, log levels, and JSON output.
    Also configures the stdlib ``logging`` root logger for compatibility.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    numeric_level: int = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format="%(message)s", force=True)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
