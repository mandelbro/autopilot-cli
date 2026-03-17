"""Tests for Python project templates (Task 007)."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

import yaml
from jinja2 import Environment, FileSystemLoader


def _get_template_env() -> Environment:
    """Create a Jinja2 environment pointing at the templates directory."""
    templates_dir = Path(__file__).resolve().parents[2] / "templates" / "python"
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
    )


class TestConfigTemplate:
    def test_renders_valid_yaml(self) -> None:
        env = _get_template_env()
        template = env.get_template("config.yaml.j2")
        rendered = template.render(
            project_name="test-project",
            project_root=".",
        )
        data = yaml.safe_load(rendered)
        assert isinstance(data, dict)
        assert data["project"]["name"] == "test-project"
        assert data["project"]["type"] == "python"

    def test_all_config_sections_present(self) -> None:
        env = _get_template_env()
        template = env.get_template("config.yaml.j2")
        rendered = template.render(project_name="test", project_root=".")
        data = yaml.safe_load(rendered)
        expected_sections = {
            "project",
            "scheduler",
            "usage_limits",
            "agents",
            "quality_gates",
            "enforcement",
            "safety",
            "approval",
            "claude",
            "git",
            "deployment_monitoring",
        }
        assert expected_sections.issubset(set(data.keys()))

    def test_python_quality_gates(self) -> None:
        env = _get_template_env()
        template = env.get_template("config.yaml.j2")
        rendered = template.render(project_name="test", project_root=".")
        data = yaml.safe_load(rendered)
        gates = data["quality_gates"]
        assert "ruff" in gates["pre_commit"]
        assert "pyright" in gates["type_check"]
        assert "pytest" in gates["test"]


class TestAgentTemplates:
    def test_all_agents_exist(self) -> None:
        templates_dir = Path(__file__).resolve().parents[2] / "templates" / "python" / "agents"
        expected = {
            "project-leader.md",
            "engineering-manager.md",
            "technical-architect.md",
            "product-director.md",
            "devops-agent.md",
            "norwood-discovery.md",
            "debugging-agent.md",
        }
        actual = {f.name for f in templates_dir.iterdir() if f.suffix == ".md"}
        assert expected == actual

    def test_agent_templates_render(self) -> None:
        env = _get_template_env()
        agents = [
            "agents/project-leader.md",
            "agents/engineering-manager.md",
            "agents/technical-architect.md",
            "agents/product-director.md",
            "agents/devops-agent.md",
            "agents/debugging-agent.md",
        ]
        for name in agents:
            template = env.get_template(name)
            rendered = template.render(
                project_name="test-project",
                agent_roster="- engineering-manager\n- technical-architect",
            )
            assert "test-project" in rendered
            assert len(rendered) > 100


class TestBoardTemplates:
    def test_all_four_board_files_exist(self) -> None:
        templates_dir = Path(__file__).resolve().parents[2] / "templates" / "python" / "board"
        expected = {
            "project-board.md",
            "question-queue.md",
            "decision-log.md",
            "announcements.md",
        }
        actual = {f.name for f in templates_dir.iterdir() if f.suffix == ".md"}
        assert expected == actual

    def test_board_templates_render(self) -> None:
        env = _get_template_env()
        boards = [
            "board/project-board.md",
            "board/question-queue.md",
            "board/decision-log.md",
            "board/announcements.md",
        ]
        for name in boards:
            template = env.get_template(name)
            rendered = template.render(project_name="test-project")
            assert "test-project" in rendered
