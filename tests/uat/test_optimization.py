"""Tests for UAT self-optimization with hooks intelligence (Task 090)."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path  # noqa: TC003 — used at runtime

import pytest

from autopilot.uat.optimization import (
    UATOptimizer,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sample_run(
    *,
    cats: dict[str, dict[str, int]] | None = None,
    total: int = 10,
    passed: int = 8,
    failed: int = 2,
    coverage: float = 0.75,
    timestamp: str = "2025-06-01T00:00:00+00:00",
) -> dict:
    """Build a sample run dict."""
    return {
        "categories": cats or {},
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "coverage_score": coverage,
        "timestamp": timestamp,
    }


def _make_categories() -> dict[str, dict[str, int]]:
    """Category data with varying effectiveness."""
    return {
        "acceptance": {"total": 20, "bugs_caught": 8, "false_positives": 1},
        "behavioral": {"total": 15, "bugs_caught": 2, "false_positives": 0},
        "ux": {"total": 10, "bugs_caught": 0, "false_positives": 6},
        "compliance": {"total": 5, "bugs_caught": 0, "false_positives": 0},
    }


@pytest.fixture()
def optimizer(tmp_path: Path) -> UATOptimizer:
    """Return an optimizer backed by a temp directory."""
    return UATOptimizer(storage_dir=tmp_path / "optimizer")


# ---------------------------------------------------------------------------
# analyze_effectiveness
# ---------------------------------------------------------------------------


class TestAnalyzeEffectiveness:
    """Tests for the effectiveness analysis engine."""

    def test_empty_returns_zero_report(self, optimizer: UATOptimizer) -> None:
        report = optimizer.analyze_effectiveness()
        assert report.total_categories == 0
        assert report.total_tests == 0
        assert report.overall_effectiveness == 0.0

    def test_aggregates_categories(self, optimizer: UATOptimizer) -> None:
        cats = _make_categories()
        results = [_sample_run(cats=cats)]
        report = optimizer.analyze_effectiveness(results=results)

        assert report.total_categories == 4
        assert report.total_tests == 50
        assert report.total_bugs_caught == 10

    def test_recommendation_expand(self, optimizer: UATOptimizer) -> None:
        """Rate >= 0.3 should recommend 'expand'."""
        cats = {"high_value": {"total": 10, "bugs_caught": 5, "false_positives": 0}}
        report = optimizer.analyze_effectiveness(results=[_sample_run(cats=cats)])

        cat = report.categories[0]
        assert cat.recommendation == "expand"
        assert cat.effectiveness_rate == 0.5

    def test_recommendation_keep(self, optimizer: UATOptimizer) -> None:
        """Rate >= 0.1 but < 0.3 should recommend 'keep'."""
        cats = {"medium": {"total": 10, "bugs_caught": 2, "false_positives": 0}}
        report = optimizer.analyze_effectiveness(results=[_sample_run(cats=cats)])

        assert report.categories[0].recommendation == "keep"

    def test_recommendation_remove(self, optimizer: UATOptimizer) -> None:
        """Zero bugs + high false positives should recommend 'remove'."""
        cats = {"noisy": {"total": 10, "bugs_caught": 0, "false_positives": 8}}
        report = optimizer.analyze_effectiveness(results=[_sample_run(cats=cats)])

        assert report.categories[0].recommendation == "remove"

    def test_recommendation_reduce(self, optimizer: UATOptimizer) -> None:
        """Low effectiveness without high false positives should recommend 'reduce'."""
        cats = {"low": {"total": 10, "bugs_caught": 0, "false_positives": 1}}
        report = optimizer.analyze_effectiveness(results=[_sample_run(cats=cats)])

        assert report.categories[0].recommendation == "reduce"


# ---------------------------------------------------------------------------
# recommend_pruning / suggest_focus_areas
# ---------------------------------------------------------------------------


class TestPruningAndFocus:
    """Tests for pruning recommendations and focus areas."""

    def test_recommend_pruning_returns_no_value_categories(self, optimizer: UATOptimizer) -> None:
        cats = _make_categories()
        optimizer.record_run(_sample_run(cats=cats))

        prunable = optimizer.recommend_pruning()
        # "ux" has remove rec + 0 bugs, "compliance" has reduce rec + 0 bugs
        assert "ux" in prunable
        assert "compliance" in prunable
        assert "acceptance" not in prunable

    def test_suggest_focus_areas_returns_expand_categories(self, optimizer: UATOptimizer) -> None:
        cats = _make_categories()
        optimizer.record_run(_sample_run(cats=cats))

        focus = optimizer.suggest_focus_areas()
        # "acceptance" has rate 0.4 -> expand
        assert "acceptance" in focus
        assert "ux" not in focus


# ---------------------------------------------------------------------------
# refresh_spec_index (drift detection)
# ---------------------------------------------------------------------------


class TestSpecDrift:
    """Tests for spec drift detection."""

    def test_detects_added_spec(self, optimizer: UATOptimizer, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec v1")

        drifts = optimizer.refresh_spec_index([spec])
        assert len(drifts) == 1
        assert drifts[0].drift_type == "added"
        assert drifts[0].spec_path == str(spec)

    def test_detects_modified_spec(self, optimizer: UATOptimizer, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec v1")
        optimizer.refresh_spec_index([spec])

        spec.write_text("# Spec v2 — changed")
        drifts = optimizer.refresh_spec_index([spec])
        assert len(drifts) == 1
        assert drifts[0].drift_type == "modified"

    def test_detects_removed_spec(self, optimizer: UATOptimizer, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec v1")
        optimizer.refresh_spec_index([spec])

        spec.unlink()
        drifts = optimizer.refresh_spec_index([spec])
        assert len(drifts) == 1
        assert drifts[0].drift_type == "removed"

    def test_no_drift_when_unchanged(self, optimizer: UATOptimizer, tmp_path: Path) -> None:
        spec = tmp_path / "spec.md"
        spec.write_text("# Spec v1")
        optimizer.refresh_spec_index([spec])

        drifts = optimizer.refresh_spec_index([spec])
        assert len(drifts) == 0

    def test_ignores_nonexistent_untracked_spec(
        self, optimizer: UATOptimizer, tmp_path: Path
    ) -> None:
        missing = tmp_path / "nonexistent.md"
        drifts = optimizer.refresh_spec_index([missing])
        assert len(drifts) == 0


# ---------------------------------------------------------------------------
# record_run / get_trends
# ---------------------------------------------------------------------------


class TestTrends:
    """Tests for run recording and trend analysis."""

    def test_record_run_and_get_trends(self, optimizer: UATOptimizer) -> None:
        optimizer.record_run(_sample_run(total=10, passed=8, coverage=0.7))
        optimizer.record_run(_sample_run(total=12, passed=10, coverage=0.85))

        trends = optimizer.get_trends()
        assert len(trends) == 2
        assert trends[0].pass_rate == 0.8
        assert trends[1].total_tests == 12

    def test_trends_limited(self, optimizer: UATOptimizer) -> None:
        for i in range(5):
            optimizer.record_run(_sample_run(total=10, passed=i + 1))

        trends = optimizer.get_trends(limit=3)
        assert len(trends) == 3

    def test_trends_empty(self, optimizer: UATOptimizer) -> None:
        assert optimizer.get_trends() == []


# ---------------------------------------------------------------------------
# export_results
# ---------------------------------------------------------------------------


class TestExportResults:
    """Tests for multi-format export."""

    def test_export_json(self, optimizer: UATOptimizer) -> None:
        optimizer.record_run(_sample_run(total=10, passed=8, failed=2))
        result = optimizer.export_results(fmt="json")
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["total_tests"] == 10

    def test_export_csv(self, optimizer: UATOptimizer) -> None:
        optimizer.record_run(_sample_run(total=10, passed=8, failed=2))
        result = optimizer.export_results(fmt="csv")

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert rows[0] == ["timestamp", "total_tests", "passed", "failed", "pass_rate"]
        assert rows[1][1] == "10"  # total_tests
        assert rows[1][2] == "8"  # passed
        assert rows[1][3] == "2"  # failed

    def test_export_html(self, optimizer: UATOptimizer) -> None:
        optimizer.record_run(_sample_run(total=10, passed=8, failed=2))
        result = optimizer.export_results(fmt="html")

        assert "<table>" in result
        assert "</table>" in result
        assert "<td>10</td>" in result

    def test_export_unsupported_format_raises(self, optimizer: UATOptimizer) -> None:
        with pytest.raises(ValueError, match="Unsupported format"):
            optimizer.export_results(fmt="xml")


# ---------------------------------------------------------------------------
# load_custom_templates
# ---------------------------------------------------------------------------


class TestCustomTemplates:
    """Tests for loading user-defined Jinja2 templates."""

    def test_loads_j2_files(self, optimizer: UATOptimizer, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "smoke.j2").write_text("{{ test_name }}")
        (tpl_dir / "regression.j2").write_text("{{ suite }}")

        templates = optimizer.load_custom_templates(tpl_dir)
        assert "smoke" in templates
        assert "regression" in templates
        assert templates["smoke"] == "{{ test_name }}"

    def test_returns_empty_for_missing_dir(self, optimizer: UATOptimizer, tmp_path: Path) -> None:
        templates = optimizer.load_custom_templates(tmp_path / "nope")
        assert templates == {}


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


class TestStatePersistence:
    """Tests for save/load state round-tripping."""

    def test_state_persists_across_instances(self, tmp_path: Path) -> None:
        storage = tmp_path / "state"

        opt1 = UATOptimizer(storage_dir=storage)
        opt1.record_run(_sample_run(total=10, passed=7))

        opt2 = UATOptimizer(storage_dir=storage)
        trends = opt2.get_trends()
        assert len(trends) == 1
        assert trends[0].total_tests == 10

    def test_corrupted_state_handled_gracefully(self, tmp_path: Path) -> None:
        storage = tmp_path / "broken"
        storage.mkdir()
        (storage / "uat_optimizer.json").write_text("not json{{{")

        opt = UATOptimizer(storage_dir=storage)
        assert opt.get_trends() == []

    def test_no_storage_dir_skips_persistence(self) -> None:
        opt = UATOptimizer(storage_dir=None)
        opt.record_run(_sample_run())
        trends = opt.get_trends()
        assert len(trends) == 1


# ---------------------------------------------------------------------------
# Empty / default behavior
# ---------------------------------------------------------------------------


class TestDefaults:
    """Sensible defaults for edge cases."""

    def test_empty_optimizer_pruning_is_empty(self) -> None:
        opt = UATOptimizer()
        assert opt.recommend_pruning() == []

    def test_empty_optimizer_focus_is_empty(self) -> None:
        opt = UATOptimizer()
        assert opt.suggest_focus_areas() == []

    def test_export_empty_json(self) -> None:
        opt = UATOptimizer()
        assert json.loads(opt.export_results(fmt="json")) == []
