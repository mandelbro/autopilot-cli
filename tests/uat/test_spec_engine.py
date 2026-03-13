"""Tests for UAT specification cross-reference engine."""

from __future__ import annotations

import pytest

from autopilot.uat.spec_engine import (
    SpecCrossReferenceEngine,
    TraceabilityMatrix,
    build_traceability_matrix,
)
from autopilot.uat.task_context import SpecReference, TaskContext

# ---------------------------------------------------------------------------
# TraceabilityMatrix dataclass tests
# ---------------------------------------------------------------------------


class TestTraceabilityMatrix:
    def test_frozen(self) -> None:
        matrix = TraceabilityMatrix(task_id="1")
        with pytest.raises(AttributeError):
            matrix.task_id = "2"  # type: ignore[misc]

    def test_defaults(self) -> None:
        matrix = TraceabilityMatrix(task_id="1")
        assert matrix.rfc_sections == []
        assert matrix.discovery_requirements == []
        assert matrix.ux_elements == []
        assert matrix.coverage_score == 0.0
        assert matrix.unmapped_specs == []
        assert matrix.unmapped_tasks == []


# ---------------------------------------------------------------------------
# SpecCrossReferenceEngine tests
# ---------------------------------------------------------------------------


class TestSpecCrossReferenceEngine:
    def setup_method(self) -> None:
        self.engine = SpecCrossReferenceEngine()

    def test_matches_rfc_section_in_prompt(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            prompt_text="Implement per RFC Section 3.4.1 requirements.",
        )
        refs = self.engine.match_explicit_references(ctx)
        rfc_refs = [r for r in refs if r.document == "RFC"]
        assert len(rfc_refs) == 1
        assert rfc_refs[0].section == "3.4.1"

    def test_matches_rfc_without_section_keyword(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            prompt_text="See RFC 6 for details.",
        )
        refs = self.engine.match_explicit_references(ctx)
        rfc_refs = [r for r in refs if r.document == "RFC"]
        assert len(rfc_refs) == 1
        assert rfc_refs[0].section == "6"

    def test_matches_ux_design_section(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            prompt_text="Follow UX Design Section 5.2 for the layout.",
        )
        refs = self.engine.match_explicit_references(ctx)
        ux_refs = [r for r in refs if r.document == "UX Design"]
        assert len(ux_refs) == 1
        assert ux_refs[0].section == "5.2"
        assert ux_refs[0].verification_type == "visual"

    def test_matches_discovery_reference(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            prompt_text="Discovery ADR-5 defines the architecture.",
        )
        refs = self.engine.match_explicit_references(ctx)
        disc_refs = [r for r in refs if r.document == "Discovery"]
        assert len(disc_refs) == 1
        assert disc_refs[0].requirement == "ADR-5"

    def test_deduplicates_references(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            spec_references=[
                SpecReference(document="RFC", section="3.4.1"),
            ],
            prompt_text="See RFC Section 3.4.1 again here.",
        )
        refs = self.engine.match_explicit_references(ctx)
        rfc_refs = [r for r in refs if "rfc" in r.document.lower() and r.section == "3.4.1"]
        assert len(rfc_refs) == 1

    def test_multiple_references_in_prompt(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            prompt_text=(
                "Implement per RFC Section 3.4.1 and RFC Section 6.2.\n"
                "Follow UX Design Section 7 for progressive disclosure.\n"
                "Discovery ADR-026 defines the routing model."
            ),
        )
        refs = self.engine.match_explicit_references(ctx)
        assert len(refs) >= 4

    def test_no_references(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            prompt_text="Just do the thing.",
        )
        refs = self.engine.match_explicit_references(ctx)
        assert refs == []

    def test_scans_user_story_and_outcome(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            user_story="Per RFC Section 2 requirements.",
            outcome="Satisfies UX Design Section 3.1.",
        )
        refs = self.engine.match_explicit_references(ctx)
        assert len(refs) == 2


# ---------------------------------------------------------------------------
# build_traceability_matrix tests
# ---------------------------------------------------------------------------


class TestBuildTraceabilityMatrix:
    def test_full_coverage(self) -> None:
        ctx = TaskContext(
            task_id="029",
            title="UAT task context loader",
            prompt_text=(
                "RFC Section 6 Phase 2: Task file parsing.\n"
                "UX Design Section 5.2: Planning Pipeline.\n"
                "Discovery ADR-5 architecture decision."
            ),
        )
        matrix = build_traceability_matrix(ctx)
        assert matrix.task_id == "029"
        assert len(matrix.rfc_sections) >= 1
        assert len(matrix.ux_elements) >= 1
        assert len(matrix.discovery_requirements) >= 1
        assert matrix.coverage_score == 1.0

    def test_partial_coverage(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            prompt_text="RFC Section 3.4.1 only.",
        )
        matrix = build_traceability_matrix(ctx)
        assert matrix.coverage_score == pytest.approx(0.33, abs=0.01)
        assert len(matrix.rfc_sections) == 1
        assert matrix.discovery_requirements == []
        assert matrix.ux_elements == []

    def test_no_coverage(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            prompt_text="No references here.",
        )
        matrix = build_traceability_matrix(ctx)
        assert matrix.coverage_score == 0.0

    def test_unmapped_specs(self) -> None:
        ctx = TaskContext(
            task_id="1",
            title="Test",
            spec_references=[
                SpecReference(
                    document="Task Workflow System", section="", requirement="Full task template"
                ),
            ],
        )
        matrix = build_traceability_matrix(ctx)
        assert len(matrix.unmapped_specs) >= 1
        assert "Task Workflow System" in matrix.unmapped_specs[0]
