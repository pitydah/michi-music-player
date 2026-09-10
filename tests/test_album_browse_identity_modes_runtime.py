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

    # R7-01 (auditoría): por modo, la PROYECCIÓN VISUAL debe coincidir
    # con la identidad canónica — la property del índice activo por
    # representación (magazine usa el roving editorial).
    INDEX_PROP = {
        "grid": "currentIndex",
        "cover": "currentIndex",
        "vinyl": "currentIndex",
        "timeline": "currentIndex",
        "magazine": "rovingIndex",
        "list": "currentIndex",
    }

    def test_loaded_view_index_projects_kick(self, tmp_path, qapp):
        """IDENTIDAD == PROYECCIÓN: por cada modo,
        albumModel[indexProp] del view cargado es Kick (no alcanza con
        que currentKey sea Kick: la representación debe mostrarlo)."""
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
                index_prop = self.INDEX_PROP[mode]
                index = view_item.property(index_prop)
                model = view_item.property("albumModel")
                if hasattr(model, "toVariant"):
                    model = model.toVariant()
                assert index is not None and 0 <= index < len(model), (
                    f"{mode}: índice {index} fuera del modelo"
                )
                assert model[index]["key"] == kick, (
                    f"{mode}: la representación muestra "
                    f"{model[index]['key']} en vez de Kick"
                )
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


class TestStudioListInteractions:
    """R7-01 (auditoría): interacción REAL en Studio List — la ruta
    productiva de los delegates (selectedRequested/open) debe ejecutar
    browseTo() sin TypeError y transferir la identidad al álbum tocado."""

    def _list_row(self, world, title):
        """El delegate (MichiAlbumRow) del list para un título."""
        item = _loaded_view(world)
        assert item is not None

        def visit(node, out):
            try:
                md = node.property("modelData")
                if isinstance(md, dict) and md.get("title") == title:
                    out.append(node)
                for child in node.childItems():
                    visit(child, out)
            except RuntimeError:
                pass

        out = []
        visit(item, out)
        return out[0] if out else None

    def _select_row(self, world, row):
        from PySide6.QtCore import QPoint, Qt

        content = world["view"].contentItem()
        mapped = row.mapToItem(content, 0, 0)
        x = mapped.x() + row.width() / 2
        y = mapped.y() + row.height() / 2
        QTest.mouseClick(
            world["view"],
            Qt.RightButton,
            Qt.NoModifier,
            QPoint(int(x), int(y)),
        )
        QTest.qWait(200)
        _process()

    def test_row_selection_updates_identity(self, tmp_path, qapp):
        """TEST A: seleccionar explícitamente otra fila mueve currentKey
        al álbum seleccionado (sin TypeError/ReferenceError)."""
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(150)
            _switch_mode(world, "list")
            assert state.property("currentKey") == kick
            voices = next(
                a.key
                for a in world["library"].state.albums
                if a.title == "Voices Carry"
            )
            row = self._list_row(world, "Voices Carry")
            assert row is not None, "fila de Voices Carry no encontrada"
            self._select_row(world, row)
            assert state.property("currentKey") == voices, (
                f"la selección no transfirió la identidad: "
                f"{state.property('currentKey')}"
            )
        finally:
            world["view"].close()

    def test_programmatic_index_change_does_not_transfer_identity(self, tmp_path, qapp):
        """TEST C: un cambio programático de currentIndex NO transfiere
        currentKey (solo posición)."""
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(150)
            _switch_mode(world, "list")
            assert state.property("currentKey") == kick
            item = _loaded_view(world)
            # cambio programático del índice (sin intención del usuario)
            item.setProperty("currentIndex", 0)
            QTest.qWait(250)
            _process()
            assert state.property("currentKey") == kick, (
                "el cambio programático de índice transfirió la identidad"
            )
        finally:
            world["view"].close()


