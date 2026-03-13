"""Enforcement engine orchestrator (Task 056, RFC Section 3.5).

Coordinates setup, check, and report operations across all 11
enforcement categories with dynamic rule loading and SQLite metrics.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.core.models import (
    CheckResult,
    EnforcementReport,
    SetupResult,
)
from autopilot.enforcement.rules.async_misuse import AsyncMisuseRule
from autopilot.enforcement.rules.comments import CommentsRule
from autopilot.enforcement.rules.conventions import ConventionsRule
from autopilot.enforcement.rules.dead_code import DeadCodeRule
from autopilot.enforcement.rules.deprecated import DeprecatedRule
from autopilot.enforcement.rules.duplication import DuplicationRule
from autopilot.enforcement.rules.error_handling import ErrorHandlingRule
from autopilot.enforcement.rules.overengineering import OverengineeringRule
from autopilot.enforcement.rules.security import SecurityRule
from autopilot.enforcement.rules.test_quality import TestQualityRule
from autopilot.enforcement.rules.type_safety import TypeSafetyRule

if TYPE_CHECKING:
    from autopilot.core.config import EnforcementConfig, ProjectConfig
    from autopilot.enforcement.rules.base import EnforcementRule

_log = logging.getLogger(__name__)


def _default_rules() -> list[EnforcementRule]:
    """Instantiate all built-in enforcement rules."""
    return [
        DuplicationRule(),
        ConventionsRule(),
        OverengineeringRule(),
        SecurityRule(),
        ErrorHandlingRule(),
        DeadCodeRule(),
        TypeSafetyRule(),
        TestQualityRule(),
        CommentsRule(),
        DeprecatedRule(),
        AsyncMisuseRule(),
    ]


def _collect_python_files(root: Path) -> list[Path]:
    """Collect all .py files under root, excluding hidden directories."""
    files: list[Path] = []
    for path in root.rglob("*.py"):
        parts = path.relative_to(root).parts
        if any(part.startswith(".") for part in parts):
            continue
        files.append(path)
    return sorted(files)


class EnforcementEngine:
    """Orchestrates enforcement checks across all 11 categories.

    Args:
        config: Enforcement configuration from project config.
        db_path: Path to SQLite metrics database.  If None, metrics
            are not persisted.
    """

    def __init__(
        self,
        config: EnforcementConfig,
        *,
        db_path: Path | None = None,
    ) -> None:
        self._config = config
        self._db_path = db_path
        self._rules = self._load_rules()

    def setup(self, project: ProjectConfig) -> SetupResult:
        """Configure enforcement layers for the project."""
        files_created: list[str] = []
        errors: list[str] = []

        if self._db_path:
            try:
                self._init_db()
                files_created.append(str(self._db_path))
            except sqlite3.Error as exc:
                errors.append(f"Failed to initialize metrics DB: {exc}")

        return SetupResult(
            layer="enforcement-engine",
            success=len(errors) == 0,
            files_created=tuple(files_created),
            errors=tuple(errors),
        )

    def check(self, project_root: Path) -> list[CheckResult]:
        """Run all enabled rule checks against the project."""
        files = _collect_python_files(project_root)
        results: list[CheckResult] = []

        for rule in self._rules:
            if rule.category not in self._config.categories:
                continue
            try:
                result = rule.check(files)
                results.append(result)
            except Exception:
                _log.exception("Rule %s:%s failed", rule.category, rule.name)
                results.append(
                    CheckResult(
                        category=rule.category,
                        files_scanned=0,
                    )
                )

        if self._db_path:
            self._store_metrics(results)

        return results

    def report(self, project_id: str) -> EnforcementReport:
        """Generate an enforcement report from stored metrics."""
        report = EnforcementReport(project_id=project_id)
        if self._db_path and self._db_path.exists():
            report.results = self._load_latest_results(project_id)
        return report

    def build_quality_gate_prompt(self) -> str:
        """Generate quality gate instructions for agent prompts."""
        categories = ", ".join(self._config.categories)
        lines = [
            "## Quality Gate: Anti-Pattern Enforcement",
            "",
            "Before submitting code, verify compliance with these categories:",
            f"  {categories}",
            "",
            "Run `ruff check --select ALL` and resolve violations.",
            "Violations with severity ERROR must be fixed before merge.",
            "Violations with severity WARNING should be addressed.",
            "Violations with severity INFO are suggestions for improvement.",
        ]
        return "\n".join(lines)

    @property
    def rules(self) -> list[EnforcementRule]:
        """Return the loaded enforcement rules."""
        return list(self._rules)

    def _load_rules(self) -> list[EnforcementRule]:
        """Load built-in rules filtered by config categories."""
        all_rules = _default_rules()
        if not self._config.enabled:
            return []
        return [r for r in all_rules if r.category in self._config.categories]

    def _init_db(self) -> None:
        """Initialize the SQLite metrics database."""
        if not self._db_path:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS enforcement_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collected_at TEXT NOT NULL,
                    category TEXT NOT NULL,
                    violations_count INTEGER NOT NULL DEFAULT 0,
                    files_scanned INTEGER NOT NULL DEFAULT 0,
                    duration_seconds REAL NOT NULL DEFAULT 0.0
                )"""
            )
            conn.commit()
        finally:
            conn.close()

    def _store_metrics(self, results: list[CheckResult]) -> None:
        """Store check results as metrics in SQLite."""
        if not self._db_path:
            return
        try:
            self._init_db()
            conn = sqlite3.connect(str(self._db_path))
            try:
                now = datetime.now(UTC).isoformat()
                for r in results:
                    conn.execute(
                        """INSERT INTO enforcement_metrics
                        (collected_at, category, violations_count, files_scanned, duration_seconds)
                        VALUES (?, ?, ?, ?, ?)""",
                        (now, r.category, len(r.violations), r.files_scanned, r.duration_seconds),
                    )
                conn.commit()
            finally:
                conn.close()
        except sqlite3.Error:
            _log.exception("Failed to store enforcement metrics")

    def _load_latest_results(self, project_id: str) -> list[CheckResult]:
        """Load the most recent check results from SQLite."""
        if not self._db_path or not self._db_path.exists():
            return []
        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cursor = conn.execute(
                    """SELECT category, violations_count, files_scanned, duration_seconds
                    FROM enforcement_metrics
                    WHERE collected_at = (SELECT MAX(collected_at) FROM enforcement_metrics)
                    ORDER BY category"""
                )
                results: list[CheckResult] = []
                for row in cursor.fetchall():
                    results.append(
                        CheckResult(
                            category=row[0],
                            files_scanned=row[2],
                            duration_seconds=row[3],
                        )
                    )
                return results
            finally:
                conn.close()
        except sqlite3.Error:
            _log.exception("Failed to load enforcement metrics")
            return []
