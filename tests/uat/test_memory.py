"""Tests for UAT memory integration (Task 089)."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 — used at runtime
from unittest.mock import MagicMock

import pytest

from autopilot.uat.memory import (
    UATMemory,
    UATResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent real subprocess calls to npx/claude-flow in all tests."""
    monkeypatch.setattr(
        "autopilot.uat.memory.subprocess.run",
        lambda *_a, **_kw: type("FakeResult", (), {"returncode": 1, "stdout": "", "stderr": ""})(),
    )


@pytest.fixture()
def memory(tmp_path: Path) -> UATMemory:
    """Return a UATMemory backed by a temp directory."""
    return UATMemory(storage_dir=tmp_path)


@pytest.fixture()
def memory_no_storage() -> UATMemory:
    """Return a UATMemory with no local storage."""
    return UATMemory()


def _make_result(
    task_id: str = "T001",
    test_type: str = "acceptance",
    passed: int = 5,
    failed: int = 0,
    skipped: int = 0,
    failures: list[str] | None = None,
) -> UATResult:
    return UATResult(
        task_id=task_id,
        test_type=test_type,
        passed=passed,
        failed=failed,
        skipped=skipped,
        failures=failures or [],
    )


# ---------------------------------------------------------------------------
# store_pattern / search_patterns
# ---------------------------------------------------------------------------


class TestStoreAndSearchPatterns:
    """Tests for pattern storage and local-fallback search."""

    def test_store_pattern_adds_to_internal_dict(self, memory: UATMemory) -> None:
        memory.store_pattern("login_flow", "acceptance", "template body", tags=["auth"])
        results = memory.search_patterns("login")
        assert len(results) == 1
        assert results[0].name == "login_flow"
        assert results[0].test_type == "acceptance"
        assert results[0].tags == ["auth"]

    def test_search_by_type(self, memory: UATMemory) -> None:
        memory.store_pattern("p1", "behavioral", "tmpl1")
        memory.store_pattern("p2", "compliance", "tmpl2")
        results = memory.search_patterns("behavioral")
        assert len(results) == 1
        assert results[0].name == "p1"

    def test_search_by_tag(self, memory: UATMemory) -> None:
        memory.store_pattern("p1", "acceptance", "t", tags=["security", "auth"])
        results = memory.search_patterns("security")
        assert len(results) == 1

    def test_search_no_match_returns_empty(self, memory: UATMemory) -> None:
        memory.store_pattern("p1", "acceptance", "t")
        assert memory.search_patterns("nonexistent") == []

    def test_search_respects_limit(self, memory: UATMemory) -> None:
        for i in range(5):
            memory.store_pattern(f"auth_pattern_{i}", "acceptance", "t")
        results = memory.search_patterns("auth", limit=3)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# record_result / failure tracking
# ---------------------------------------------------------------------------


class TestRecordResult:
    """Tests for result recording and failure count tracking."""

    def test_record_result_stores_result(self, memory: UATMemory) -> None:
        result = _make_result(passed=3, failed=1, failures=["test_x failed"])
        memory.record_result("T001", result)
        # Verify internal state
        assert len(memory._results) == 1
        assert memory._results[0].task_id == "T001"

    def test_failure_counts_accumulate(self, memory: UATMemory) -> None:
        r1 = _make_result(failed=1, failures=["assertion error in login"])
        r2 = _make_result(failed=1, failures=["assertion error in login"])
        memory.record_result("T001", r1)
        memory.record_result("T002", r2)
        patterns = memory.get_failure_patterns(min_occurrences=2)
        assert len(patterns) == 1
        assert patterns[0].occurrence_count == 2


# ---------------------------------------------------------------------------
# get_failure_patterns
# ---------------------------------------------------------------------------


class TestGetFailurePatterns:
    """Tests for recurring failure pattern detection."""

    def test_below_threshold_returns_empty(self, memory: UATMemory) -> None:
        result = _make_result(failed=1, failures=["flaky test"])
        memory.record_result("T001", result)
        assert memory.get_failure_patterns(min_occurrences=2) == []

    def test_patterns_sorted_by_count(self, memory: UATMemory) -> None:
        for _ in range(3):
            memory.record_result(
                "T001",
                _make_result(failed=2, failures=["err_a", "err_b"]),
            )
        # Record err_b one more time to make it higher
        memory.record_result(
            "T002",
            _make_result(failed=1, failures=["err_b"]),
        )
        patterns = memory.get_failure_patterns(min_occurrences=2)
        assert len(patterns) == 2
        assert patterns[0].occurrence_count >= patterns[1].occurrence_count

    def test_failure_pattern_has_category(self, memory: UATMemory) -> None:
        for _ in range(2):
            memory.record_result(
                "T001",
                _make_result(test_type="compliance", failed=1, failures=["spec mismatch"]),
            )
        patterns = memory.get_failure_patterns(min_occurrences=2)
        assert len(patterns) == 1
        assert patterns[0].category == "compliance"


# ---------------------------------------------------------------------------
# detect_false_positives
# ---------------------------------------------------------------------------


