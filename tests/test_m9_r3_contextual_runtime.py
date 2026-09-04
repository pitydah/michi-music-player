"""M9-R3 CONTEXTUAL ACTION RECOVERY — runtime gates.

Runtime (QQuickView offscreen, fakes mínimos) para los contratos de
interacción contextual:

- right-click sobre el hero de MagazineView abre el menú del álbum SIN
  efectos de play/open (sin side effects);
- el router de teclado roving (openRovingContext) selecciona el target
  exacto antes del popup y abre el menú raíz con el álbum correcto;
- AlbumContextArea traduce Menu / Shift+F10 al menú (pointer y teclado
  comparten la misma semántica);
- ArtistContextMenu fail-close: sin canAddToPlaylist el item
  "Add Artist to Playlist" NO es visible (nunca dead UI).

Nota de entorno: QTest.keyClick no entrega eventos al ListView de
MagazineView (verificado también contra el archivo pre-cambio: el
enrutamiento físico del roving queda sellado por gates estructurales;
el flujo del menú se prueba invocando el router real).
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
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _album(key, title="Album", artist="Artist", year=2000):
    return {
        "key": key,
        "title": title,
        "artist": artist,
        "year": year,
        "trackCount": 12,
        "artworkPath": "",
        "hasArtwork": False,
        "artistKey": "artist-x",
        "isRecentlyAdded": False,
        "isFavorite": False,
        "containsHighResolution": False,
        "technicalSummary": "",
    }


def _find_by_object_name(root, name):
    """Los delegates de Repeater/ListView NO son alcanzables con
    findChildren — traversal por childItems (patrón del seam runtime)."""

    def visit(item):
        if item.property("objectName") == name:
            return item
        for child in item.childItems():
            found = visit(child)
            if found is not None:
                return found
        return None

    return visit(root)


def _visible_menus(root):
    return [
        child
        for child in root.findChildren(QObject)
        if child.property("visible") is True
        and "Menu" in child.metaObject().className()
    ]


class _AlbumLibrary(QObject):  # noqa: N815 (QML-facing properties)
    """Fake de library para MagazineView/AlbumContextMenu: registra las
    llamadas de acción (play/open/queue) para probar ausencia de side
    effects durante la invocación contextual."""

    changed = Signal()

    def __init__(self, albums):
        super().__init__()
        self._albums = albums
        self.calls: list[tuple[str, str]] = []

    albums = Property("QVariantList", lambda self: self._albums, notify=changed)
    canQueueTracks = Property(bool, lambda self: True)
    canAddTracksToPlaylists = Property(bool, lambda self: True)

    @Slot(str)
    def select_album(self, key):
        self.calls.append(("select_album", key))

    @Slot(str)
    def play_album(self, key):
        self.calls.append(("play_album", key))

    @Slot(str)
    def queue_album(self, key):
        self.calls.append(("queue_album", key))

    @Slot(str)
    def select_artist(self, key):
        self.calls.append(("select_artist", key))

    @Slot(str)
    def request_album_playlist_target(self, key):
        self.calls.append(("album_target", key))

    @Slot(str)
    def request_new_playlist_for_album(self, key):
        self.calls.append(("new_playlist", key))

    @Slot(str)
    def request_album_palette(self, key):
        pass


class TestMagazineContextRuntime:
    def _magazine(self, qapp, album_count=10):
        library = _AlbumLibrary(
            [_album(f"album-{i}", f"Album {i}") for i in range(album_count)]
        )
        view = QQuickView()
        view.engine().addImportPath(str(QML_DIR))
        view.rootContext().setContextProperty("library", library)
        view.setSource(QUrl.fromLocalFile(str(QML_DIR / "views" / "MagazineView.qml")))
        assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.resize(1200, 900)
        view.show()
        view.requestActivate()
        QTest.qWait(80)
        # El fake debe sobrevivir al engine (GC no-determinista).
        self._kept = library
        return view, library

    def test_right_click_hero_opens_context_without_playback(self, qapp):
        """Pointer: right-click sobre el hero abre el menú contextual y NO
        dispara play/open/select (cero side effects)."""
        view, library = self._magazine(qapp)
        root = view.rootObject()

        QTest.mouseClick(
            view,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
            pos=QPoint(600, 120),
        )
        QTest.qWait(40)

        assert _visible_menus(root), "menú contextual abierto"
        assert not any(
            call[0] in ("play_album", "select_album") for call in library.calls
        ), "el contexto no reproduce ni abre"
        view.close()

    def test_roving_keyboard_context_selects_exact_album_then_opens(self, qapp):
        """Teclado (roving): openRovingContext selecciona el target exacto
        (contextAlbum == albumModel[rovingIndex]) y abre el menú raíz."""
        view, library = self._magazine(qapp)
        root = view.rootObject()
        root.setProperty("rovingIndex", 2)

        mo = root.metaObject()
        idx = mo.indexOfMethod("openRovingContext()")
        assert idx >= 0
        assert mo.method(idx).invoke(root)
        QTest.qWait(40)

        context = root.property("contextAlbum")
        assert context is not None
        assert context["key"] == "album-2", "target exacto del roving"
        assert _visible_menus(root), "menú raíz abierto"
        assert not any(
            call[0] in ("play_album", "select_album") for call in library.calls
        )
        view.close()


class TestAreaKeyboardRuntime:
    """Menu / Shift+F10 traducidos por AlbumContextArea a la apertura del
    menú — misma semántica que el right-click."""

    _HARNESS = """
