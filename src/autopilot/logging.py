"""Structured logging configuration using structlog.

Provides a ``configure_logging`` function that sets up structlog with
ISO timestamps, log level injection, and JSON rendering for
machine-parsable output.
"""

from __future__ import annotations

import logging

import structlog

_VALID_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging for the CLI.

    Sets up structlog with ISO timestamps, log levels, and JSON output.
    Also configures the stdlib ``logging`` root logger for compatibility.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Raises:
        ValueError: If *level* is not a recognized log level name.
    """
    upper_level = level.upper()
    if upper_level not in _VALID_LEVELS:
        msg = f"Invalid log level: {level!r}. Must be one of {sorted(_VALID_LEVELS)}"
        raise ValueError(msg)
    numeric_level: int = logging.getLevelNamesMapping()[upper_level]
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
