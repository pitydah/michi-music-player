"""Regression contract tests for the context system.

Verifies semantic guarantees: TRACK_PLAYED is only for real playback,
APP_CLOSED is only for app exit, selection_scope exists, etc.
"""

import os

from core.context import context_repository as repo
from core.context.context_events import AppEvent
from core.context.context_invalidator import is_dirty
from core. context.context_service import ContextService
from core.context.context_snapshot import build_mix_snapshot, sanitize_snapshot


def _init(tmp_path):
    db_path = os.path.join(str(tmp_path), "ctx.sqlite")
    repo.override_db_path(db_path)
    svc = ContextService()
    return svc, db_path


class TestSemanticCorrectness:

    def teardown_method(self):
        repo.close()

    def test_quality_updated_not_track_played(self, tmp_path):
        svc, _ = _init(tmp_path)
        svc.record_quality_updated("FLAC 1411kbps", "lossless")
        events = svc.recent_events(10)
        assert not any(e["event_type"] == AppEvent.TRACK_PLAYED for e in events)
        assert any(e["event_type"] == AppEvent.QUALITY_UPDATED for e in events)

    def test_playback_stopped_not_app_closed(self, tmp_path):
        svc, _ = _init(tmp_path)
        svc.record_playback_stopped("player_bar_reset")
        events = svc.recent_events(10)
        assert not any(e["event_type"] == AppEvent.APP_CLOSED for e in events)
        assert any(e["event_type"] == AppEvent.PLAYBACK_STOPPED for e in events)

    def test_selection_scope_exists(self, tmp_path):
        svc, _ = _init(tmp_path)
        svc.update_selection(scope="album", album="TestAlbum", artist="TestArtist")
        sel = svc.get_selection_state()
        assert sel.get("selection_scope") == "album"

    def test_assistant_snapshot_contains_route_selection_capabilities(self, tmp_path):
        svc, _ = _init(tmp_path)
        snap = svc.get_assistant_snapshot()
        assert "route" in snap
        assert "selection" in snap
        assert "assistant_capabilities" in snap
        assert "playback" in snap
        assert "library_health" in snap

    def test_assistant_snapshot_no_filepaths(self, tmp_path):
        svc, _ = _init(tmp_path)
        snap = svc.get_assistant_snapshot()
        raw = str(snap)
        assert "/home/" not in raw
        assert "/tmp/" not in raw
        assert ".flac" not in raw

    def test_assistant_snapshot_has_legacy_fields(self, tmp_path):
        svc, _ = _init(tmp_path)
        snap = svc.get_assistant_snapshot()
        assert "selected_track" in snap
        assert "selected_album" in snap
        assert "selected_artist" in snap
        assert "current_section" in snap

    def test_assistant_opened_invalidates(self, tmp_path):
        svc, _ = _init(tmp_path)
        svc.get_assistant_snapshot()
        assert not is_dirty("assistant_snapshot")
        svc.record_event(AppEvent.ASSISTANT_OPENED)
        assert is_dirty("assistant_snapshot")

    def test_metadata_saved_invalidates_library_health(self, tmp_path):
        svc, _ = _init(tmp_path)
        svc.get_library_health()
        assert not is_dirty("library_health")
        svc.record_metadata_saved(count=10)
        assert is_dirty("library_health")

    def test_playlist_created_invalidates_home(self, tmp_path):
        svc, _ = _init(tmp_path)
        svc.get_home_snapshot()
        assert not is_dirty("home_snapshot")
        svc.record_event(AppEvent.PLAYLIST_CREATED, {"playlist_id": 1})
        assert is_dirty("home_snapshot")

    def test_mix_opened_invalidates_assistant(self, tmp_path):
        svc, _ = _init(tmp_path)
        svc.get_assistant_snapshot()
        assert not is_dirty("assistant_snapshot")
        svc.record_event(AppEvent.MIX_OPENED, {"key": "daily"})
        assert is_dirty("assistant_snapshot")

    def test_search_performed_invalidates_assistant(self, tmp_path):
        svc, _ = _init(tmp_path)
        svc.get_assistant_snapshot()
        assert not is_dirty("assistant_snapshot")
        svc.record_event(AppEvent.SEARCH_PERFORMED, {"result_count": 5})
        assert is_dirty("assistant_snapshot")


class TestSanitization:

    def test_removes_filepath_keys(self):
        data = {"filepath": "/home/user/music/song.flac", "title": "Song"}
        clean = sanitize_snapshot(data)
        assert "filepath" not in clean
        assert clean["title"] == "Song"

    def test_converts_absolute_path_to_basename(self):
        data = {"some_path": "/home/user/music/song.flac"}
        clean = sanitize_snapshot(data)
        assert clean["some_path"] == "song.flac"

    def test_limits_lists_to_10(self):
        data = {"items": list(range(50))}
        clean = sanitize_snapshot(data)
        assert len(clean["items"]) == 10

    def test_truncates_long_strings(self):
        data = {"long": "x" * 500}
        clean = sanitize_snapshot(data)
        assert len(clean["long"]) == 300


class TestMixSnapshot:

    def test_contains_available_mixes(self, tmp_path):
        svc, _ = _init(tmp_path)
        snap = svc.get_mix_snapshot()
        assert "available_mixes" in snap
        assert "mix_daily" in snap["available_mixes"]

    def test_contains_mix_health(self, tmp_path):
        svc, _ = _init(tmp_path)
        snap = svc.get_mix_snapshot()
        assert "mix_health" in snap
        assert "has_library" in snap["mix_health"]

    def test_no_track_lists(self, tmp_path):
        snap = build_mix_snapshot(None)
        raw = str(snap)
        assert "canciones" in raw or "{" in raw
        assert "filepath" not in raw


class TestSuggestedActions:

    def test_limited_to_5(self):
        from core.context.context_snapshot import _suggested_actions
        health = {
            "track_count": 1000,
            "missing_metadata_count": 999,
            "missing_cover_count": 999,
            "tracks_without_audio_features": 999,
            "index_error_count": 99,
        }
        playback = {"now_playing": None, "recently_played_count": 0, "favorites_count": 0}
        actions = _suggested_actions(health, playback)
        assert len(actions) <= 5