import QtQuick
import "{qml}/media"
Item {{
    id: root
    objectName: "areaHost"
    width: 300
    height: 200
    property bool menuOpened: false
    Rectangle {{
        id: target
        objectName: "areaTarget"
        anchors.fill: parent
        color: "transparent"
        AlbumContextArea {{
            id: area
            objectName: "testAlbumArea"
            anchors.fill: parent
            album: ({{
                key: "album-x", title: "Album X", artist: "Artist",
                year: 2001, hasArtwork: false, artworkPath: "",
                artistKey: "artist-x", trackCount: 10
            }})
            onContextRequested: root.menuOpened = true
        }}
        Keys.onPressed: e => area.handleContextKey(e)
    }}
}}
"""

    def _area(self, qapp):
        from PySide6.QtQml import QQmlComponent, QQmlEngine

        library = _AlbumLibrary([])
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", library)
        component = QQmlComponent(engine)
        component.setData(
            self._HARNESS.format(qml=QML_DIR.as_uri()).encode("utf-8"),
            QUrl("area_harness.qml"),
        )
        assert component.status() == QQmlComponent.Ready, [
            e.toString() for e in component.errors()
        ]
        obj = component.create()
        # Retener engine + componente + fake: sin refs, el C++ se destruye
        # antes de adoptar el item (GC no-determinista).
        self._kept = [engine, component, obj, library]
        return obj

    def test_menu_key_opens_context_menu(self, qapp):
        # El harness se instancia vía engine propio; se renderiza en un
        # QQuickWindow host (patrón del repo).
        obj = self._area(qapp)
        # QQuickView no puede adoptar un item de otro engine: usamos el
        # patrón del repo (window contentItem).
        from PySide6.QtQuick import QQuickWindow

        window = QQuickWindow()
        window.resize(300, 200)
        obj.setParentItem(window.contentItem())
        window.show()
        window.requestActivate()
        QTest.qWait(60)
        target = obj.findChild(QObject, "areaTarget")
        target.forceActiveFocus()
        QTest.qWait(20)
        QTest.keyClick(window, Qt.Key.Key_Menu)
        QTest.qWait(30)
        assert obj.property("menuOpened") is True, "Menu abre el contexto"
        window.close()

    def test_shift_f10_opens_context_menu(self, qapp):
        obj = self._area(qapp)
        from PySide6.QtQuick import QQuickWindow

        window = QQuickWindow()
        window.resize(300, 200)
        obj.setParentItem(window.contentItem())
        window.show()
        window.requestActivate()
        QTest.qWait(60)
        target = obj.findChild(QObject, "areaTarget")
        target.forceActiveFocus()
        QTest.qWait(20)
        QTest.keyClick(window, Qt.Key.Key_F10, Qt.KeyboardModifier.ShiftModifier)
        QTest.qWait(30)
        assert obj.property("menuOpened") is True, "Shift+F10 abre el contexto"
        window.close()


class TestArtistMenuFailClosedRuntime:
    def test_artist_add_to_playlist_item_hidden_without_capability(self, qapp):
        """Fail-close runtime: canAddToPlaylist false (default) → el item
        'Add Artist to Playlist' no es visible aunque
        library.canAddTracksToPlaylists sea true."""
        from PySide6.QtQml import QQmlComponent, QQmlEngine

        library = _AlbumLibrary([])
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", library)
        component = QQmlComponent(
            engine, str(QML_DIR / "media" / "ArtistContextMenu.qml")
        )
        assert component.status() == QQmlComponent.Ready, [
            e.toString() for e in component.errors()
        ]
        menu = component.create()
        menu.setProperty(
            "artist",
            {
                "key": "artist-1",
                "name": "Artist One",
                "albumCount": 2,
                "trackCount": 20,
                "artworkPath": "",
            },
        )
        assert menu.property("canAddToPlaylist") is False
        item = None
        for child in menu.findChildren(QObject):
            if child.property("text") == "Add Artist to Playlist":
                item = child
                break
        assert item is not None, "item presente en el árbol del menú"
        assert item.property("visible") is False, (
            "acción oculta sin la capacidad explícita (dead UI prohibida)"
        )
        self._kept = [menu, library]
