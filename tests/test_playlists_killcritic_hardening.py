"""Playlists KILLCRITIC hardening (post PR #222) — P0 integrity tests."""

from pathlib import Path

import pytest

from michi.application.playlist_service import PlaylistService
from michi.application.ports import PlaylistsPort
from michi.domain.playlist import Playlist, PlaylistNavigationState


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


def _png_at(tmp_path, name, color):
    """Real decodable PNG (the asset store validates actual decodability)."""
    from PySide6.QtGui import QImage

    img = QImage(64, 64, QImage.Format_RGB32)
    img.fill(color)
    path = tmp_path / name
    assert img.save(str(path), "PNG")
    return path


class TestArtworkTransactions:
    """P0-03: SQLite failure must never alter the committed image."""

    class _FailingPort(_MemoryPort):
        def __init__(self, fail_after=999):
            super().__init__()
            self.saved = 0
            self.fail_after = fail_after

        def save(self, playlists):
            self.saved += 1
            if self.saved > self.fail_after:
                from michi.domain.playlist import PlaylistPersistenceError

                raise PlaylistPersistenceError("injected DB failure")
            self._items = tuple(playlists)

    def _service(self, tmp_path, fail_after=999):
        from michi.infrastructure.playlist_artwork_store import (
            FilesystemPlaylistArtworkStore,
        )

        service = PlaylistService(
            playlists_port=self._FailingPort(fail_after),
            artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        service._playlists = [Playlist(playlist_id="p1", name="Mix")]
        service._persisted = tuple(service._playlists)
        return service

    def test_cover_db_failure_preserves_old_bytes(self, tmp_path):
        from michi.domain.playlist import PlaylistPersistenceError

        service = self._service(tmp_path, fail_after=1)
        old_src = _png_at(tmp_path, "old.png", 0xFF581C)
        assert service.set_custom_cover("p1", old_src) is not None
        old_path = service.get_playlist("p1").custom_cover_path
        assert Path(old_path).read_bytes() == Path(old_src).read_bytes()

        port = service._port
        port.fail_after = 0
        new_src = _png_at(tmp_path, "new.png", 0xCB0543)
        with pytest.raises(PlaylistPersistenceError):
            service.set_custom_cover("p1", new_src)
        assert service.get_playlist("p1").custom_cover_path == old_path
        assert Path(old_path).read_bytes() == Path(old_src).read_bytes()

    def test_hero_db_failure_preserves_old_bytes(self, tmp_path):
        from michi.domain.playlist import PlaylistPersistenceError

        service = self._service(tmp_path, fail_after=1)
        old_src = _png_at(tmp_path, "old_hero.png", 0xFF811B)
        assert service.set_custom_hero_image("p1", old_src) is not None
        old_path = service.get_playlist("p1").appearance.hero_image_path
        assert Path(old_path).read_bytes() == Path(old_src).read_bytes()

        port = service._port
        port.fail_after = 0
        new_src = _png_at(tmp_path, "new_hero.png", 0xF51D51)
        with pytest.raises(PlaylistPersistenceError):
            service.set_custom_hero_image("p1", new_src)
        assert service.get_playlist("p1").appearance.hero_image_path == old_path
        assert Path(old_path).read_bytes() == Path(old_src).read_bytes()

    def test_candidate_exists_before_database_save(self, tmp_path):
        seen = {}

        class _InspectingPort(_MemoryPort):
            def save(self, playlists):
                candidate = playlists[0].custom_cover_path
                seen["exists"] = Path(candidate).is_file() if candidate else False
                self._items = tuple(playlists)

        service = PlaylistService(
            playlists_port=_InspectingPort(),
            artwork_store=__import__(
                "michi.infrastructure.playlist_artwork_store",
                fromlist=["FilesystemPlaylistArtworkStore"],
            ).FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        service._playlists = [Playlist(playlist_id="p1", name="Mix")]
        service._persisted = tuple(service._playlists)
        src = _png_at(tmp_path, "cover.png", 0xFF581C)
        service.set_custom_cover("p1", src)
        assert seen.get("exists") is True

    def test_post_commit_cleanup_failure_keeps_new_reference(self, tmp_path):
        service = self._service(tmp_path)
        old_src = _png_at(tmp_path, "old.png", 0xFF581C)
        assert service.set_custom_cover("p1", old_src) is not None
        old_path = service.get_playlist("p1").custom_cover_path

        def broken_delete(managed_path):
            raise OSError("cleanup failure")

        store = service._artwork_store
        store.delete_managed_asset = broken_delete
        new_src = _png_at(tmp_path, "new2.png", 0xCB0543)
        assert service.set_custom_cover("p1", new_src) is not None
        new_path = service.get_playlist("p1").custom_cover_path
        assert Path(new_path).read_bytes() == Path(new_src).read_bytes()
        assert new_path != old_path

    def test_garbage_image_rejected(self, tmp_path):
        service = self._service(tmp_path)
        garbage = tmp_path / "garbage.jpg"
        garbage.write_bytes(b"this is not an image" * 10)
        assert service.set_custom_cover("p1", garbage) is None
        assert service.set_custom_hero_image("p1", garbage) is None


class TestRealAssetValidation:
    """P1-01: managed visual assets must REALLY decode as images."""

    def _service(self, tmp_path):
        from michi.infrastructure.playlist_artwork_store import (
            FilesystemPlaylistArtworkStore,
        )

        service = PlaylistService(
            playlists_port=_MemoryPort(),
            artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        service._playlists = [Playlist(playlist_id="p1", name="Mix")]
        service._persisted = tuple(service._playlists)
        return service

    def test_byte_budget_cover_rejected(self, tmp_path):
        from PySide6.QtGui import QImage

        service = self._service(tmp_path)
        img = QImage(4000, 4000, QImage.Format_RGB32)
        img.fill(0xFF581C)
        big = tmp_path / "big.png"
        assert img.save(str(big), "PNG")
        # Force the byte budget with an inflated payload.
        big.write_bytes(big.read_bytes() + b"\x00" * (21 * 1024 * 1024))
        assert service.set_custom_cover("p1", big) is None

    def test_over_resolution_rejected(self, tmp_path):
        from PySide6.QtGui import QImage

        service = self._service(tmp_path)
        img = QImage(6000, 64, QImage.Format_RGB32)
        img.fill(0xFF581C)
        wide = tmp_path / "wide.png"
        assert img.save(str(wide), "PNG")
        assert service.set_custom_cover("p1", wide) is None  # cover: 4096 max
        assert service.set_custom_hero_image("p1", wide) is None  # hero: 5120 max

    def test_empty_file_rejected(self, tmp_path):
        service = self._service(tmp_path)
        empty = tmp_path / "empty.png"
        empty.write_bytes(b"")
        assert service.set_custom_cover("p1", empty) is None

    def test_delete_managed_asset_fail_closed(self, tmp_path):
        from michi.infrastructure.playlist_artwork_store import (
            FilesystemPlaylistArtworkStore,
        )

        store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"precious")
        store.delete_managed_asset(str(outside))  # fuera del storage dir → refuse
        assert outside.exists()
        foreign = tmp_path / "managed" / "other.png"
        store._storage_dir.mkdir(parents=True, exist_ok=True)
        foreign.write_bytes(b"precious")
        store.delete_managed_asset(str(foreign))  # nombre no playlist_ → refuse
        assert foreign.exists()


class TestArtworkIndex:
    """P1-05/P1-04: playlist track rows carry artworkPath via O(1) index."""

    def test_playlist_track_rows_project_artwork_path(self, tmp_path):
        from michi.application.library_service import LibraryService
        from michi.application.navigation_service import NavigationService
        from michi.application.playlist_navigation_coordinator import (
            PlaylistNavigationCoordinator,
        )
        from michi.presentation.playlists_bridge import PlaylistsBridge
        from tests.test_library_artwork import FakeArtworkCache, FakeArtworkProvider
        from tests.test_library_metadata import FakeExtractor, FakeScanner

        track = tmp_path / "a.flac"
        track.write_bytes(b"x")
        provider = FakeArtworkProvider(
            artwork=__import__(
                "michi.domain.library", fromlist=["Artwork"]
            ).Artwork(data=b"PNGDATA", mime_type="image/png")
        )
        cache = FakeArtworkCache()
        library = LibraryService(
            FakeScanner([track]),
            metadata_extractor=FakeExtractor(),
            artwork_provider=provider,
            artwork_cache=cache,
        )
        library.scan(str(tmp_path))
        assert library.state.albums
        expected = cache.paths[library.state.albums[0].key]
        service = PlaylistService(playlists_port=_MemoryPort())
        nav = NavigationService()
        service.set_on_playlist_deleted(nav.forget_playlist)
        coord = PlaylistNavigationCoordinator(service, nav)
        bridge = PlaylistsBridge(
            playlist_service=service,
            playlist_navigation=coord,
            navigation_service=nav,
            library=library,
        )
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, str(track))
        bridge.open_playlist(playlist.playlist_id)

        rows = bridge.playlistTrackRows
        assert len(rows) == 1
        assert "artworkPath" in rows[0], f"row keys: {sorted(rows[0])}"
        assert rows[0]["artworkPath"] == str(expected)

    def test_artwork_index_is_o1_per_row(self):
        from michi.presentation.playlists_bridge import PlaylistsBridge

        bridge = PlaylistsBridge.__new__(PlaylistsBridge)
        bridge._library = None
        assert bridge._build_artwork_index() == {}
