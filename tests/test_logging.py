"""Tests for structured logging configuration."""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

import pytest
import structlog

from autopilot.logging import configure_logging


class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def test_configures_structlog_with_json_renderer(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify structlog is configured with JSON rendering."""
        configure_logging()
        logger = structlog.get_logger()
        logger.info("test message", key="value")

        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip())
        assert parsed["key"] == "value"
        assert "timestamp" in parsed
        assert "level" in parsed

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

    def test_output_is_valid_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify log output is parseable JSON."""
        configure_logging(level="DEBUG")
        logger = structlog.get_logger()
        logger.debug("json check", number=42)

        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip())
        assert parsed["number"] == 42
        assert parsed["event"] == "json check"

    def test_invalid_level_raises_value_error(self) -> None:
        """Verify invalid log level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid log level"):
            configure_logging(level="TYPO")

    def test_invalid_level_misspelling(self) -> None:
        """Verify misspelled level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid log level"):
            configure_logging(level="DEBU")
