"""UAT test pattern learning with claude-flow memory (Task 089).

Stores and retrieves test patterns, tracks failure patterns,
and detects false positives using claude-flow memory subprocess.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 — used at runtime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Namespaces for organizing patterns in memory
_NS_PATTERNS = "uat-patterns"
_NS_RESULTS = "uat-results"


@dataclass(frozen=True)
class TestPattern:
    """A reusable test pattern template."""

    name: str
    test_type: str  # acceptance, behavioral, compliance, ux
    template: str
    tags: list[str] = field(default_factory=list[str])
    usage_count: int = 0
    last_used: str = ""


@dataclass(frozen=True)
class FailurePattern:
    """A recurring failure pattern across test runs."""

    category: str
    spec_reference: str
    occurrence_count: int
    first_seen: str
    last_seen: str
    description: str = ""


@dataclass(frozen=True)
class UATResult:
    """Result of a UAT run for memory storage."""

    task_id: str
    test_type: str
    passed: int
    failed: int
    skipped: int
    failures: list[str] = field(default_factory=list[str])
    recorded_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class UATMemory:
    """UAT test pattern learning using claude-flow memory.

    Stores test patterns and results via subprocess calls to
    ``npx claude-flow memory store/search``. Falls back to local
    JSON storage when claude-flow is not available.
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        self._storage_dir = storage_dir
        self._patterns: dict[str, TestPattern] = {}
        self._results: list[UATResult] = []
        self._failure_counts: dict[str, int] = {}
        if storage_dir:
            storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_local()

    def store_pattern(
        self,
        pattern_name: str,
        test_type: str,
        template: str,
        tags: list[str] | None = None,
    ) -> None:
        """Store a test pattern for future reuse."""
        pattern = TestPattern(
            name=pattern_name,
            test_type=test_type,
            template=template,
            tags=tags or [],
            last_used=datetime.now(UTC).isoformat(),
        )
        self._patterns[pattern_name] = pattern

        # Try claude-flow, fall back to local
        self._store_to_memory(
            key=f"pattern-{pattern_name}",
            value=json.dumps(asdict(pattern)),
            namespace=_NS_PATTERNS,
        )
        self._save_local()
        logger.info("pattern_stored", name=pattern_name, type=test_type)

    def search_patterns(self, query: str, limit: int = 10) -> list[TestPattern]:
        """Search for test patterns matching a query."""
        # Try claude-flow search first
        results = self._search_memory(query, namespace=_NS_PATTERNS, limit=limit)
        if results:
            return [self._parse_pattern(r) for r in results if r]

        # Fall back to local search
        matching: list[TestPattern] = []
        query_lower = query.lower()
        for pattern in self._patterns.values():
            if (
                query_lower in pattern.name.lower()
                or query_lower in pattern.test_type.lower()
                or any(query_lower in t.lower() for t in pattern.tags)
            ):
                matching.append(pattern)
                if len(matching) >= limit:
                    break
        return matching

    def record_result(self, task_id: str, result: UATResult) -> None:
        """Store a UAT run result and update failure tracking."""
        self._results.append(result)

        # Track failure patterns
        for failure_desc in result.failures:
            key = f"{result.test_type}:{failure_desc[:100]}"
            self._failure_counts[key] = self._failure_counts.get(key, 0) + 1

        self._store_to_memory(
            key=f"result-{task_id}-{result.recorded_at}",
            value=json.dumps(asdict(result)),
            namespace=_NS_RESULTS,
        )
        self._save_local()
        logger.info(
            "result_recorded",
            task_id=task_id,
            passed=result.passed,
            failed=result.failed,
        )

    def get_failure_patterns(self, min_occurrences: int = 2) -> list[FailurePattern]:
        """Get recurring failure patterns (spec mismatches)."""
        patterns: list[FailurePattern] = []
        now = datetime.now(UTC).isoformat()

        for key, count in self._failure_counts.items():
            if count >= min_occurrences:
                parts = key.split(":", 1)
                category = parts[0] if len(parts) > 1 else "unknown"
                description = parts[1] if len(parts) > 1 else key
                patterns.append(
                    FailurePattern(
                        category=category,
                        spec_reference="",
                        occurrence_count=count,
                        first_seen=now,
                        last_seen=now,
                        description=description,
                    )
                )

        return sorted(patterns, key=lambda p: p.occurrence_count, reverse=True)

    def detect_false_positives(
        self,
        recent_results: list[UATResult] | None = None,
    ) -> list[str]:
        """Identify tests that consistently fail -- possible false positives.

        A test is flagged if it fails in every run over 3+ results.
        """
        results = recent_results or self._results
        if len(results) < 3:
            return []

        # Track failure frequency per test description
        failure_freq: dict[str, int] = {}
        total_runs = len(results)

        for result in results:
            for failure in result.failures:
                failure_freq[failure] = failure_freq.get(failure, 0) + 1

        # Flag tests that fail in every run
        return [desc for desc, count in failure_freq.items() if count >= total_runs]

    def get_pruning_candidates(self, min_sprints: int = 3) -> list[str]:
        """Identify tests that pass 100% for N+ sprints -- removal candidates."""
        if len(self._results) < min_sprints:
            return []

        # Find patterns where all recent results have 0 failures
        recent = self._results[-min_sprints:]
        all_passing_types: set[str] = set()

        for result in recent:
            if result.failed == 0 and result.passed > 0:
                all_passing_types.add(result.test_type)

        # Only flag types that passed in ALL recent runs
        for result in recent:
            if result.test_type in all_passing_types and result.failed > 0:
                all_passing_types.discard(result.test_type)

        return sorted(all_passing_types)

    # -- Private helpers ----------------------------------------------------

    def _store_to_memory(self, key: str, value: str, namespace: str) -> bool:
        """Store to claude-flow memory via subprocess (best-effort)."""
        try:
            subprocess.run(
                [
                    "npx",
                    "claude-flow",
                    "memory",
                    "store",
                    "--key",
                    key,
                    "--value",
                    value,
                    "--namespace",
                    namespace,
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            logger.debug("claude_flow_memory_unavailable", key=key)
            return False
        else:
            return True

    def _search_memory(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
    ) -> list[str]:
        """Search claude-flow memory (best-effort)."""
        try:
            proc = subprocess.run(
                [
                    "npx",
                    "claude-flow",
                    "memory",
                    "search",
                    "--query",
                    query,
                    "--namespace",
                    namespace,
                    "--limit",
                    str(limit),
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip().split("\n")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            logger.debug("claude_flow_search_unavailable", query=query)
        return []

    def _parse_pattern(self, raw: str) -> TestPattern:
        """Parse a pattern from memory search result."""
        try:
            data: dict[str, Any] = json.loads(raw)
            return TestPattern(**data)
        except (json.JSONDecodeError, TypeError):
            return TestPattern(name=raw, test_type="unknown", template="")

    def _save_local(self) -> None:
        """Persist to local JSON storage."""
        if not self._storage_dir:
            return

        data = {
            "patterns": {k: asdict(v) for k, v in self._patterns.items()},
            "results": [asdict(r) for r in self._results[-100:]],  # Keep last 100
            "failure_counts": self._failure_counts,
        }
        path = self._storage_dir / "uat_memory.json"
        path.write_text(json.dumps(data, indent=2))

    def _load_local(self) -> None:
        """Load from local JSON storage."""
        if not self._storage_dir:
            return
        path = self._storage_dir / "uat_memory.json"
        if not path.exists():
            return
        try:
            data: dict[str, Any] = json.loads(path.read_text())
            for name, pdata in data.get("patterns", {}).items():
                self._patterns[name] = TestPattern(**pdata)
            for rdata in data.get("results", []):
                self._results.append(UATResult(**rdata))
            self._failure_counts = data.get("failure_counts", {})
        except (json.JSONDecodeError, TypeError):
            logger.warning("uat_memory_load_failed")
