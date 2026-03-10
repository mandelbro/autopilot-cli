"""Tests for the DuplicationRule enforcement rule.

TDD: tests define the contract for duplication.py before implementation.
"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autopilot.core.models import CheckResult, ViolationSeverity
from autopilot.enforcement.rules.base import RuleConfig
from autopilot.enforcement.rules.duplication import DuplicationRule

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write_py(tmp_path: Path, name: str, source: str) -> Path:
    """Write a Python source file to a temp directory and return its path."""
    p = tmp_path / name
    p.write_text(textwrap.dedent(source))
    return p


# ---------------------------------------------------------------------------
# RuleConfig tests
# ---------------------------------------------------------------------------


class TestRuleConfig:
    def test_defaults(self) -> None:
        cfg = RuleConfig()
        assert cfg.min_lines == 6
        assert cfg.similarity_threshold == 0.80
        assert cfg.severity == ViolationSeverity.WARNING

    def test_custom_values(self) -> None:
        cfg = RuleConfig(min_lines=10, similarity_threshold=0.90)
        assert cfg.min_lines == 10
        assert cfg.similarity_threshold == 0.90

    def test_invalid_similarity_raises(self) -> None:
        with pytest.raises(ValueError):
            RuleConfig(similarity_threshold=1.5)

    def test_invalid_min_lines_raises(self) -> None:
        with pytest.raises(ValueError):
            RuleConfig(min_lines=0)


# ---------------------------------------------------------------------------
# DuplicationRule protocol surface
# ---------------------------------------------------------------------------


class TestDuplicationRuleInterface:
    def test_category(self) -> None:
        rule = DuplicationRule()
        assert rule.category == "duplication"

    def test_name(self) -> None:
        rule = DuplicationRule()
        assert rule.name == "duplicate-code-blocks"

    def test_check_returns_check_result(self, tmp_path: Path) -> None:
        rule = DuplicationRule()
        result = rule.check([])
        assert isinstance(result, CheckResult)
        assert result.category == "duplication"

    def test_empty_file_list_has_no_violations(self, tmp_path: Path) -> None:
        rule = DuplicationRule()
        result = rule.check([])
        assert len(result.violations) == 0
        assert result.files_scanned == 0


# ---------------------------------------------------------------------------
# No-duplicate scenarios (should NOT flag)
# ---------------------------------------------------------------------------


class TestNoDuplicationDetected:
    def test_single_file_no_flag(self, tmp_path: Path) -> None:
        f = write_py(
            tmp_path,
            "single.py",
            """\
            def add(a: int, b: int) -> int:
                return a + b
            """,
        )
        result = DuplicationRule().check([f])
        assert len(result.violations) == 0

    def test_distinct_functions_no_flag(self, tmp_path: Path) -> None:
        f1 = write_py(
            tmp_path,
            "math_utils.py",
            """\
            def multiply(a: int, b: int) -> int:
                result = a * b
                if result < 0:
                    raise ValueError("negative")
                return result

            def divide(a: float, b: float) -> float:
                if b == 0:
                    raise ZeroDivisionError
                return a / b
            """,
        )
        f2 = write_py(
            tmp_path,
            "string_utils.py",
            """\
            def slugify(text: str) -> str:
                text = text.lower()
                text = text.strip()
                text = text.replace(" ", "-")
                return text

            def truncate(text: str, max_len: int) -> str:
                if len(text) <= max_len:
                    return text
                return text[:max_len] + "..."
            """,
        )
        result = DuplicationRule().check([f1, f2])
        assert len(result.violations) == 0

    def test_short_similar_blocks_below_threshold_no_flag(self, tmp_path: Path) -> None:
        # Only 3 lines — below min_lines=6
        f1 = write_py(
            tmp_path,
            "a.py",
            """\
            def greet(name: str) -> str:
                msg = f"Hello, {name}"
                return msg
            """,
        )
        f2 = write_py(
            tmp_path,
            "b.py",
            """\
            def greet(name: str) -> str:
                msg = f"Hello, {name}"
                return msg
            """,
        )
        result = DuplicationRule().check([f1, f2])
        assert len(result.violations) == 0

    def test_test_files_excluded_by_default(self, tmp_path: Path) -> None:
        src = write_py(
            tmp_path,
            "validators.py",
            """\
            import re

            def validate_email(email: str) -> bool:
                pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'
                if not email:
                    return False
                match = re.match(pattern, email)
                return match is not None
            """,
        )
        test_file = write_py(
            tmp_path,
            "test_validators.py",
            """\
            import re

            def validate_email(email: str) -> bool:
                pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'
                if not email:
                    return False
                match = re.match(pattern, email)
                return match is not None
            """,
        )
        result = DuplicationRule().check([src, test_file])
        # test_validators.py should be excluded; only 1 real file → no pair → no violations
        assert len(result.violations) == 0


# ---------------------------------------------------------------------------
# Duplication detection scenarios (SHOULD flag)
# ---------------------------------------------------------------------------


class TestDuplicationDetected:
    def test_identical_function_bodies_flagged(self, tmp_path: Path) -> None:
        body = """\
        def validate_email(email: str) -> bool:
            import re
            pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'
            if not email:
                return False
            match = re.match(pattern, email)
            return match is not None
        """
        f1 = write_py(tmp_path, "service_a.py", body)
        f2 = write_py(tmp_path, "service_b.py", body)

        result = DuplicationRule().check([f1, f2])

        assert len(result.violations) >= 1
        v = result.violations[0]
        assert v.category == "duplication"
        assert v.rule == "duplicate-code-blocks"
        assert v.severity == ViolationSeverity.WARNING
        assert "service_a.py" in v.file or "service_b.py" in v.file
        assert v.line > 0
        assert "duplicate" in v.message.lower() or "similar" in v.message.lower()

    def test_violation_includes_suggestion(self, tmp_path: Path) -> None:
        body = """\
        def parse_date(raw: str) -> str:
            from datetime import datetime
            formats = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"]
            for fmt in formats:
                try:
                    dt = datetime.strptime(raw, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            raise ValueError(f"Unrecognised date: {raw}")
        """
        f1 = write_py(tmp_path, "billing.py", body)
        f2 = write_py(tmp_path, "reporting.py", body)

        result = DuplicationRule().check([f1, f2])
        assert len(result.violations) >= 1
        assert result.violations[0].suggestion != ""

    def test_files_scanned_count_correct(self, tmp_path: Path) -> None:
        body = """\
        def validate_email(email: str) -> bool:
            import re
            pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'
            if not email:
                return False
            match = re.match(pattern, email)
            return match is not None
        """
        f1 = write_py(tmp_path, "a.py", body)
        f2 = write_py(tmp_path, "b.py", body)

        result = DuplicationRule().check([f1, f2])
        assert result.files_scanned == 2

    def test_multiple_duplicate_pairs_reported(self, tmp_path: Path) -> None:
        """Two unrelated duplicate blocks across three files should produce violations."""
        email_body = """\
        def validate_email(email: str) -> bool:
            import re
            pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'
            if not email:
                return False
            match = re.match(pattern, email)
            return match is not None
        """
        f1 = write_py(tmp_path, "svc_a.py", email_body)
        f2 = write_py(tmp_path, "svc_b.py", email_body)
        # A third, unrelated file adds to scanned count but not violations
        write_py(tmp_path, "svc_c.py", "x = 1\n")

        result = DuplicationRule().check([f1, f2, tmp_path / "svc_c.py"])
        assert len(result.violations) >= 1

    def test_high_similarity_but_not_identical_flagged(self, tmp_path: Path) -> None:
        """Functions that differ only in variable names should be flagged."""
        f1 = write_py(
            tmp_path,
            "auth_service.py",
            """\
            def get_user_token(user_id: str) -> str:
                import hashlib
                import time
                timestamp = int(time.time())
                raw = f"{user_id}:{timestamp}:secret_key"
                token = hashlib.sha256(raw.encode()).hexdigest()
                return token
            """,
        )
        f2 = write_py(
            tmp_path,
            "api_service.py",
            """\
            def get_api_token(api_id: str) -> str:
                import hashlib
                import time
                timestamp = int(time.time())
                raw = f"{api_id}:{timestamp}:secret_key"
                token = hashlib.sha256(raw.encode()).hexdigest()
                return token
            """,
        )
        result = DuplicationRule().check([f1, f2])
        # Structural similarity should catch this (differs only in names)
        assert len(result.violations) >= 1

    def test_error_severity_configurable(self, tmp_path: Path) -> None:
        cfg = RuleConfig(severity=ViolationSeverity.ERROR)
        body = """\
        def validate_email(email: str) -> bool:
            import re
            pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'
            if not email:
                return False
            match = re.match(pattern, email)
            return match is not None
        """
        f1 = write_py(tmp_path, "x.py", body)
        f2 = write_py(tmp_path, "y.py", body)

        result = DuplicationRule(config=cfg).check([f1, f2])
        assert all(v.severity == ViolationSeverity.ERROR for v in result.violations)


# ---------------------------------------------------------------------------
# Cross-file pattern detection (pattern-name heuristics)
# ---------------------------------------------------------------------------


class TestPatternHeuristics:
    """Test that well-known duplication anti-patterns are named correctly."""

    def test_email_validator_pattern_name(self, tmp_path: Path) -> None:
        body = """\
        def validate_email(email: str) -> bool:
            import re
            pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'
            if not email:
                return False
            match = re.match(pattern, email)
            return match is not None
        """
        f1 = write_py(tmp_path, "a.py", body)
        f2 = write_py(tmp_path, "b.py", body)
        result = DuplicationRule().check([f1, f2])
        messages = " ".join(v.message for v in result.violations).lower()
        assert "email" in messages or "duplicate" in messages

    def test_nonexistent_file_skipped_gracefully(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.py"
        result = DuplicationRule().check([missing])
        assert len(result.violations) == 0
        assert result.files_scanned == 0

    def test_syntax_error_file_skipped_gracefully(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad_syntax.py"
        bad.write_text("def broken(:\n    pass\n")
        result = DuplicationRule().check([bad])
        assert len(result.violations) == 0
        assert result.files_scanned == 0
