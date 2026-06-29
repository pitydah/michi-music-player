"""Tests: View context consistency — CoverFlow, grid, table selection."""

import os
from core.context import context_repository as repo
from core.context.context_service import ContextService


class TestViewContextConsistency:

    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def _svc(self, tmp_path):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        return ContextService()

    def test_coverflow_album_selection_scope(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="album", album="Test Album")
        state = svc.get_selection_state()
        assert state.get("selection_scope") == "album"
        assert state.get("album") == "Test Album"

    def test_table_track_selection_scope(self, tmp_path):
        svc = self._svc(tmp_path)
        class FakeTrack:
            title = "Song"
            artist = "Artist"
            album = "Album"
            genre = "Rock"
        svc.update_selection(scope="track", track=FakeTrack())
        state = svc.get_selection_state()
        assert state.get("selection_scope") == "track"
        assert state.get("track") == "Song"

    def test_grid_selection_no_mixed_fields(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="album", album="Album")
        state = svc.get_selection_state()
        assert state.get("selection_scope") == "album"
        assert state.get("playlist_id") is None or state.get("playlist_id") == ""
        assert state.get("folder_name") is None or state.get("folder_name") == ""
        assert state.get("mix_key") is None or state.get("mix_key") == ""

    def test_no_filepaths_in_selection_snapshot(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.update_selection(scope="folder", folder_name="/home/user/Music")
        snap = svc.get_assistant_snapshot()
        raw = str(snap)
        assert "/home/" not in raw
