"""Tests: Audio analysis context — AUDIO_ANALYSIS_STARTED/FINISHED/FAILED."""

import os
from core.context import context_repository as repo
from core.context.context_events import AppEvent
from core.context.context_invalidator import is_dirty
from core.context.context_service import ContextService


class TestAudioAnalysisContext:

    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def _svc(self, tmp_path):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        return ContextService()

    def test_started_finished_failed_sequence(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_audio_analysis_started(count=10, scope="album")
        svc.record_audio_analysis_failed(count=2, reason="timeout")
        svc.record_audio_analysis_finished(None)
        events = svc.recent_events(limit=10)
        types = [e["event_type"] for e in events]
        assert AppEvent.AUDIO_ANALYSIS_STARTED in types
        assert AppEvent.AUDIO_ANALYSIS_FAILED in types
        assert AppEvent.AUDIO_ANALYSIS_FINISHED in types

    def test_no_filepaths_in_payloads(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_audio_analysis_started(count=5)
        svc.record_audio_analysis_failed(count=1, reason="corrupt file")
        svc.record_audio_analysis_finished({"batch_id": "b1"})
        events = svc.recent_events(limit=10)
        raw = str(events)
        assert "/home/" not in raw
        assert "filepath" not in raw

    def test_features_updated(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_audio_features_updated(count=50)
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.AUDIO_FEATURES_UPDATED)
        assert ev["payload"].get("count") == 50

    def test_analysis_started_invalidates_snapshots(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_audio_analysis_started(count=5)
        assert is_dirty("assistant_snapshot")

    def test_analysis_failed_reason_truncated(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_audio_analysis_failed(count=1, reason="x" * 500)
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.AUDIO_ANALYSIS_FAILED)
        assert len(ev["payload"].get("reason", "")) <= 200
