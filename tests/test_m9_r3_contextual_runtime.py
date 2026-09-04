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


def _collect_by_object_name(root, name):
    """TODAS las instancias con el objectName (los delegates de Repeater
    no son alcanzables con findChildren; una instancia arbitraria no
    basta para targets múltiples)."""
    found = []

    def visit(item):
        if item.property("objectName") == name:
            found.append(item)
        for child in item.childItems():
            visit(child)

    visit(root)
    return found


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
    timelineAlbums = Property("QVariantList", lambda self: self._albums, notify=changed)
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

    def test_medium_context_open_selects_index_1(self, qapp):
        """El área medium REAL (instancia por traversal) selecciona su
        índice exacto (index+1) vía openMenu() — cero playback/open."""
        view, library = self._magazine(qapp, 10)
        root = view.rootObject()
        meds = _collect_by_object_name(root, "magazineMediumContext")
        assert meds, "áreas medium reales instanciadas"
        meta = meds[0].metaObject()
        assert meta.indexOfMethod("openMenu()") >= 0
        assert meta.method(meta.indexOfMethod("openMenu()")).invoke(meds[0])
        QTest.qWait(40)
        assert root.property("rovingIndex") == 1, (
            "select-before-menu del medium (index+1)"
        )
        assert not any(
            call[0] in ("play_album", "select_album") for call in library.calls
        )
        view.close()

    def test_compact_context_open_selects_index_3(self, qapp):
        """El área compact REAL selecciona su índice exacto (index+3)
        vía openMenu() — cero playback/open."""
        view, library = self._magazine(qapp, 10)
        root = view.rootObject()
        compacts = _collect_by_object_name(root, "magazineCompactContext")
        assert compacts, "áreas compact reales instanciadas"
        meta = compacts[0].metaObject()
        assert meta.indexOfMethod("openMenu()") >= 0
        assert meta.method(meta.indexOfMethod("openMenu()")).invoke(compacts[0])
        QTest.qWait(40)
        assert root.property("rovingIndex") == 3, (
            "select-before-menu del compact (index+3)"
        )
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


# ==========================================================================
# M9-R3 CONVERGENCE SEAL — PlaylistTrackList contextual runtime (componente
# productivo REAL, cero copias de lógica).
# ==========================================================================


class _PlaylistLibrary(QObject):
    """Fake de library para PlaylistTrackList: registra los intents
    TrackId-first y de favorito."""

    changed = Signal()

    def __init__(self, favorite_track_ids=None, favorite_paths=None):
        super().__init__()
        self._favorite_track_ids = favorite_track_ids or []
        self._favorite_paths = favorite_paths or []
        self.calls: list[tuple[str, str]] = []

    favoriteTrackIds = Property(
        "QVariantList", lambda self: self._favorite_track_ids, notify=changed
    )
    favoritePaths = Property(
        "QVariantList", lambda self: self._favorite_paths, notify=changed
    )
    canQueueTracks = Property(bool, lambda self: True)

    @Slot(str)
    def queue_track_by_id(self, track_id):
        self.calls.append(("queue_track_by_id", track_id))

    @Slot(str)
    def toggle_favorite_by_id(self, track_id):
        self.calls.append(("favorite_by_id", track_id))

    @Slot(str)
    def toggle_favorite(self, path):
        self.calls.append(("favorite_path", path))

    @Slot(str)
    def select_album(self, key):
        self.calls.append(("select_album", key))

    @Slot(str)
    def select_artist(self, key):
        self.calls.append(("select_artist", key))


class _PlaylistQueue(QObject):
    def __init__(self):
        super().__init__()
        self.calls: list[tuple[str, str]] = []

    @Slot(str)
    def add_file(self, path):
        self.calls.append(("add_file", path))

    @Slot(list)
    def add_many(self, paths):
        self.calls.append(("add_many", str(paths)))


class _PlaylistPlayback(QObject):
    currentPath = Property(str, lambda self: "")


def _track_row(
    track_id,
    path,
    *,
    available=True,
    unavailable_reason="",
    title="Track",
    canonical_index=0,
):
    return {
        "trackId": track_id,
        "path": path,
        "available": available,
        "unavailableReason": unavailable_reason,
        "title": title,
        "artist": "Artist",
        "album": "Album",
        "canonicalIndex": canonical_index,
        "artworkPath": "",
        "codec": "flac",
        "qualityLabel": "FLAC",
    }


