"""Tests for UAT spec index builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.uat.spec_index import (
    SpecEntry,
    SpecIndex,
    SpecIndexBuilder,
    _infer_verification_type,
    _is_testable,
)

# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestSpecEntry:
    def test_frozen(self) -> None:
        entry = SpecEntry(spec_id="R001", document="RFC", section="Intro", requirement_text="x")
        with pytest.raises(AttributeError):
            entry.spec_id = "R002"  # type: ignore[misc]

    def test_defaults(self) -> None:
        entry = SpecEntry(spec_id="R001", document="RFC", section="A", requirement_text="x")
        assert entry.verification_type == "manual"


class TestSpecIndex:
    def test_frozen(self) -> None:
        idx = SpecIndex()
        with pytest.raises(AttributeError):
            idx.total_requirements = 5  # type: ignore[misc]

    def test_defaults(self) -> None:
        idx = SpecIndex()
        assert idx.entries == []
        assert idx.total_requirements == 0
        assert idx.testable_count == 0


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestInferVerificationType:
    def test_automated_for_api(self) -> None:
        assert _infer_verification_type("The API must return 200") == "automated"

    def test_automated_for_cli(self) -> None:
        assert _infer_verification_type("The CLI command must work") == "automated"

    def test_visual_for_design(self) -> None:
        assert _infer_verification_type("The design must follow specs") == "visual"

    def test_manual_default(self) -> None:
        assert _infer_verification_type("The system must be reliable") == "manual"


class TestIsTestable:
    def test_must_is_testable(self) -> None:
        assert _is_testable("The system MUST validate input") is True

    def test_should_is_testable(self) -> None:
        assert _is_testable("It should handle errors") is True

    def test_returns_is_testable(self) -> None:
        assert _is_testable("returns a JSON object") is True

    def test_plain_text_not_testable(self) -> None:
        assert _is_testable("This is just a note.") is False


# ---------------------------------------------------------------------------
# SpecIndexBuilder tests
# ---------------------------------------------------------------------------

_SAMPLE_RFC = """\
# Sample RFC

## Overview

This document defines the requirements.

### Authentication

The system MUST support JWT tokens.
The API endpoint SHALL return 401 for invalid tokens.

### Authorization

Users SHOULD have role-based access control.
This is just descriptive text without requirements.

## Data Model

### Storage

The database MUST persist session data.
The CLI command MUST accept --format flag.

## Notes

No requirements here, just notes.
"""


class TestSpecIndexBuilder:
    @pytest.fixture()
    def builder(self) -> SpecIndexBuilder:
        return SpecIndexBuilder()

    @pytest.fixture()
    def rfc_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "sample-rfc.md"
        p.write_text(_SAMPLE_RFC, encoding="utf-8")
        return p

    def test_build_rfc_index(self, builder: SpecIndexBuilder, rfc_file: Path) -> None:
        index = builder.build_rfc_index(rfc_file)
        assert index.total_requirements > 0
        assert index.testable_count > 0
        assert index.generated_at != ""

    def test_entries_have_spec_ids(self, builder: SpecIndexBuilder, rfc_file: Path) -> None:
        index = builder.build_rfc_index(rfc_file)
        for entry in index.entries:
            assert entry.spec_id.startswith("sample-rfc-R")
            assert entry.document == "sample-rfc"

    def test_sections_reflect_hierarchy(self, builder: SpecIndexBuilder, rfc_file: Path) -> None:
        index = builder.build_rfc_index(rfc_file)
        sections = [e.section for e in index.entries]
        # Should contain nested section paths
        assert any("Authentication" in s for s in sections)
        assert any("Storage" in s for s in sections)

    def test_verification_types_inferred(self, builder: SpecIndexBuilder, rfc_file: Path) -> None:
        index = builder.build_rfc_index(rfc_file)
        types = {e.verification_type for e in index.entries}
        assert "automated" in types  # API/CLI entries

    def test_missing_file_returns_empty(self, builder: SpecIndexBuilder, tmp_path: Path) -> None:
        index = builder.build_rfc_index(tmp_path / "nonexistent.md")
        assert index.total_requirements == 0
        assert index.entries == []

    def test_empty_file(self, builder: SpecIndexBuilder, tmp_path: Path) -> None:
        p = tmp_path / "empty.md"
        p.write_text("", encoding="utf-8")
        index = builder.build_rfc_index(p)
        assert index.total_requirements == 0

    def test_testable_count_subset_of_total(
        self, builder: SpecIndexBuilder, rfc_file: Path
    ) -> None:
        index = builder.build_rfc_index(rfc_file)
        assert index.testable_count <= index.total_requirements


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------


class TestSpecIndexSerialization:
    @pytest.fixture()
    def builder(self) -> SpecIndexBuilder:
        return SpecIndexBuilder()

    @pytest.fixture()
    def sample_index(self, builder: SpecIndexBuilder, tmp_path: Path) -> SpecIndex:
        rfc = tmp_path / "rfc.md"
        rfc.write_text(_SAMPLE_RFC, encoding="utf-8")
        return builder.build_rfc_index(rfc)

    def test_save_and_load_roundtrip(
        self,
        builder: SpecIndexBuilder,
        sample_index: SpecIndex,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "index.json"
        builder.save_index(sample_index, out)
        assert out.exists()

        loaded = builder.load_index(out)
        assert loaded.total_requirements == sample_index.total_requirements
        assert loaded.testable_count == sample_index.testable_count
        assert len(loaded.entries) == len(sample_index.entries)

    def test_save_to_file_object(
        self,
        builder: SpecIndexBuilder,
        sample_index: SpecIndex,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "index2.json"
        with open(out, "w", encoding="utf-8") as f:
            builder.save_index(sample_index, f)
        assert out.exists()
        loaded = builder.load_index(out)
        assert loaded.total_requirements == sample_index.total_requirements


# ---------------------------------------------------------------------------
# Discovery index tests
# ---------------------------------------------------------------------------

_SAMPLE_DISCOVERY = """\
# Discovery Document

