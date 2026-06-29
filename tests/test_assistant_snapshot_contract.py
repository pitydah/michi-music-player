"""Tests: Assistant snapshot contract — route, selection, capabilities, no filepaths."""

import os
from core.context import context_repository as repo
from core.context.context_service import ContextService


class DummyTrack:
    uri = "/home/user/music/secret_song.flac"
    title = "Song"
    artist = "Artist"
    album = "Album"
    genre = "Rock"


class TestAssistantSnapshotContract:

    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def _svc(self, tmp_path):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        return ContextService()

    def test_contains_route_selection_playback_health(self, tmp_path):
        svc = self._svc(tmp_path)
        snap = svc.get_assistant_snapshot()
        assert "route" in snap
        assert "selection" in snap
        assert "playback" in snap
        assert "library_health" in snap

    def test_contains_capabilities_and_legacy(self, tmp_path):
        svc = self._svc(tmp_path)
        snap = svc.get_assistant_snapshot()
        assert "assistant_capabilities" in snap
        assert "selected_track" in snap
        assert "selected_album" in snap
        assert "current_section" in snap
        assert "selection_scope" in snap
        assert "now_playing" in snap
        assert "queue_length" in snap

    def test_sanitizes_absolute_paths_from_selection(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(
            scope="track",
            track=DummyTrack(),
            folder_name="/home/user/Music/Rock",
            search_query="/tmp/private/song.flac",
        )
        snap = svc.get_assistant_snapshot()
        raw = str(snap)
        assert "/home/" not in raw
        assert "/tmp/" not in raw
        assert "filepath" not in raw
        assert "uri" not in raw

    def test_sanitizes_windows_paths(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(
            scope="folder",
            folder_name="C:\\Users\\me\\Music",
        )
        snap = svc.get_assistant_snapshot()
        assert "C:\\" not in str(snap)
        assert "Music" in str(snap)

    def test_track_scope_capabilities(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="track", track=DummyTrack())
        snap = svc.get_assistant_snapshot()
        caps = snap.get("assistant_capabilities", {})
        assert caps.get("can_edit_metadata") is True
        assert caps.get("can_queue_selection") is True
        assert caps.get("can_create_playlist_from_selection") is True
        assert caps.get("can_analyze_selected_tracks") is True

    def test_playlist_scope_capabilities(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="playlist", playlist_id=1, playlist_name="P")
        snap = svc.get_assistant_snapshot()
        caps = snap.get("assistant_capabilities", {})
        assert caps.get("can_edit_metadata") is False
        assert caps.get("can_queue_selection") is True
        assert caps.get("can_create_playlist_from_selection") is True

    def test_search_scope_capabilities(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="search", search_query="abc")
        snap = svc.get_assistant_snapshot()
        caps = snap.get("assistant_capabilities", {})
        assert caps.get("can_create_playlist_from_selection") is True
        assert caps.get("can_analyze_selected_tracks") is True
        assert caps.get("can_edit_metadata") is False

    def test_folder_scope_capabilities(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="folder", folder_name="Music")
        snap = svc.get_assistant_snapshot()
        caps = snap.get("assistant_capabilities", {})
        assert caps.get("can_queue_selection") is True
        assert caps.get("can_create_playlist_from_selection") is True

    def test_no_scope_capabilities_default_false(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection()  # no scope
        snap = svc.get_assistant_snapshot()
        caps = snap.get("assistant_capabilities", {})
        # When scope is None, only can_search_library is True
        assert caps.get("can_search_library") is True

    def test_scope_none_capabilities(self, tmp_path):
        svc = self._svc(tmp_path)
        snap = svc.get_assistant_snapshot()
        caps = snap.get("assistant_capabilities", {})
        assert "can_search_library" in caps

    def test_recent_events_max_10(self, tmp_path):
        svc = self._svc(tmp_path)
        for i in range(20):
            svc.record_event("test_event", {"i": i})
        snap = svc.get_assistant_snapshot()
        assert len(snap.get("recent_events", [])) <= 10

    def test_suggested_actions_max_5(self, tmp_path):
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

    @staticmethod
    def _assert_caps(caps, search=True, create=True, queue=True, edit=False,
                     analyze=True, play=True):
        assert caps.get("can_search_library") is search
        assert caps.get("can_create_playlist_from_selection") is create
        assert caps.get("can_queue_selection") is queue
        assert caps.get("can_edit_metadata") is edit
        assert caps.get("can_analyze_selected_tracks") is analyze
        assert caps.get("can_play_selection") is play

    def test_caps_scope_none(self, tmp_path):
        svc = self._svc(tmp_path)
        snap = svc.get_assistant_snapshot()
        self._assert_caps(
            snap.get("assistant_capabilities", {}),
            search=True, create=False, queue=False, edit=False, analyze=False,
            play=False,
        )

    def test_caps_scope_track(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="track", track=DummyTrack())
        snap = svc.get_assistant_snapshot()
        self._assert_caps(
            snap.get("assistant_capabilities", {}),
            search=True, create=True, queue=True, edit=True, analyze=True,
        )

    def test_caps_scope_album(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="album", album="Album")
        snap = svc.get_assistant_snapshot()
        self._assert_caps(
            snap.get("assistant_capabilities", {}),
            search=True, create=True, queue=True, edit=True, analyze=True,
        )

    def test_caps_scope_artist(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="artist", artist="Artist")
        snap = svc.get_assistant_snapshot()
        self._assert_caps(
            snap.get("assistant_capabilities", {}),
            search=True, create=True, queue=True, edit=True, analyze=True,
        )

    def test_caps_scope_genre(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="genre", genre="Rock")
        snap = svc.get_assistant_snapshot()
        self._assert_caps(
            snap.get("assistant_capabilities", {}),
            search=True, create=True, queue=True, edit=True, analyze=True,
        )

    def test_caps_scope_playlist(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="playlist", playlist_id=1, playlist_name="P")
        snap = svc.get_assistant_snapshot()
        self._assert_caps(
            snap.get("assistant_capabilities", {}),
            search=True, create=True, queue=True, edit=False, analyze=True,
        )

    def test_caps_scope_mix(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="mix", mix_key="daily")
        snap = svc.get_assistant_snapshot()
        self._assert_caps(
            snap.get("assistant_capabilities", {}),
            search=True, create=True, queue=True, edit=False, analyze=True,
        )

    def test_caps_scope_folder(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="folder", folder_name="Music")
        snap = svc.get_assistant_snapshot()
        self._assert_caps(
            snap.get("assistant_capabilities", {}),
            search=True, create=True, queue=True, edit=False, analyze=False,
        )

    def test_caps_scope_search(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="search", search_query="abc")
        snap = svc.get_assistant_snapshot()
        self._assert_caps(
            snap.get("assistant_capabilities", {}),
            search=True, create=True, queue=True, edit=False, analyze=True,
        )

    def test_sanitize_nested_dict_removes_paths(self, tmp_path):
        from core.context.context_snapshot import sanitize_snapshot
        payload = {
            "selection": {
                "nested": {
                    "filepath": "/home/user/Music/a.flac",
                    "uri": "/tmp/private/b.flac",
                    "safe": "ok",
                }
            }
        }
        result = sanitize_snapshot(payload)
        raw = str(result)
        assert "filepath" not in raw
        assert "uri" not in raw
        assert "/home/" not in raw
        assert "/tmp/" not in raw
        assert "ok" in raw

    def test_sanitize_list_truncated(self, tmp_path):
        from core.context.context_snapshot import sanitize_snapshot
        items = [{"i": i} for i in range(20)]
        result = sanitize_snapshot(items)
        assert len(result) == 10
