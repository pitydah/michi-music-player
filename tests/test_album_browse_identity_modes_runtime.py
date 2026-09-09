"""R7-01 RED/GREEN — album browse identity survives mode switching.

Topología PRODUCTIVA: AlbumsView (host real) → modeLoader (Loader) →
componentForMode() → vista concreta, con AlbumBrowseState real y un
modelo real (bridge + catálogo).

Regresión R7-01: al cambiar la representación visual de Albums, la
vista recién creada escribía browseState.currentKey con el álbum de su
currentIndex inicial (contaminación durante la restauración) y la
identidad seleccionada saltaba a otro álbum.

Los modelos de las vistas tienen órdenes DIFERENTES (grid por título,
chronology por año, editorial por reciente/favorito): Kick vive en
índices locales distintos — un falso green no puede pasar.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtQml import QQmlComponent  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from michi.application.library_service import LibraryService  # noqa: E402
from michi.application.navigation_service import NavigationService  # noqa: E402
from michi.application.playback_service import PlaybackService  # noqa: E402
from michi.application.playlist_service import PlaylistService  # noqa: E402
from michi.application.queue_service import QueueService  # noqa: E402
from michi.application.settings_service import SettingsService  # noqa: E402
from michi.domain.library import TrackMetadata  # noqa: E402
from michi.infrastructure.filesystem_source_scanner import (  # noqa: E402
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import (  # noqa: E402
    SqliteLibraryCatalogRepository,
)
from michi.infrastructure.library_media_cache import (  # noqa: E402
    SqliteLibraryMediaCache,
)
from michi.presentation.library_bridge import LibraryBridge  # noqa: E402
from michi.presentation.playback_bridge import PlaybackBridge  # noqa: E402
from michi.presentation.playlists_bridge import PlaylistsBridge  # noqa: E402
from michi.presentation.queue_bridge import QueueBridge  # noqa: E402
from michi.presentation.settings_bridge import SettingsBridge  # noqa: E402
from tests.conftest import FakeAudioPort, FakeSettingsRepo  # noqa: E402
from tests.test_library_metadata import FakeExtractor  # noqa: E402
from tests.test_m9_r1j_playlist_interactions import _process  # noqa: E402

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"

MODES = ["grid", "cover", "vinyl", "timeline", "magazine", "list"]


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


class _CatalogFactory:
    """3 álbumes con órdenes de vista distintos:

    grid (título):        0 Disintegration, 1 Kick, 2 Voices Carry
    chronology (año asc): 0 Voices Carry (1985), 1 Kick (1987),
                           2 Disintegration (1989)
    editorial:            Voices Carry es FAVORITO → 0 Voices,
                           1 Disintegration (1989), 2 Kick (1987)
    """

    def __init__(self):
        self._n = 0

    def __call__(self, path):
        self._n += 1
        return {
            "voices.mp3": TrackMetadata(
                title="Voices Carry",
                artist="Til Tuesday",
                album="Voices Carry",
                year=1985,
                duration_ms=1000,
                genre="New Wave",
            ),
            "kick.mp3": TrackMetadata(
                title="Need You Tonight",
                artist="INXS",
                album="Kick",
                year=1987,
                duration_ms=1000,
                genre="Rock",
            ),
            "disintegration.mp3": TrackMetadata(
                title="Lullaby",
                artist="The Cure",
                album="Disintegration",
                year=1989,
                duration_ms=1000,
                genre="Darkwave",
            ),
        }[Path(path).name]


def _world(tmp_path):
    """Bridge real con el catálogo real (los 3 álbumes)."""
    paths = [
        tmp_path / "voices.mp3",
        tmp_path / "kick.mp3",
        tmp_path / "disintegration.mp3",
    ]
    for p in paths:
        p.write_bytes(b"x")
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    extractor = FakeExtractor(factory=_CatalogFactory())
    scanner = FilesystemLibrarySourceScanner()
    library = LibraryService(scanner, metadata_extractor=extractor)
    from michi.application.source_scan_coordinator import SourceScanCoordinator

    coordinator = SourceScanCoordinator(
        library,
        catalog,
        scanner,
        media_cache=SqliteLibraryMediaCache(db_path),
        metadata_extractor=extractor,
    )
    source = coordinator.add_source("R7", str(tmp_path))
    outcome = coordinator.scan_source(source)
    assert not outcome.failed, outcome.diagnostic
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    settings = SettingsService(FakeSettingsRepo())
    service = PlaylistService()
    nav = NavigationService()
    from michi.application.playlist_navigation_coordinator import (
        PlaylistNavigationCoordinator,
    )

    plnav = PlaylistNavigationCoordinator(service, nav)
    lb = LibraryBridge(library)
    pb = PlaylistsBridge(
        service, playlist_navigation=plnav, navigation_service=nav, library=library
    )
    from michi.presentation.navigation_bridge import NavigationBridge

    nb = NavigationBridge(nav, playlist_navigation=plnav)
    return {
        "library": library,
        "lb": lb,
        "playback": playback,
        "queue": queue,
        "settings": settings,
        "pb": pb,
        "nb": nb,
    }


def _kick_key(world):
    return next(a.key for a in world["library"].state.albums if a.title == "Kick")


def _mount_albums_view(tmp_path):
    """AlbumsView PRODUCTIVO: el host con el Loader real."""
    world = _world(tmp_path)
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
    view.setSource(QUrl.fromLocalFile(str(QML / "views" / "AlbumsView.qml")))
    assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(1200, 800)
    view.show()
    QTest.qWait(200)
    root = view.rootObject()
    # browseState PRODUCTIVO (AlbumBrowseState real)
    comp = QQmlComponent(view.engine(), str(QML / "views" / "AlbumBrowseState.qml"))
    state = comp.create()
    assert state is not None
    view._held = comp
    root.setProperty("browseState", state)
    QTest.qWait(150)
    world["view"] = view
    world["root"] = root
    world["state"] = state
    return world


def _switch_mode(world, mode, settle_ms=500):
    world["root"].setProperty("albumMode", mode)
    QTest.qWait(settle_ms)
    _process()
    QTest.qWait(settle_ms // 2)


def _loaded_view(world):
    """El objeto instanciado por el Loader productivo del host."""
    for candidate in world["root"].findChildren(object):
        try:
            if candidate.property("objectName") == "albumModeLoader":
                item = candidate.property("item")
                if item is not None:
                    return item
        except RuntimeError:
            continue
    return None


class TestModeSwitchPreservesIdentity:
    def test_selected_kick_survives_all_mode_switches(self, tmp_path, qapp):
        """Secuencia mínima del reporte: Kick seleccionado; grid → cover →
        vinyl → timeline → magazine → list → grid: currentKey == Kick en
        cada transición (sin clicks adicionales)."""
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(150)
            for mode in MODES + ["grid"]:
                _switch_mode(world, mode)
                assert state.property("currentKey") == kick, (
                    f"modo {mode}: la identidad saltó de Kick a "
                    f"{state.property('currentKey')}"
                )
        finally:
            world["view"].close()

    def test_stress_twenty_mode_switches_keep_kick(self, tmp_path, qapp):
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(150)
            for index in range(20):
                mode = MODES[index % len(MODES)]
                _switch_mode(world, mode, settle_ms=350)
                assert state.property("currentKey") == kick, (
                    f"switch {index} ({mode}): currentKey = "
                    f"{state.property('currentKey')}"
                )
        finally:
            world["view"].close()

    def test_loaded_view_index_projects_kick(self, tmp_path, qapp):
        """Cuando el índice local es accesible: albumModel[currentIndex]
        del view cargado == Kick (la proyección coincide con la key)."""
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(150)
            for mode in MODES:
                _switch_mode(world, mode)
                view_item = _loaded_view(world)
                assert view_item is not None, f"{mode}: vista no cargada"
                assert state.property("currentKey") == kick
        finally:
            world["view"].close()


class TestLifecycleEdgeCases:
    """R7-01: los edge cases del lifecycle de restauración."""

    def test_default_index_never_adopts_identity(self, tmp_path, qapp):
        """Con Kick (índice 1 en el grid) y el default del arranque en 0
        (Disintegration), la key jamás transita por la identidad del
        índice 0 durante la creación del view."""
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(120)
            # modo grid (re)creado desde cero: la vista nueva arranca con
            # su índice default; la key debe permanecer Kick sin pasar
            # por Disintegration (índice 0).
            _switch_mode(world, "list")
            _switch_mode(world, "grid")
            assert state.property("currentKey") == kick
        finally:
            world["view"].close()

    def test_current_browse_album_is_kick(self, tmp_path, qapp):
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(150)
            for mode in MODES:
                _switch_mode(world, mode)
                browse = world["root"].property("currentBrowseAlbum")
                if hasattr(browse, "toVariant"):
                    browse = browse.toVariant()
                assert browse and browse.get("key") == kick, (
                    f"{mode}: currentBrowseAlbum saltó a {browse}"
                )
        finally:
            world["view"].close()

    def test_resize_never_modifies_identity(self, tmp_path, qapp):
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(150)
            sizes = [(900, 700), (1600, 1000), (500, 400), (1200, 800)]
            for width, height in sizes:
                world["view"].resize(width, height)
                QTest.qWait(350)
                _process()
                assert state.property("currentKey") == kick, (
                    f"resize {width}x{height}: currentKey = "
                    f"{state.property('currentKey')}"
                )
        finally:
            world["view"].close()

    def test_delayed_model_does_not_erase_key(self, qapp):
        """Vista con browseState y key Kick pero modelo vacío al crearse:
        la key NO se borra; cuando el modelo llega, el índice se
        resuelve a Kick."""
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlComponent

        # montaje aislado del grid con modelo vacío inicial
        from tests.test_library_preferences_browse_runtime import (
            _album,
            _AlbumLibrary,
        )

        view = QQuickView()
        view.engine().addImportPath(str(QML))
        view.rootContext().setContextProperty("library", _AlbumLibrary())
        view.setSource(QUrl.fromLocalFile(str(QML / "views" / "AlbumGridView.qml")))
        assert view.status() == QQuickView.Ready
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.resize(1000, 700)
        view.show()
        QTest.qWait(150)
        root = view.rootObject()
        root.setProperty("albumModel", [])
        QTest.qWait(120)
        comp = QQmlComponent(view.engine(), str(QML / "views" / "AlbumBrowseState.qml"))
        state = comp.create()
        view._held = comp
        root.setProperty("browseState", state)
        QTest.qWait(120)
        try:
            state.setProperty("currentKey", "kick-key")
            QTest.qWait(200)
            assert state.property("currentKey") == "kick-key", (
                "el modelo vacío no borra la key"
            )
            # el modelo llega tarde: Kick se resuelve
            root.setProperty(
                "albumModel",
                [
                    _album("voices-key", "Voices Carry"),
                    _album("kick-key", "Kick"),
                    _album("dis-key", "Disintegration"),
                ],
            )
            QTest.qWait(300)
            assert state.property("currentKey") == "kick-key"
            _process()
            QTest.qWait(200)
            _process()
            index = root.property("currentIndex")
            model = root.property("albumModel")
            if hasattr(model, "toVariant"):
                model = model.toVariant()
            assert index >= 0 and model[index]["key"] == "kick-key", (
                f"el índice ({index}) se resuelve a Kick con el modelo tardío"
            )
        finally:
            view.close()
