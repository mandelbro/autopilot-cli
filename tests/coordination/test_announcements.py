"""Tests for AnnouncementManager (Task 019)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autopilot.coordination.announcements import AnnouncementManager

if TYPE_CHECKING:
    from pathlib import Path


class TestAnnouncementManager:
    def test_post_and_list(self, tmp_path: Path) -> None:
        mgr = AnnouncementManager(tmp_path)
        a = mgr.post("Priority Shift", "Focus on auth module", "architect")
        assert a.id.startswith("ANN-")
        assert a.archived is False
        active = mgr.list_active()
        assert len(active) == 1
        assert active[0].title == "Priority Shift"

    def test_list_active_excludes_archived(self, tmp_path: Path) -> None:
        mgr = AnnouncementManager(tmp_path)
        a1 = mgr.post("Active", "Still active", "admin")
        a2 = mgr.post("To Archive", "Will be archived", "admin")
        mgr.archive(a2.id)
        active = mgr.list_active()
        assert len(active) == 1
        assert active[0].id == a1.id

    def test_list_active_ordered_newest_first(self, tmp_path: Path) -> None:
        mgr = AnnouncementManager(tmp_path)
        mgr.post("First", "first", "admin")
        mgr.post("Second", "second", "admin")
        active = mgr.list_active()
        assert active[0].title == "Second"
        assert active[1].title == "First"

    def test_archive(self, tmp_path: Path) -> None:
        mgr = AnnouncementManager(tmp_path)
        a = mgr.post("Test", "content", "admin")
        mgr.archive(a.id)
        assert len(mgr.list_active()) == 0

    def test_archive_missing_raises(self, tmp_path: Path) -> None:
        mgr = AnnouncementManager(tmp_path)
        with pytest.raises(KeyError, match="not found"):
            mgr.archive("ANN-nonexistent")

    def test_clear_all(self, tmp_path: Path) -> None:
        mgr = AnnouncementManager(tmp_path)
        mgr.post("A", "a", "admin")
        mgr.post("B", "b", "admin")
        mgr.clear_all()
        assert len(mgr.list_active()) == 0

    def test_clear_all_empty_is_noop(self, tmp_path: Path) -> None:
        mgr = AnnouncementManager(tmp_path)
        mgr.clear_all()  # Should not crash

    def test_persists_across_instances(self, tmp_path: Path) -> None:
        mgr1 = AnnouncementManager(tmp_path)
        mgr1.post("Persistent", "data", "admin")
        mgr2 = AnnouncementManager(tmp_path)
        assert len(mgr2.list_active()) == 1

    def test_file_created(self, tmp_path: Path) -> None:
        mgr = AnnouncementManager(tmp_path)
        mgr.post("Test", "content", "admin")
        assert (tmp_path / "announcements.md").exists()

    def test_maintains_active_and_archived_sections(self, tmp_path: Path) -> None:
        mgr = AnnouncementManager(tmp_path)
        mgr.post("Active One", "still active", "admin")
        a2 = mgr.post("Archived One", "now archived", "admin")
        mgr.archive(a2.id)
        content = (tmp_path / "announcements.md").read_text()
        assert "## Active" in content
        assert "## Archived" in content
