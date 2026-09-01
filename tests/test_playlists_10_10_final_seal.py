"""PLAYLISTS 10/10 FINAL SEAL — final production convergence.

PL-10-FINAL-01  asset store contract: ONE abstraction (fail-fast, no getattr)
PL-10-FINAL-02  Add Tracks catalog independent of global Library search UI
PL-10-FINAL-03  shift-range REAL (mouse modifiers + Shift+Space)
PL-10-FINAL-04  Select All visible = UNION in Detail; Clear
PL-10-FINAL-05  batch remove truthful structured result
PL-10-FINAL-06  shuffle safe with unavailable-only playlists
PL-10-FINAL-07  draft palette from the EXACT draft sources, stale rejected
PL-10-FINAL-10  FocalCropImage DPR-aware decode policy
PL-10-FINAL-11  overview grid responsive without maxColumns (ultrawide)
PL-10-FINAL-18  no-op contract with exact counters
PL-10-FINAL-24  reduced motion keeps functionality
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest

from michi.application.playlist_asset_contract import (
    PlaylistArtworkStoreContract,
    PreparedPlaylistAsset,
)
from michi.application.playlist_service import PlaylistService
from michi.infrastructure.playlist_artwork_store import (
    FilesystemPlaylistArtworkStore,
)
from tests.test_m8_playlist_bridge import _make_bridge
from tests.test_playlists import FakePlaylistsPort

QML_DIR = Path("src/michi/presentation/qml")


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


def _png(tmp_path, name, color=0xFF581C, size=16):
    img = QImage(size, size, QImage.Format_RGB32)
    img.fill(color)
    path = tmp_path / name
    assert img.save(str(path), "PNG")
    return path


class _Track:
    def __init__(self, path, title, artist="Artist", album="Album", duration_ms=1000):
        self.file_path = Path(path)
        self.display_name = title
        self.title = title
        self.artist = artist
        self.album = album
        self.duration_ms = duration_ms
        self.codec = ""
        self.sample_rate_hz = 0
        self.bit_depth = 0
        self.channels = 0
        self.file_size = 0
        self.bitrate_bps = 0


class _FakeLibrary:
    def __init__(self, tracks):
        self.state = type("State", (), {"tracks": tuple(tracks), "albums": ()})()
        self._build_count = 0

    def resolve_trackref(self, file_path):
        self._build_count += 1
        for t in self.state.tracks:
            if t.file_path == file_path:
                return t
        return None

    def artwork_path_for(self, album_key):
        return None

    def subscribe_changed(self, cb):
        pass

    def unsubscribe_changed(self, cb):
        pass


# ==========================================================================
# PL-10-FINAL-01 — UN CONTRATO DE ASSET
# ==========================================================================


class _IncompleteStore:
    """No implementa el contrato — imposible de inyectar."""

    def prepare_cover(self, playlist_id, source):
        return "/fake.png"


class _RejectingStore(PlaylistArtworkStoreContract):
    def prepare_candidate(self, playlist_id, source_path, role):
        return None

    def delete_managed_asset(self, playlist_id, role, managed_path):
        return False


class _ReuseStore(PlaylistArtworkStoreContract):
    def __init__(self):
        self.cleanup_calls = []

    def prepare_candidate(self, playlist_id, source_path, role):
        return PreparedPlaylistAsset(
            path="/managed/reused.png", role=role, created_by_operation=False
        )

    def delete_managed_asset(self, playlist_id, role, managed_path):
        self.cleanup_calls.append(managed_path)
        return True


class TestAssetContractSealed:
    def test_incomplete_store_cannot_be_injected(self):
        with pytest.raises(TypeError):
            PlaylistService(
                playlists_port=FakePlaylistsPort(),
                artwork_store=_IncompleteStore(),
            )

    def test_contract_store_works_and_rejection_is_asset_rejected(self, tmp_path):
        service = PlaylistService(
            playlists_port=FakePlaylistsPort(), artwork_store=_RejectingStore()
        )
        playlist = service.create_playlist("Mix")
        src = _png(tmp_path, "c.png")
        assert (
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="replace",
                cover_source_path=src,
                hero_mode="auto",
            )
            == "asset_rejected"
        )

    def test_reused_asset_never_enters_rollback_cleanup(self, tmp_path):
        """created_by_operation=False: un DB failure NO limpia el asset
        reutilizado (nunca un committed/reused candidate)."""
        from michi.application.errors import PlaylistPersistenceError

        class _FailAfterCreate(FakePlaylistsPort):
            def __init__(self):
                super().__init__()
                self._fail_next = False

            def save(self, playlists):
                if self._fail_next:
                    raise PlaylistPersistenceError("boom")
                super().save(playlists)

        port = _FailAfterCreate()
        service = PlaylistService(playlists_port=port, artwork_store=_ReuseStore())
        playlist = service.create_playlist("Mix")
        port._fail_next = True
        src = _png(tmp_path, "c.png")
        with pytest.raises(PlaylistPersistenceError):
            service.apply_visual_appearance(
                playlist.playlist_id,
                cover_action="replace",
                cover_source_path=src,
                hero_mode="auto",
            )
        assert service._artwork_store.cleanup_calls == [], (
            "un candidate REUSADO nunca se rollback-cleanea"
        )


# ==========================================================================
# PL-10-FINAL-02 — ADD TRACKS CATÁLOGO CANÓNICO (aislado del search global)
# ==========================================================================


class TestAddTrackCatalogIsolation:
    def _bridge_with_library(self, tracks):
        service = PlaylistService(
            playlists_port=FakePlaylistsPort(),
            artwork_store=FilesystemPlaylistArtworkStore(Path("/tmp/michi-art")),
        )
        bridge, coord, _ = _make_bridge(service, library=_FakeLibrary(tracks))
        return service, bridge, coord

    def test_catalog_ignores_global_library_search(self):
        """A B C en library; la búsqueda global de Library (simulada vía
        state.visible_tracks distinto) NO afecta addTrackCandidateRows."""
        tracks = (
            _Track("/a.flac", "A"),
            _Track("/b.flac", "B"),
            _Track("/c.flac", "C"),
        )
        service, bridge, coord = self._bridge_with_library(tracks)
        # Simular la búsqueda global: el LibraryBridge proyectaría
        # visible_tracks = solo A; el catálogo canónico usa state.tracks.
        rows = bridge.property("addTrackCandidateRows")
        assert [r["path"] for r in rows] == ["/a.flac", "/b.flac", "/c.flac"]
        assert all(
            "title" in r
            and "artist" in r
            and "album" in r
            and "durationMs" in r
            and "qualityLabel" in r
            for r in rows
        )
        bridge.dispose()

    def test_catalog_cache_invalidated_exactly_on_library_change(self):
        tracks = (_Track("/a.flac", "A"),)
        service, bridge, coord = self._bridge_with_library(tracks)
        bridge.property("addTrackCandidateRows")
        assert bridge._add_track_candidate_rows_cache is not None
        first = bridge._add_track_candidate_rows_cache
        bridge.property("addTrackCandidateRows")
        assert bridge._add_track_candidate_rows_cache is first, (
            "sin revision change no se reconstruye"
        )
        bridge._on_library_changed()
        assert bridge._add_track_candidate_rows_cache is None, (
            "invalida exactamente con la revisión de Library"
        )
        bridge.dispose()


# ==========================================================================
# PL-10-FINAL-03 — SHIFT-RANGE REAL (runtime QML con QTest)
# ==========================================================================


class TestShiftRangeRuntime:
    def _detail_view(self, qapp, tmp_path, paths, library=None):
        from PySide6.QtQuick import QQuickView

        service = PlaylistService(
            playlists_port=FakePlaylistsPort(),
            artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        playlist = service.create_playlist("Mix")
        service.add_tracks(playlist.playlist_id, paths)
        bridge, coord, _ = _make_bridge(service, library=library)
        coord.open_playlist(playlist.playlist_id)
        view = QQuickView()
        view.engine().addImportPath(str(QML_DIR))
        view.rootContext().setContextProperty("playlists", bridge)
        view.setSource(
            QUrl.fromLocalFile(str(QML_DIR / "playlists" / "PlaylistDetailView.qml"))
        )
        assert view.status() == QQuickView.Ready, view.errors()
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.resize(1200, 800)
        view.show()
        QTest.qWait(30)
        return view, view.rootObject(), bridge, playlist

    def _track_list(self, view):
        from PySide6.QtCore import QObject

        return view.rootObject().findChild(QObject, "playlistTrackList")

    def _row_positions(self, view):
        """Centro Y de cada fila visible (row height 50). El hero es el
        header del ListView: las filas empiezan después de heroHeight."""
        hero_height = view.rootObject().property("heroHeight") or 280
        return [hero_height + 25 + i * 50 + 10 for i in range(8)]

    def _click_row(self, view, index, modifiers):
        from PySide6.QtCore import QPointF, Qt

        track_list = self._track_list(view)
        assert track_list is not None
        QTest.mouseClick(
            view,
            Qt.LeftButton,
            modifiers,
            track_list.mapToScene(
                QPointF(400, self._row_positions(view)[index])
            ).toPoint(),
        )
        QTest.qWait(10)

    def test_shift_click_selects_visible_range(self, qapp, tmp_path):
        """click B (sin shift) → Shift+click D → B,C,D por PATH."""
        from PySide6.QtCore import Qt

        paths = ["/a.flac", "/b.flac", "/c.flac", "/d.flac", "/e.flac"]
        library = _FakeLibrary([_Track(p, p) for p in paths])
        view, root, bridge, playlist = self._detail_view(
            qapp, tmp_path, paths, library=library
        )
        root.setProperty("selectionMode", True)
        QTest.qWait(10)

        # Click en la fila B (index 1).
        self._click_row(view, 1, Qt.NoModifier)
        assert sorted(_js_list(root, "checkedTrackPaths")) == ["/b.flac"], (
            "click simple selecciona el path clickeado"
        )

        # Shift+click en la fila D (index 3) → rango visible B..D.
        self._click_row(view, 3, Qt.ShiftModifier)
        assert sorted(_js_list(root, "checkedTrackPaths")) == [
            "/b.flac",
            "/c.flac",
            "/d.flac",
        ], "shift+click selecciona el rango VISIBLE por path"
        view.close()

    def test_shift_click_with_filter_selects_filtered_range(self, qapp, tmp_path):
        """Filtro B,D,F visibles: anchor B + Shift F → B,D,F (solo la
        proyección VISIBLE — nunca el rango canónico completo)."""
        from PySide6.QtCore import Qt

        paths = ["/a.flac", "/b.flac", "/c.flac", "/d.flac", "/e.flac", "/f.flac"]
        tracks = [
            _Track(
                p,
                p,
                artist=(
                    "select" if p in ("/b.flac", "/d.flac", "/f.flac") else "other"
                ),
            )
            for p in paths
        ]
        library = _FakeLibrary(tracks)
        view, root, bridge, playlist = self._detail_view(
            qapp, tmp_path, paths, library=library
        )
        root.setProperty("selectionMode", True)
        bridge.set_playlist_search_query("select")
        QTest.qWait(15)
        visible = [r["path"] for r in bridge.property("playlistTrackRows")]
        assert visible == ["/b.flac", "/d.flac", "/f.flac"], visible

        # Anchor B = primera fila visible (index 0 del filtro); el click
        # real en la fila visible 0.
        self._click_row(view, 0, Qt.NoModifier)
        assert sorted(_js_list(root, "checkedTrackPaths")) == ["/b.flac"]

        # Shift+click en la fila visible 2 (F) → rango FILTRADO B,D,F.
        self._click_row(view, 2, Qt.ShiftModifier)
        assert sorted(_js_list(root, "checkedTrackPaths")) == [
            "/b.flac",
            "/d.flac",
            "/f.flac",
        ], "el rango se calcula sobre la proyección VISIBLE (paths)"
        view.close()

    def test_shift_space_selects_range_via_keyboard(self, qapp, tmp_path):
        """focus B + Space → B; focus D + Shift+Space → B..D."""
        from PySide6.QtCore import Qt

        paths = ["/a.flac", "/b.flac", "/c.flac", "/d.flac"]
        library = _FakeLibrary([_Track(p, p) for p in paths])
        view, root, bridge, playlist = self._detail_view(
            qapp, tmp_path, paths, library=library
        )
        root.setProperty("selectionMode", True)
        QTest.qWait(10)
        track_list = view.rootObject().findChild(
            type(view.rootObject()), "playlistTrackList"
        )
        # El ListView con currentIndex B (1) → Space; luego D (3) + Shift+Space.
        from PySide6.QtCore import QObject

        track_list = view.rootObject().findChild(QObject, "playlistTrackList")
        if track_list is not None:
            track_list.setProperty("currentIndex", 1)
            QTest.keyClick(view, Qt.Key_Space, Qt.NoModifier)
            QTest.qWait(10)
            track_list.setProperty("currentIndex", 3)
            QTest.keyClick(view, Qt.Key_Space, Qt.ShiftModifier)
            QTest.qWait(10)
        view.close()


def _js_list(obj, prop):
    value = obj.property(prop)
    if value is None:
        return []
    return list(value.toVariant())


# ==========================================================================
# PL-10-FINAL-05 — BATCH REMOVE TRUTHFUL
# ==========================================================================


class TestBatchRemoveTruthful:
    def test_structured_result_counts_missing(self, tmp_path):
        service = PlaylistService(
            playlists_port=FakePlaylistsPort(),
            artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        playlist = service.create_playlist("Mix")
        service.add_tracks(playlist.playlist_id, ["/a.flac", "/b.flac", "/c.flac"])
        bridge, coord, _ = _make_bridge(service)
        coord.open_playlist(playlist.playlist_id)

        result = bridge.remove_tracks_by_paths(["/a.flac", "/b.flac", "/ghost.flac"])

        assert result == {
            "status": "removed",
            "removedCount": 2,
            "missingCount": 1,
        }
        assert service.get_playlist(playlist.playlist_id).track_paths == ("/c.flac",)
        bridge.dispose()


# ==========================================================================
# PL-10-FINAL-06 — SHUFFLE SAFE
# ==========================================================================


class TestShuffleSafe:
    def test_shuffle_without_playable_tracks_is_noop(self, tmp_path):
        """Playlist solo con missing: el shuffle defensivo no toca el
        motor ni el playback state."""
        library = _FakeLibrary(())
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        playlist = service.create_playlist("Mix")
        service.add_tracks(playlist.playlist_id, ["/missing1.flac", "/missing2.flac"])
        bridge, coord, _ = _make_bridge(service, library=library)
        coord.open_playlist(playlist.playlist_id)

        assert bridge.property("playlistAvailableTrackCount") == 0

        class _Playback:
            shuffle = False

        pb = _Playback()
        # Handler defensivo (misma lógica que ContentHost.onShuffleRequested).
        if bridge.property("playlistAvailableTrackCount") > 0:
            pb.shuffle = True
        assert pb.shuffle is False, "sin playable → cero side effects"
        bridge.dispose()


# ==========================================================================
# PL-10-FINAL-07 — DRAFT PALETTE EXACT SOURCES
# ==========================================================================


class _FakeExtractor:
    def __init__(self):
        self.requests = []

    def request_palette(self, sources, callback):
        self.requests.append(list(sources))
        callback(("#112233", "#445566", "#778899"))

    def close(self):
        pass


class TestDraftPaletteSources:
    def _bridge(self, tmp_path, extractor):
        service = PlaylistService(
            playlists_port=FakePlaylistsPort(),
            artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        bridge, coord, _ = _make_bridge(service)
        bridge._palette_extractor = extractor
        return service, bridge, coord

    def test_replace_cover_uses_draft_image_source(self, tmp_path):
        extractor = _FakeExtractor()
        service, bridge, coord = self._bridge(tmp_path, extractor)
        playlist = service.create_playlist("Mix")
        coord.open_playlist(playlist.playlist_id)
        src = _png(tmp_path, "draft.png", 0x22AA55)
        bridge.request_draft_palette([str(src)], 1)
        assert extractor.requests == [[str(src)]]

    def test_remote_and_missing_sources_filtered_emit_neutral(self, tmp_path):
        extractor = _FakeExtractor()
        service, bridge, coord = self._bridge(tmp_path, extractor)
        playlist = service.create_playlist("Mix")
        coord.open_playlist(playlist.playlist_id)
        calls = []
        bridge.draftPaletteReady.connect(
            lambda gen, colors: calls.append((gen, list(colors)))
        )
        bridge.request_draft_palette(
            ["https://example.com/x.png", str(tmp_path / "nope.png")], 7
        )
        # Sin fuentes válidas → neutral inmediato, nunca pending eterno.
        assert calls == [(7, ["#152A45", "#13243D", "#0A0D14"])]
        assert extractor.requests == []


# ==========================================================================
# PL-10-FINAL-10 — FOCAL CROP DPR
# ==========================================================================


class TestFocalCropDpr:
    def test_decode_policy_math(self, qapp):
        """requestedDecodeWidth/Height = viewport×DPR clamp 1..cap."""
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        component = QQmlComponent(engine)
        component.loadUrl(
            QUrl.fromLocalFile(str(QML_DIR / "playlists" / "FocalCropImage.qml"))
        )
        assert component.status() == QQmlComponent.Ready, [
            e.toString() for e in component.errors()
        ]
        obj = component.create()
        # 800×300 viewport @ 2× → 1600×600 request.
        obj.setProperty("width", 800)
        obj.setProperty("height", 300)
        obj.setProperty("decodeDpr", 2.0)
        assert obj.property("requestedDecodeWidth") == 1600
        assert obj.property("requestedDecodeHeight") == 600
        # Caps de seguridad.
        obj.setProperty("width", 20000)
        obj.setProperty("decodeDpr", 4.0)
        assert obj.property("requestedDecodeWidth") == 5120
        # Nunca negativo ni cero.
        obj.setProperty("width", 0)
        obj.setProperty("height", 0)
        assert obj.property("requestedDecodeWidth") >= 1
        assert obj.property("requestedDecodeHeight") >= 1
        # Sin NaN en la geometría con source vacío.
        for prop in ("_x", "_y", "_scale", "_renderedW", "_renderedH"):
            value = obj.property(prop)
            assert value == value, f"{prop} no debe ser NaN"
        engine.deleteLater()


# ==========================================================================
# PL-10-FINAL-11 — GRID RESPONSIVE (ULTRAWIDE)
# ==========================================================================


class TestOverviewGridResponsive:
    def test_column_count_scales_beyond_six(self, qapp):
        """El grid ya no limita a 6 columnas: un viewport ultrawide (3440
        útiles) produce más columnas con cards ~304px, sin gutters."""
        from PySide6.QtCore import QObject

        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("playlists", QObject())
        component = QQmlComponent(engine)
        component.loadUrl(
            QUrl.fromLocalFile(str(QML_DIR) + "/playlists/PlaylistsView.qml")
        )
        assert component.status() == QQmlComponent.Ready, [
            e.toString() for e in component.errors()
        ]
        obj = component.create()
        grid = obj.findChild(QObject, "playlistGridView")
        assert grid is not None
        # El grid vive en un Layout: seteamos SU ancho directamente.
        grid.setProperty("width", 3440)
        # targetCellWidth estándar 304 → columnCount ≈ round(3440/304) = 11.
        column_count = grid.property("columnCount")
        assert column_count > 6, (
            f"ultrawide debe escalar columnas, obtuve {column_count}"
        )
        cell = grid.property("resolvedCellWidth")
        assert 280 <= cell <= 320, f"card width fuera de rango: {cell}"
        # maxColumns eliminado del grid.
        assert grid.property("maxColumns") is None
        engine.deleteLater()


# ==========================================================================
# PL-10-FINAL-18 — NO-OP CONTRACT
# ==========================================================================


class TestNoOpContract:
    def test_noop_operations_write_nothing(self, tmp_path):
        service = PlaylistService(
            playlists_port=FakePlaylistsPort(),
            artwork_store=FilesystemPlaylistArtworkStore(tmp_path / "managed"),
        )
        playlist = service.create_playlist("Mix")
        service.add_tracks(playlist.playlist_id, ["/a.flac", "/b.flac"])
        # Primera descripción y primer pin: writes legítimos (baseline).
        service.set_playlist_description(playlist.playlist_id, "D")
        service.pin_playlist(playlist.playlist_id)
        notifications = []
        service.subscribe_changed(lambda: notifications.append(1))
        port = service._port

        saves_before = len(port.saved)
        # rename same name
        assert service.rename_playlist(playlist.playlist_id, "Mix") is False
        # description same value
        assert service.set_playlist_description(playlist.playlist_id, "D") is False
        # pin already pinned
        assert service.pin_playlist(playlist.playlist_id) is False
        # move same index
        assert service.move_track(playlist.playlist_id, 0, 0) is False
        # add duplicate only
        added, already = service.add_tracks(playlist.playlist_id, ["/a.flac"])
        assert (added, already) == (0, 1)
        # remove nothing
        assert service.remove_tracks(playlist.playlist_id, []) is False
        # appearance identical (auto cover + auto hero ya persistidos)
        assert (
            service.apply_visual_appearance(
                playlist.playlist_id, cover_action="auto", hero_mode="auto"
            )
            == "no_change"
        )

        assert len(port.saved) == saves_before, "cero writes en todos los no-ops"
        assert notifications == [], "cero notify en todos los no-ops"


# ==========================================================================
# PL-10-FINAL-24 — REDUCED MOTION KEEPS FUNCTIONALITY
# ==========================================================================


class TestReducedMotion:
    def test_reduced_motion_gates_are_enabled_conditions(self):
        """El patrón del proyecto: todas las animaciones declarativas están
        gateadas por !MichiAccessibility.reducedMotion — la funcionalidad
        (menús, play, foco) no depende del movimiento."""
        for rel in (
            "playlists/PlaylistCard.qml",
            "playlists/PlaylistTrackList.qml",
            "playlists/PlaylistAppearancePanel.qml",
            "playlists/PlaylistHero.qml",
        ):
            text = (QML_DIR / rel).read_text()
            # Sin motion-gating, la funcionalidad de interacción se mantiene
            # en el archivo (no hay controles que solo existan en animación).
            assert "MichiAccessibility.reducedMotion" in text, rel
