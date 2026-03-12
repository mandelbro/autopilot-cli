"""Tests for TemplateRenderer (Task 016)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autopilot.core.templates import TemplateRenderer, list_available_templates

if TYPE_CHECKING:
    from pathlib import Path


class TestListAvailableTemplates:
    def test_lists_package_templates(self) -> None:
        templates = list_available_templates()
        assert "python" in templates

    def test_includes_user_templates(self, tmp_path: Path) -> None:
        user_dir = tmp_path / "templates"
        (user_dir / "custom").mkdir(parents=True)
        from unittest.mock import patch

        with patch("autopilot.core.templates.get_global_dir", return_value=tmp_path):
            templates = list_available_templates()
            assert "custom" in templates


class TestTemplateRenderer:
    def test_render_to_creates_files(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg_templates"
        tpl_dir = pkg_dir / "test-type"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "config.yaml.j2").write_text("name: {{ project_name }}\n")
        (tpl_dir / "readme.md").write_text("# {{ project_name }}\n")

        output = tmp_path / "output"
        output.mkdir()

        renderer = TemplateRenderer(
            "test-type",
            package_templates_dir=pkg_dir,
            user_templates_dir=tmp_path / "user_templates",
        )
        files = renderer.render_to(output, {"project_name": "my-app"})
        assert "config.yaml" in files
        assert "readme.md" in files
        assert (output / "config.yaml").read_text() == "name: my-app\n"

    def test_user_templates_override_package(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg"
        tpl_dir = pkg_dir / "mytype"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "config.yaml").write_text("package default")

        user_dir = tmp_path / "user"
        user_tpl = user_dir / "mytype"
        user_tpl.mkdir(parents=True)
        (user_tpl / "config.yaml").write_text("user override")

        output = tmp_path / "output"
        output.mkdir()

        renderer = TemplateRenderer(
            "mytype",
            package_templates_dir=pkg_dir,
            user_templates_dir=user_dir,
        )
        renderer.render_to(output, {})
        assert (output / "config.yaml").read_text() == "user override"

    def test_missing_template_type_raises(self, tmp_path: Path) -> None:
        renderer = TemplateRenderer(
            "nonexistent",
            package_templates_dir=tmp_path / "empty",
            user_templates_dir=tmp_path / "empty2",
        )
        with pytest.raises(ValueError, match="No templates found"):
            renderer.render_to(tmp_path / "out", {})

    def test_jinja2_variable_substitution(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg"
        tpl_dir = pkg_dir / "test"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "output.txt.j2").write_text("Hello {{ name }}, type={{ project_type }}")

        output = tmp_path / "output"
        output.mkdir()

        renderer = TemplateRenderer(
            "test",
            package_templates_dir=pkg_dir,
            user_templates_dir=tmp_path / "nope",
        )
        renderer.render_to(output, {"name": "World", "project_type": "python"})
        assert (output / "output.txt").read_text() == "Hello World, type=python"

    def test_subdirectory_templates(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg"
        tpl_dir = pkg_dir / "test"
        sub = tpl_dir / "subdir"
        sub.mkdir(parents=True)
        (sub / "nested.txt").write_text("nested content")

        output = tmp_path / "output"
        output.mkdir()

        renderer = TemplateRenderer(
            "test",
            package_templates_dir=pkg_dir,
            user_templates_dir=tmp_path / "nope",
        )
        renderer.render_to(output, {})
        assert (output / "subdir" / "nested.txt").read_text() == "nested content"

    def test_skips_underscore_prefixed(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg"
        tpl_dir = pkg_dir / "test"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "visible.txt").write_text("visible")
        (tpl_dir / "_hidden.txt").write_text("hidden")

        output = tmp_path / "output"
        output.mkdir()

        renderer = TemplateRenderer(
            "test",
            package_templates_dir=pkg_dir,
            user_templates_dir=tmp_path / "nope",
        )
        files = renderer.render_to(output, {})
        assert "visible.txt" in files
        assert "_hidden.txt" not in files


class TestStrictUndefined:
    def test_missing_variable_raises(self, tmp_path: Path) -> None:
        from jinja2.exceptions import UndefinedError

        pkg_dir = tmp_path / "pkg"
        tpl_dir = pkg_dir / "test"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "config.yaml.j2").write_text("name: {{ missing_var }}\n")

        output = tmp_path / "output"
        output.mkdir()

        renderer = TemplateRenderer(
            "test",
            package_templates_dir=pkg_dir,
            user_templates_dir=tmp_path / "nope",
        )
        with pytest.raises(UndefinedError):
            renderer.render_to(output, {})


class TestTemplateInheritance:
    def test_extends_parent(self, tmp_path: Path) -> None:
        import yaml

        pkg_dir = tmp_path / "pkg"

        # Parent type
        parent_dir = pkg_dir / "base"
        parent_dir.mkdir(parents=True)
        (parent_dir / "base-file.txt").write_text("from base")

        # Child type with extends
        child_dir = pkg_dir / "child"
        child_dir.mkdir(parents=True)
        (child_dir / "_template.yaml").write_text(yaml.dump({"extends": "base"}))
        (child_dir / "child-file.txt").write_text("from child")

        output = tmp_path / "output"
        output.mkdir()

        renderer = TemplateRenderer(
            "child",
            package_templates_dir=pkg_dir,
            user_templates_dir=tmp_path / "nope",
        )
        files = renderer.render_to(output, {})
        assert "base-file.txt" in files
        assert "child-file.txt" in files
        assert (output / "base-file.txt").read_text() == "from base"
        assert (output / "child-file.txt").read_text() == "from child"


class TestTemplateValidation:
    def test_validate_all_present(self, tmp_path: Path) -> None:
        import yaml

        pkg_dir = tmp_path / "pkg"
        tpl_dir = pkg_dir / "test"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "_template.yaml").write_text(yaml.dump({"expected_files": ["config.yaml"]}))
        (tpl_dir / "config.yaml").write_text("content")

        renderer = TemplateRenderer(
            "test",
            package_templates_dir=pkg_dir,
            user_templates_dir=tmp_path / "nope",
        )
        assert renderer.validate() == []

    def test_validate_missing_file(self, tmp_path: Path) -> None:
        import yaml

        pkg_dir = tmp_path / "pkg"
        tpl_dir = pkg_dir / "test"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "_template.yaml").write_text(yaml.dump({"expected_files": ["missing.txt"]}))

        renderer = TemplateRenderer(
            "test",
            package_templates_dir=pkg_dir,
            user_templates_dir=tmp_path / "nope",
        )
        issues = renderer.validate()
        assert len(issues) == 1
        assert "missing.txt" in issues[0]

    def test_validate_j2_extension_accepted(self, tmp_path: Path) -> None:
        import yaml

        pkg_dir = tmp_path / "pkg"
        tpl_dir = pkg_dir / "test"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "_template.yaml").write_text(yaml.dump({"expected_files": ["config.yaml"]}))
        (tpl_dir / "config.yaml.j2").write_text("content")

        renderer = TemplateRenderer(
            "test",
            package_templates_dir=pkg_dir,
            user_templates_dir=tmp_path / "nope",
        )
        assert renderer.validate() == []
