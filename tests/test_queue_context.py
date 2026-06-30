"""Tests: Queue context events — QUEUE_UPDATED, QUEUE_CLEARED, TRACK_QUEUED."""

import os
from core.context import context_repository as repo
from core.context.context_events import AppEvent
from core.context.context_invalidator import is_dirty
from core.context.context_service import ContextService


class TestQueueContext:

    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def _svc(self, tmp_path):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        return ContextService()

    def test_queue_updated_invalidates_playback(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_queue_updated(count=5, source="playlist")
        events = svc.recent_events(limit=5)
        assert any(e["event_type"] == AppEvent.QUEUE_UPDATED for e in events)
        ev = next(e for e in events if e["event_type"] == AppEvent.QUEUE_UPDATED)
        assert ev["payload"].get("count") == 5
        assert ev["payload"].get("source") == "playlist"

    def test_queue_cleared_no_filepath(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_queue_cleared(reason="user_action")
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.QUEUE_CLEARED)
        raw = str(ev)
        assert "/home/" not in raw
        assert "/tmp/" not in raw

    def test_track_queued_not_confused_with_played(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_track_queued(title="Song", artist="Artist", source="search")
        events = svc.recent_events(limit=5)
        queued = [e for e in events if e["event_type"] == AppEvent.TRACK_QUEUED]
        played = [e for e in events if e["event_type"] == AppEvent.TRACK_PLAYED]
        assert len(queued) == 1
        assert len(played) == 0

    def test_queue_cleared_not_playback_stopped(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_queue_cleared(reason="user")
        svc.record_playback_stopped(reason="end_of_queue")
        events = svc.recent_events(limit=5)
        cleared = [e for e in events if e["event_type"] == AppEvent.QUEUE_CLEARED]
        stopped = [e for e in events if e["event_type"] == AppEvent.PLAYBACK_STOPPED]
        assert len(cleared) == 1
        assert len(stopped) == 1

    def test_queue_updated_dirty_flag(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_queue_updated(count=3)
        assert is_dirty("playback_context")

    def test_playback_mode_changed(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_playback_mode_changed(shuffle=True, repeat="all")
        events = svc.recent_events(limit=5)
        ev = next(e for e in events if e["event_type"] == AppEvent.PLAYBACK_MODE_CHANGED)
        assert ev["payload"].get("shuffle") is True
        assert ev["payload"].get("repeat") == "all"

    def test_app_closed_event(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_event(AppEvent.APP_CLOSED)
        events = svc.recent_events(limit=5)
        assert any(e["event_type"] == AppEvent.APP_CLOSED for e in events)
