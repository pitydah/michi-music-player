"""Tests: Disc Lab context — DISC_DETECTED, RIP_STARTED/FINISHED/FAILED."""

import os
from core.context import context_repository as repo
from core.context.context_events import AppEvent
from core.context.context_service import ContextService


class TestDiscLabContext:

    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def _svc(self, tmp_path):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        return ContextService()

    def test_rip_finished_not_scan_finished(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_rip_finished(source="cd", count=12)
        events = svc.recent_events(limit=10)
        rip = [e for e in events if e["event_type"] == AppEvent.RIP_FINISHED]
        scan = [e for e in events if e["event_type"] == AppEvent.SCAN_FINISHED]
        assert len(rip) == 1
        assert len(scan) == 0

    def test_recording_events_no_routes(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_disc_detected(source="cd")
        svc.record_rip_started(source="cd", format="flac")
        events = svc.recent_events(limit=10)
        raw = str(events)
        assert "/home/" not in raw
        assert "filepath" not in raw

    def test_rip_failed_safe_error(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_rip_failed(source="cd", error_type="read_error")
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.RIP_FAILED)
        assert ev["payload"].get("error_type") == "read_error"

    def test_failed_error_type_truncated(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_rip_failed(source="cd", error_type="x" * 500)
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.RIP_FAILED)
        assert len(ev["payload"].get("error_type", "")) <= 100
