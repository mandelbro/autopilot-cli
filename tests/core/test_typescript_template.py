"""Tests for TypeScript project template (Task 081)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "typescript"

# Common context variables used across template rendering
_RENDER_CONTEXT = {
    "project_name": "test-ts-project",
    "project_root": "/tmp/test-ts-project",
    "project_type": "typescript",
    "agent_roster": "- engineering-manager\n- technical-architect",
}


@pytest.fixture
def ts_env() -> Environment:
    """Jinja2 environment configured for TypeScript templates."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )


class TestConfigTemplate:
    """Tests for config.yaml.j2 rendering."""

    def test_renders_valid_yaml(self, ts_env: Environment) -> None:
        template = ts_env.get_template("config.yaml.j2")
        rendered = template.render(**_RENDER_CONTEXT)
        config = yaml.safe_load(rendered)
        assert isinstance(config, dict)

    def test_project_type_is_typescript(self, ts_env: Environment) -> None:
        template = ts_env.get_template("config.yaml.j2")
        rendered = template.render(**_RENDER_CONTEXT)
        config = yaml.safe_load(rendered)
        assert config["project"]["type"] == "typescript"

    def test_project_name_substituted(self, ts_env: Environment) -> None:
        template = ts_env.get_template("config.yaml.j2")
        rendered = template.render(**_RENDER_CONTEXT)
        config = yaml.safe_load(rendered)
        assert config["project"]["name"] == "test-ts-project"

    def test_quality_gates_use_pnpm(self, ts_env: Environment) -> None:
        template = ts_env.get_template("config.yaml.j2")
        rendered = template.render(**_RENDER_CONTEXT)
        config = yaml.safe_load(rendered)
        gates = config["quality_gates"]
        assert "pnpm lint" in gates["pre_commit"]
        assert "pnpm typecheck" in gates["type_check"]
        assert "pnpm test" in gates["test"]
        assert "pnpm lint" in gates["all"]
        assert "pnpm typecheck" in gates["all"]
        assert "pnpm test" in gates["all"]

    def test_no_python_tooling_references(self, ts_env: Environment) -> None:
        template = ts_env.get_template("config.yaml.j2")
        rendered = template.render(**_RENDER_CONTEXT)
        assert "uv run" not in rendered
        assert "ruff" not in rendered
        assert "pyright" not in rendered
        assert "pytest" not in rendered

    def test_init_command_references_typescript(self, ts_env: Environment) -> None:
        template = ts_env.get_template("config.yaml.j2")
        rendered = template.render(**_RENDER_CONTEXT)
        assert "--type typescript" in rendered


