"""Tests for UAT traceability matrix (Task 069)."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 — used at runtime

import pytest

from autopilot.uat.spec_index import SpecEntry, SpecIndex
from autopilot.uat.traceability import (
    CoverageReport,
    TraceabilityEntry,
    TraceabilityMatrix,
    TraceabilityStore,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_spec_index(prefix: str = "doc", count: int = 3) -> SpecIndex:
    """Build a small SpecIndex for testing."""
    entries = [
        SpecEntry(
            spec_id=f"{prefix}-R{i:03d}",
            document=prefix,
            section=f"Section {i}",
            requirement_text=f"The system MUST do thing {i}.",
        )
        for i in range(1, count + 1)
    ]
    return SpecIndex(
        entries=entries,
        generated_at="2025-01-01T00:00:00+00:00",
        total_requirements=count,
        testable_count=count,
    )


@pytest.fixture()
def store(tmp_path: Path) -> TraceabilityStore:
    """Return a TraceabilityStore backed by a temp directory."""
    return TraceabilityStore(tmp_path / "traceability.json")


# ---------------------------------------------------------------------------
# TraceabilityMatrix property tests
# ---------------------------------------------------------------------------


class TestTraceabilityMatrix:
    """Tests for the TraceabilityMatrix dataclass properties."""

    def test_empty_matrix_coverage(self) -> None:
        matrix = TraceabilityMatrix()
        assert matrix.total_requirements == 0
        assert matrix.requirements_covered == 0
        assert matrix.requirements_passing == 0
        assert matrix.coverage_percentage == 0.0
        assert matrix.pass_percentage == 0.0

    def test_coverage_calculations(self) -> None:
        entries = [
            TraceabilityEntry(
                spec_id="a-R001",
                spec_document="a",
                spec_section="s1",
                requirement_text="r1",
                uat_status="pass",
            ),
            TraceabilityEntry(
                spec_id="a-R002",
                spec_document="a",
                spec_section="s2",
                requirement_text="r2",
                uat_status="fail",
            ),
            TraceabilityEntry(
                spec_id="a-R003",
                spec_document="a",
                spec_section="s3",
                requirement_text="r3",
                uat_status="untested",
            ),
            TraceabilityEntry(
                spec_id="a-R004",
                spec_document="a",
                spec_section="s4",
                requirement_text="r4",
                uat_status="partial",
            ),
        ]
        matrix = TraceabilityMatrix(entries=entries)

        assert matrix.total_requirements == 4
        assert matrix.requirements_covered == 3  # pass, fail, partial
        assert matrix.requirements_passing == 1  # pass only
        assert matrix.coverage_percentage == 75.0
        assert matrix.pass_percentage == 25.0


# ---------------------------------------------------------------------------
# TraceabilityStore tests
# ---------------------------------------------------------------------------


class TestInitializeMatrix:
    """Tests for TraceabilityStore.initialize_matrix."""

    def test_creates_entries_from_spec_indices(self, store: TraceabilityStore) -> None:
        idx1 = _make_spec_index("alpha", 2)
        idx2 = _make_spec_index("beta", 1)

        matrix = store.initialize_matrix([idx1, idx2])

        assert matrix.total_requirements == 3
        ids = [e.spec_id for e in matrix.entries]
        assert ids == ["alpha-R001", "alpha-R002", "beta-R001"]

    def test_entries_default_to_untested(self, store: TraceabilityStore) -> None:
        idx = _make_spec_index("doc", 2)
        matrix = store.initialize_matrix([idx])

        for entry in matrix.entries:
            assert entry.uat_status == "untested"
            assert entry.uat_score == 0.0

    def test_generated_at_is_set(self, store: TraceabilityStore) -> None:
        idx = _make_spec_index("doc", 1)
        matrix = store.initialize_matrix([idx])
        assert matrix.generated_at != ""


class TestUpdateEntry:
    """Tests for TraceabilityStore.update_entry."""

    def test_updates_status_and_score(self, store: TraceabilityStore) -> None:
        store.initialize_matrix([_make_spec_index("doc", 2)])

        result = store.update_entry(
            "doc-R001",
            uat_status="pass",
            uat_score=95.0,
            test_files=["tests/test_foo.py"],
        )

        assert result is True
        entry = store._matrix.entries[0]
        assert entry.uat_status == "pass"
        assert entry.uat_score == 95.0
        assert entry.test_files == ["tests/test_foo.py"]
        assert entry.last_tested != ""

    def test_returns_false_for_missing_spec_id(self, store: TraceabilityStore) -> None:
        store.initialize_matrix([_make_spec_index("doc", 1)])
        result = store.update_entry("nonexistent-R999", uat_status="pass")
        assert result is False

    def test_updates_implementing_tasks(self, store: TraceabilityStore) -> None:
        store.initialize_matrix([_make_spec_index("doc", 1)])

        store.update_entry("doc-R001", implementing_tasks=["T001", "T002"])

        entry = store._matrix.entries[0]
        assert entry.implementing_tasks == ["T001", "T002"]

    def test_updates_notes(self, store: TraceabilityStore) -> None:
        store.initialize_matrix([_make_spec_index("doc", 1)])

        store.update_entry("doc-R001", notes="needs review")

        entry = store._matrix.entries[0]
        assert entry.notes == "needs review"


class TestGetCoverage:
    """Tests for TraceabilityStore.get_coverage."""

    def test_returns_correct_report(self, store: TraceabilityStore) -> None:
        store.initialize_matrix([_make_spec_index("doc", 4)])
        store.update_entry("doc-R001", uat_status="pass", uat_score=100.0)
        store.update_entry("doc-R002", uat_status="fail", uat_score=20.0)

        report = store.get_coverage()

        assert isinstance(report, CoverageReport)
        assert report.total == 4
        assert report.covered == 2
        assert report.passing == 1
        assert report.coverage_pct == 50.0
        assert report.pass_pct == 25.0

    def test_empty_matrix_report(self, store: TraceabilityStore) -> None:
        store.initialize_matrix([])
        report = store.get_coverage()

        assert report.total == 0
        assert report.covered == 0
        assert report.passing == 0
        assert report.coverage_pct == 0.0
        assert report.pass_pct == 0.0


class TestGetGaps:
    """Tests for TraceabilityStore.get_gaps."""

    def test_returns_untested_entries(self, store: TraceabilityStore) -> None:
        store.initialize_matrix([_make_spec_index("doc", 3)])
        store.update_entry("doc-R001", uat_status="pass", uat_score=100.0)

        gaps = store.get_gaps()

        assert len(gaps) == 2
        gap_ids = [g.spec_id for g in gaps]
        assert "doc-R002" in gap_ids
        assert "doc-R003" in gap_ids

    def test_no_gaps_when_all_tested(self, store: TraceabilityStore) -> None:
        store.initialize_matrix([_make_spec_index("doc", 2)])
        store.update_entry("doc-R001", uat_status="pass", uat_score=100.0)
        store.update_entry("doc-R002", uat_status="fail", uat_score=10.0)

        gaps = store.get_gaps()
        assert gaps == []


class TestSaveLoad:
    """Tests for TraceabilityStore.save and load round-trip."""

    def test_round_trip_preserves_data(self, store: TraceabilityStore) -> None:
        store.initialize_matrix([_make_spec_index("doc", 2)])
        store.update_entry(
            "doc-R001",
            uat_status="pass",
            uat_score=90.0,
            test_files=["tests/test_a.py"],
            implementing_tasks=["T010"],
            notes="all good",
        )

        store.save()

        # Create a new store pointing at the same file
        store2 = TraceabilityStore(store._path)
        loaded = store2.load()

        assert loaded.total_requirements == 2
        e0 = loaded.entries[0]
        assert e0.spec_id == "doc-R001"
        assert e0.uat_status == "pass"
        assert e0.uat_score == 90.0
        assert e0.test_files == ["tests/test_a.py"]
        assert e0.implementing_tasks == ["T010"]
        assert e0.notes == "all good"

        e1 = loaded.entries[1]
        assert e1.uat_status == "untested"

    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        store = TraceabilityStore(tmp_path / "does_not_exist.json")
        matrix = store.load()

        assert matrix.total_requirements == 0
        assert matrix.entries == []

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "traceability.json"
        store = TraceabilityStore(nested)
        store.initialize_matrix([_make_spec_index("doc", 1)])

        store.save()

        assert nested.exists()
