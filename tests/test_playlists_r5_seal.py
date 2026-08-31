"""Playlists R5 — 10/10 convergence gates.

R5-01  appearance validated BEFORE asset preparation (zero leaks)
R5-02  result semantics converge (no False→persistence_failed)
R5-05  mark_recent no-op (zero write + zero notify)
R5-06  legacy asset retirement safe (fail-closed on ambiguity)
R5-09  strengthened side-effect assertions (writes/notify/signals/files)
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtGui import QImage

from michi.application.errors import PlaylistPersistenceError
from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.infrastructure.playlist_artwork_store import (
    FilesystemPlaylistArtworkStore,
)
from michi.presentation.playlists_bridge import PlaylistsBridge
from tests.test_playlists import FakePlaylistsPort


def _png(tmp_path, name, color=0xFF581C):
    img = QImage(16, 16, QImage.Format_RGB32)
    img.fill(color)
    path = tmp_path / name
    assert img.save(str(path), "PNG")
    return path


def _world(tmp_path, port=None):
    service = PlaylistService(playlists_port=port or FakePlaylistsPort())
    nav = NavigationService()
    coord = PlaylistNavigationCoordinator(service, nav)
    bridge = PlaylistsBridge(service, playlist_navigation=coord, navigation_service=nav)
    return service, nav, coord, bridge


# ==========================================================================
# R5-01 — ZERO ASSET LEAKS ON INVALID APPEARANCE
# ==========================================================================


class TestAppearanceNoLeaks:
    def _managed_files(self, tmp_path):
        managed = tmp_path / "managed"
        return sorted(p.name for p in managed.iterdir()) if managed.exists() else []

    def _store_world(self, tmp_path):
        store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
        service = PlaylistService(
            playlists_port=FakePlaylistsPort(), artwork_store=store
        )
        return service, store

    def test_cover_candidate_not_left_on_invalid_gradient_length(self, tmp_path):
        service, store = self._store_world(tmp_path)
        playlist = service.create_playlist("Mix")
        cover = _png(tmp_path, "cover.png")
        before = self._managed_files(tmp_path)

        result = service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="replace",
            cover_source_path=cover,
            hero_mode="gradient",
            hero_gradient_colors=("#112233",),  # length 1 → invalid
            hero_gradient_angle=45.0,
        )
        assert result == "invalid"
        assert self._managed_files(tmp_path) == before, "candidate huérfano"

    def test_cover_candidate_not_left_on_nan_angle(self, tmp_path):
        service, store = self._store_world(tmp_path)
        playlist = service.create_playlist("Mix")
        cover = _png(tmp_path, "cover.png")
        before = self._managed_files(tmp_path)

        result = service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="replace",
            cover_source_path=cover,
            hero_mode="gradient",
            hero_gradient_colors=("#112233", "#445566"),
            hero_gradient_angle=float("nan"),
        )
        assert result == "invalid"
        assert self._managed_files(tmp_path) == before, "candidate huérfano"

    def test_cover_candidate_not_left_on_inf_angle(self, tmp_path):
        service, store = self._store_world(tmp_path)
        playlist = service.create_playlist("Mix")
        cover = _png(tmp_path, "cover.png")
        before = self._managed_files(tmp_path)

        result = service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="replace",
            cover_source_path=cover,
            hero_mode="gradient",
            hero_gradient_colors=("#112233", "#445566"),
            hero_gradient_angle=float("inf"),
        )
        assert result == "invalid"
        assert self._managed_files(tmp_path) == before

    def test_cover_candidate_not_left_on_invalid_solid(self, tmp_path):
        service, store = self._store_world(tmp_path)
        playlist = service.create_playlist("Mix")
        cover = _png(tmp_path, "cover.png")
        before = self._managed_files(tmp_path)

        result = service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="replace",
            cover_source_path=cover,
            hero_mode="solid",
            hero_solid_color="not-a-color",
        )
        assert result == "invalid"
        assert self._managed_files(tmp_path) == before

    def test_hero_candidate_not_left_on_invalid_cover_action(self, tmp_path):
        service, store = self._store_world(tmp_path)
        playlist = service.create_playlist("Mix")
        hero = _png(tmp_path, "hero.png")
        before = self._managed_files(tmp_path)

        result = service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="bogus",  # invalid antes de preparar nada
            hero_mode="image",
            hero_image_source=hero,
        )
        assert result == "invalid"
        assert self._managed_files(tmp_path) == before

    def test_valid_apply_creates_and_retires_correctly(self, tmp_path):
        service, store = self._store_world(tmp_path)
        playlist = service.create_playlist("Mix")
        cover_a = _png(tmp_path, "a.png")
        assert (
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="replace",
                cover_source_path=cover_a,
                hero_mode="auto",
            )
            == "updated"
        )
        managed = self._managed_files(tmp_path)
        assert len(managed) == 1
        cover_b = _png(tmp_path, "b.png", 0xCB0543)
        assert (
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="replace",
                cover_source_path=cover_b,
                hero_mode="auto",
            )
            == "updated"
        )
        managed_after = self._managed_files(tmp_path)
        assert len(managed_after) == 1, "old cover no retirado"
        assert managed_after != managed


# ==========================================================================
# R5-02 — RESULT SEMANTICS CONVERGE
# ==========================================================================


class TestResultSemanticsConverged:
    def test_same_hero_solid_no_change_no_signal(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        # PL-FINAL-03: el camino canónico es apply_visual_appearance (los
        # slots legacy set_hero_* fueron removidos — cero consumers QML).
        assert (
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="keep",
                hero_mode="solid",
                hero_solid_color="#112233",
            )
            == "updated"
        )
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert (
            bridge.apply_visual_appearance(
                playlist.playlist_id, "keep", "", "solid", "#112233", [], 135.0, ""
            )
            == "no_change"
        )
        assert failures == []

    def test_same_hero_gradient_no_change_no_signal(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="keep",
            hero_mode="gradient",
            hero_gradient_colors=("#112233", "#445566"),
            hero_gradient_angle=45.0,
        )
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert (
            bridge.apply_visual_appearance(
                playlist.playlist_id,
                "keep",
                "",
                "gradient",
                "",
                ["#112233", "#445566"],
                45.0,
                "",
            )
            == "no_change"
        )
        assert failures == []

    def test_same_hero_auto_no_change_no_signal(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        service.apply_visual_appearance(
            playlist.playlist_id, cover_action="keep", hero_mode="auto"
        )
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert (
            bridge.apply_visual_appearance(
                playlist.playlist_id, "keep", "", "auto", "", [], 135.0, ""
            )
            == "no_change"
        )
        assert failures == []

    def test_duplicate_add_is_already_present_no_signal(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert bridge.add_track(playlist.playlist_id, "/a.flac") == "already_present"
        assert failures == []

    def test_real_db_failure_is_persistence_failed_with_signal(self, tmp_path):
        class _Failing(FakePlaylistsPort):
            def __init__(self):
                super().__init__()
                self.fail = False

            def save(self, playlists):
                if self.fail:
                    raise PlaylistPersistenceError("disk full")
                super().save(playlists)

            def save_navigation(self, state):
                if self.fail:
                    raise PlaylistPersistenceError("nav down")
                super().save_navigation(state)

            def save_state(self, playlists, navigation):
                if self.fail:
                    raise PlaylistPersistenceError("disk full")
                self._items = list(playlists)
                self._nav_stored = navigation

        port = _Failing()
        service, nav, coord, bridge = _world(tmp_path, port=port)
        playlist = service.create_playlist("Mix")  # write 1 OK
        port.fail = True
        failures = []
        bridge.persistenceFailed.connect(failures.append)
        assert bridge.pin_playlist(playlist.playlist_id) == "persistence_failed"
        assert failures == ["pin"]


# ==========================================================================
# R5-05 — mark_recent NO-OP
# ==========================================================================


class TestMarkRecentNoOp:
    def test_mark_recent_already_mru_zero_write_zero_notify(self, tmp_path):
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        a = service.create_playlist("A")
        service.mark_recent(a.playlist_id)
        writes_before = len(port.saved_nav)
        calls = []

        class _Sub:
            def __call__(self):
                calls.append(1)

        service.subscribe_changed(_Sub())
        assert service.mark_recent(a.playlist_id) is False
        assert len(port.saved_nav) == writes_before
        assert calls == []


# ==========================================================================
# R5-06 — LEGACY ASSET RETIREMENT
# ==========================================================================


class TestLegacyRetirement:
    def _legacy_store(self, tmp_path):
        store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
        (tmp_path / "managed").mkdir(exist_ok=True)
        return store

    def test_legacy_safe_uuid_cover_retired(self, tmp_path):
        store = self._legacy_store(tmp_path)
        legacy = (
            tmp_path / "managed" / "playlist_550e8400-e29b-41d4-a716-446655440000.png"
        )
        legacy.write_bytes(b"legacy")
        assert (
            store.delete_legacy_managed_asset(
                "550e8400-e29b-41d4-a716-446655440000", "cover", str(legacy)
            )
            is True
        )
        assert not legacy.exists()

    def test_legacy_safe_uuid_hero_retired(self, tmp_path):
        store = self._legacy_store(tmp_path)
        legacy = (
            tmp_path
            / "managed"
            / "playlist_550e8400-e29b-41d4-a716-446655440000_hero.png"
        )
        legacy.write_bytes(b"legacy")
        assert (
            store.delete_legacy_managed_asset(
                "550e8400-e29b-41d4-a716-446655440000", "hero", str(legacy)
            )
            is True
        )
        assert not legacy.exists()

    def test_ambiguous_legacy_owner_fail_closed(self, tmp_path):
        store = self._legacy_store(tmp_path)
        legacy = tmp_path / "managed" / "playlist_abc_hero_9a8b7c6d5e4f3a2b1c0d.png"
        legacy.write_bytes(b"legacy")
        # playlist_id terminando en _hero → gramática legacy ambigua.
        assert (
            store.delete_legacy_managed_asset("abc_hero", "cover", str(legacy)) is False
        )
        assert legacy.exists()

    def test_legacy_cross_playlist_never_removed(self, tmp_path):
        store = self._legacy_store(tmp_path)
        legacy = (
            tmp_path / "managed" / "playlist_550e8400-e29b-41d4-a716-446655440000.png"
        )
        legacy.write_bytes(b"legacy")
        other_id = "550e8400-e29b-41d4-a716-446655440001"
        assert (
            store.delete_legacy_managed_asset(other_id, "cover", str(legacy)) is False
        )
        assert legacy.exists()
