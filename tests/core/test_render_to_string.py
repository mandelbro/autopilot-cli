"""Tests for TemplateRenderer.render_to_string (Task 007)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from jinja2 import UndefinedError

from autopilot.core.templates import TemplateRenderer

if TYPE_CHECKING:
    from pathlib import Path


class TestRenderToString:
    def test_renders_simple_template(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "mytype"
        tpl_dir.mkdir()
        (tpl_dir / "hello.j2").write_text("Hello, {{ name }}!")

        renderer = TemplateRenderer("mytype", package_templates_dir=tmp_path)
        result = renderer.render_to_string("hello.j2", {"name": "World"})
        assert result == "Hello, World!"

    def test_raises_on_missing_variable(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "mytype"
        tpl_dir.mkdir()
        (tpl_dir / "strict.j2").write_text("{{ missing_var }}")

        renderer = TemplateRenderer("mytype", package_templates_dir=tmp_path)
        with pytest.raises(UndefinedError):
            renderer.render_to_string("strict.j2", {})

    def test_user_override_takes_precedence(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg" / "mytype"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "greet.j2").write_text("package: {{ name }}")

        user_dir = tmp_path / "user" / "mytype"
        user_dir.mkdir(parents=True)
        (user_dir / "greet.j2").write_text("user: {{ name }}")

        renderer = TemplateRenderer(
            "mytype",
            package_templates_dir=tmp_path / "pkg",
            user_templates_dir=tmp_path / "user",
        )
        result = renderer.render_to_string("greet.j2", {"name": "test"})
        assert result == "user: test"

    def test_render_to_still_works(self, tmp_path: Path) -> None:
        tpl_dir = tmp_path / "pkg" / "mytype"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "file.txt.j2").write_text("content: {{ val }}")

        renderer = TemplateRenderer("mytype", package_templates_dir=tmp_path / "pkg")
        output = tmp_path / "output"
        output.mkdir()
        files = renderer.render_to(output, {"val": "hello"})

        assert "file.txt" in files
        assert (output / "file.txt").read_text() == "content: hello"