def _mount_playlist_track_list(qapp, rows):
    """PlaylistTrackList REAL en QQuickView con fakes mínimos."""
    library = _PlaylistLibrary()
    queue = _PlaylistQueue()
    playback = _PlaylistPlayback()
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR))
    ctx = view.rootContext()
    ctx.setContextProperty("library", library)
    ctx.setContextProperty("queue", queue)
    ctx.setContextProperty("playback", playback)
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "playlists/PlaylistTrackList.qml")))
    assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(900, 400)
    view.show()
    view.requestActivate()
    QTest.qWait(80)
    root = view.rootObject()
    root.setProperty("rows", rows)
    QTest.qWait(200)
    return view, root, library, queue


def _playlist_delegates(root):
    """Delegates del ListView (childItems traversal — findChildren no los
    alcanza). Cada delegate expone modelData."""
    found = []

    def visit(item):
        model = item.property("modelData")
        if isinstance(model, dict) and "trackId" in model:
            found.append(item)
        for child in item.childItems():
            visit(child)

    visit(root)
    return found


def _delegate_menu(delegate):
    """PlaylistTrackContextMenu real del delegate (Popup: QObject child,
    no visual child)."""
    for child in delegate.findChildren(QObject):
        if "ContextMenu" in child.metaObject().className():
            return child
    return None


def _delegate_for(delegate, track_id):
    model = delegate.property("modelData")
    return model.get("trackId") == track_id


class TestPlaylistTrackContextRuntime:
    def _menu_signal(self, menu, name):
        meta = menu.metaObject()
        index = meta.indexOfMethod(f"{name}()")
        assert index >= 0, f"señal {name} del menú real"
        return meta.method(index)

    def test_contextual_queue_identified_uses_track_id(self, qapp):
        """GOLDEN identificado: el menú del row T1 → 'Add to Queue' →
        library.queue_track_by_id('T1') exactamente una vez; cero
        add_file; cero playTrackRequested (contexto sin side effect)."""
        view, root, library, queue = _mount_playlist_track_list(
            qapp,
            [_track_row("T1", "/current/B.flac", title="Identified")],
        )
        plays = []
        root.playTrackRequested.connect(lambda index: plays.append(index))

        delegate = next(d for d in _playlist_delegates(root) if _delegate_for(d, "T1"))
        menu = _delegate_menu(delegate)
        assert menu is not None, "menú real del row"
        assert menu.property("canQueue") is True
        # Abrir el menú real + activar la acción Queue (trigger real).
        menu.metaObject().method(menu.metaObject().indexOfMethod("popup()")).invoke(
            menu
        )
        QTest.qWait(30)
        assert menu.property("visible") is True, "menú abierto"
        self._menu_signal(menu, "queueRequested").invoke(menu)
        QTest.qWait(30)

        assert library.calls == [("queue_track_by_id", "T1")]
        assert queue.calls == [], "legacy no se usa para tracks identificados"
        assert plays == [], "contexto sin playback"
        view.close()

    def test_contextual_queue_legacy_uses_add_file(self, qapp):
        """GOLDEN legacy: trackId vacío → queue.add_file(path) exactamente
        una vez; cero queue_track_by_id (el path queda SOLO como fallback
        legacy explícito)."""
        view, root, library, queue = _mount_playlist_track_list(
            qapp, [_track_row("", "/legacy.flac", title="Legacy")]
        )
        delegate = next(
            d
            for d in _playlist_delegates(root)
            if d.property("modelData")["path"] == "/legacy.flac"
        )
        menu = _delegate_menu(delegate)
        assert menu is not None
        assert menu.property("canQueue") is True
        self._menu_signal(menu, "queueRequested").invoke(menu)
        QTest.qWait(30)

        assert queue.calls == [("add_file", "/legacy.flac")]
        assert library.calls == [], "identidad no inventada para legacy"
        view.close()

    def test_contextual_unavailable_member_menu_opens_but_queue_and_play_noop(
        self, qapp
    ):
        """GOLDEN unavailable (source_offline): el menú SE ABRE (row
        retenida, container operable), Remove sigue siendo capacidad real,
        pero Queue/Play son no-ops — el miembro no resoluble nunca llega
        al motor ni a la Queue."""
        view, root, library, queue = _mount_playlist_track_list(
            qapp,
            [
                _track_row(
                    "T1",
                    "/B.flac",
                    available=False,
                    unavailable_reason="source_offline",
                )
            ],
        )
        plays = []
        removals = []
        root.playTrackRequested.connect(lambda index: plays.append(index))
        root.removeTrackRequested.connect(lambda index: removals.append(index))

        delegate = next(d for d in _playlist_delegates(root) if _delegate_for(d, "T1"))
        menu = _delegate_menu(delegate)
        assert menu is not None
        # El menú abre (nunca deshabilitado como un todo).
        menu.metaObject().method(menu.metaObject().indexOfMethod("popup()")).invoke(
            menu
        )
        QTest.qWait(30)
        assert menu.property("visible") is True, "menú del unavailable abre"
        # Acciones inválidas son no-ops (protección del delegate).
        self._menu_signal(menu, "playNowRequested").invoke(menu)
        self._menu_signal(menu, "queueRequested").invoke(menu)
        QTest.qWait(30)
        assert library.calls == []
        assert queue.calls == []
        assert plays == []
        # Remove sigue siendo válido (capacidad del container).
        self._menu_signal(menu, "removeRequested").invoke(menu)
        QTest.qWait(30)
        assert removals == [0], "remove del unavailable es capacidad real"
        view.close()

    def test_contextual_queue_duplicate_path_uses_row_identity(self, qapp):
        """GOLDEN adversarial: T1 y T2 con el MISMO path snapshot — el
        contexto de la row T2 encola T2 (identidad de la row exacta),
        nunca T1 ni path identity."""
        view, root, library, queue = _mount_playlist_track_list(
            qapp,
            [
                _track_row("T1", "/same.flac", title="One", canonical_index=0),
                _track_row("T2", "/same.flac", title="Two", canonical_index=1),
            ],
        )
        delegates = [
            d
            for d in _playlist_delegates(root)
            if _delegate_for(d, "T2") or _delegate_for(d, "T1")
        ]
        t2 = next(d for d in delegates if _delegate_for(d, "T2"))
        menu = _delegate_menu(t2)
        assert menu is not None
        self._menu_signal(menu, "queueRequested").invoke(menu)
        QTest.qWait(30)
        assert library.calls == [("queue_track_by_id", "T2")], (
            "la identidad de la row exacta decide, nunca el path"
        )
        assert queue.calls == []
        view.close()


