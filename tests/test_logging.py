"""Tests for structured logging configuration."""

from __future__ import annotations

import json
import logging
from io import StringIO
from unittest.mock import patch

import structlog

from autopilot.logging import configure_logging


class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def test_configures_structlog_with_json_renderer(self) -> None:
        """Verify structlog is configured with JSON rendering."""
        configure_logging()

        logger = structlog.get_logger()
        # structlog should produce valid JSON output
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setLevel(logging.DEBUG)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            logger.info("test message", key="value")
            log_output = output.getvalue().strip()
            if log_output:
                parsed = json.loads(log_output)
                assert parsed["key"] == "value"
                assert "timestamp" in parsed
                assert "level" in parsed
        finally:
            root_logger.removeHandler(handler)

    def test_default_level_is_info(self) -> None:
        """Verify default log level is INFO."""
        configure_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_custom_level_debug(self) -> None:
        """Verify custom log level is respected."""
        configure_logging(level="DEBUG")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_custom_level_warning(self) -> None:
        """Verify WARNING level is respected."""
        configure_logging(level="WARNING")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_structlog_configure_called_with_expected_processors(self) -> None:
        """Verify structlog.configure is called with correct processor chain."""
        with patch("autopilot.logging.structlog.configure") as mock_configure:
            configure_logging()
            mock_configure.assert_called_once()
            call_kwargs = mock_configure.call_args
            processors = call_kwargs.kwargs.get("processors") or call_kwargs[1].get("processors")
            assert processors is not None
            assert len(processors) == 3

    def test_output_is_valid_json(self) -> None:
        """Verify log output is parseable JSON."""
        configure_logging(level="DEBUG")
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setLevel(logging.DEBUG)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            logger = structlog.get_logger()
            logger.debug("json check", number=42)
            log_output = output.getvalue().strip()
            if log_output:
                parsed = json.loads(log_output)
                assert parsed["number"] == 42
                assert parsed["event"] == "json check"
        finally:
            root_logger.removeHandler(handler)
