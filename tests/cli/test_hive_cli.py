"""Tests for hive CLI task ID parser (Task 011)."""

from __future__ import annotations

from autopilot.cli.hive import _parse_task_ids


class TestParseTaskIds:
    """Unit tests for _parse_task_ids covering all format variations."""

    def test_range_format(self) -> None:
        assert _parse_task_ids("001-005") == ["001", "002", "003", "004", "005"]

    def test_comma_format(self) -> None:
        assert _parse_task_ids("001,003,005") == ["001", "003", "005"]

    def test_mixed_format(self) -> None:
        assert _parse_task_ids("001-003,005,007-008") == [
            "001",
            "002",
            "003",
            "005",
            "007",
            "008",
        ]

    def test_single_id(self) -> None:
        assert _parse_task_ids("042") == ["042"]

    def test_zero_padded(self) -> None:
        assert _parse_task_ids("1-3") == ["001", "002", "003"]

    def test_empty_input(self) -> None:
        assert _parse_task_ids("") == []

    def test_overlapping_ranges_deduplicated(self) -> None:
        result = _parse_task_ids("001-003,002-004")
        assert result == ["001", "002", "003", "004"]

    def test_single_digit_padded(self) -> None:
        assert _parse_task_ids("5") == ["005"]
