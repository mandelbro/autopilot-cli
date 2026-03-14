"""Tests for DiscoveryConverter end-to-end pipeline (Task 079)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autopilot.core.discovery import DiscoveryConverter, Phase

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def discovery_file(tmp_path: Path) -> Path:
    """Create a sample discovery document."""
    content = (
        "# Authentication Discovery\n\n"
        "Analysis of authentication requirements.\n\n"
        "## Phase 1: Foundation\n\n"
        "- Set up auth module structure\n"
        "- Configure JWT token handling\n"
        "- Implement password hashing\n\n"
        "Effort: medium\n\n"
        "## Phase 2: Integration\n\n"
        "- Add OAuth2 provider integration\n"
        "- Build session management RFC Section 3.4\n\n"
        "Effort: large\n"
    )
    path = tmp_path / "auth-discovery.md"
    path.write_text(content)
    return path


class TestDiscoveryConverter:
    def test_parse_returns_document(self, discovery_file: Path) -> None:
        converter = DiscoveryConverter()
        doc = converter.parse(discovery_file)
        assert doc.title == "Authentication Discovery"
        assert len(doc.phases) == 2

    def test_extract_phases(self, discovery_file: Path) -> None:
        converter = DiscoveryConverter()
        doc = converter.parse(discovery_file)
        phases = converter.extract_phases(doc)
        assert len(phases) == 2
        assert phases[0].name == "Foundation"
        assert len(phases[0].deliverables) == 3

    def test_generate_tasks_from_phases(self) -> None:
        converter = DiscoveryConverter()
        phases = [
            Phase(name="Setup", deliverables=["Init project", "Add config"], effort_estimate="small"),
        ]
        tasks = converter.generate_tasks(phases, project_title="Test")
        assert len(tasks) == 2
        assert tasks[0].id == "001"
        assert tasks[1].id == "002"
        assert tasks[0].sprint_points == 2  # small

    def test_generate_tasks_with_spec_refs(self) -> None:
        converter = DiscoveryConverter()
        phases = [
            Phase(
                name="Build RFC Section 3.4 compliance",
                deliverables=["Implement schema per Discovery Section 5"],
                effort_estimate="medium",
            ),
        ]
        tasks = converter.generate_tasks(phases, project_title="Test")
        assert len(tasks) == 1
        assert tasks[0].spec_references  # Should have extracted refs

    def test_generate_tasks_start_id(self) -> None:
        converter = DiscoveryConverter()
        phases = [Phase(name="P1", deliverables=["Task A"], effort_estimate="")]
        tasks = converter.generate_tasks(phases, start_id=50)
        assert tasks[0].id == "050"

    def test_write_files(self, tmp_path: Path) -> None:
        converter = DiscoveryConverter()
        from autopilot.core.task import Task

        tasks = [
            Task(id="001", title="Task one", sprint_points=3),
            Task(id="002", title="Task two", sprint_points=5),
        ]
        files = converter.write_files(tasks, tmp_path / "tasks")
        assert len(files) >= 2  # task file + index
        assert (tmp_path / "tasks" / "tasks-index.md").exists()

    def test_convert_end_to_end(self, discovery_file: Path, tmp_path: Path) -> None:
        converter = DiscoveryConverter()
        output_dir = tmp_path / "output" / "tasks"
        files = converter.convert(discovery_file, output_dir)
        assert len(files) >= 2
        assert (output_dir / "tasks-index.md").exists()

    def test_convert_with_merge(self, discovery_file: Path, tmp_path: Path) -> None:
        converter = DiscoveryConverter()
        output_dir = tmp_path / "tasks"

        # First conversion
        converter.convert(discovery_file, output_dir)

        # Second conversion with merge
        files = converter.convert(discovery_file, output_dir, merge=True)
        assert len(files) >= 2

        # Check index has merged counts
        index_text = (output_dir / "tasks-index.md").read_text()
        assert "Total Tasks" in index_text

    def test_proportional_point_distribution(self) -> None:
        converter = DiscoveryConverter()
        phases = [
            Phase(
                name="Phase A",
                deliverables=["Small thing"],
                effort_estimate="trivial",
            ),
            Phase(
                name="Phase B",
                deliverables=["Big thing 1", "Big thing 2"],
                effort_estimate="large",
            ),
        ]
        tasks = converter.generate_tasks(phases)
        assert tasks[0].sprint_points == 1  # trivial
        assert tasks[1].sprint_points == 5  # large
        assert tasks[2].sprint_points == 5  # large
