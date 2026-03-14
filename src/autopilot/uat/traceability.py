"""UAT traceability matrix (Task 069, UAT Discovery).

Maps specification requirements to implementing tasks and UAT status,
with JSON persistence, CRUD operations, and gap detection.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 — used at runtime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from autopilot.uat.spec_index import SpecIndex

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

_VALID_UAT_STATUSES = frozenset({"untested", "pass", "fail", "partial"})


@dataclass
class TraceabilityEntry:
    """A single requirement mapped to its implementation and UAT status."""

    spec_id: str
    spec_document: str
    spec_section: str
    requirement_text: str
    implementing_tasks: list[str] = field(default_factory=list)
    uat_status: str = "untested"
    uat_score: float = 0.0
    last_tested: str = ""
    test_files: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class TraceabilityMatrix:
    """Full traceability matrix containing all requirement entries."""

    entries: list[TraceabilityEntry] = field(default_factory=list)
    generated_at: str = ""

    @property
    def total_requirements(self) -> int:
        """Total number of requirements in the matrix."""
        return len(self.entries)

    @property
    def requirements_covered(self) -> int:
        """Number of requirements with a non-untested status."""
        return sum(1 for e in self.entries if e.uat_status != "untested")

    @property
    def requirements_passing(self) -> int:
        """Number of requirements with passing status."""
        return sum(1 for e in self.entries if e.uat_status == "pass")

    @property
    def coverage_percentage(self) -> float:
        """Percentage of requirements that have been tested."""
        if not self.entries:
            return 0.0
        return (self.requirements_covered / self.total_requirements) * 100

    @property
    def pass_percentage(self) -> float:
        """Percentage of requirements that are passing."""
        if not self.entries:
            return 0.0
        return (self.requirements_passing / self.total_requirements) * 100


@dataclass(frozen=True)
class CoverageReport:
    """Snapshot of coverage statistics."""

    total: int
    covered: int
    passing: int
    coverage_pct: float
    pass_pct: float


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class TraceabilityStore:
    """Persists and manages the traceability matrix on disk."""

    def __init__(self, storage_path: Path) -> None:
        self._path = storage_path
        self._matrix = TraceabilityMatrix()

    # -- public API ---------------------------------------------------------

    def initialize_matrix(self, spec_indices: list[SpecIndex]) -> TraceabilityMatrix:
        """Create a fresh matrix from one or more :class:`SpecIndex` objects."""
        entries: list[TraceabilityEntry] = []
        for index in spec_indices:
            for spec_entry in index.entries:
                entries.append(
                    TraceabilityEntry(
                        spec_id=spec_entry.spec_id,
                        spec_document=spec_entry.document,
                        spec_section=spec_entry.section,
                        requirement_text=spec_entry.requirement_text,
                    )
                )

        self._matrix = TraceabilityMatrix(
            entries=entries,
            generated_at=_now_iso(),
        )
        logger.info(
            "traceability_matrix_initialized",
            total_entries=len(entries),
        )
        return self._matrix

    def update_entry(
        self,
        spec_id: str,
        *,
        uat_status: str = "",
        uat_score: float = 0.0,
        test_files: list[str] | None = None,
        implementing_tasks: list[str] | None = None,
        notes: str = "",
    ) -> bool:
        """Update an existing entry by *spec_id*.

        Returns ``True`` if the entry was found and updated, ``False`` otherwise.
        """
        for entry in self._matrix.entries:
            if entry.spec_id == spec_id:
                if uat_status:
                    if uat_status not in _VALID_UAT_STATUSES:
                        logger.warning(
                            "invalid_uat_status",
                            spec_id=spec_id,
                            status=uat_status,
                        )
                        return False
                    entry.uat_status = uat_status
                if uat_score:
                    entry.uat_score = uat_score
                if test_files is not None:
                    entry.test_files = test_files
                if implementing_tasks is not None:
                    entry.implementing_tasks = implementing_tasks
                if notes:
                    entry.notes = notes
                if uat_status in {"pass", "fail", "partial"}:
                    entry.last_tested = _now_iso()
                logger.info("traceability_entry_updated", spec_id=spec_id)
                return True
        logger.warning("traceability_entry_not_found", spec_id=spec_id)
        return False

    def get_coverage(self) -> CoverageReport:
        """Return a :class:`CoverageReport` for the current matrix."""
        m = self._matrix
        return CoverageReport(
            total=m.total_requirements,
            covered=m.requirements_covered,
            passing=m.requirements_passing,
            coverage_pct=m.coverage_percentage,
            pass_pct=m.pass_percentage,
        )

    def get_gaps(self) -> list[TraceabilityEntry]:
        """Return entries that have not yet been tested."""
        return [e for e in self._matrix.entries if e.uat_status == "untested"]

    def save(self) -> None:
        """Persist the current matrix to *storage_path* as JSON."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self._matrix)
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("traceability_matrix_saved", path=str(self._path))

    def load(self) -> TraceabilityMatrix:
        """Load the matrix from *storage_path*.

        Returns an empty matrix if the file does not exist.
        """
        if not self._path.exists():
            logger.info("traceability_file_not_found", path=str(self._path))
            self._matrix = TraceabilityMatrix()
            return self._matrix

        raw = json.loads(self._path.read_text(encoding="utf-8"))
        entries = [TraceabilityEntry(**e) for e in raw.get("entries", [])]
        self._matrix = TraceabilityMatrix(
            entries=entries,
            generated_at=raw.get("generated_at", ""),
        )
        logger.info(
            "traceability_matrix_loaded",
            total_entries=len(entries),
        )
        return self._matrix


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(UTC).isoformat()
