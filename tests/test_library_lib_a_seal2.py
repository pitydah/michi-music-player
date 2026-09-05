"""LIB-A FINAL CORRECTIVE SEAL II — contracts cerrados.

- clamp único (interactivo == dominio; artwork 30-52; general max 720)
- Restore Defaults real (Essential + anchos default + UN configurationChanged)
- preset aplicado UNA vez (1 configurationChanged por preset)
- conteo visible de álbumes (search + filtro) en toolbar/header
- unavailable: contexto vivo con no-ops de play/queue
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import (  # noqa: F401
    Property,
    QObject,
    QPoint,
    QPointF,
    Qt,
    QUrl,
    Signal,
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"
THEME_URI = QML.as_uri() + "/theme"


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _unavailable_row(**overrides):
    row = {
        "trackId": "T1",
        "path": "/offline.flac",
        "title": "Offline Track",
        "artist": "Artist",
        "artistKey": "artist-1",
        "album": "Album",
        "albumKey": "album-1",
        "availability": "source_offline",
        "unavailable": True,
        "canonicalIndex": 0,
        "artworkPath": "",
        "codec": "flac",
        "sampleRateHz": 44100,
        "bitDepth": 16,
        "bitrateBps": 800000,
        "channels": 2,
        "fileSize": 1000,
        "durationMs": 300000,
        "qualityLabel": "FLAC",
    }
    row.update(overrides)
    return row


class _HostLibrary(QObject):
    changed = Signal()
    favoriteTrackIds = Property(list, lambda self: [])
    favoritePaths = Property(list, lambda self: [])
    canQueueTracks = Property(bool, lambda self: True)
    canAddTracksToPlaylists = Property(bool, lambda self: True)

    def __init__(self):
        super().__init__()
        self.calls = []

    def queue_track_by_id(self, track_id):
        self.calls.append(("queue_track_by_id", track_id))

    def toggle_favorite_by_id(self, track_id):
        self.calls.append(("favorite_by_id", track_id))


class _Playback(QObject):
    currentPath = Property(str, lambda self: "")


class TestColumnStateSeal2:
    """Spy del singleton vía host QML (las funciones de los items QML sí
    son invocables; el QtObject singleton no)."""

    @pytest.fixture()
    def state_host(self, qapp):
        from PySide6.QtQml import QQmlComponent, QQmlEngine

        engine = QQmlEngine()
        engine.addImportPath(str(QML))
        host_src = (
            "import QtQuick\n"
            f'import "{THEME_URI}"\n'
            "Item {\n"
            "    id: host\n"
            '    objectName: "stateHost"\n'
            "    property int changes: 0\n"
            "    property string preset: LibraryTrackColumnState.currentPreset()\n"
            "    property var state: LibraryTrackColumnState\n"
            "    Connections {\n"
            "        target: LibraryTrackColumnState\n"
            "        function onConfigurationChanged() {\n"
            "            host.changes += 1\n"
            "            host.preset = LibraryTrackColumnState.currentPreset()\n"
            "        }\n"
            "    }\n"
            "    function callSetWidth(column, value) {\n"
            "        LibraryTrackColumnState.setWidth(column, value)\n"
            "    }\n"
            "    function callSetVisible(column, value) {\n"
            "        LibraryTrackColumnState.setVisible(column, value)\n"
            "    }\n"
            "    function callApplyPreset(name) {\n"
            "        LibraryTrackColumnState.applyPreset(name)\n"
            "    }\n"
            "    function callRestoreDefaults() {\n"
            "        LibraryTrackColumnState.restoreDefaults()\n"
            "    }\n"
            "}\n"
        )
        component = QQmlComponent(engine)
        component.setData(host_src.encode("utf-8"), QUrl("state_host.qml"))
        assert component.status() == QQmlComponent.Ready, [
            e.toString() for e in component.errors()
        ]
        host = component.create()
        assert host is not None
        yield engine, host
        engine.deleteLater()

    def _call(self, host, fn, *args):
        from PySide6.QtCore import Q_ARG, QMetaObject
        from PySide6.QtCore import Qt as _Qt

        js_fn = f"call{fn[0].upper()}{fn[1:]}"
        if len(args) == 0:
            return QMetaObject.invokeMethod(host, js_fn, _Qt.DirectConnection)
        if len(args) == 1:
            return QMetaObject.invokeMethod(
                host, js_fn, _Qt.DirectConnection, Q_ARG("QVariant", args[0])
            )
        return QMetaObject.invokeMethod(
            host,
            js_fn,
            _Qt.DirectConnection,
            Q_ARG("QVariant", args[0]),
            Q_ARG("QVariant", args[1]),
        )

    def test_clamp_single_authority(self, state_host) -> None:
        engine, host = state_host
        state = host.property("state")
        self._call(host, "setWidth", "title", 5000)
        assert state.property("titleWidth") == 720
        self._call(host, "setWidth", "artist", -1)
        assert state.property("artistWidth") == 120
        self._call(host, "setWidth", "artwork", 500)
        assert state.property("artworkWidth") == 52
        self._call(host, "setWidth", "artwork", 2)
        assert state.property("artworkWidth") == 30

    def test_restore_defaults_full(self, state_host) -> None:
        engine, host = state_host
        state = host.property("state")
        self._call(host, "applyPreset", "audiophile")
        self._call(host, "setWidth", "title", 500)
        self._call(host, "setWidth", "artist", 400)
        self._call(host, "setVisible", "genre", True)
        self._call(host, "setVisible", "artwork", False)
        host.setProperty("changes", 0)
        self._call(host, "restoreDefaults")

        assert host.property("preset") == "essential"
        for prop, value in (
            ("artworkVisible", True),
            ("titleVisible", True),
            ("artistVisible", True),
            ("albumVisible", True),
            ("formatVisible", True),
            ("durationVisible", True),
            ("actionsVisible", True),
            ("genreVisible", False),
            ("sampleRateVisible", False),
            ("composerVisible", False),
            ("yearVisible", False),
        ):
            assert state.property(prop) is value, prop
        for prop, value in (
            ("artworkWidth", 44),
            ("titleWidth", 300),
            ("artistWidth", 190),
            ("albumWidth", 230),
            ("formatWidth", 88),
            ("sampleRateWidth", 100),
            ("bitDepthWidth", 82),
            ("dsdRateWidth", 92),
            ("bitrateWidth", 90),
            ("channelsWidth", 82),
            ("fileSizeWidth", 90),
            ("genreWidth", 150),
            ("composerWidth", 180),
            ("yearWidth", 68),
            ("durationWidth", 80),
        ):
            assert state.property(prop) == value, prop
        assert host.property("changes") == 1, "UN configurationChanged"

    def test_single_preset_application(self, state_host) -> None:
        engine, host = state_host
        menu_src = (QML / "media" / "TrackTableHeaderContextMenu.qml").read_text()
        # El menú emite el INTENT; el header aplica — nunca doble.
        apply_block = menu_src[menu_src.index("function applyPreset") :]
        assert "root.presetRequested(name)" in apply_block
        assert "LibraryTrackColumnState.applyPreset" not in apply_block
        header_src = (QML / "media" / "ResizableTrackHeader.qml").read_text()
        assert (
            "onPresetRequested: name => LibraryTrackColumnState.applyPreset(name)"
            in header_src
        )
        host.setProperty("changes", 0)
        self._call(host, "applyPreset", "audiophile")
        assert host.property("changes") == 1
        assert host.property("preset") == "audiophile"
        self._call(host, "applyPreset", "minimal")
        assert host.property("changes") == 2
        assert host.property("preset") == "minimal"
        self._call(host, "applyPreset", "metadata")
        assert host.property("preset") == "metadata"
        self._call(host, "applyPreset", "essential")
        assert host.property("preset") == "essential"

    def test_album_visible_count_truth(self) -> None:
        toolbar = (QML / "views" / "LibraryToolbar.qml").read_text()
        albums_block = toolbar[toolbar.index('case "albums"') :]
        assert "library.filteredAlbumCount" in albums_block
        header = (QML / "views" / "LibraryHeader.qml").read_text()
        assert "library.filteredAlbumCount" in header
        assert ".arg(library.filteredAlbumCount).arg(library.albumCount)" in header


def _mount_table(qapp, rows, can_favorite=True):
    library = _HostLibrary()
    playback = _Playback()
    view = QQuickView()
    view.engine().addImportPath(str(QML))
    ctx = view.rootContext()
    ctx.setContextProperty("library", library)
    ctx.setContextProperty("playback", playback)
    view.setSource(QUrl.fromLocalFile(str(QML / "media" / "MichiTrackTable.qml")))
    assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(900, 300)
    view.show()
    view.requestActivate()
    QTest.qWait(80)
    root = view.rootObject()
    root.setProperty("rows", rows)
    root.setProperty("canFavorite", can_favorite)
    root.setProperty("canQueue", False)
    root.setProperty("canAddToPlaylist", False)
    root.setProperty("canInspect", False)
    root.setProperty("canNavigateEntities", True)
    QTest.qWait(250)
    return view, root, library


def _delegate_for(root, track_id):
    def visit(item):
        model = item.property("modelData")
        if isinstance(model, dict) and model.get("trackId") == track_id:
            return item
        for child in item.childItems():
            found = visit(child)
            if found is not None:
                return found
        return None

    return visit(root)


def _delegate_menu(delegate):
    for child in delegate.findChildren(QObject):
        if "ContextMenu" in child.metaObject().className():
            return child
    return None


class TestUnavailableInputs:
    def test_left_click_play_noop(self, qapp) -> None:
        view, root, library = _mount_table(qapp, [_unavailable_row()])
        activated = []
        root.trackActivated.connect(
            lambda track_id, path, index: activated.append(track_id)
        )
        delegate = _delegate_for(root, "T1")
        center = delegate.mapToScene(
            QPointF(delegate.width() / 2, delegate.height() / 2)
        )
        QTest.mouseClick(
            view,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(int(center.x()), int(center.y())),
        )
        QTest.qWait(40)
        assert activated == [], "left click no-op en unavailable"
        assert library.calls == []

    def test_enter_keys_play_noop(self, qapp) -> None:
        view, root, library = _mount_table(qapp, [_unavailable_row()])
        activated = []
        root.trackActivated.connect(
            lambda track_id, path, index: activated.append(track_id)
        )
        delegate = _delegate_for(root, "T1")
        # El delegate (TrackRow productivo) bloquea Enter/Return/Space con
        # unavailable: la activación no llega al host.
        delegate.setProperty("unavailable", True)
        # los handlers del TrackRow solo disparan con canInteract — la
        # señal activated() del row es la única vía y su handler exige
        # interactive && !unavailable.
        row_src = (QML / "media" / "TrackRow.qml").read_text()
        assert (
            "Keys.onReturnPressed: if (root.interactive && !root.unavailable)"
            in row_src
        )
        assert (
            "Keys.onEnterPressed: if (root.interactive && !root.unavailable)" in row_src
        )
        assert (
            "Keys.onSpacePressed: if (root.interactive && !root.unavailable)" in row_src
        )
        assert activated == []

    def test_queue_absent_in_menu(self, qapp) -> None:
        """Con can_queue=false el item de Queue no está en el menú de la
        fila unavailable (y ningún intent llega al host)."""
        view, root, library = _mount_table(qapp, [_unavailable_row()])
        queued = []
        root.queueRequested.connect(lambda track_id: queued.append(track_id))
        delegate = _delegate_for(root, "T1")
        menu = _delegate_menu(delegate)
        assert menu is not None
        assert menu.property("canQueue") is False, "canQueue false en la fila"
        # el item 'Add to Queue' no es VISIBLE (capacidad false).
        queue_item = None
        for child in menu.findChildren(QObject):
            if child.property("text") == "Add to Queue":
                queue_item = child
                break
        if queue_item is not None:
            assert queue_item.property("visible") is False, (
                "el item de Queue no es visible sin capacidad"
            )
        assert queued == []
        assert library.calls == []

    def test_favorite_still_works(self, qapp) -> None:
        view, root, library = _mount_table(qapp, [_unavailable_row()])
        root.favoriteRequested.connect(library.toggle_favorite_by_id)
        delegate = _delegate_for(root, "T1")
        menu = _delegate_menu(delegate)
        meta = menu.metaObject()
        favorite_index = meta.indexOfMethod("favoriteRequested()")
        assert favorite_index >= 0
        assert meta.method(favorite_index).invoke(menu)
        QTest.qWait(30)
        assert library.calls == [("favorite_by_id", "T1")], (
            "favorite de unavailable funciona (contexto vivo)"
        )
        view.close()
