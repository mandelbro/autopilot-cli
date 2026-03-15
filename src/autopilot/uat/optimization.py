"""UAT self-optimization with hooks intelligence (Task 090).

Analyzes test effectiveness, recommends pruning, detects spec drift,
supports custom test templates, and exports UAT results.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 — used at runtime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CategoryEffectiveness:
    """Effectiveness metrics for a test category."""

    category: str
    total_tests: int
    bugs_caught: int  # tests that found real issues
    false_positives: int
    effectiveness_rate: float  # bugs_caught / total_tests
    recommendation: str  # "keep", "expand", "reduce", "remove"


@dataclass(frozen=True)
class EffectivenessReport:
    """Overall UAT effectiveness analysis."""

    total_categories: int
    total_tests: int
    total_bugs_caught: int
    overall_effectiveness: float
    categories: list[CategoryEffectiveness] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True)
class SpecDriftItem:
    """A spec section that has drifted from its last indexed state."""

    spec_path: str
    section: str
    drift_type: str  # "modified", "added", "removed"
    last_indexed: str


@dataclass(frozen=True)
class TrendPoint:
    """A single point in a UAT historical trend."""

    run_date: str
    pass_rate: float
    coverage_score: float
    total_tests: int


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------


class UATOptimizer:
    """UAT self-optimization engine with effectiveness analysis.

    Analyzes which test categories catch real bugs, recommends pruning,
    detects spec drift, and provides historical trend analysis.
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        self._storage_dir = storage_dir
        self._run_history: list[dict[str, Any]] = []
        self._spec_checksums: dict[str, str] = {}
        if storage_dir:
            storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    # -- effectiveness analysis --------------------------------------------

    def analyze_effectiveness(
        self,
        results: list[dict[str, Any]] | None = None,
    ) -> EffectivenessReport:
        """Analyze which test categories are most effective at catching bugs.

        Args:
            results: List of test run results with category breakdowns.
                     If None, uses stored run history.
        """
        runs = results or self._run_history
        if not runs:
            return EffectivenessReport(
                total_categories=0,
                total_tests=0,
                total_bugs_caught=0,
                overall_effectiveness=0.0,
            )

        # Aggregate by category
        category_stats: dict[str, dict[str, int]] = {}
        for run in runs:
            for cat_name, cat_data in run.get("categories", {}).items():
                if cat_name not in category_stats:
                    category_stats[cat_name] = {"total": 0, "bugs": 0, "false_pos": 0}
                category_stats[cat_name]["total"] += cat_data.get("total", 0)
                category_stats[cat_name]["bugs"] += cat_data.get("bugs_caught", 0)
                category_stats[cat_name]["false_pos"] += cat_data.get("false_positives", 0)

        categories: list[CategoryEffectiveness] = []
        total_tests = 0
        total_bugs = 0

        for name, stats in sorted(category_stats.items()):
            total = stats["total"]
            bugs = stats["bugs"]
            false_pos = stats["false_pos"]
            rate = bugs / max(total, 1)

            # Recommendation logic
            if rate >= 0.3:
                rec = "expand"
            elif rate >= 0.1:
                rec = "keep"
            elif total > 0 and bugs == 0 and false_pos > total * 0.5:
                rec = "remove"
            else:
                rec = "reduce"

            categories.append(
                CategoryEffectiveness(
                    category=name,
                    total_tests=total,
                    bugs_caught=bugs,
                    false_positives=false_pos,
                    effectiveness_rate=round(rate, 3),
                    recommendation=rec,
                )
            )
            total_tests += total
            total_bugs += bugs

        return EffectivenessReport(
            total_categories=len(categories),
            total_tests=total_tests,
            total_bugs_caught=total_bugs,
            overall_effectiveness=round(total_bugs / max(total_tests, 1), 3),
            categories=categories,
        )

    def recommend_pruning(self) -> list[str]:
        """Identify tests that provide no value (always pass, no bugs caught)."""
        report = self.analyze_effectiveness()
        return [
            cat.category
            for cat in report.categories
            if cat.recommendation in ("remove", "reduce") and cat.bugs_caught == 0
        ]

    def suggest_focus_areas(self) -> list[str]:
        """Identify spec sections with most drift or failures."""
        report = self.analyze_effectiveness()
        return [cat.category for cat in report.categories if cat.recommendation == "expand"]

    # -- spec drift --------------------------------------------------------

    def refresh_spec_index(self, spec_paths: list[Path]) -> list[SpecDriftItem]:
        """Detect spec changes by comparing checksums."""
        drifts: list[SpecDriftItem] = []
        now = datetime.now(UTC).isoformat()

        for path in spec_paths:
            path_str = str(path)

            if not path.exists():
                if path_str in self._spec_checksums:
                    drifts.append(
                        SpecDriftItem(
                            spec_path=path_str,
                            section="",
                            drift_type="removed",
                            last_indexed=now,
                        )
                    )
                    del self._spec_checksums[path_str]
                continue

            content = path.read_text()
            checksum = hashlib.sha256(content.encode()).hexdigest()[:16]

            if path_str not in self._spec_checksums:
                drifts.append(
                    SpecDriftItem(
                        spec_path=path_str,
                        section="",
                        drift_type="added",
                        last_indexed=now,
                    )
                )
            elif self._spec_checksums[path_str] != checksum:
                drifts.append(
                    SpecDriftItem(
                        spec_path=path_str,
                        section="",
                        drift_type="modified",
                        last_indexed=now,
                    )
                )

            self._spec_checksums[path_str] = checksum

        self._save_state()
        return drifts

    # -- run history & trends ----------------------------------------------

    def record_run(self, run_data: dict[str, Any]) -> None:
        """Record a UAT run for historical tracking."""
        run_data.setdefault("timestamp", datetime.now(UTC).isoformat())
        self._run_history.append(run_data)
        self._save_state()

    def get_trends(self, limit: int = 20) -> list[TrendPoint]:
        """Get historical UAT pass rate and coverage trends."""
        trends: list[TrendPoint] = []
        for run in self._run_history[-limit:]:
            total = run.get("total_tests", 0)
            passed = run.get("passed", 0)
            pass_rate = passed / max(total, 1)
            coverage = run.get("coverage_score", 0.0)
            trends.append(
                TrendPoint(
                    run_date=run.get("timestamp", ""),
                    pass_rate=round(pass_rate, 3),
                    coverage_score=round(coverage, 3),
                    total_tests=total,
                )
            )
        return trends

    # -- export ------------------------------------------------------------

    def export_results(
        self,
        fmt: str = "json",
        limit: int = 50,
    ) -> str:
        """Export UAT results in JSON, CSV, or HTML format."""
        runs = self._run_history[-limit:]

        if fmt == "json":
            return json.dumps(runs, indent=2)

        if fmt == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["timestamp", "total_tests", "passed", "failed", "pass_rate"])
            for run in runs:
                total = run.get("total_tests", 0)
                passed = run.get("passed", 0)
                failed = run.get("failed", 0)
                rate = passed / max(total, 1)
                writer.writerow(
                    [
                        run.get("timestamp", ""),
                        total,
                        passed,
                        failed,
                        f"{rate:.3f}",
                    ]
                )
            return output.getvalue()

        if fmt == "html":
            lines = [
                "<table>",
                "<tr><th>Date</th><th>Tests</th><th>Passed</th><th>Failed</th><th>Rate</th></tr>",
            ]
            for run in runs:
                total = run.get("total_tests", 0)
                passed = run.get("passed", 0)
                failed = run.get("failed", 0)
                rate = passed / max(total, 1)
                lines.append(
                    f"<tr><td>{run.get('timestamp', '')}</td><td>{total}</td>"
                    f"<td>{passed}</td><td>{failed}</td><td>{rate:.1%}</td></tr>"
                )
            lines.append("</table>")
            return "\n".join(lines)

        msg = f"Unsupported format: {fmt}"
        raise ValueError(msg)

    # -- templates ---------------------------------------------------------

    def load_custom_templates(self, template_dir: Path) -> dict[str, str]:
        """Load user-defined Jinja2 test templates from a directory."""
        templates: dict[str, str] = {}
        if not template_dir.is_dir():
            return templates

        for path in sorted(template_dir.glob("*.j2")):
            templates[path.stem] = path.read_text()
            logger.info("custom_template_loaded", name=path.stem)

        return templates

    # -- persistence -------------------------------------------------------

    def _save_state(self) -> None:
        """Persist optimizer state to JSON."""
        if not self._storage_dir:
            return
        state = {
            "run_history": self._run_history[-200:],
            "spec_checksums": self._spec_checksums,
        }
        path = self._storage_dir / "uat_optimizer.json"
        path.write_text(json.dumps(state, indent=2))

    def _load_state(self) -> None:
        """Load optimizer state from JSON."""
        if not self._storage_dir:
            return
        path = self._storage_dir / "uat_optimizer.json"
        if not path.exists():
            return
        try:
            state = json.loads(path.read_text())
            self._run_history = state.get("run_history", [])
            self._spec_checksums = state.get("spec_checksums", {})
        except (json.JSONDecodeError, TypeError):
            logger.warning("uat_optimizer_load_failed")
