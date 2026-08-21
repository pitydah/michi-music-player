"""M8-R1: stable playlist identity gates — domain + persistence level.

PlaylistId: immutable, opaque, collision-resistant, serializable,
name-independent. Service-level identity gates (create/rename/mutations/
restart/recreate) are covered by test_m8_playlist_navigation_convergence.py
(TestGetPlaylistQuery) plus the historical behavior locked in
test_playlists.py (TestPlaylistService, identity-based API).
"""

import sqlite3

from michi.domain.playlist import (
    Playlist,
    legacy_playlist_id,
    new_playlist_id,
)
from michi.infrastructure.playlists import SqlitePlaylistsRepository


class TestPlaylistId:
    def test_new_id_is_nonempty_opaque_string(self):
        assert isinstance(new_playlist_id(), str)
        assert new_playlist_id() != ""

    def test_new_ids_are_distinct(self):
        assert new_playlist_id() != new_playlist_id()

    def test_legacy_id_is_deterministic(self):
        a = legacy_playlist_id("Jazz")
        b = legacy_playlist_id("Jazz")
        assert a == b
        assert a != legacy_playlist_id("Rock")

    def test_legacy_id_never_collides_with_fresh_id(self):
        for _ in range(25):
            assert new_playlist_id() != legacy_playlist_id("Jazz")


class TestRealPersistenceRoundTrip:
    def _repo(self, tmp_path):
        return SqlitePlaylistsRepository(tmp_path / "michi.db")

    def test_save_load_roundtrip_preserves_id(self, tmp_path):
        repo = self._repo(tmp_path)
        playlist = Playlist(playlist_id="id-1", name="Jazz", track_paths=("/a", "/b"))
        repo.save((playlist,))
        loaded = repo.load()
        assert len(loaded) == 1
        assert loaded[0].playlist_id == "id-1"
        assert loaded[0].name == "Jazz"
        assert loaded[0].track_paths == ("/a", "/b")

    def test_stored_shape_is_v2(self, tmp_path):
        repo = self._repo(tmp_path)
        repo.save((Playlist(playlist_id="id-x", name="Jazz"),))
        conn = sqlite3.connect(str(tmp_path / "michi.db"))
        try:
            row = conn.execute(
                "SELECT value FROM library_prefs WHERE key='playlists'"
            ).fetchone()
        finally:
            conn.close()
        import json

        payload = json.loads(row[0])
        assert payload[0]["id"] == "id-x"
        assert payload[0]["name"] == "Jazz"