class TestAgentTemplates:
    """Tests for agent prompt templates."""

    @pytest.mark.parametrize(
        "template_name",
        [
            "agents/project-leader.md",
            "agents/engineering-manager.md",
            "agents/product-director.md",
            "agents/technical-architect.md",
            "agents/norwood-discovery.md",
        ],
    )
    def test_agent_template_renders(
        self, ts_env: Environment, template_name: str
    ) -> None:
        template = ts_env.get_template(template_name)
        rendered = template.render(**_RENDER_CONTEXT)
        assert "test-ts-project" in rendered

    def test_project_leader_references_typescript_gates(
        self, ts_env: Environment
    ) -> None:
        template = ts_env.get_template("agents/project-leader.md")
        rendered = template.render(**_RENDER_CONTEXT)
        assert "pnpm lint" in rendered
        assert "pnpm typecheck" in rendered
        assert "pnpm test" in rendered
        assert "TypeScript" in rendered

    def test_engineering_manager_references_typescript_tools(
        self, ts_env: Environment
    ) -> None:
        template = ts_env.get_template("agents/engineering-manager.md")
        rendered = template.render(**_RENDER_CONTEXT)
        assert "pnpm lint" in rendered
        assert "pnpm typecheck" in rendered
        assert "pnpm test" in rendered
        assert "ESLint" in rendered
        assert "TypeScript" in rendered

    def test_technical_architect_references_typescript(
        self, ts_env: Environment
    ) -> None:
        template = ts_env.get_template("agents/technical-architect.md")
        rendered = template.render(**_RENDER_CONTEXT)
        assert "TypeScript" in rendered

    def test_product_director_renders(self, ts_env: Environment) -> None:
        template = ts_env.get_template("agents/product-director.md")
        rendered = template.render(**_RENDER_CONTEXT)
        assert "TypeScript" in rendered
        assert "test-ts-project" in rendered

    def test_norwood_discovery_renders(self, ts_env: Environment) -> None:
        template = ts_env.get_template("agents/norwood-discovery.md")
        rendered = template.render(**_RENDER_CONTEXT)
        assert "test-ts-project" in rendered
        assert "typescript" in rendered

    def test_devops_agent_renders(self, ts_env: Environment) -> None:
        template = ts_env.get_template("agents/devops-agent.md")
        rendered = template.render(**_RENDER_CONTEXT)
        assert "test-ts-project" in rendered

    def test_devops_agent_typescript_error_patterns(
        self, ts_env: Environment
    ) -> None:
        template = ts_env.get_template("agents/devops-agent.md")
        rendered = template.render(**_RENDER_CONTEXT)
        assert "Cannot find module" in rendered
        assert "ERR_MODULE_NOT_FOUND" in rendered

    @pytest.mark.parametrize(
        "template_name",
        [
            "agents/project-leader.md",
            "agents/engineering-manager.md",
            "agents/technical-architect.md",
        ],
    )
    def test_no_python_references_in_agent_prompts(
        self, ts_env: Environment, template_name: str
    ) -> None:
        template = ts_env.get_template(template_name)
        rendered = template.render(**_RENDER_CONTEXT)
        assert "uv run" not in rendered
        assert "ruff check" not in rendered
        assert "pyright" not in rendered
        assert "PEP 8" not in rendered


class TestBoardTemplates:
    """Tests for board markdown templates."""

    @pytest.mark.parametrize(
        "template_name",
        [
            "board/project-board.md",
            "board/question-queue.md",
            "board/decision-log.md",
            "board/announcements.md",
        ],
    )
    def test_board_template_renders(
        self, ts_env: Environment, template_name: str
    ) -> None:
        template = ts_env.get_template(template_name)
        rendered = template.render(**_RENDER_CONTEXT)
        assert "test-ts-project" in rendered

    def test_project_board_has_expected_sections(
        self, ts_env: Environment
    ) -> None:
        template = ts_env.get_template("board/project-board.md")
        rendered = template.render(**_RENDER_CONTEXT)
        assert "Sprint Status" in rendered
        assert "Active Work" in rendered
        assert "Blockers" in rendered
        assert "Completed This Sprint" in rendered


class TestTemplateRendererIntegration:
    """Test TypeScript templates work with the TemplateRenderer."""

    def test_typescript_in_available_templates(self) -> None:
        from autopilot.core.templates import list_available_templates

        templates = list_available_templates()
        assert "typescript" in templates

    def test_render_all_templates(self, tmp_path: Path) -> None:
        from autopilot.core.templates import TemplateRenderer

        output = tmp_path / "output"
        output.mkdir()

        renderer = TemplateRenderer("typescript")
        files = renderer.render_to(output, _RENDER_CONTEXT)
        assert "config.yaml" in files
        assert "agents/project-leader.md" in files
        assert "agents/engineering-manager.md" in files
        assert "agents/product-director.md" in files
        assert "agents/technical-architect.md" in files
        assert "agents/norwood-discovery.md" in files
        assert "agents/devops-agent.md" in files
        assert "board/project-board.md" in files
        assert "board/question-queue.md" in files
        assert "board/decision-log.md" in files
        assert "board/announcements.md" in files

    def test_rendered_config_is_valid_yaml(self, tmp_path: Path) -> None:
        from autopilot.core.templates import TemplateRenderer

        output = tmp_path / "output"
        output.mkdir()

        renderer = TemplateRenderer("typescript")
        renderer.render_to(output, _RENDER_CONTEXT)

        config = yaml.safe_load((output / "config.yaml").read_text())
        assert config["project"]["type"] == "typescript"
        assert "pnpm" in config["quality_gates"]["pre_commit"]