class TestDetectFalsePositives:
    """Tests for false positive detection across runs."""

    def test_fewer_than_three_results_returns_empty(self, memory: UATMemory) -> None:
        memory.record_result("T1", _make_result(failed=1, failures=["x"]))
        memory.record_result("T2", _make_result(failed=1, failures=["x"]))
        assert memory.detect_false_positives() == []

    def test_consistent_failure_flagged(self, memory: UATMemory) -> None:
        for i in range(4):
            memory.record_result(
                f"T{i}",
                _make_result(failed=1, failures=["always_fails"]),
            )
        flagged = memory.detect_false_positives()
        assert "always_fails" in flagged

    def test_intermittent_failure_not_flagged(self, memory: UATMemory) -> None:
        memory.record_result("T1", _make_result(failed=1, failures=["sometimes"]))
        memory.record_result("T2", _make_result(failed=0, failures=[]))
        memory.record_result("T3", _make_result(failed=1, failures=["sometimes"]))
        flagged = memory.detect_false_positives()
        assert "sometimes" not in flagged


# ---------------------------------------------------------------------------
# get_pruning_candidates
# ---------------------------------------------------------------------------


class TestGetPruningCandidates:
    """Tests for identifying always-passing test types."""

    def test_insufficient_sprints_returns_empty(self, memory: UATMemory) -> None:
        memory.record_result("T1", _make_result())
        assert memory.get_pruning_candidates(min_sprints=3) == []

    def test_always_passing_type_flagged(self, memory: UATMemory) -> None:
        for i in range(4):
            memory.record_result(
                f"T{i}",
                _make_result(test_type="ux", passed=5, failed=0),
            )
        candidates = memory.get_pruning_candidates(min_sprints=3)
        assert "ux" in candidates

    def test_type_with_failures_not_flagged(self, memory: UATMemory) -> None:
        memory.record_result("T1", _make_result(test_type="compliance", passed=5, failed=0))
        memory.record_result("T2", _make_result(test_type="compliance", passed=4, failed=1))
        memory.record_result("T3", _make_result(test_type="compliance", passed=5, failed=0))
        candidates = memory.get_pruning_candidates(min_sprints=3)
        assert "compliance" not in candidates


# ---------------------------------------------------------------------------
# Local JSON persistence
# ---------------------------------------------------------------------------


class TestLocalPersistence:
    """Tests for JSON save and load round-trip."""

    def test_save_and_load_patterns(self, tmp_path: Path) -> None:
        mem1 = UATMemory(storage_dir=tmp_path)
        mem1.store_pattern("p1", "acceptance", "tmpl", tags=["auth"])
        mem1.record_result("T1", _make_result(failed=1, failures=["err"]))

        # Load into a fresh instance
        mem2 = UATMemory(storage_dir=tmp_path)
        assert "p1" in mem2._patterns
        assert mem2._patterns["p1"].tags == ["auth"]
        assert len(mem2._results) == 1
        assert mem2._failure_counts.get("acceptance:err") == 1

    def test_load_nonexistent_file_succeeds(self, tmp_path: Path) -> None:
        mem = UATMemory(storage_dir=tmp_path / "nonexistent")
        assert mem._patterns == {}
        assert mem._results == []

    def test_corrupt_json_handles_gracefully(self, tmp_path: Path) -> None:
        (tmp_path / "uat_memory.json").write_text("{invalid json")
        mem = UATMemory(storage_dir=tmp_path)
        assert mem._patterns == {}


# ---------------------------------------------------------------------------
# Empty state defaults
# ---------------------------------------------------------------------------


class TestEmptyState:
    """Tests for sensible defaults when no data exists."""

    def test_search_on_empty_returns_empty(self, memory_no_storage: UATMemory) -> None:
        assert memory_no_storage.search_patterns("anything") == []

    def test_failure_patterns_on_empty(self, memory_no_storage: UATMemory) -> None:
        assert memory_no_storage.get_failure_patterns() == []

    def test_false_positives_on_empty(self, memory_no_storage: UATMemory) -> None:
        assert memory_no_storage.detect_false_positives() == []

    def test_pruning_on_empty(self, memory_no_storage: UATMemory) -> None:
        assert memory_no_storage.get_pruning_candidates() == []


# ---------------------------------------------------------------------------
# Subprocess mocking (claude-flow unavailable)
# ---------------------------------------------------------------------------


class TestSubprocessFallback:
    """Tests that claude-flow subprocess failures fall back gracefully."""

    def test_store_falls_back_when_npx_missing(
        self, memory: UATMemory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "autopilot.uat.memory.subprocess.run",
            MagicMock(side_effect=FileNotFoundError),
        )
        memory.store_pattern("p1", "acceptance", "template")
        # Pattern still stored locally
        assert "p1" in memory._patterns

    def test_search_falls_back_when_npx_missing(
        self, memory: UATMemory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        memory.store_pattern("p1", "acceptance", "template")
        monkeypatch.setattr(
            "autopilot.uat.memory.subprocess.run",
            MagicMock(side_effect=FileNotFoundError),
        )
        results = memory.search_patterns("p1")
        assert len(results) == 1

    def test_store_falls_back_on_timeout(
        self, memory: UATMemory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from subprocess import TimeoutExpired

        monkeypatch.setattr(
            "autopilot.uat.memory.subprocess.run",
            MagicMock(side_effect=TimeoutExpired("npx", 10)),
        )
        memory.store_pattern("p1", "acceptance", "template")
        assert "p1" in memory._patterns
