"""Tests: Context operational errors — sanitized, no tracebacks, no paths."""

import os
from core.context import context_repository as repo
from core.context.context_events import AppEvent
from core.context.context_service import ContextService


class TestContextOperationalErrors:

    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def _svc(self, tmp_path):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        return ContextService()

    def test_error_sanitized_no_traceback(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_operational_error(
            area="playback", code="PLAYBACK_ERR",
            message="Failed to play /home/user/secret.flac: permission denied",
        )
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.CONTEXT_ERROR_RECORDED)
        msg = ev["payload"].get("message", "")
        assert "Traceback" not in msg
        assert ev["payload"].get("area") == "playback"

    def test_error_message_truncated(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_operational_error(
            area="scan", code="SCAN_ERR",
            message="x" * 1000,
        )
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.CONTEXT_ERROR_RECORDED)
        assert len(ev["payload"].get("message", "")) <= 300

    def test_snapshot_not_bloated(self, tmp_path):
        svc = self._svc(tmp_path)
        for i in range(50):
            svc.record_operational_error(area="test", code=f"ERR_{i}", message=f"error {i}")
        snap = svc.get_assistant_snapshot()
        events = snap.get("recent_events", [])
        assert len(events) <= 10

    def test_no_absolute_paths_in_snapshot(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_operational_error(
            area="scan", code="SCAN_ERR",
            message="/home/user/Music/bad.flac failed",
        )
        snap = svc.get_assistant_snapshot()
        raw = str(snap)
        assert "/home/" not in raw
