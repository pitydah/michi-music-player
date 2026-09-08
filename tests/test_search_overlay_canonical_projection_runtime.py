"""POST-R4 P1 — SearchOverlay canonical projection runtime seals.

SearchOverlay productivo con las CINCO categorías (>=1 track/album/artist/
playlist/genre) para la misma query:

- UNA autoridad de offsets (trackStart..genreStart/resultEnd) gobierna los
  delegates y activateResult (nunca sumas manuales por grupo);
- por cada resultIndex existe EXACTAMENTE UN delegate seleccionado (el bug
  del genre omitiendo visiblePlaylistCount producía doble selección);
- la activación de un track usa EXACT TrackId (activate_track_by_id) —
  nunca activate(index) — con cero mutaciones de Queue;
- mouse y teclado recorren el mismo seam.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from michi.application.library_service import LibraryService  # noqa: E402
from michi.application.navigation_service import NavigationService  # noqa: E402
from michi.application.playback_service import PlaybackService  # noqa: E402
from michi.application.playlist_navigation_coordinator import (  # noqa: E402
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService  # noqa: E402
from michi.application.settings_service import SettingsService  # noqa: E402
from michi.domain.library import TrackMetadata  # noqa: E402
from michi.presentation.library_bridge import LibraryBridge  # noqa: E402
from michi.presentation.navigation_bridge import NavigationBridge  # noqa: E402
from michi.presentation.playlists_bridge import PlaylistsBridge  # noqa: E402
from tests.conftest import FakeAudioPort, FakeSettingsRepo  # noqa: E402
from tests.test_library_metadata import FakeExtractor  # noqa: E402
from tests.test_m9_r1j_playlist_interactions import (  # noqa: E402
    _process,
)
from tests.test_playlists import (  # noqa: E402
    FakePlaylistsPort,
)

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


class _RockFactory:
    """Cada archivo produce un track que matchea la query 'Rock' en TODAS
    las dimensiones: título 'Rock Anthem N', artista 'Rock Band N', álbum
    'Rock Ballads N', género 'Rock'."""

    def __init__(self):
        self._n = 0

    def __call__(self, path):
        self._n += 1
        n = self._n
        return TrackMetadata(
            title=f"Rock Anthem {n}",
            artist=f"Rock Band {n}",
            album=f"Rock Ballads {n}",
            duration_ms=1000,
            genre="Rock",
        )


class _RecordingPlaybackCoordinator:
    """Punto de observación de los intents de activación (el contrato del
    seam: TrackId exacto, cero índice). El LibraryBridge PRODUCTIVO los
    delega aquí — como FakeAudioPort en el resto de la suite."""

    def __init__(self):
        self.calls = []

    def play_track_by_id(self, track_id: str) -> None:
        self.calls.append(("play_track_by_id", track_id))

    def play_visible_track(self, visible_index: int) -> None:
        self.calls.append(("play_visible_track", visible_index))


def _five_category_world(tmp_path):
    """Mundo donde la query 'Rock' proyecta >=1 de cada categoría:
    tracks (por título), álbum, artista y género (por nombre) y la
    playlist 'Rock Trip' (proyección local del PlaylistsBridge).

    El catálogo es REAL (SqliteLibraryCatalogRepository + scan del
    SourceScanCoordinator): los tracks llevan TrackId estables — el
    contrato TrackId del seam exige identidades reales, no vacías."""
    from michi.application.source_scan_coordinator import SourceScanCoordinator
    from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
    from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache

    paths = []
    for name in ("rock-1.mp3", "rock-2.mp3"):
        p = tmp_path / name
        p.write_bytes(b"x")
        paths.append(p)
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    from michi.infrastructure.filesystem_source_scanner import (
        FilesystemLibrarySourceScanner,
    )

    scanner = FilesystemLibrarySourceScanner()
    extractor = FakeExtractor(factory=_RockFactory())
    library = LibraryService(scanner, metadata_extractor=extractor)
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        scanner,
        media_cache=SqliteLibraryMediaCache(db_path),
        metadata_extractor=extractor,
    )
    source = coordinator.add_source("Rock", str(tmp_path))
    outcome = coordinator.scan_source(source)
    assert not outcome.failed, outcome.diagnostic
    from michi.application.queue_service import QueueService

    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    settings = SettingsService(FakeSettingsRepo())
    service = PlaylistService(playlists_port=FakePlaylistsPort())
    nav = NavigationService()
    playlists_coord = PlaylistNavigationCoordinator(service, nav)
    service.set_on_playlist_deleted(nav.forget_playlist)
    playback_coordinator = _RecordingPlaybackCoordinator()
    lb = LibraryBridge(library, playback_coordinator=playback_coordinator)
    pb = PlaylistsBridge(
        service,
        playlist_navigation=playlists_coord,
        navigation_service=nav,
        library=library,
    )
    nb = NavigationBridge(nav, playlist_navigation=playlists_coord)
    service.create_playlist("Rock Trip")
    return {
        "library": library,
        "queue": queue,
        "playback": playback,
        "settings": settings,
        "service": service,
        "nav": nav,
        "pb": pb,
        "nb": nb,
        "lb": lb,
        "playback_coordinator": playback_coordinator,
    }


def _overlay_all_five(tmp_path):
    """Monta el SearchOverlay PRODUCTIVO en un QQuickView real: el
    rootObject es un QQuickItem completo — childItems alcanza los
    delegates del Repeater (la vía canónica de los runtime gates M9)."""
    from PySide6.QtCore import QUrl
    from PySide6.QtQuick import QQuickView

    from michi.presentation.playback_bridge import PlaybackBridge
    from michi.presentation.queue_bridge import QueueBridge
    from michi.presentation.settings_bridge import SettingsBridge

    world = _five_category_world(tmp_path)
    world["lb"].search("Rock")
    view = QQuickView()
    view.engine().addImportPath(str(QML))
    ctx = view.rootContext()
    ctx.setContextProperty("library", world["lb"])
    ctx.setContextProperty("playlists", world["pb"])
    ctx.setContextProperty("navigation", world["nb"])
    ctx.setContextProperty(
        "playback", PlaybackBridge(world["playback"], world["library"])
    )
    ctx.setContextProperty("queue", QueueBridge(world["queue"], world["library"]))
    ctx.setContextProperty("settingsBridge", SettingsBridge(world["settings"]))
    view.setSource(QUrl.fromLocalFile(str(QML / "patterns" / "SearchOverlay.qml")))
    assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
    _process()
    _process()
    view.show()
    _process()
    overlay = view.rootObject()
    overlay.setProperty("opened", True)
    _process()
    world["view"] = view
    return world, view, overlay


def _collect_visual_rows(root):
    """Delegates del árbol REAL (traversal childItems — los delegates del
    Repeater no cuelgan del QObject tree del engine) con su estado
    visual 'selected'."""

    def visit(item, out):
        try:
            selected = item.property("selected")
            if selected is True:
                out.append(item)
        except RuntimeError:
            pass
        try:
            for child in item.childItems():
                visit(child, out)
        except RuntimeError:
            pass

    out = []
    visit(root, out)
    return out


class TestCanonicalProjectionOffsets:
    def test_single_offset_authority_properties(self, tmp_path, qapp):
        """trackStart..resultEnd viven en el overlay y encadenan los
        counts visibles — una sola autoridad, sin sumas manuales."""
        world, view, overlay = _overlay_all_five(tmp_path)
        try:
            for k in (
                "searchTrackCount",
                "searchAlbumCount",
                "searchArtistCount",
                "searchGenreCount",
            ):
                assert world["lb"].property(k) >= 1, k
            assert world["pb"].property("searchPlaylistCount") >= 1
            vt = overlay.property("visibleTrackCount")
            va = overlay.property("visibleAlbumCount")
            var = overlay.property("visibleArtistCount")
            vp = overlay.property("visiblePlaylistCount")
            vg = overlay.property("visibleGenreCount")
            assert overlay.property("trackStart") == 0
            assert overlay.property("albumStart") == vt
            assert overlay.property("artistStart") == vt + va
            assert overlay.property("playlistStart") == vt + va + var
            assert overlay.property("genreStart") == vt + va + var + vp
            assert overlay.property("resultEnd") == vt + va + var + vp + vg
            assert overlay.property("actionableResultCount") == overlay.property(
                "resultEnd"
            )
        finally:
            view.close()

    def test_genre_global_index_differs_from_playlist(self, tmp_path, qapp):
        """Playlist y Genre NUNCA comparten resultIndex: con ambas visibles,
        genreStart = playlistStart + visiblePlaylistCount."""
        world, view, overlay = _overlay_all_five(tmp_path)
        try:
            ps = overlay.property("playlistStart")
            gs = overlay.property("genreStart")
            assert ps >= 1 and gs >= 1
            assert gs != ps
            assert gs - ps == overlay.property("visiblePlaylistCount")
        finally:
            view.close()

    def test_every_result_index_selects_exactly_one_visual_row(self, tmp_path, qapp):
        """Para CADA resultIndex accionable hay EXACTAMENTE UN delegate
        seleccionado (el bug del genre omitiendo visiblePlaylistCount
        seleccionaba playlist y genre a la vez o ninguno)."""
        world, view, overlay = _overlay_all_five(tmp_path)
        try:
            total = overlay.property("actionableResultCount")
            assert total >= 5, "las cinco categorías visibles"
            for result_index in range(total):
                overlay.setProperty("resultIndex", result_index)
                _process()
                selected = _collect_visual_rows(overlay)
                assert len(selected) == 1, (
                    f"resultIndex={result_index}: "
                    f"{len(selected)} seleccionados (esperado 1)"
                )
        finally:
            view.close()

    def test_delegates_consume_shared_offsets(self, tmp_path, qapp):
        """Los delegates referencian los offsets del overlay (nunca sumas
        ad-hoc de counts que puedan divergir del activateResult)."""
        src = (QML / "patterns" / "SearchOverlay.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        # El archivo declara las propiedades de autoridad una sola vez.
        for prop in (
            "trackStart",
            "albumStart",
            "artistStart",
            "playlistStart",
            "genreStart",
            "resultEnd",
        ):
            assert f"readonly property int {prop}:" in src, prop
        # Genre consume playlistStart — el bug histórico omitía la playlist.
        assert "genreStart + index" in src or "searchOverlay.genreStart + index" in src


class TestTrackActivationTrackId:
    def test_keyboard_activation_uses_exact_track_id(self, tmp_path, qapp):
        """activateResult sobre un track → activate_track_by_id(EXACT id):
        cero activate(index), cero mutaciones de Queue."""
        world, view, overlay = _overlay_all_five(tmp_path)
        try:
            lb = world["lb"]
            calls = world["playback_coordinator"].calls
            first_track_id = world["library"].visible_tracks()[0].track_id
            assert first_track_id, "track id real"
            overlay.setProperty("resultIndex", 0)
            overlay.activateResult()
            _process()
            assert calls == [("play_track_by_id", first_track_id)], calls
        finally:
            view.close()

    def test_mouse_and_keyboard_share_one_seam(self, tmp_path, qapp):
        """El delegate de track (mouse) y activateResult (teclado) pasan
        por la misma función del overlay — el QML no vuelve a activar por
        índice en ningún camino."""
        src = (QML / "patterns" / "SearchOverlay.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        track_delegate = src[src.index("model: searchOverlay.visibleTrackCount") :]
        track_delegate = track_delegate[: track_delegate.index("Albums")]
        assert "searchOverlay.activateTrack(" in track_delegate, (
            "el mouse usa el seam de activación por TrackId"
        )
        assert "library.activate(" not in track_delegate, (
            "el delegate de track no activa por índice"
        )
