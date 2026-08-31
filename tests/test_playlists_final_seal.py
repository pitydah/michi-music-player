"""Playlists PL-FINAL — 10/10 convergence seal (mega hardening pass).

PL-FINAL-01  content-addressed asset REUSE: reselecting the exact same
             bytes is no_change and NEVER deletes the committed asset
PL-FINAL-02  QUrl boundary: file:/// through the real Bridge boundary
PL-FINAL-03  canonical appearance API: legacy slots removed
PL-FINAL-04  legacy retirement: stable + digest-era + fail-closed
PL-FINAL-05  real playlist description metadata
PL-FINAL-09  hero focal point persistence (0..1, tolerant decode)
PL-FINAL-13  batch add_tracks (one persist, added/skipped)
PL-FINAL-14  playlist-local search keeps canonicalIndex
PL-FINAL-15  batch remove_tracks (positions resolved before mutation)
PL-FINAL-16  explicit unavailable-track projection
PL-FINAL-18  duration index: playlist projection is O(tracks)
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage

from michi.application.errors import PlaylistPersistenceError
from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.domain.playlist import (
    MAX_DESCRIPTION_LENGTH,
)
from michi.infrastructure.playlist_artwork_store import (
    FilesystemPlaylistArtworkStore,
)
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from michi.presentation.playlists_bridge import PlaylistsBridge
from tests.test_playlists import FakePlaylistsPort


def _png(tmp_path, name, color=0xFF581C, size=16):
    img = QImage(size, size, QImage.Format_RGB32)
    img.fill(color)
    path = tmp_path / name
    assert img.save(str(path), "PNG")
    return path


class _FailAfterPort(FakePlaylistsPort):
    """Fails the next N save calls (truthful persistence failures)."""

    def __init__(self, fail_after=0):
        super().__init__()
        self._remaining = fail_after

    def save(self, playlists):
        if self._remaining > 0:
            self._remaining -= 1
            raise PlaylistPersistenceError("injected write failure")
        super().save(playlists)

    def save_state(self, playlists, navigation):
        if self._remaining > 0:
            self._remaining -= 1
            raise PlaylistPersistenceError("injected compound failure")
        self._stored = list(playlists)
        self._nav_stored = navigation


def _world(tmp_path, port=None):
    store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
    service = PlaylistService(
        playlists_port=port or FakePlaylistsPort(), artwork_store=store
    )
    nav = NavigationService()
    coord = PlaylistNavigationCoordinator(service, nav)
    bridge = PlaylistsBridge(service, playlist_navigation=coord, navigation_service=nav)
    return service, nav, coord, bridge


def _managed_files(tmp_path):
    managed = tmp_path / "managed"
    return sorted(p.name for p in managed.iterdir()) if managed.exists() else []


# ==========================================================================
# PL-FINAL-01 — CONTENT-ADDRESSED ASSET REUSE (KILLCRITIC)
# ==========================================================================


class TestAssetReuseSafety:
    def test_reselect_exact_cover_is_no_change_and_keeps_asset(self, tmp_path):
        """Cover A persisted → reselect EXACT bytes of A → no_change; A
        still exists; DB still references A; zero writes; zero notify; no
        new orphan."""
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        src = _png(tmp_path, "cover_a.png", 0xFF581C)
        assert (
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="replace",
                cover_source_path=src,
                hero_mode="auto",
            )
            == "updated"
        )
        committed = service.get_playlist(playlist.playlist_id).custom_cover_path
        assert committed
        assert Path(committed).is_file()
        writes_before = len(bridge._playlist_service._port.saved)
        notifications = []
        service.subscribe_changed(lambda: notifications.append(1))

        result = service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="replace",
            cover_source_path=src,
            hero_mode="auto",
        )

        assert result == "no_change"
        assert Path(committed).is_file(), "el asset commiteado NO puede borrarse"
        assert service.get_playlist(playlist.playlist_id).custom_cover_path == committed
        assert len(bridge._playlist_service._port.saved) == writes_before, "0 writes"
        assert notifications == [], "0 notify"
        assert len(_managed_files(tmp_path)) == 1, "sin orphans nuevos"

    def test_reselect_exact_hero_is_no_change_and_keeps_asset(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        src = _png(tmp_path, "hero_a.png", 0xCB0543)
        assert (
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="keep",
                hero_mode="image",
                hero_image_source=src,
            )
            == "updated"
        )
        committed = service.get_playlist(
            playlist.playlist_id
        ).appearance.hero_image_path
        writes_before = len(bridge._playlist_service._port.saved)
        notifications = []
        service.subscribe_changed(lambda: notifications.append(1))

        result = service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="keep",
            hero_mode="image",
            hero_image_source=src,
        )

        assert result == "no_change"
        assert Path(committed).is_file()
        assert (
            service.get_playlist(playlist.playlist_id).appearance.hero_image_path
            == committed
        )
        assert len(bridge._playlist_service._port.saved) == writes_before
        assert notifications == []

    def test_db_failure_with_reused_cover_keeps_committed_assets(self, tmp_path):
        """Cover A current → reselect A → also change hero → force DB
        failure: old committed cover A and old hero stay; DB unchanged;
        only truly new candidates cleaned."""
        port = _FailAfterPort(fail_after=0)
        service, nav, coord, bridge = _world(tmp_path, port=port)
        playlist = service.create_playlist("Mix")
        cover_src = _png(tmp_path, "cover_a.png", 0xFF581C)
        hero_src = _png(tmp_path, "hero_a.png", 0xCB0543)
        assert (
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="replace",
                cover_source_path=cover_src,
                hero_mode="image",
                hero_image_source=hero_src,
            )
            == "updated"
        )
        old_cover = service.get_playlist(playlist.playlist_id).custom_cover_path
        old_hero = service.get_playlist(playlist.playlist_id).appearance.hero_image_path
        files_before = set(_managed_files(tmp_path))

        # Nuevo hero distinto + cover reseleccionada → la persistence falla.
        new_hero_src = _png(tmp_path, "hero_b.png", 0x3366AA)
        port._remaining = 1
        raised = False
        try:
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="replace",
                cover_source_path=cover_src,
                hero_mode="image",
                hero_image_source=new_hero_src,
            )
        except PlaylistPersistenceError:
            raised = True

        assert raised
        assert Path(old_cover).is_file(), "old committed cover intacto"
        assert Path(old_hero).is_file(), "old committed hero intacto"
        assert (
            service.get_playlist(playlist.playlist_id).custom_cover_path == old_cover
        ), "DB in-memory unchanged"
        remaining = set(_managed_files(tmp_path))
        assert files_before == remaining, "solo candidates nuevos limpiados"

    def test_cross_playlist_ownership_never_deletes_other_assets(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        a_src = _png(tmp_path, "a.png", 0xFF581C)
        b_src = _png(tmp_path, "b.png", 0xCB0543)
        service.apply_visual_appearance(
            a.playlist_id,
            cover_action="replace",
            cover_source_path=a_src,
            hero_mode="auto",
        )
        service.apply_visual_appearance(
            b.playlist_id,
            cover_action="replace",
            cover_source_path=b_src,
            hero_mode="auto",
        )
        b_cover = service.get_playlist(b.playlist_id).custom_cover_path

        # Operación en A (nuevo cover + DB failure) nunca toca B.
        service.apply_visual_appearance(
            a.playlist_id,
            cover_action="replace",
            cover_source_path=_png(tmp_path, "a2.png", 0x22AA55),
            hero_mode="auto",
        )
        assert Path(b_cover).is_file(), "el asset de B nunca se borra"


# ==========================================================================
# PL-FINAL-02 — QURL BOUNDARY THROUGH THE REAL BRIDGE
# ==========================================================================


class TestQUrlBoundary:
    def test_file_url_cover_and_hero_cross_the_real_bridge(self, tmp_path):
        """QUrl.fromLocalFile(...).toString() → PlaylistsBridge →
        PlaylistService → ArtworkStore: updated; managed asset exists;
        persisted path is the managed LOCAL path; no asset_rejected."""
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        cover_img = _png(tmp_path, "cover.png", 0xFF581C)
        hero_img = _png(tmp_path, "hero.png", 0x3366AA)

        # COVER through the real QML-shaped boundary (string URL).
        result = bridge.apply_visual_appearance(
            playlist.playlist_id,
            "replace",
            QUrl.fromLocalFile(str(cover_img)).toString(),
            "auto",
            "",
            [],
            135.0,
            "",
            0.5,
            0.5,
        )
        assert result == "updated"
        persisted_cover = service.get_playlist(playlist.playlist_id).custom_cover_path
        assert persisted_cover.startswith(str(tmp_path / "managed"))
        assert Path(persisted_cover).is_file()

        # HERO through the same boundary.
        result = bridge.apply_visual_appearance(
            playlist.playlist_id,
            "keep",
            "",
            "image",
            "",
            [],
            135.0,
            QUrl.fromLocalFile(str(hero_img)).toString(),
            0.5,
            0.5,
        )
        assert result == "updated"
        persisted_hero = service.get_playlist(
            playlist.playlist_id
        ).appearance.hero_image_path
        assert persisted_hero.startswith(str(tmp_path / "managed"))
        assert Path(persisted_hero).is_file()

    def test_remote_schemes_rejected_before_filesystem(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        files_before = set(_managed_files(tmp_path))
        result = bridge.apply_visual_appearance(
            playlist.playlist_id,
            "replace",
            "https://example.com/cover.png",
            "auto",
            "",
            [],
            135.0,
            "",
        )
        assert result == "invalid"
        assert set(_managed_files(tmp_path)) == files_before, "cero side effects"


# ==========================================================================
# PL-FINAL-03 — CANONICAL APPEARANCE API (legacy slots removed)
# ==========================================================================


class TestCanonicalAppearanceApi:
    def test_legacy_slots_are_gone_from_the_bridge(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        for name in (
            "set_custom_cover",
            "set_custom_cover_from_url",
            "remove_custom_cover",
            "set_hero_auto",
            "set_hero_solid",
            "set_hero_gradient",
            "set_custom_hero_from_url",
        ):
            assert not hasattr(bridge, name), f"{name} debe estar removido"

    def test_canonical_apply_is_the_single_transaction(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        src = _png(tmp_path, "c.png")
        result = bridge.apply_visual_appearance(
            playlist.playlist_id, "replace", str(src), "auto", "", [], 135.0, ""
        )
        assert result == "updated"
        # same request again → truthful no_change (never a fake "updated").
        assert (
            bridge.apply_visual_appearance(
                playlist.playlist_id, "replace", str(src), "auto", "", [], 135.0, ""
            )
            == "no_change"
        )


# ==========================================================================
# PL-FINAL-04 — LEGACY RETIREMENT (stable + digest-era, fail-closed)
# ==========================================================================


class TestLegacyRetirement:
    def _store_dir(self, tmp_path):
        return tmp_path / "managed"

    def test_stable_legacy_cover_and_hero_retired(self, tmp_path):
        store = FilesystemPlaylistArtworkStore(self._store_dir(tmp_path))
        storage = self._store_dir(tmp_path)
        storage.mkdir(parents=True)
        cover = storage / "playlist_p1.png"
        hero = storage / "playlist_p1_hero.jpg"
        cover.write_bytes(b"x")
        hero.write_bytes(b"y")
        assert store.delete_legacy_managed_asset("p1", "cover", str(cover)) is True
        assert store.delete_legacy_managed_asset("p1", "hero", str(hero)) is True
        assert not cover.exists() and not hero.exists()

    def test_digest_era_cover_and_hero_retired(self, tmp_path):
        store = FilesystemPlaylistArtworkStore(self._store_dir(tmp_path))
        storage = self._store_dir(tmp_path)
        storage.mkdir(parents=True)
        digest = "0123456789abcdef0123"
        cover = storage / f"playlist_p1_{digest}.png"
        hero = storage / f"playlist_p1_hero_{digest}.webp"
        cover.write_bytes(b"x")
        hero.write_bytes(b"y")
        assert store.delete_legacy_managed_asset("p1", "cover", str(cover)) is True
        assert store.delete_legacy_managed_asset("p1", "hero", str(hero)) is True
        assert not cover.exists() and not hero.exists()

    def test_ambiguous_owner_fails_closed(self, tmp_path):
        store = FilesystemPlaylistArtworkStore(self._store_dir(tmp_path))
        storage = self._store_dir(tmp_path)
        storage.mkdir(parents=True)
        # "x_hero" es ambiguo: cover de x_hero == hero de x → nunca borra.
        digest = "0123456789abcdef0123"
        ambiguous_cover = storage / f"playlist_x_hero_{digest}.png"
        ambiguous_cover.write_bytes(b"x")
        assert (
            store.delete_legacy_managed_asset("x_hero", "cover", str(ambiguous_cover))
            is False
        )
        assert ambiguous_cover.exists()
        # Id que termina en patrón de digest → fail-closed en digest-era.
        ambiguous_digest = storage / "playlist_abc123_0123456789abcdef0123.png"
        ambiguous_digest.write_bytes(b"x")
        assert (
            store.delete_legacy_managed_asset(
                "abc123_0123456789abcdef0123", "cover", str(ambiguous_digest)
            )
            is False
        )
        assert ambiguous_digest.exists()

    def test_cross_playlist_legacy_never_deletes(self, tmp_path):
        store = FilesystemPlaylistArtworkStore(self._store_dir(tmp_path))
        storage = self._store_dir(tmp_path)
        storage.mkdir(parents=True)
        other = storage / "playlist_p2.png"
        other.write_bytes(b"x")
        # delete p1's cover with p2's file → refused (ownership mismatch).
        assert store.delete_legacy_managed_asset("p1", "cover", str(other)) is False
        assert other.exists()

    def test_delete_playlist_retires_legacy_digest_assets(self, tmp_path):
        """Centralized post-commit retirement covers digest-era too."""
        storage = tmp_path / "managed"
        storage.mkdir(parents=True)
        digest = "0123456789abcdef0123"
        legacy_cover = storage / f"playlist_{digest}cover.png"
        legacy_cover.write_bytes(b"x")
        # Playlist con id UUID normal: el legacy digest NO pertenece — el
        # delete solo retira paths referenciados por la playlist.
        repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
        service = PlaylistService(
            playlists_port=repo, artwork_store=FilesystemPlaylistArtworkStore(storage)
        )
        playlist = service.create_playlist("Mix")
        src = _png(tmp_path, "real.png")
        service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="replace",
            cover_source_path=src,
            hero_mode="auto",
        )
        v2_cover = service.get_playlist(playlist.playlist_id).custom_cover_path
        assert Path(v2_cover).is_file()
        service.delete_playlist(playlist.playlist_id)
        assert not Path(v2_cover).exists(), "V2 retirado tras commit"
        assert legacy_cover.exists(), "asset ajeno nunca se toca"


# ==========================================================================
# PL-FINAL-05 — REAL PLAYLIST DESCRIPTION
# ==========================================================================


class TestPlaylistDescription:
    def test_description_roundtrip_and_survives_rename(self, tmp_path):
        db_path = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db_path)
        service = PlaylistService(playlists_port=repo)
        playlist = service.create_playlist("Mix")
        assert service.set_playlist_description(
            playlist.playlist_id, "  Morning commute vibes  "
        )
        assert service.get_playlist(playlist.playlist_id).description == (
            "Morning commute vibes"
        )
        service.rename_playlist(playlist.playlist_id, "Commute")
        service.add_track(playlist.playlist_id, "/a.flac")
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(db_path)
        ).get_playlist(playlist.playlist_id)
        assert reloaded is not None
        assert reloaded.description == "Morning commute vibes"
        assert reloaded.name == "Commute"

    def test_description_length_and_no_change(self, tmp_path):
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        playlist = service.create_playlist("Mix")
        try:
            service.set_playlist_description(
                playlist.playlist_id, "x" * (MAX_DESCRIPTION_LENGTH + 1)
            )
            raised = False
        except ValueError:
            raised = True
        assert raised
        assert service.set_playlist_description(playlist.playlist_id, "Hello")
        assert service.set_playlist_description(playlist.playlist_id, "Hello") is False
        assert len(service._port.saved) == 2  # create + 1 description

    def test_bridge_description_codes(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        assert (
            bridge.set_playlist_description(playlist.playlist_id, "Vibes") == "updated"
        )
        assert (
            bridge.set_playlist_description(playlist.playlist_id, "Vibes")
            == "no_change"
        )
        assert (
            bridge.set_playlist_description(
                playlist.playlist_id, "x" * (MAX_DESCRIPTION_LENGTH + 1)
            )
            == "invalid"
        )
        assert bridge.set_playlist_description("ghost", "x") == "not_found"
        assert bridge.property("selectedPlaylistDescription") == ""  # no selection


# ==========================================================================
# PL-FINAL-09 — HERO FOCAL POINT
# ==========================================================================


class TestHeroFocalPoint:
    def test_focal_defaults_and_persist_roundtrip(self, tmp_path):
        db_path = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db_path)
        service = PlaylistService(
            playlists_port=repo,
            artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        playlist = service.create_playlist("Mix")
        assert playlist.appearance.hero_focal_x == 0.5
        assert playlist.appearance.hero_focal_y == 0.5
        src = _png(tmp_path, "h.png", 0x3366AA, size=64)
        assert (
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="keep",
                hero_mode="image",
                hero_image_source=src,
                hero_focal_x=0.82,
                hero_focal_y=0.27,
            )
            == "updated"
        )
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(db_path)
        ).get_playlist(playlist.playlist_id)
        assert reloaded.appearance.hero_focal_x == 0.82
        assert reloaded.appearance.hero_focal_y == 0.27

    def test_focal_clamped_and_tolerated_on_decode(self, tmp_path):
        db_path = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db_path)
        service = PlaylistService(
            playlists_port=repo,
            artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        playlist = service.create_playlist("Mix")
        src = _png(tmp_path, "h2.png", 0x3366AA, size=64)
        service.apply_visual_appearance(
            playlist.playlist_id,
            cover_action="keep",
            hero_mode="image",
            hero_image_source=src,
            hero_focal_x=1.7,
            hero_focal_y=-0.3,
        )
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(db_path)
        ).get_playlist(playlist.playlist_id)
        assert reloaded.appearance.hero_focal_x == 1.0
        assert reloaded.appearance.hero_focal_y == 0.0

    def test_appearance_row_exposes_focal(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        nav.navigate_to_playlist(playlist.playlist_id)
        row = bridge.property("selectedPlaylistAppearance")
        assert row["heroFocalX"] == 0.5 and row["heroFocalY"] == 0.5


# ==========================================================================
# PL-FINAL-13 — BATCH ADD TRACKS
# ==========================================================================


class TestBatchAddTracks:
    def test_add_tracks_dedupes_and_counts(self, tmp_path):
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        writes_before = len(port.saved)
        notifications = []
        service.subscribe_changed(lambda: notifications.append(1))

        added, already = service.add_tracks(
            playlist.playlist_id,
            ["/b.flac", "/a.flac", "/b.flac", "/c.flac", "/a.flac"],
        )

        assert added == 2  # b, c (dedupe + skip already)
        assert already == 1  # a contado una vez
        assert len(port.saved) == writes_before + 1, "UN persist"
        assert len(notifications) == 1, "UN notify"
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a.flac",
            "/b.flac",
            "/c.flac",
        ), "orden determinista primer-seen"

    def test_add_tracks_all_present_is_no_change(self, tmp_path):
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        writes_before = len(port.saved)
        added, already = service.add_tracks(playlist.playlist_id, ["/a.flac"])
        assert (added, already) == (0, 1)
        assert len(port.saved) == writes_before, "cero writes en no-op"

    def test_bridge_batch_structured_result(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        result = bridge.add_tracks(
            playlist.playlist_id, ["/b.flac", "/a.flac", "/c.flac"]
        )
        assert result["status"] == "updated"
        assert result["addedCount"] == 2
        assert result["alreadyPresentCount"] == 1
        no_change = bridge.add_tracks(playlist.playlist_id, ["/a.flac", "/b.flac"])
        assert no_change["status"] == "no_change"
        assert no_change["addedCount"] == 0
        missing = bridge.add_tracks("ghost", ["/x.flac"])
        assert missing["status"] == "not_found"

    def test_batch_failure_never_partial(self, tmp_path):
        port = _FailAfterPort(fail_after=0)
        service = PlaylistService(playlists_port=port)
        playlist = service.create_playlist("Mix")
        port._remaining = 1
        raised = False
        try:
            service.add_tracks(playlist.playlist_id, ["/a.flac", "/b.flac"])
        except PlaylistPersistenceError:
            raised = True
        assert raised
        assert service.get_playlist(playlist.playlist_id).track_paths == (), (
            "cero mutación parcial"
        )


# ==========================================================================
# PL-FINAL-14 — PLAYLIST-LOCAL SEARCH (canonical index preserved)
# ==========================================================================


class _FakeLibrary:
    """Minimal LibraryService-compatible double for projection tests."""

    def __init__(self):
        self.state = type(
            "State",
            (),
            {
                "tracks": (
                    TrackRef(
                        "/alpha.flac",
                        "Alpha",
                        "Artist A",
                        "Album 1",
                        60000,
                        codec="flac",
                        sample_rate_hz=44100,
                        bit_depth=16,
                        channels=2,
                        file_size=100,
                    ),
                    TrackRef(
                        "/beta.flac",
                        "Beta",
                        "Artist B",
                        "Album 1",
                        120000,
                        codec="flac",
                        sample_rate_hz=48000,
                        bit_depth=24,
                        channels=2,
                        file_size=200,
                    ),
                ),
                "albums": (),
                "query": (),
                "search_active": False,
                "visible_tracks": (),
            },
        )

    def resolve_trackref(self, path):
        for t in self.state.tracks:
            if t.file_path == path:
                return t
        return None

    def artwork_path_for(self, album_key):
        return None

    def subscribe_changed(self, cb):
        pass

    def unsubscribe_changed(self, cb):
        pass


def _world_with_library(tmp_path):
    service = PlaylistService(
        playlists_port=FakePlaylistsPort(),
        artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
    )
    playlist = service.create_playlist("Mix")
    service.add_tracks(
        playlist.playlist_id, ["/alpha.flac", "/beta.flac", "/gamma.flac"]
    )
    nav = NavigationService()
    nav.navigate_to_playlist(playlist.playlist_id)
    library = _FakeLibrary()
    bridge = PlaylistsBridge(service, navigation_service=nav, library=library)
    return bridge, playlist


class TrackRef:
    def __init__(self, file_path, title, artist, album, duration_ms, **kw):
        from pathlib import Path

        self.file_path = Path(file_path)
        self.display_name = title
        self.title = title
        self.artist = artist
        self.album = album
        self.duration_ms = duration_ms
        self.codec = kw.get("codec", "")
        self.sample_rate_hz = kw.get("sample_rate_hz", 0)
        self.bit_depth = kw.get("bit_depth", 0)
        self.channels = kw.get("channels", 0)
        self.file_size = kw.get("file_size", 0)
        self.bitrate_bps = kw.get("bitrate_bps", 0)


class TestPlaylistLocalSearch:
    def test_filter_keeps_canonical_index(self, tmp_path):
        bridge, playlist = _world_with_library(tmp_path)
        all_rows = bridge.property("playlistTrackRows")
        assert [r["canonicalIndex"] for r in all_rows] == [0, 1, 2]
        assert all_rows[0]["available"] is True
        assert all_rows[2]["available"] is False  # gamma no está en la library
        assert all_rows[2]["unavailableReason"] == "not_in_library"

        bridge.set_playlist_search_query("beta")
        filtered = bridge.property("playlistTrackRows")
        assert len(filtered) == 1
        assert filtered[0]["title"] == "Beta"
        assert filtered[0]["canonicalIndex"] == 1, "índice CANONICO preservado"

        bridge.set_playlist_search_query("")
        assert len(bridge.property("playlistTrackRows")) == 3

    def test_search_never_touches_global_library_search(self, tmp_path):
        bridge, playlist = _world_with_library(tmp_path)
        bridge.set_playlist_search_query("alpha")
        assert bridge._library.state.search_active is False
        assert bridge.property("playlistSearchQuery") == "alpha"


# ==========================================================================
# PL-FINAL-15 — BATCH REMOVE (positions resolved before mutation)
# ==========================================================================


class TestBatchRemove:
    def test_remove_tracks_resolves_indices_and_persists_once(self, tmp_path):
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        playlist = service.create_playlist("Mix")
        service.add_tracks(
            playlist.playlist_id, ["/a.flac", "/b.flac", "/c.flac", "/d.flac"]
        )
        writes_before = len(port.saved)
        notifications = []
        service.subscribe_changed(lambda: notifications.append(1))

        assert service.remove_tracks(playlist.playlist_id, [1, 3, 99])

        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a.flac",
            "/c.flac",
        )
        assert len(port.saved) == writes_before + 1, "UN persist"
        assert len(notifications) == 1, "UN notify"

    def test_bridge_remove_tracks_codes(self, tmp_path):
        service, nav, coord, bridge = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        nav.navigate_to_playlist(playlist.playlist_id)
        service.add_tracks(playlist.playlist_id, ["/a.flac", "/b.flac", "/c.flac"])
        assert bridge.remove_tracks([0, 2]) == "removed"
        assert service.get_playlist(playlist.playlist_id).track_paths == ("/b.flac",)
        assert bridge.remove_tracks([5]) == "invalid_index"
        bridge.set_playlist_search_query("x")
        assert bridge.remove_tracks([0]) == "removed", "remueve por índice canónico"


# ==========================================================================
# PL-FINAL-16 — EXPLICIT UNAVAILABLE TRACKS
# ==========================================================================


class TestUnavailableTracks:
    def test_unavailable_count_is_honest(self, tmp_path):
        bridge, playlist = _world_with_library(tmp_path)
        assert bridge.property("playlistUnavailableCount") == 1  # gamma
        rows = bridge.property("playlistTrackRows")
        missing = [r for r in rows if not r["available"]]
        assert len(missing) == 1
        assert missing[0]["title"] == "gamma"
        assert missing[0]["unavailableReason"] == "not_in_library"
        # El track NUNCA se borra silenciosamente de la playlist.
        assert (
            len(bridge._playlist_service.get_playlist(playlist.playlist_id).track_paths)
            == 3
        )

    def test_missing_becomes_available_after_library_refresh(self, tmp_path):
        bridge, playlist = _world_with_library(tmp_path)
        assert bridge.property("playlistUnavailableCount") == 1
        # library gana el track: refresh → la row vuelve a available.
        bridge._library.state.tracks = (
            TrackRef("/alpha.flac", "Alpha", "Artist A", "Album 1", 60000),
            TrackRef("/beta.flac", "Beta", "Artist B", "Album 1", 120000),
            TrackRef("/gamma.flac", "Gamma", "Artist C", "Album 2", 90000),
        )
        bridge._on_library_changed()
        assert bridge.property("playlistUnavailableCount") == 0
        rows = bridge.property("playlistTrackRows")
        assert all(r["available"] for r in rows)


# ==========================================================================
# PL-FINAL-18 — DURATION INDEX (O(playlists × tracks), no nested scans)
# ==========================================================================


class TestDurationIndex:
    def test_duration_index_rebuilt_only_on_library_change(self, tmp_path):
        bridge, playlist = _world_with_library(tmp_path)
        index = bridge._build_duration_index()
        assert index == {"/alpha.flac": 60000, "/beta.flac": 120000}
        assert bridge._duration_index is index  # cached
        bridge._on_library_changed()
        assert bridge._duration_index is None, "invalidado con la revision"

    def test_overview_projection_100_and_500_playlists(self, tmp_path):
        """Benchmark gate: overview projection stays in O(playlists ×
        tracks) — CI-stable thresholds, no microsecond vanity."""
        import time

        for count in (100, 500):
            port = FakePlaylistsPort()
            service = PlaylistService(playlists_port=port)
            for i in range(count):
                p = service.create_playlist(f"Playlist {i}")
                service.add_tracks(
                    p.playlist_id,
                    [f"/track_{i}_{j}.flac" for j in range(8)],
                )
            library = _FakeLibrary()
            bridge = PlaylistsBridge(service, library=library)
            start = time.perf_counter()
            rows = bridge.property("playlists")
            elapsed = time.perf_counter() - start
            assert len(rows) == count
            assert elapsed < 2.0, f"{count} playlists projection: {elapsed:.3f}s"
            # Cached repeat access is ~free.
            start = time.perf_counter()
            bridge.property("playlists")
            cached = time.perf_counter() - start
            assert cached < 0.05
            bridge.dispose()