## Architecture Decisions

### ADR-001 Event Sourcing

The system MUST use event sourcing for state changes.
All events SHALL be immutable and append-only.

### ADR-002 API Gateway

The API gateway MUST route requests to appropriate services.

## Risk Mitigations

### Security Risks

The system MUST encrypt all data at rest.
Access control SHOULD follow least-privilege principle.

## Background

Just some context without requirements.
"""

_SAMPLE_UX = """\
# UX Design Document

## REPL Behavior

### Command Input

The CLI MUST support tab completion for commands.
The interface SHOULD display inline help text.

## Dashboard Layout

### Status Panel

The dashboard MUST show system health indicators.
The layout SHOULD be responsive to terminal width.

## Workflow UX

### Error Handling

The system MUST display user-friendly error messages.
Error output SHOULD include suggested fixes.

## Appendix

No requirements here, just reference material.
"""


class TestBuildDiscoveryIndex:
    @pytest.fixture()
    def builder(self) -> SpecIndexBuilder:
        return SpecIndexBuilder()

    @pytest.fixture()
    def discovery_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "architecture-discovery.md"
        p.write_text(_SAMPLE_DISCOVERY, encoding="utf-8")
        return p

    def test_returns_spec_index_with_entries(
        self, builder: SpecIndexBuilder, discovery_file: Path
    ) -> None:
        index = builder.build_discovery_index(discovery_file)
        assert index.total_requirements > 0
        assert index.testable_count > 0
        assert index.generated_at != ""

    def test_spec_ids_use_discovery_prefix(
        self, builder: SpecIndexBuilder, discovery_file: Path
    ) -> None:
        index = builder.build_discovery_index(discovery_file)
        for entry in index.entries:
            assert entry.spec_id.startswith("discovery-architecture-discovery-R")
            assert entry.document == "discovery-architecture-discovery"

    def test_sections_contain_adr_headings(
        self, builder: SpecIndexBuilder, discovery_file: Path
    ) -> None:
        index = builder.build_discovery_index(discovery_file)
        sections = [e.section for e in index.entries]
        assert any("ADR-001" in s for s in sections)
        assert any("Security Risks" in s for s in sections)

    def test_missing_file_returns_empty(self, builder: SpecIndexBuilder, tmp_path: Path) -> None:
        index = builder.build_discovery_index(tmp_path / "nonexistent.md")
        assert index.total_requirements == 0
        assert index.entries == []
        assert index.generated_at != ""


# ---------------------------------------------------------------------------
# UX design index tests
# ---------------------------------------------------------------------------


class TestBuildUxIndex:
    @pytest.fixture()
    def builder(self) -> SpecIndexBuilder:
        return SpecIndexBuilder()

    @pytest.fixture()
    def ux_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "cli-ux-design.md"
        p.write_text(_SAMPLE_UX, encoding="utf-8")
        return p

    def test_returns_spec_index_with_entries(
        self, builder: SpecIndexBuilder, ux_file: Path
    ) -> None:
        index = builder.build_ux_index(ux_file)
        assert index.total_requirements > 0
        assert index.testable_count > 0
        assert index.generated_at != ""

    def test_spec_ids_use_ux_design_prefix(self, builder: SpecIndexBuilder, ux_file: Path) -> None:
        index = builder.build_ux_index(ux_file)
        for entry in index.entries:
            assert entry.spec_id.startswith("ux-design-cli-ux-design-R")
            assert entry.document == "ux-design-cli-ux-design"

    def test_sections_contain_ux_headings(self, builder: SpecIndexBuilder, ux_file: Path) -> None:
        index = builder.build_ux_index(ux_file)
        sections = [e.section for e in index.entries]
        assert any("Command Input" in s for s in sections)
        assert any("Error Handling" in s for s in sections)

    def test_missing_file_returns_empty(self, builder: SpecIndexBuilder, tmp_path: Path) -> None:
        index = builder.build_ux_index(tmp_path / "nonexistent.md")
        assert index.total_requirements == 0
        assert index.entries == []
        assert index.generated_at != ""


# ---------------------------------------------------------------------------
# Merge indices tests
# ---------------------------------------------------------------------------


class TestMergeIndices:
    @pytest.fixture()
    def builder(self) -> SpecIndexBuilder:
        return SpecIndexBuilder()

    @pytest.fixture()
    def rfc_index(self, builder: SpecIndexBuilder, tmp_path: Path) -> SpecIndex:
        p = tmp_path / "rfc.md"
        p.write_text(_SAMPLE_RFC, encoding="utf-8")
        return builder.build_rfc_index(p)

    @pytest.fixture()
    def discovery_index(self, builder: SpecIndexBuilder, tmp_path: Path) -> SpecIndex:
        p = tmp_path / "disc.md"
        p.write_text(_SAMPLE_DISCOVERY, encoding="utf-8")
        return builder.build_discovery_index(p)

    @pytest.fixture()
    def ux_index(self, builder: SpecIndexBuilder, tmp_path: Path) -> SpecIndex:
        p = tmp_path / "ux.md"
        p.write_text(_SAMPLE_UX, encoding="utf-8")
        return builder.build_ux_index(p)

    def test_combines_entries(
        self,
        builder: SpecIndexBuilder,
        rfc_index: SpecIndex,
        discovery_index: SpecIndex,
    ) -> None:
        merged = builder.merge_indices(rfc_index, discovery_index)
        expected_count = len(rfc_index.entries) + len(discovery_index.entries)
        assert len(merged.entries) == expected_count

    def test_recalculates_totals(
        self,
        builder: SpecIndexBuilder,
        rfc_index: SpecIndex,
        discovery_index: SpecIndex,
        ux_index: SpecIndex,
    ) -> None:
        merged = builder.merge_indices(rfc_index, discovery_index, ux_index)
        expected_total = (
            rfc_index.total_requirements
            + discovery_index.total_requirements
            + ux_index.total_requirements
        )
        assert merged.total_requirements == expected_total
        assert merged.testable_count <= merged.total_requirements
        assert merged.generated_at != ""

    def test_merge_empty_indices(self, builder: SpecIndexBuilder) -> None:
        empty1 = SpecIndex(generated_at="t1")
        empty2 = SpecIndex(generated_at="t2")
        merged = builder.merge_indices(empty1, empty2)
        assert merged.total_requirements == 0
        assert merged.testable_count == 0
        assert merged.entries == []
        assert merged.generated_at != ""

    def test_merge_no_arguments(self, builder: SpecIndexBuilder) -> None:
        merged = builder.merge_indices()
        assert merged.total_requirements == 0
        assert merged.entries == []
