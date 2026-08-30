"""Playlists R3 — regression tests for the seal findings.

R3-01  asset ownership (cross-playlist delete rejected)
R3-02  port contract (no silent no-op writes)
R3-03  open survives Recent persistence failure
R3-04  feedback: one authority per durable-write failure
R3-12  no-op writes (zero persistence, zero notify)
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest
from PySide6.QtGui import QImage

from michi.application.errors import (
    PlaylistPersistenceError,
)
from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.application.ports import PlaylistsPort
from michi.infrastructure.playlist_artwork_store import (
    FilesystemPlaylistArtworkStore,
)
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from michi.presentation.playlists_bridge import PlaylistsBridge
from tests.test_playlists import FakePlaylistsPort


def _png(tmp_path, name, color=0xFF581C):
    img = QImage(32, 32, QImage.Format_RGB32)
    img.fill(color)
    path = tmp_path / name
    assert img.save(str(path), "PNG")
    return path


def _bridge(tmp_path, port=None):
    service = PlaylistService(playlists_port=port or FakePlaylistsPort())
    nav = NavigationService()
    coord = PlaylistNavigationCoordinator(service, nav)
    bridge = PlaylistsBridge(service, playlist_navigation=coord, navigation_service=nav)
    return service, nav, coord, bridge


# ==========================================================================
# R3-01 — ASSET OWNERSHIP
# ==========================================================================


class TestAssetOwnership:
    def _store_with_assets(self, tmp_path):
        store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
        cover_a = store.prepare_cover("playlist-a", _png(tmp_path, "a.png"))
        hero_b = store.prepare_hero("playlist-b", _png(tmp_path, "b.png", 0xCB0543))
        assert cover_a and hero_b
        return store, cover_a, hero_b

    def test_cross_playlist_cover_cannot_be_deleted(self, tmp_path):
        store, cover_a, hero_b = self._store_with_assets(tmp_path)
        # La playlist B intenta borrar el cover de A.
        assert store.delete_managed_asset("playlist-b", "cover", cover_a) is False
        assert Path(cover_a).exists()

    def test_cross_playlist_hero_cannot_be_deleted(self, tmp_path):
        store, cover_a, hero_b = self._store_with_assets(tmp_path)
        assert store.delete_managed_asset("playlist-a", "hero", hero_b) is False
        assert Path(hero_b).exists()

    def test_cover_role_cannot_delete_hero(self, tmp_path):
        store, cover_a, hero_b = self._store_with_assets(tmp_path)
        assert store.delete_managed_asset("playlist-b", "cover", hero_b) is False
        assert Path(hero_b).exists()

    def test_hero_role_cannot_delete_cover(self, tmp_path):
        store, cover_a, hero_b = self._store_with_assets(tmp_path)
        assert store.delete_managed_asset("playlist-a", "hero", cover_a) is False
        assert Path(cover_a).exists()

    def test_unsafe_playlist_id_cannot_delete_asset(self, tmp_path):
        store, cover_a, hero_b = self._store_with_assets(tmp_path)
        assert store.delete_managed_asset("../../etc", "cover", cover_a) is False
        assert Path(cover_a).exists()

    def test_valid_owned_asset_is_deleted(self, tmp_path):
        store, cover_a, hero_b = self._store_with_assets(tmp_path)
        assert store.delete_managed_asset("playlist-a", "cover", cover_a) is True
        assert not Path(cover_a).exists()
        assert Path(hero_b).exists()


# ==========================================================================
# R3-02 — PORT CONTRACT
# ==========================================================================


class TestPortContract:
    def test_incomplete_playlists_port_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            PlaylistsPort()

    def test_service_delete_uses_save_state_only(self, tmp_path):
        db = tmp_path / "m.db"
        repo = SqlitePlaylistsRepository(db)
        service = PlaylistService(playlists_port=repo)
        a = service.create_playlist("A")
        service.pin_playlist(a.playlist_id)
        service.delete_playlist(a.playlist_id)
        # Ambas autoridades cambiaron juntas (save_state atómico).
        reloaded = PlaylistService(playlists_port=SqlitePlaylistsRepository(db))
        assert reloaded.playlists == ()
        assert reloaded.navigation.pinned_ids == ()


# ==========================================================================
# R3-03 — OPEN SURVIVES RECENT PERSISTENCE FAILURE
# ==========================================================================


class _RecentFailingPort(FakePlaylistsPort):
    def __init__(self):
        super().__init__()
        self.fail_nav = False

    def save_navigation(self, state):
        if self.fail_nav:
            raise PlaylistPersistenceError("nav down")
        super().save_navigation(state)


class TestOpenRecentResilience:
    def test_open_valid_playlist_when_recent_persistence_fails(self, tmp_path):
        port = _RecentFailingPort()
        service = PlaylistService(playlists_port=port)
        nav = NavigationService()
        coord = PlaylistNavigationCoordinator(service, nav)
        bridge = PlaylistsBridge(
            service, playlist_navigation=coord, navigation_service=nav
        )
        playlist = service.create_playlist("Mix")
        port.fail_nav = True
        result = bridge.open_playlist(playlist.playlist_id)
        assert result == "opened_recent_unsaved"
        assert nav.state.playlist_id == playlist.playlist_id

    def test_open_failure_never_escapes_raw_exception(self, tmp_path):
        port = _RecentFailingPort()
        service = PlaylistService(playlists_port=port)
        nav = NavigationService()
        coord = PlaylistNavigationCoordinator(service, nav)
        bridge = PlaylistsBridge(
            service, playlist_navigation=coord, navigation_service=nav
        )
        playlist = service.create_playlist("Mix")
        port.fail_nav = True
        # Sin excepción raw hacia QML.
        result = bridge.open_playlist(playlist.playlist_id)
        assert result in ("opened", "opened_recent_unsaved")

    def test_open_recent_failure_emits_one_warning(self, tmp_path):
        port = _RecentFailingPort()
        service = PlaylistService(playlists_port=port)
        nav = NavigationService()
        coord = PlaylistNavigationCoordinator(service, nav)
        bridge = PlaylistsBridge(
            service, playlist_navigation=coord, navigation_service=nav
        )
        playlist = service.create_playlist("Mix")
        warnings = []
        bridge.persistenceFailed.connect(warnings.append)
        port.fail_nav = True
        bridge.open_playlist(playlist.playlist_id)
        assert warnings == ["recent"]

    def test_create_success_recent_failure_still_opens_detail(self, tmp_path):
        port = _RecentFailingPort()
        service = PlaylistService(playlists_port=port)
        nav = NavigationService()
        coord = PlaylistNavigationCoordinator(service, nav)
        bridge = PlaylistsBridge(
            service, playlist_navigation=coord, navigation_service=nav
        )
        port.fail_nav = True
        result = bridge.create_and_open_playlist("New")
        assert result == "created_recent_unsaved"
        assert nav.state.playlist_id is not None
        assert service.playlists[0].name == "New"

    def test_invalid_open_falls_back_to_all_playlists(self, tmp_path):
        service, nav, coord, bridge = _bridge(tmp_path)
        coord.open_all_playlists()
        assert bridge.open_playlist("ghost-id") == "not_found"


# ==========================================================================
# R3-04 — FEEDBACK AUTHORITY
# ==========================================================================


class TestFeedbackAuthority:
    def test_name_conflict_does_not_emit_persistence_failure(self, tmp_path):
        service, nav, coord, bridge = _bridge(tmp_path)
        service.create_playlist("Jazz")
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert bridge.create_and_open_playlist("Jazz") == "conflict"
        assert failures == []

    def test_invalid_name_does_not_emit_persistence_failure(self, tmp_path):
        service, nav, coord, bridge = _bridge(tmp_path)
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert bridge.create_and_open_playlist("   ") == "invalid"
        assert failures == []

    def test_create_persistence_failure_does_not_show_name_conflict(
        self,
        tmp_path,
    ):
        class _FailFirst(FakePlaylistsPort):
            def save(self, playlists):
                raise PlaylistPersistenceError("disk full")

        service = PlaylistService(playlists_port=_FailFirst())
        nav = NavigationService()
        coord = PlaylistNavigationCoordinator(service, nav)
        bridge = PlaylistsBridge(
            service, playlist_navigation=coord, navigation_service=nav
        )
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert bridge.create_and_open_playlist("Jazz") == "persistence_failed"
        assert failures == ["create"]


# ==========================================================================
# R3-12 — NO-OP WRITES
# ==========================================================================


class TestNoOpWrites:
    def test_rename_same_name_no_write(self, tmp_path):
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        a = service.create_playlist("Jazz")
        writes_before = len(port.saved)
        service.rename_playlist(a.playlist_id, "Jazz")
        assert len(port.saved) == writes_before

    def test_move_same_index_no_write(self, tmp_path):
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        a = service.create_playlist("Jazz")
        service.add_track(a.playlist_id, "/a.flac")
        writes_before = len(port.saved)
        service.move_track(a.playlist_id, 0, 0)
        assert len(port.saved) == writes_before

    def test_set_hero_auto_when_already_auto_no_write(self, tmp_path):
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        a = service.create_playlist("Jazz")
        writes_before = len(port.saved)
        service.set_hero_auto(a.playlist_id)
        assert len(port.saved) == writes_before
