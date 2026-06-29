"""Tests: Home context snapshot — compact, no paths, max 4 actions."""

import os
from core.context import context_repository as repo
from core.context.context_service import ContextService


class TestHomeContextSnapshot:

    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def _svc(self, tmp_path):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        return ContextService()

    def test_snapshot_contains_keys(self, tmp_path):
        svc = self._svc(tmp_path)
        snap = svc.get_home_snapshot()
        assert "library_health" in snap
        assert "playback" in snap
        assert "current_context" in snap
        assert "next_actions" in snap
        assert "warnings" in snap

    def test_current_context_includes_section_and_scope(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_navigation(section="library", tab="all")
        svc.update_selection(scope="album", album="Test Album")
        snap = svc.get_home_snapshot()
        cc = snap.get("current_context", {})
        assert cc.get("section") == "library"
        assert cc.get("selection_scope") == "album"
        assert cc.get("selection_label") == "Test Album"

    def test_next_actions_max_4(self, tmp_path):
        svc = self._svc(tmp_path)
        snap = svc.get_home_snapshot()
        assert len(snap.get("next_actions", [])) <= 4

    def test_warnings_are_compact(self, tmp_path):
        svc = self._svc(tmp_path)
        snap = svc.get_home_snapshot()
        for w in snap.get("warnings", []):
            assert "kind" in w
            assert "message" in w

    def test_no_absolute_paths_in_snapshot(self, tmp_path):
        svc = self._svc(tmp_path)
        snap = svc.get_home_snapshot()
        raw = str(snap)
        assert "/home/" not in raw
        assert "/tmp/" not in raw
        assert "C:\\" not in raw

    def test_no_long_lists(self, tmp_path):
        svc = self._svc(tmp_path)
        snap = svc.get_home_snapshot()
        for k, v in snap.items():
            if isinstance(v, list):
                assert len(v) <= 10, f"{k} has {len(v)} items"