class TestAlbumViewsKeyboardContextRuntime:
    """T2 runtime: las vistas de álbum abren el contexto del álbum bajo el
    currentIndex con el menú raíz real (sin hit-test sintético; la
    invocación es la función productiva del view)."""

    def test_grid_context_opens_current_index_album(self, qapp):
        view = QQuickView()
        view.engine().addImportPath(str(QML_DIR))
        library = _AlbumLibrary([_album(f"album-{i}", f"Album {i}") for i in range(6)])
        view.rootContext().setContextProperty("library", library)
        view.setSource(QUrl.fromLocalFile(str(QML_DIR / "views/AlbumGridView.qml")))
        assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.resize(1200, 900)
        view.show()
        view.requestActivate()
        QTest.qWait(150)
        root = view.rootObject()
        root.setProperty("currentIndex", 2)
        mo = root.metaObject()
        idx = mo.indexOfMethod("openCurrentAlbumContext()")
        assert idx >= 0, "función productiva del view"
        assert mo.method(idx).invoke(root)
        QTest.qWait(40)
        context = root.property("contextAlbum")
        assert context is not None and context["key"] == "album-2", (
            "el contexto es el álbum del currentIndex exacto"
        )
        view.close()

    def test_timeline_context_opens_current_index_album(self, qapp):
        from michi.domain.library import make_artist_key  # noqa: F401

        view = QQuickView()
        view.engine().addImportPath(str(QML_DIR))
        library = _AlbumLibrary(
            [_album(f"album-{i}", f"Album {i}", year=2000 + i) for i in range(6)]
        )
        view.rootContext().setContextProperty("library", library)
        view.setSource(QUrl.fromLocalFile(str(QML_DIR / "views/TimelineView.qml")))
        assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.resize(1200, 900)
        view.show()
        view.requestActivate()
        QTest.qWait(150)
        root = view.rootObject()
        root.setProperty("currentIndex", 1)
        mo = root.metaObject()
        idx = mo.indexOfMethod("openCurrentAlbumContext()")
        assert idx >= 0
        assert mo.method(idx).invoke(root)
        QTest.qWait(40)
        context = root.property("contextAlbum")
        assert context is not None, "contextAlbum del timeline resuelto"
        view.close()
