"""Tests for UAT test generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.uat.task_context import TaskContext
from autopilot.uat.test_generator import (
    GeneratedTestFile,
    TestGenerator,
    _sanitize_id,
    _slugify,
)

# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestGeneratedTestFile:
    def test_frozen(self) -> None:
        g = GeneratedTestFile(file_path="x.py", test_count=0)
        with pytest.raises(AttributeError):
            g.file_path = "y.py"  # type: ignore[misc]

    def test_defaults(self) -> None:
        g = GeneratedTestFile(file_path="x.py", test_count=0)
        assert g.test_names == []
        assert g.source_code == ""


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic(self) -> None:
        assert _slugify("Parser works correctly") == "parser_works_correctly"

    def test_special_chars(self) -> None:
        slug = _slugify("All tests pass (100%)")
        assert slug.isidentifier() or slug.replace("_", "a").isalnum()
        assert "%" not in slug

    def test_empty_returns_criterion(self) -> None:
        assert _slugify("") == "criterion"

    def test_max_length(self) -> None:
        long_text = "a" * 200
        assert len(_slugify(long_text, max_length=60)) <= 60


class TestSanitizeId:
    def test_numeric_id(self) -> None:
        assert _sanitize_id("046") == "046"

    def test_hyphenated_id(self) -> None:
        assert _sanitize_id("046-1") == "046_1"

    def test_dotted_id(self) -> None:
        assert _sanitize_id("1.2.3") == "1_2_3"


# ---------------------------------------------------------------------------
# TestGenerator tests
# ---------------------------------------------------------------------------


class TestTestGenerator:
    @pytest.fixture()
    def generator(self) -> TestGenerator:
        return TestGenerator()

    @pytest.fixture()
    def sample_context(self) -> TaskContext:
        return TaskContext(
            task_id="046",
            title="Spec Index Builder",
            sprint_points=3,
            acceptance_criteria=[
                "Parser works correctly",
                "All tests pass",
                "Sections are extracted by heading hierarchy",
            ],
        )

    def test_generates_correct_count(
        self, generator: TestGenerator, sample_context: TaskContext
    ) -> None:
        result = generator.generate_acceptance_tests(sample_context)
        assert result.test_count == 3
        assert len(result.test_names) == 3

    def test_file_path_format(self, generator: TestGenerator, sample_context: TaskContext) -> None:
        result = generator.generate_acceptance_tests(sample_context)
        assert result.file_path == "tests/uat/test_task_046_uat.py"

    def test_test_names_follow_convention(
        self, generator: TestGenerator, sample_context: TaskContext
    ) -> None:
        result = generator.generate_acceptance_tests(sample_context)
        for name in result.test_names:
            assert name.startswith("test_task_046_")

    def test_source_code_is_valid_python(
        self, generator: TestGenerator, sample_context: TaskContext
    ) -> None:
        result = generator.generate_acceptance_tests(sample_context)
        # Should compile without syntax errors
        compile(result.source_code, "<test>", "exec")

    def test_source_contains_future_annotations(
        self, generator: TestGenerator, sample_context: TaskContext
    ) -> None:
        result = generator.generate_acceptance_tests(sample_context)
        assert "from __future__ import annotations" in result.source_code

    def test_source_contains_pytest_import(
        self, generator: TestGenerator, sample_context: TaskContext
    ) -> None:
        result = generator.generate_acceptance_tests(sample_context)
        assert "import pytest" in result.source_code

    def test_empty_criteria_generates_no_tests(self, generator: TestGenerator) -> None:
        ctx = TaskContext(task_id="999", title="Empty", acceptance_criteria=[])
        result = generator.generate_acceptance_tests(ctx)
        assert result.test_count == 0

    def test_max_tests_capped_by_story_points(self) -> None:
        gen = TestGenerator(max_tests_per_sp=2)
        ctx = TaskContext(
            task_id="001",
            title="Small task",
            sprint_points=1,
            acceptance_criteria=[f"Criterion {i}" for i in range(10)],
        )
        result = gen.generate_acceptance_tests(ctx)
        assert result.test_count == 2  # 2 * 1 SP = 2

    def test_duplicate_criteria_get_unique_slugs(self, generator: TestGenerator) -> None:
        ctx = TaskContext(
            task_id="001",
            title="Dup test",
            sprint_points=5,
            acceptance_criteria=["All tests pass", "All tests pass", "All tests pass"],
        )
        result = generator.generate_acceptance_tests(ctx)
        assert len(set(result.test_names)) == 3  # All unique

    def test_write_test_file(
        self, generator: TestGenerator, sample_context: TaskContext, tmp_path: Path
    ) -> None:
        generated = generator.generate_acceptance_tests(sample_context)
        path = generator.write_test_file(generated, tmp_path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "test_task_046" in content