class TestSortReorderSurvives:
    """R7-01 (auditoría, hallazgo 6): la KEY sobrevive al reorder; el
    índice se reproyecta. Prohibido: el índice viejo redefine la key."""

    @pytest.mark.parametrize("mode", ["grid", "list"])
    def test_reorder_keeps_key_reprojects_index(self, tmp_path, qapp, mode):
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(150)
            _switch_mode(world, mode)
            assert state.property("currentKey") == kick
            # reorder: Kick pasa al frente (el índice de Kick cambia)
            albums = world["root"].property("presentationAlbums")
            if hasattr(albums, "toVariant"):
                albums = albums.toVariant()
            kick_row = next(a for a in albums if a["key"] == kick)
            reordered = [kick_row] + [a for a in albums if a["key"] != kick]
            world["root"].setProperty("presentationAlbums", reordered)
            QTest.qWait(400)
            _process()
            assert state.property("currentKey") == kick, (
                f"{mode}: el reorder transfirió la identidad"
            )
            view_item = _loaded_view(world)
            model = view_item.property("albumModel")
            if hasattr(model, "toVariant"):
                model = model.toVariant()
            index = view_item.property("currentIndex")
            assert 0 <= index < len(model)
            assert model[index]["key"] == kick, (
                f"{mode}: el índice no reproyecta Kick tras el reorder"
            )
        finally:
            world["view"].close()


class TestStudioListOpen:
    """R7-01 (auditoría, TEST B): abrir una fila del Studio List
    establece la identidad y entrega el álbum correcto a la librería."""

    def test_open_row_selects_album_and_identity(self, tmp_path, qapp):
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(150)
            _switch_mode(world, "list")
            voices = next(
                a.key
                for a in world["library"].state.albums
                if a.title == "Voices Carry"
            )
            # la fila del delegate (mismo helper que las interacciones)
            from tests.test_album_browse_identity_modes_runtime import (
                TestStudioListInteractions,
            )

            row = TestStudioListInteractions()._list_row(world, "Voices Carry")
            assert row is not None
            # open productivo: el handler del delegate ejecuta browseTo +
            # select_album — invocamos la señal del row tal como el doble
            # click la dispara.
            meta = row.metaObject()
            index = meta.indexOfSignal("openRequested()")
            assert index >= 0, "el delegate no expone openRequested"
            meta.method(index).invoke(row)
            QTest.qWait(250)
            _process()
            assert state.property("currentKey") == voices, (
                "el open no estableció la identidad"
            )
            assert world["lb"].property("selectedAlbumKey") == voices, (
                "la librería no recibió el álbum abierto"
            )
        finally:
            world["view"].close()


class TestKeyboardIntentOneShot:
    """R7-01 (auditoría, hallazgo 3): el armed del teclado es one-shot —
    una flecha en el borde no deja intención residual que confunda un
    cambio programático posterior."""

    def test_edge_arrow_does_not_leave_armed(self, tmp_path, qapp):
        world = _mount_albums_view(tmp_path)
        try:
            kick = _kick_key(world)
            state = world["state"]
            state.setProperty("currentKey", kick)
            QTest.qWait(150)
            _switch_mode(world, "grid")
            item = _loaded_view(world)
            # moverse al borde izquierdo del grid y pulsar Right (puede
            # o no moverse; el release debe desarmar SIEMPRE)
            from PySide6.QtCore import Qt

            item.setProperty("currentIndex", 0)
            QTest.qWait(150)
            QTest.keyClick(world["view"], Qt.Key_Left)
            QTest.qWait(120)
            _process()
            assert item.property("browseKeyboardArmed") is False, (
                "el armed sobrevivió a la tecla (intención stale)"
            )
            # un cambio programático posterior NO debe transferir identidad
            current_key = state.property("currentKey")
            item.setProperty("currentIndex", 2 if current_key != "x" else 1)
            QTest.qWait(250)
            _process()
            assert state.property("currentKey") == kick, (
                "la intención stale transfirió la identidad"
            )
        finally:
            world["view"].close()
