"""Tests for ContextService — public facade."""

import os

from core.context import context_repository as repo
from core.context.context_service import ContextService
from core.context.context_events import AppEvent


class TestContextService:

    def setup_method(self):
        self.db_path = "/tmp/test_context_svc.sqlite"
        repo.override_db_path(self.db_path)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.svc = ContextService(db=None, playback=None, sync=None)

    def teardown_method(self):
        repo.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_record_event(self):
        self.svc.record_event("test_event", {"key": "value"})
        events = self.svc.recent_events(5)
        assert any(e["event_type"] == "test_event" for e in events)

    def test_update_navigation_sets_state(self):
        self.svc.update_navigation("albums", tab="all", extra={"filter": "active"})
        state = repo.get_state("navigation")
        assert state["section"] == "albums"
        assert state["tab"] == "all"
        assert state["filter"] == "active"

    def test_update_selection(self):
        track = type("Track", (), {"title": "Song", "artist": "Artist", "name": "Song"})()
        self.svc.update_selection(track=track, album="Album", artist="Artist")
        state = repo.get_state("selection")
        assert state["album"] == "Album"
        assert state["artist"] == "Artist"
        assert state["track"] == "Song"

    def test_record_track_played(self):
        track = type("Track", (), {"title": "Song", "artist": "Artist", "album": "Album"})()
        self.svc.record_track_played(track)
        events = self.svc.recent_events(5)
        assert any(e["event_type"] == AppEvent.TRACK_PLAYED for e in events)

    def test_get_library_health_returns_dict(self):
        health = self.svc.get_library_health()
        assert isinstance(health, dict)
        assert "track_count" in health

    def test_get_home_snapshot_returns_dict(self):
        snap = self.svc.get_home_snapshot()
        assert isinstance(snap, dict)
        assert "library_health" in snap

    def test_get_assistant_snapshot_returns_dict(self):
        snap = self.svc.get_assistant_snapshot()
        assert isinstance(snap, dict)
        assert "current_section" in snap
        assert "suggested_actions" in snap

    def test_get_mix_snapshot_returns_dict(self):
        snap = self.svc.get_mix_snapshot()
        assert isinstance(snap, dict)
        assert "total_tracks" in snap

    def test_invalidate_marks_dirty(self):
        self.svc.invalidate("home_snapshot")
        assert repo.is_dirty("home_snapshot")

    def test_snapshot_cached_after_fetch(self):
        self.svc.get_home_snapshot()
        assert not repo.is_dirty("home_snapshot")

    def test_snapshot_regenerated_after_invalidation(self):
        self.svc.get_home_snapshot()
        self.svc.invalidate("home_snapshot")
        assert repo.is_dirty("home_snapshot")

    def test_no_crash_without_db(self):
        svc = ContextService(db=None, playback=None, sync=None)
        snap = svc.get_assistant_snapshot()
        assert snap["library_health"]["track_count"] == 0

    def test_selection_with_all_params(self):
        svc = ContextService()
        svc.update_selection(album="Album1", artist="Artist1", genre="Rock")
        snap = svc.get_assistant_snapshot()
        assert snap.get("selected_album") == "Album1"
        assert snap.get("selected_artist") == "Artist1"
        assert snap.get("selected_genre") == "Rock"

    def test_selection_roundtrip(self):
        svc = ContextService()
        svc.update_selection(genre="Jazz")
        sel = svc.get_selection_state()
        assert sel.get("genre") == "Jazz"
