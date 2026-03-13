"""Tests for the EnforcementEngine (Task 056)."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from autopilot.core.config import EnforcementConfig
from autopilot.core.models import CheckResult, EnforcementReport, SetupResult
from autopilot.enforcement.engine import EnforcementEngine

if TYPE_CHECKING:
    from pathlib import Path


class TestEnforcementEngineInterface:
    def test_creates_with_config(self) -> None:
        cfg = EnforcementConfig()
        engine = EnforcementEngine(cfg)
        assert engine is not None

    def test_loads_all_11_rules(self) -> None:
        cfg = EnforcementConfig()
        engine = EnforcementEngine(cfg)
        categories = {r.category for r in engine.rules}
        assert len(categories) == 11
        assert "duplication" in categories
        assert "async_misuse" in categories

    def test_disabled_engine_loads_no_rules(self) -> None:
        cfg = EnforcementConfig(enabled=False)
        engine = EnforcementEngine(cfg)
        assert len(engine.rules) == 0

    def test_filtered_categories(self) -> None:
        cfg = EnforcementConfig(categories=["security", "dead_code"])
        engine = EnforcementEngine(cfg)
        categories = {r.category for r in engine.rules}
        assert categories == {"security", "dead_code"}


class TestEnforcementEngineSetup:
    def test_setup_returns_setup_result(self, tmp_path: Path) -> None:
        from autopilot.core.config import ProjectConfig

        cfg = EnforcementConfig()
        db = tmp_path / "metrics.db"
        engine = EnforcementEngine(cfg, db_path=db)
        result = engine.setup(ProjectConfig(name="test"))
        assert isinstance(result, SetupResult)
        assert result.layer == "enforcement-engine"
        assert result.success is True

    def test_setup_creates_db(self, tmp_path: Path) -> None:
        from autopilot.core.config import ProjectConfig

        cfg = EnforcementConfig()
        db = tmp_path / "metrics.db"
        engine = EnforcementEngine(cfg, db_path=db)
        engine.setup(ProjectConfig(name="test"))
        assert db.exists()


class TestEnforcementEngineCheck:
    def test_check_returns_results_list(self, tmp_path: Path) -> None:
        cfg = EnforcementConfig(categories=["comments"])
        engine = EnforcementEngine(cfg)
        py_file = tmp_path / "example.py"
        py_file.write_text("x = 1\n")
        results = engine.check(tmp_path)
        assert isinstance(results, list)
        assert all(isinstance(r, CheckResult) for r in results)

    def test_check_stores_metrics(self, tmp_path: Path) -> None:
        cfg = EnforcementConfig(categories=["comments"])
        db = tmp_path / "metrics.db"
        engine = EnforcementEngine(cfg, db_path=db)
        py_file = tmp_path / "src" / "example.py"
        py_file.parent.mkdir()
        py_file.write_text("x = 1\n")
        engine.check(tmp_path)

        conn = sqlite3.connect(str(db))
        count = conn.execute(
            "SELECT COUNT(*) FROM enforcement_metrics"
        ).fetchone()[0]
        conn.close()
        assert count >= 1


class TestEnforcementEngineReport:
    def test_report_returns_enforcement_report(self) -> None:
        cfg = EnforcementConfig()
        engine = EnforcementEngine(cfg)
        report = engine.report("test-project")
        assert isinstance(report, EnforcementReport)
        assert report.project_id == "test-project"


class TestQualityGatePrompt:
    def test_prompt_contains_categories(self) -> None:
        cfg = EnforcementConfig()
        engine = EnforcementEngine(cfg)
        prompt = engine.build_quality_gate_prompt()
        assert "duplication" in prompt
        assert "Quality Gate" in prompt
