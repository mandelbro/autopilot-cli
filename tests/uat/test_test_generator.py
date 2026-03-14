"""Tests for UAT test generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.uat.spec_index import SpecEntry, SpecIndex
from autopilot.uat.task_context import TaskContext
from autopilot.uat.test_generator import (
    BehavioralTestGenerator,
    ComplianceTestGenerator,
    GeneratedTestFile,
    TestGenerator,
    UXTestGenerator,
    _parse_user_story,
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


# ---------------------------------------------------------------------------
# User story parser tests (Task 071)
# ---------------------------------------------------------------------------


class TestParseUserStory:
    def test_parses_standard_story(self) -> None:
        story = "As a developer, I want to run tests, so that I verify correctness."
        parts = _parse_user_story(story)
        assert parts["role"] == "developer"
        assert "run tests" in parts["action"]
        assert "verify correctness" in parts["outcome"]

    def test_parses_story_with_an(self) -> None:
        story = "As an admin, I want to manage users, so that access is controlled."
        parts = _parse_user_story(story)
        assert parts["role"] == "admin"

    def test_fallback_for_non_standard_story(self) -> None:
        story = "Just some text that isn't a user story"
        parts = _parse_user_story(story)
        assert parts["role"] == "user"
        assert parts["action"] == story.strip()


# ---------------------------------------------------------------------------
# BehavioralTestGenerator tests (Task 071)
# ---------------------------------------------------------------------------


class TestBehavioralTestGenerator:
    @pytest.fixture()
    def generator(self) -> BehavioralTestGenerator:
        return BehavioralTestGenerator()

    @pytest.fixture()
    def story_context(self) -> TaskContext:
        return TaskContext(
            task_id="071",
            title="Behavioral test generator",
            sprint_points=3,
            user_story=(
                "As a UAT agent, I want to generate behavioral tests "
                "from user stories, so that the system verifies end-to-end workflows."
            ),
            acceptance_criteria=[
                "User stories are parsed into testable components",
                "Generated tests follow Given-When-Then structure",
                "Test names are descriptive and unique",
            ],
        )

    def test_generates_from_user_story(
        self, generator: BehavioralTestGenerator, story_context: TaskContext
    ) -> None:
        result = generator.generate_behavioral_tests(story_context)
        assert result.test_count >= 1
        assert all(name.startswith("test_user_story_071_") for name in result.test_names)

    def test_file_path_format(
        self, generator: BehavioralTestGenerator, story_context: TaskContext
    ) -> None:
        result = generator.generate_behavioral_tests(story_context)
        assert result.file_path == "tests/uat/test_task_071_behavioral.py"

    def test_source_is_valid_python(
        self, generator: BehavioralTestGenerator, story_context: TaskContext
    ) -> None:
        result = generator.generate_behavioral_tests(story_context)
        compile(result.source_code, "<test>", "exec")

    def test_contains_given_when_then(
        self, generator: BehavioralTestGenerator, story_context: TaskContext
    ) -> None:
        result = generator.generate_behavioral_tests(story_context)
        assert "# Given:" in result.source_code
        assert "# When:" in result.source_code
        assert "# Then:" in result.source_code

    def test_empty_story_generates_no_tests(self, generator: BehavioralTestGenerator) -> None:
        ctx = TaskContext(task_id="999", title="No story", user_story="")
        result = generator.generate_behavioral_tests(ctx)
        assert result.test_count == 0

    def test_unique_test_names(
        self, generator: BehavioralTestGenerator, story_context: TaskContext
    ) -> None:
        result = generator.generate_behavioral_tests(story_context)
        assert len(set(result.test_names)) == len(result.test_names)


# ---------------------------------------------------------------------------
# ComplianceTestGenerator tests (Task 072)
# ---------------------------------------------------------------------------


class TestComplianceTestGenerator:
    @pytest.fixture()
    def generator(self) -> ComplianceTestGenerator:
        return ComplianceTestGenerator()

    @pytest.fixture()
    def spec_index(self) -> SpecIndex:
        return SpecIndex(
            entries=[
                SpecEntry(
                    spec_id="RFC-R001",
                    document="RFC",
                    section="Config > Fields",
                    requirement_text="Config MUST include project_name field",
                ),
                SpecEntry(
                    spec_id="RFC-R002",
                    document="RFC",
                    section="SQL > Tables",
                    requirement_text="Sessions table MUST have id column",
                ),
                SpecEntry(
                    spec_id="RFC-R003",
                    document="RFC",
                    section="CLI > Commands",
                    requirement_text="CLI SHOULD register init command",
                ),
            ],
            total_requirements=3,
            testable_count=3,
        )

    @pytest.fixture()
    def context(self) -> TaskContext:
        return TaskContext(task_id="072", title="Compliance test generator", sprint_points=3)

    def test_generates_from_spec_index(
        self,
        generator: ComplianceTestGenerator,
        context: TaskContext,
        spec_index: SpecIndex,
    ) -> None:
        result = generator.generate_compliance_tests(context, spec_index)
        assert result.test_count == 3
        assert all(name.startswith("test_rfc_") for name in result.test_names)

    def test_file_path_format(
        self,
        generator: ComplianceTestGenerator,
        context: TaskContext,
        spec_index: SpecIndex,
    ) -> None:
        result = generator.generate_compliance_tests(context, spec_index)
        assert result.file_path == "tests/uat/test_task_072_compliance.py"

    def test_source_is_valid_python(
        self,
        generator: ComplianceTestGenerator,
        context: TaskContext,
        spec_index: SpecIndex,
    ) -> None:
        result = generator.generate_compliance_tests(context, spec_index)
        compile(result.source_code, "<test>", "exec")

    def test_empty_index_generates_no_tests(
        self, generator: ComplianceTestGenerator, context: TaskContext
    ) -> None:
        empty = SpecIndex(entries=[], total_requirements=0, testable_count=0)
        result = generator.generate_compliance_tests(context, empty)
        assert result.test_count == 0

    def test_unique_test_names(
        self,
        generator: ComplianceTestGenerator,
        context: TaskContext,
        spec_index: SpecIndex,
    ) -> None:
        result = generator.generate_compliance_tests(context, spec_index)
        assert len(set(result.test_names)) == len(result.test_names)


# ---------------------------------------------------------------------------
# UXTestGenerator tests (Task 073)
# ---------------------------------------------------------------------------


class TestUXTestGenerator:
    @pytest.fixture()
    def generator(self) -> UXTestGenerator:
        return UXTestGenerator()

    @pytest.fixture()
    def ux_index(self) -> SpecIndex:
        return SpecIndex(
            entries=[
                SpecEntry(
                    spec_id="ux-design-R001",
                    document="ux-design",
                    section="Dashboard > Layout",
                    requirement_text="Dashboard MUST fit within 80x24 terminal",
                ),
                SpecEntry(
                    spec_id="ux-design-R002",
                    document="ux-design",
                    section="Prompt > Format",
                    requirement_text="Prompt MUST show project name and agent count",
                ),
            ],
            total_requirements=2,
            testable_count=2,
        )

    @pytest.fixture()
    def context(self) -> TaskContext:
        return TaskContext(task_id="073", title="UX compliance test generator", sprint_points=3)

    def test_generates_from_ux_index(
        self,
        generator: UXTestGenerator,
        context: TaskContext,
        ux_index: SpecIndex,
    ) -> None:
        result = generator.generate_ux_tests(context, ux_index)
        assert result.test_count == 2
        assert all(name.startswith("test_ux_") for name in result.test_names)

    def test_file_path_format(
        self,
        generator: UXTestGenerator,
        context: TaskContext,
        ux_index: SpecIndex,
    ) -> None:
        result = generator.generate_ux_tests(context, ux_index)
        assert result.file_path == "tests/uat/test_task_073_ux.py"

    def test_source_is_valid_python(
        self,
        generator: UXTestGenerator,
        context: TaskContext,
        ux_index: SpecIndex,
    ) -> None:
        result = generator.generate_ux_tests(context, ux_index)
        compile(result.source_code, "<test>", "exec")

    def test_empty_index_generates_no_tests(
        self, generator: UXTestGenerator, context: TaskContext
    ) -> None:
        empty = SpecIndex(entries=[], total_requirements=0, testable_count=0)
        result = generator.generate_ux_tests(context, empty)
        assert result.test_count == 0

    def test_unique_test_names(
        self,
        generator: UXTestGenerator,
        context: TaskContext,
        ux_index: SpecIndex,
    ) -> None:
        result = generator.generate_ux_tests(context, ux_index)
        assert len(set(result.test_names)) == len(result.test_names)
