"""Tests for shell completion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from autopilot.cli.completions import complete_project_names, complete_project_types

# ---------------------------------------------------------------------------
# complete_project_types
# ---------------------------------------------------------------------------


class TestCompleteProjectTypes:
    """Tests for project type completion."""

    def test_returns_all_types_for_empty_prefix(self) -> None:
        result = complete_project_types("")
        assert result == ["python", "typescript", "hybrid"]

    def test_filters_by_prefix(self) -> None:
        assert complete_project_types("p") == ["python"]
        assert complete_project_types("t") == ["typescript"]
        assert complete_project_types("h") == ["hybrid"]

    def test_returns_empty_for_no_match(self) -> None:
        assert complete_project_types("z") == []

    def test_partial_match(self) -> None:
        assert complete_project_types("py") == ["python"]
        assert complete_project_types("type") == ["typescript"]


# ---------------------------------------------------------------------------
# complete_project_names
# ---------------------------------------------------------------------------


@dataclass
class _FakeProject:
    name: str
    archived: bool = False


class TestCompleteProjectNames:
    """Tests for project name completion from registry."""

    def test_returns_matching_project_names(self) -> None:
        projects = [_FakeProject("webapp"), _FakeProject("worker"), _FakeProject("api")]
        mock_registry = MagicMock()
        mock_registry.return_value.load.return_value = projects

        with patch("autopilot.core.project.ProjectRegistry", mock_registry):
            result = complete_project_names("w")

        assert result == ["webapp", "worker"]

    def test_excludes_archived_projects(self) -> None:
        projects = [
            _FakeProject("active-app"),
            _FakeProject("archived-app", archived=True),
        ]
        mock_registry = MagicMock()
        mock_registry.return_value.load.return_value = projects

        with patch("autopilot.core.project.ProjectRegistry", mock_registry):
            result = complete_project_names("a")

        assert result == ["active-app"]

    def test_returns_all_for_empty_prefix(self) -> None:
        projects = [_FakeProject("alpha"), _FakeProject("beta")]
        mock_registry = MagicMock()
        mock_registry.return_value.load.return_value = projects

        with patch("autopilot.core.project.ProjectRegistry", mock_registry):
            result = complete_project_names("")

        assert result == ["alpha", "beta"]

    def test_returns_empty_on_exception(self) -> None:
        mock_registry = MagicMock()
        mock_registry.side_effect = FileNotFoundError("no registry")

        with patch("autopilot.core.project.ProjectRegistry", mock_registry):
            result = complete_project_names("x")

        assert result == []

    def test_returns_empty_when_no_match(self) -> None:
        projects = [_FakeProject("webapp")]
        mock_registry = MagicMock()
        mock_registry.return_value.load.return_value = projects

        with patch("autopilot.core.project.ProjectRegistry", mock_registry):
            result = complete_project_names("z")

        assert result == []
