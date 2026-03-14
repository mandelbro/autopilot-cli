"""Tests for the ProtectedRegionManager (Task 064)."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from autopilot.enforcement.protected import (
    ProtectedRegion,
    ProtectedRegionManager,
    ProtectionViolation,
)

if TYPE_CHECKING:
    from pathlib import Path


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class TestScan:
    def test_scan_finds_markers(self, tmp_path: Path) -> None:
        code_lines = "x = 1\ny = 2\n"
        h = _sha256(code_lines)
        content = f"# header\n#@protected 2 {h}\nx = 1\ny = 2\n# footer\n"
        f = tmp_path / "example.py"
        f.write_text(content)

        mgr = ProtectedRegionManager()
        regions = mgr.scan(f)

        assert len(regions) == 1
        region = regions[0]
        assert region.file_path == str(f)
        assert region.start_line == 3  # line after marker (1-indexed)
        assert region.line_count == 2
        assert region.hash_value == h

    def test_scan_no_markers_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "plain.py"
        f.write_text("x = 1\ny = 2\n")

        mgr = ProtectedRegionManager()
        assert mgr.scan(f) == []

    def test_scan_multiple_markers(self, tmp_path: Path) -> None:
        block_a = "a = 1\n"
        block_b = "b = 2\nc = 3\n"
        ha = _sha256(block_a)
        hb = _sha256(block_b)
        content = f"#@protected 1 {ha}\na = 1\n#@protected 2 {hb}\nb = 2\nc = 3\n"
        f = tmp_path / "multi.py"
        f.write_text(content)

        mgr = ProtectedRegionManager()
        regions = mgr.scan(f)
        assert len(regions) == 2


class TestValidate:
    def test_validate_no_violations_when_hashes_match(self, tmp_path: Path) -> None:
        code = "x = 1\n"
        h = _sha256(code)
        f = tmp_path / "ok.py"
        f.write_text(f"#@protected 1 {h}\nx = 1\n")

        mgr = ProtectedRegionManager()
        violations = mgr.validate(f)
        assert violations == []

    def test_validate_detects_hash_mismatch(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("#@protected 1 0000deadbeef\nx = 1\n")

        mgr = ProtectedRegionManager()
        violations = mgr.validate(f)

        assert len(violations) == 1
        v = violations[0]
        assert isinstance(v, ProtectionViolation)
        assert v.expected_hash == "0000deadbeef"
        assert v.actual_hash == _sha256("x = 1\n")
        assert "hash mismatch" in v.message


class TestProtect:
    def test_protect_adds_marker_and_returns_region(self, tmp_path: Path) -> None:
        f = tmp_path / "target.py"
        f.write_text("a = 1\nb = 2\nc = 3\n")

        mgr = ProtectedRegionManager()
        region = mgr.protect(f, start_line=2, line_count=2)

        assert isinstance(region, ProtectedRegion)
        assert region.line_count == 2
        assert region.hash_value == _sha256("b = 2\nc = 3\n")

        # The marker should be in the file now
        lines = f.read_text().splitlines(keepends=True)
        assert lines[1].startswith("#@protected 2 ")
        # Original lines shifted down by 1
        assert lines[2] == "b = 2\n"
        assert lines[3] == "c = 3\n"

    def test_protect_region_validates_clean(self, tmp_path: Path) -> None:
        f = tmp_path / "clean.py"
        f.write_text("x = 1\ny = 2\n")

        mgr = ProtectedRegionManager()
        mgr.protect(f, start_line=1, line_count=2)

        violations = mgr.validate(f)
        assert violations == []


class TestUpdateHash:
    def test_update_hash_after_code_change(self, tmp_path: Path) -> None:
        code = "x = 1\n"
        old_hash = _sha256(code)
        f = tmp_path / "update.py"
        f.write_text(f"#@protected 1 {old_hash}\nx = 1\n")

        # Modify the protected line
        lines = f.read_text().splitlines(keepends=True)
        lines[1] = "x = 42\n"
        f.write_text("".join(lines))

        mgr = ProtectedRegionManager()
        region_id = f"{f}:2"
        updated = mgr.update_hash(f, region_id)

        assert updated is not None
        assert updated.hash_value == _sha256("x = 42\n")
        assert updated.region_id == region_id

        # After update, validation should pass
        violations = mgr.validate(f)
        assert violations == []

    def test_update_hash_returns_none_for_unknown_id(self, tmp_path: Path) -> None:
        code = "x = 1\n"
        h = _sha256(code)
        f = tmp_path / "nope.py"
        f.write_text(f"#@protected 1 {h}\nx = 1\n")

        mgr = ProtectedRegionManager()
        result = mgr.update_hash(f, "nonexistent:999")
        assert result is None


class TestRegionId:
    def test_region_id_format(self, tmp_path: Path) -> None:
        code = "x = 1\n"
        h = _sha256(code)
        f = tmp_path / "rid.py"
        f.write_text(f"#@protected 1 {h}\nx = 1\n")

        mgr = ProtectedRegionManager()
        regions = mgr.scan(f)
        assert len(regions) == 1
        assert regions[0].region_id == f"{f}:2"
