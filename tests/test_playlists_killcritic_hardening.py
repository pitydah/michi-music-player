"""Playlists KILLCRITIC hardening (post PR #222) — P0 integrity tests."""


import pytest

from michi.application.playlist_service import PlaylistService
from michi.application.ports import PlaylistsPort
from michi.domain.playlist import PlaylistNavigationState


class _MemoryPort(PlaylistsPort):
    def __init__(self):
        self._items = ()
        self.nav = PlaylistNavigationState()

    def load(self):
        return self._items

    def save(self, playlists):
        self._items = tuple(playlists)

    def load_navigation(self):
        return self.nav

    def save_navigation(self, state):
        self.nav = state


def _service_with(names):
    service = PlaylistService(playlists_port=_MemoryPort())
    playlist = service.create_playlist("A")
    for n in names:
        service.add_track(playlist.playlist_id, f"/{n}")
    return service, playlist


class TestUndoFrozenProvenance:
    def test_undo_restores_exact_position(self):
        service, playlist = _service_with(["a", "b", "c", "d"])
        service.remove_track(playlist.playlist_id, 1)  # remove b
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a",
            "/c",
            "/d",
        )
        assert service.insert_track(playlist.playlist_id, 1, "/b") is True
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a",
            "/b",
            "/c",
            "/d",
        )

    def test_undo_first_and_last_index(self):
        service, playlist = _service_with(["a", "b", "c"])
        service.remove_track(playlist.playlist_id, 0)
        assert service.insert_track(playlist.playlist_id, 0, "/a") is True
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a",
            "/b",
            "/c",
        )
        service.remove_track(playlist.playlist_id, 2)
        assert service.insert_track(playlist.playlist_id, 2, "/c") is True
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a",
            "/b",
            "/c",
        )

    def test_undo_after_navigating_never_touches_other_playlist(self):
        service, playlist_a = _service_with(["a", "b", "c"])
        playlist_b = service.create_playlist("B")
        service.add_track(playlist_b.playlist_id, "/x")
        service.remove_track(playlist_a.playlist_id, 1)  # remove b from A
        # "Navigate" to B: Undo uses the FROZEN playlist A id.
        assert service.insert_track(playlist_a.playlist_id, 1, "/b") is True
        assert service.get_playlist(playlist_a.playlist_id).track_paths == (
            "/a",
            "/b",
            "/c",
        )
        assert service.get_playlist(playlist_b.playlist_id).track_paths == ("/x",)

    def test_undo_after_all_playlists(self):
        service, playlist = _service_with(["a", "b", "c"])
        service.remove_track(playlist.playlist_id, 1)
        # Returning to All Playlists changes nothing: frozen id + index.
        assert service.insert_track(playlist.playlist_id, 1, "/b") is True
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a",
            "/b",
            "/c",
        )

    def test_undo_no_accidental_duplicates(self):
        service, playlist = _service_with(["a", "b"])
        service.remove_track(playlist.playlist_id, 1)
        assert service.insert_track(playlist.playlist_id, 1, "/b") is True
        # Double Undo → duplicate policy skips.
        assert service.insert_track(playlist.playlist_id, 1, "/b") is False
        assert service.get_playlist(playlist.playlist_id).track_paths == ("/a", "/b")

    def test_undo_after_playlist_deleted_degrades_safely(self):
        service, playlist = _service_with(["a", "b"])
        service.remove_track(playlist.playlist_id, 1)
        service.delete_playlist(playlist.playlist_id)
        assert service.insert_track(playlist.playlist_id, 1, "/b") is False
        assert service.playlists == ()


class TestTruthfulPersistence:
    """P0-02: a failed write must never report success."""

    class _FailingPort(_MemoryPort):
        def __init__(self, fail_after=0):
            super().__init__()
            self.saved = 0
            self.fail_after = fail_after

        def save(self, playlists):
            self.saved += 1
            if self.saved > self.fail_after:
                from michi.domain.playlist import PlaylistPersistenceError

                raise PlaylistPersistenceError("injected DB failure")
            self._items = tuple(playlists)

    def test_create_failure_never_publishes(self):
        from michi.domain.playlist import PlaylistPersistenceError

        service = PlaylistService(playlists_port=self._FailingPort(fail_after=0))
        with pytest.raises(PlaylistPersistenceError):
            service.create_playlist("X")
        assert service.playlists == ()

    def test_mutation_failure_rolls_back_to_persisted(self):
        from michi.domain.playlist import PlaylistPersistenceError

        service = PlaylistService(playlists_port=self._FailingPort(fail_after=1))
        playlist = service.create_playlist("Mix")  # save 1 ok
        with pytest.raises(PlaylistPersistenceError):
            service.rename_playlist(playlist.playlist_id, "Renamed")  # save 2 fails
        assert service.get_playlist(playlist.playlist_id).name == "Mix"

    def test_restart_reproduces_persisted_state(self, tmp_path):
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
        service = PlaylistService(playlists_port=repo)
        playlist = service.create_playlist("Restart")
        service.add_track(playlist.playlist_id, "/a.flac")
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(tmp_path / "michi.db")
        )
        assert reloaded.get_playlist(playlist.playlist_id).track_paths == ("/a.flac",)
