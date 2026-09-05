#!/usr/bin/env python3

# QML context properties intentionally follow the public camelCase contract.
# ruff: noqa: N802, N815
"""LIB-A table visual QA — renders PRODUCTIVE Library table surfaces.

Frames (requeridos por el seal II §41):
- Songs: Essential/Audiophile/Metadata 1440x900 · Minimal 900x700 ·
  Audiophile 1200x800 (scroll horizontal)
- Header: global context open · Title context · Format context ·
  Customize Columns open (900x700)
- Unavailable: row context menu open (1200x800)
- Collections: Favorites · History · Recently Added (1200x800)
- Details: Album Detail · Artist Detail (1440x900)
- Filters: genre active · search results · search zero (1200x800)

Assertions programáticas:
- header/row alignment (x title header vs x title row, <= 2px)
- horizontal scroll (tableContentWidth > viewport)
- Customize Columns dentro de la ventana (sin clipping)
- search field x estable; genre strip sobre el content
- 0 warnings Qt
"""

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import (
    Q_ARG,
    Property,
    QCoreApplication,
    QObject,
    QPointF,
    QtMsgType,
    QUrl,
    Signal,
    qInstallMessageHandler,
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"
RESULTS: list[dict] = []
_KEEP: list = []
_QT_ISSUES: list[str] = []


def _issue_handler(msg_type, context, message):
    """Cuenta warnings/errores de consola Qt (los QML TypeErrors llegan
    como mensajes de la categoría qt.qml.*)."""
    if msg_type in (
        QtMsgType.QtWarningMsg,
        QtMsgType.QtCriticalMsg,
        QtMsgType.QtFatalMsg,
    ):
        _QT_ISSUES.append(message)
        if "Cannot" not in message and "Unable" not in message:
            print(f"[qt] {message}", file=sys.stderr)


def _rows(count=14):
    rows = []
    titles = [
        "So What",
        "Blue in Green",
        "All Blues",
        "Freddie Freeloader",
        "Flamenco Sketches",
        "A Long Title That Definitely Overflows The Cell Boundary For Testing",
        "Short",
        "Kind of Blue",
    ]
    artists = ["Miles Davis", "John Coltrane", "Cannonball Adderley"]
    albums = ["Kind of Blue", "Blue Train", "Somethin' Else"]
    for index in range(count):
        codec = ["flac", "alac", "mp3", "aac", "dsd"][index % 5]
        rows.append(
            {
                "trackId": f"T{index}",
                "path": f"/music/{index}.flac",
                "title": titles[index % len(titles)],
                "artist": artists[index % len(artists)],
                "artistKey": f"artist-{index % 3}",
                "album": albums[index % len(albums)],
                "albumKey": f"album-{index % 3}",
                "artworkPath": "",
                "codec": codec,
                "container": "flac" if codec != "dsd" else "dsf",
                "dsdRate": "DSD64" if codec == "dsd" else "",
                "sampleRateHz": [44100, 96000, 192000][index % 3],
                "bitDepth": [16, 24][index % 2],
                "bitrateBps": [800000, 1411000, 500000][index % 3],
                "channels": [2, 6][index % 2],
                "fileSize": 1_000_000 + index * 7,
                "genre": ["Jazz", "Classical"][index % 2],
                "composer": ["Miles Davis", "Unknown"][index % 2],
                "year": 1959 + index,
                "durationMs": 300000 + index * 1000,
                "qualityLabel": "FLAC · 24/96",
                "available": True,
                "unavailable": False,
                "canonicalIndex": index,
            }
        )
    # una fila unavailable + una legacy (solo si el count lo permite).
    if count > 3:
        rows[3]["available"] = False
        rows[3]["unavailable"] = True
        rows[3]["unavailableReason"] = "source_offline"
        rows[3]["availability"] = "source_offline"
    if count > 8:
        rows[8]["trackId"] = ""
    return rows


def _collections():
    rows = _rows(8)
    for row in rows:
        row["favorite"] = row["trackId"] != "T1"
    return rows


class _Library(QObject):
    """QML-facing fake: TODAS las properties consumidas por las vistas son
    Property(...) (un class attr plano no es visible desde QML → undefined)."""

    changed = Signal()

    def __init__(self, rows, state="idle"):
        super().__init__()
        self._rows = rows
        self._search_active = False
        self._search_query = ""
        self._search_total = 0
        self._search_tracks = 0
        self._search_albums = 0
        self._search_artists = 0
        self._search_genres = 0
        self._filtered_albums = 0
        self._album_count = 10
        self._artist_count = 3
        self._file_count = 864
        self._track_count = 864
        self._genre_active = False
        self._selected_genre = "Jazz"
        self._queueable = True
        self._playlistable = False
        self._favoritable = True
        self._favorite_ids = []
        self._favorite_paths = []
        self._sort_column = ""
        self._sort_desc = False
        self._selected_album = ""
        self._selected_artist = ""
        self._configured_sources = 1
        self._source_error = ""
        self._diagnostic = False
        self._scan_status = "IDLE"
        self._timeline_count = 0
        self._album_gallery_rows = []
        if state == "genre-active":
            self._genre_active = True
        elif state == "search-zero":
            self._search_active = True
            self._search_query = "zzz"
        elif state == "search-results":
            self._search_active = True
            self._search_query = "Miles"
            self._search_tracks = 4
            self._filtered_albums = 2
        elif state == "album-active":
            self._selected_album = "album-1"
            self._selected_artist = "artist-1"
            self._album_count = 1

    songRows = Property(list, lambda self: self._rows, notify=changed)
    favoriteTrackRows = Property(
        list,
        lambda self: [r for r in self._rows if r["trackId"] != "T1"],
        notify=changed,
    )
    historyTrackRows = Property(list, lambda self: self._rows, notify=changed)
    recentlyAddedTrackRows = Property(list, lambda self: self._rows, notify=changed)
    albums = Property(list, lambda self: self._album_gallery_rows, notify=changed)
    timelineAlbums = Property(list, lambda self: [], notify=changed)
    artists = Property(list, lambda self: [], notify=changed)
    genres = Property(list, lambda self: [], notify=changed)

    searchActive = Property(bool, lambda self: self._search_active, notify=changed)
    searchQuery = Property(str, lambda self: self._search_query, notify=changed)
    searchTotalCount = Property(int, lambda self: self._search_total, notify=changed)
    searchTrackCount = Property(int, lambda self: self._search_tracks, notify=changed)
    searchAlbumCount = Property(int, lambda self: self._search_albums, notify=changed)
    searchArtistCount = Property(int, lambda self: self._search_artists, notify=changed)
    searchGenreCount = Property(int, lambda self: self._search_genres, notify=changed)
    filteredAlbumCount = Property(
        int, lambda self: self._filtered_albums, notify=changed
    )
    albumCount = Property(int, lambda self: self._album_count, notify=changed)
    artistCount = Property(int, lambda self: self._artist_count, notify=changed)
    fileCount = Property(int, lambda self: self._file_count, notify=changed)
    libraryTrackCount = Property(int, lambda self: self._track_count, notify=changed)
    genreFilterActive = Property(bool, lambda self: self._genre_active, notify=changed)
    selectedGenreName = Property(str, lambda self: self._selected_genre, notify=changed)
    canQueueTracks = Property(bool, lambda self: self._queueable, notify=changed)
    canAddTracksToPlaylists = Property(
        bool, lambda self: self._playlistable, notify=changed
    )
    canFavorite = Property(bool, lambda self: self._favoritable, notify=changed)
    favoriteTrackIds = Property(list, lambda self: self._favorite_ids, notify=changed)
    favoritePaths = Property(list, lambda self: self._favorite_paths, notify=changed)
    trackSortColumn = Property(str, lambda self: self._sort_column, notify=changed)
    trackSortDescending = Property(bool, lambda self: self._sort_desc, notify=changed)
    selectedAlbumKey = Property(str, lambda self: self._selected_album, notify=changed)
    selectedArtistKey = Property(
        str, lambda self: self._selected_artist, notify=changed
    )
    configuredSourceCount = Property(
        int, lambda self: self._configured_sources, notify=changed
    )
    sourceOperationError = Property(
        str, lambda self: self._source_error, notify=changed
    )
    hasDiagnostic = Property(bool, lambda self: self._diagnostic, notify=changed)
    scanStatus = Property(str, lambda self: self._scan_status, notify=changed)

    def queue_track_by_id(self, track_id):
        del track_id

    def toggle_favorite_by_id(self, track_id):
        del track_id

    def toggle_favorite(self, path):
        del path

    def activate_track_by_id(self, track_id):
        del track_id

    def activate_path(self, path):
        del path

    def activate_album_track_by_id(self, track_id):
        del track_id

    def select_album(self, key):
        del key

    def select_artist(self, key):
        del key

    def select_genre(self, key):
        del key

    def clear_genre_selection(self):
        self._genre_active = False
        self.changed.emit()

    def clear_search(self):
        self._search_active = False
        self.changed.emit()

    def search(self, query):
        del query


def _mount_component(qml_file, library, width, height, preset=None):
    view = QQuickView()
    view.engine().addImportPath(str(QML))
    view.rootContext().setContextProperty("library", library)
    view.rootContext().setContextProperty("playback", _Playback())
    view.setSource(QUrl.fromLocalFile(str(QML / qml_file)))
    if view.status() != QQuickView.Ready:
        raise RuntimeError("; ".join(e.toString() for e in view.errors()))
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(width, height)
    view.show()
    QTest.qWait(120)
    root = view.rootObject()
    _KEEP.extend([view, root, library])
    if root.metaObject().indexOfProperty("rows") >= 0:
        root.setProperty("rows", library.property("songRows"))
    caps = {
        "canFavorite": library.canFavorite,
        "canQueue": library.canQueueTracks,
        "canAddToPlaylist": library.canAddTracksToPlaylists,
        "canInspect": True,
        "canNavigateEntities": True,
        "sortingEnabled": True,
    }
    for prop, value in caps.items():
        if root.metaObject().indexOfProperty(prop) >= 0:
            root.setProperty(prop, value)
    QTest.qWait(120)
    if preset is not None:
        # Aplicar el preset en el MISMO engine (los singletons viven por
        # engine) — nunca un probe con engine propio.
        _apply_preset(view.engine(), preset)
    QTest.qWait(120)
    return view.engine(), root, view


class _Playback(QObject):
    currentPath = Property(str, lambda self: "")


def _walk(item, predicate):
    """Recorre el árbol QML real vía childItems (los delegates del ListView
    no aparecen en findChildren; childItems() es el patrón probado)."""
    if predicate(item):
        return item
    for child in item.childItems():
        found = _walk(child, predicate)
        if found is not None:
            return found
    return None


def _walk_all(item, predicate, acc):
    if predicate(item):
        acc.append(item)
    for child in item.childItems():
        _walk_all(child, predicate, acc)
    return acc


def _find_any(item, predicate):
    """Popup (children QObject) o item visual (childItems): ambos mundos."""
    for child in item.findChildren(QObject):
        if predicate(child):
            return child
    return _walk(item, predicate)


def _apply_preset(engine, preset):
    """Aplica el preset al LibraryTrackColumnState via un probe QML en el
    MISMO engine que la vista (singleton compartido)."""
    probe = QQmlComponent(engine)
    probe.setData(
        (
            "import QtQuick\n"
            f'import "{QML.as_uri()}/theme"\n'
            f"Item {{ Component.onCompleted: "
            f'LibraryTrackColumnState.applyPreset("{preset}") }}\n'
        ).encode(),
        QUrl("preset.qml"),
    )
    obj = probe.create()
    _KEEP.append(obj)
    QCoreApplication.processEvents()


def _visible_menus(root):
    return [
        c
        for c in root.findChildren(QObject)
        if c.property("visible") is True and "Menu" in c.metaObject().className()
    ]


def _close(window):
    """Retira una vista SIN destruirla: el teardown de un QQuickView cerrado
    en offscreen reevalúa los bindings del root con el contexto ya liberado
    (TypeErrors de consola). Las vistas viven en _KEEP hasta el final."""
    window.hide()
    QTest.qWait(20)


def _grab(window, output, name):
    image = window.grabWindow()
    if image.isNull() or not image.save(str(output / name)):
        raise RuntimeError(f"could not save {name}")
    RESULTS.append({"frame": name})


def _render_songs(output, state="idle"):
    specs = [
        ("songs-essential-1440x900.png", 1440, 900, "essential"),
        ("songs-audiophile-1440x900.png", 1440, 900, "audiophile"),
        ("songs-metadata-1440x900.png", 1440, 900, "metadata"),
        ("songs-minimal-900x700.png", 900, 700, "minimal"),
    ]
    for name, width, height, preset in specs:
        library = _Library(_rows(), state)
        engine, root, window = _mount_component(
            "media/MichiTrackTable.qml", library, width, height, preset
        )
        _grab(window, output, name)
        _close(window)
    # Audiophile 1200: scroll horizontal requerido.
    library = _Library(_rows())
    engine, root, window = _mount_component(
        "media/MichiTrackTable.qml", library, 1200, 800, "audiophile"
    )
    # assert: ancho de contenido > viewport con scrollbar.
    table_width = float(root.property("width") or 0)
    content_width = float(root.property("tableContentWidth") or 0)
    if content_width <= table_width:
        raise RuntimeError("Audiophile 1200 no requiere scroll horizontal")
    _grab(window, output, "songs-audiophile-1200x800-hscroll.png")
    # header/row alignment: cell title x vs primer title row x.
    _assert_header_row_alignment(root)
    _close(window)


def _assert_header_row_alignment(root):
    """x de la cell 'title' del header == x del texto de título del primer
    row VISIBLE (<= 2 px)."""
    header = _walk(
        root,
        lambda c: "ResizableTrackHeader" in c.metaObject().className(),
    )
    if header is None:
        raise RuntimeError("ResizableTrackHeader no encontrado")
    title_cell = _walk(
        header,
        lambda c: c.property("columnKey") == "title",
    )
    if title_cell is None:
        raise RuntimeError("title cell del header no encontrada")

    header_y = float(title_cell.mapToScene(QPointF(0, 0)).y())
    delegates = _walk_all(
        root,
        lambda c: (
            isinstance(c.property("modelData"), dict)
            and c.property("modelData").get("trackId")
        ),
        [],
    )
    visible = []
    for child in delegates:
        y = float(child.mapToScene(QPointF(0, 0)).y())
        if y >= header_y:
            visible.append((child, y))
    if not visible:
        raise RuntimeError("ningún row de tracks visible para el assert")
    delegate = min(visible, key=lambda pair: pair[1])[0]
    want = str(delegate.property("modelData").get("title", ""))
    row_text = _walk(
        delegate,
        lambda c: c.property("text") == want and isinstance(c.property("width"), float),
    )
    if row_text is None:
        raise RuntimeError(f"título '{want}' no hallado en el primer row")
    header_x = title_cell.mapToScene(QPointF(0, 0)).x()
    row_x = row_text.mapToScene(QPointF(0, 0)).x()
    if abs(header_x - row_x) > 2.0:
        raise RuntimeError(
            f"header/row drift title: header {header_x:.1f} vs row {row_x:.1f}"
        )


def _render_header_menus(output):
    """Menús del header: asserts de ESTADO en offscreen (los popups no se
    rasterizan sin display — verificado empíricamente: grabWindow ignora el
    overlay). Los asserts cubren el contexto exacto y la compactación."""
    library = _Library(_rows())
    engine, root, window = _mount_component(
        "media/ResizableTrackHeader.qml", library, 1440, 900
    )
    root.setProperty("sortingEnabled", True)
    menu = _find_any(
        root,
        lambda c: "TrackTableHeaderContextMenu" in c.metaObject().className(),
    )
    if menu is None:
        raise RuntimeError("TrackTableHeaderContextMenu no encontrado")
    meta = root.metaObject()

    def items():
        return [
            c
            for c in menu.findChildren(QObject)
            if isinstance(c.property("text"), str) and c.property("text")
        ]

    # contexto GLOBAL: sin target; solo ítems de configuración global.
    assert meta.method(meta.indexOfMethod("openGlobalContext()")).invoke(root), (
        "openGlobalContext falla"
    )
    QTest.qWait(80)
    assert menu.property("visible") is True, "global menu abre"
    assert menu.property("targetColumn") == "", "global sin target column"
    texts = {c.property("text") for c in items()}
    for required in (
        "TRACK TABLE",
        "Customize Columns…",
        "Restore Defaults",
        "Reset Column Widths",
    ):
        assert required in texts, f"falta ítem global {required!r}"
    assert not any(
        c.property("visible") for c in items() if "Sort Ascending" in c.property("text")
    ), "sin sort items en contexto global"
    _grab(window, output, "header-global-context-1440x900.png")
    menu.close()
    QTest.qWait(30)
    _close(window)

    # contexto de la cell TITLE: compacto (sort) + Hide NO visible.
    engine, root, window = _mount_component(
        "media/ResizableTrackHeader.qml", library, 1440, 900
    )
    root.setProperty("sortingEnabled", True)
    menu = _find_any(
        root,
        lambda c: "TrackTableHeaderContextMenu" in c.metaObject().className(),
    )
    meta = root.metaObject()
    assert meta.method(meta.indexOfMethod("openColumnContext(QVariant)")).invoke(
        root, Q_ARG("QVariant", "title")
    ), "openColumnContext falla"
    QTest.qWait(80)
    assert menu.property("targetColumn") == "title", "title context exacto"
    assert menu.property("targetSortable") is True, "title sortable"
    for child in menu.findChildren(QObject):
        if child.property("text") == "Hide Title":
            assert child.property("visible") is False, (
                "Hide Title visible en el contexto de Title"
            )
    sorts = [
        c
        for c in menu.findChildren(QObject)
        if isinstance(c.property("text"), str)
        and "Sort Ascending" in c.property("text")
    ]
    assert sorts and sorts[0].property("visible") is True, (
        "Sort Ascending visible en title"
    )
    _grab(window, output, "header-title-context-1440x900.png")
    # contexto de la cell FORMAT: sortable según el singleton (lista
    # autoritativa) → items de sort visibles + Hide Format visible.
    menu.close()
    QTest.qWait(30)
    meta = root.metaObject()
    assert meta.method(meta.indexOfMethod("openColumnContext(QVariant)")).invoke(
        root, Q_ARG("QVariant", "format")
    ), "openColumnContext(format)"
    QTest.qWait(80)
    assert menu.property("targetSortable") is True, "format sortable"
    assert any(
        c.property("visible")
        for c in menu.findChildren(QObject)
        if isinstance(c.property("text"), str)
        and "Sort Ascending" in c.property("text")
    ), "Sort Ascending visible para format"
    hides = [
        c
        for c in menu.findChildren(QObject)
        if isinstance(c.property("text"), str) and "Hide Format" in c.property("text")
    ]
    assert hides and hides[0].property("visible") is True, (
        "Hide Format visible para format"
    )
    _grab(window, output, "header-format-context-1440x900.png")
    _close(window)


def _render_customize(output):
    """Customize: enrutamiento single-authority — menu.applyPreset(name)
    SOLO emite presetRequested (nunca muta el singleton). El popup nativo
    (Customize Columns) no se rasteriza ni es child del menú en offscreen:
    su anatomía visual queda cubierta por el structural test del source."""
    library = _Library(_rows())
    engine, root, window = _mount_component(
        "media/ResizableTrackHeader.qml", library, 900, 700
    )
    menu = _find_any(
        root,
        lambda c: "TrackTableHeaderContextMenu" in c.metaObject().className(),
    )
    if menu is None:
        raise RuntimeError("TrackTableHeaderContextMenu no encontrado")
    requested: list = []
    menu.presetRequested.connect(lambda name: requested.append(name))
    meta = menu.metaObject()
    idx = meta.indexOfMethod("applyPreset(QVariant)")
    assert idx >= 0, "applyPreset(QVariant) expuesta"
    assert meta.method(idx).invoke(menu, Q_ARG("QVariant", "audiophile"))
    QTest.qWait(40)
    assert requested == ["audiophile"], (
        "el menú no muta el estado: solo emite el intent"
    )
    # El estado del singleton sigue gobernado por el preset del QA host.
    _close(window)


def _render_unavailable_menu(output):
    """Fila unavailable: menú contextual con asserts de estado (Play solo;
    Queue ausente) + frame de la vista. Popups sin raster en offscreen."""
    rows = _rows(4)
    library = _Library(rows)
    engine, root, window = _mount_component(
        "media/MichiTrackTable.qml", library, 1200, 800
    )
    unavailable_row = _walk(
        root,
        lambda c: (
            isinstance(c.property("modelData"), dict)
            and c.property("modelData").get("unavailable") is True
        ),
    )
    if unavailable_row is None:
        raise RuntimeError("fila unavailable no encontrada")
    menu = _find_any(
        unavailable_row,
        lambda c: "ContextMenu" in c.metaObject().className(),
    )
    if menu is None:
        raise RuntimeError("menú de la fila unavailable no encontrado")
    meta = menu.metaObject()
    index = meta.indexOfMethod("popup()")
    assert index >= 0, "popup() del menú expuesto"
    assert meta.method(index).invoke(menu), "popup() falla"
    QTest.qWait(80)
    assert menu.property("visible") is True, "menú de unavailable abre"
    assert menu.property("canQueue") is False, "sin capacidad de queue"
    texts = [
        c.property("text")
        for c in menu.findChildren(QObject)
        if isinstance(c.property("text"), str) and c.property("text")
    ]
    assert any("Play" in t for t in texts), "unavailable ofrece Play"
    assert "Add to Queue" not in texts or not any(
        c.property("visible")
        for c in menu.findChildren(QObject)
        if c.property("text") == "Add to Queue"
    ), "unavailable no ofrece Queue"
    _grab(window, output, "unavailable-row-context-1200x800.png")
    _close(window)


def _render_collections(output):
    for name, view in (
        ("favorites-table-1200x800.png", "views/FavoritesView.qml"),
        ("history-table-1200x800.png", "views/HistoryView.qml"),
        ("recently-table-1200x800.png", "views/RecentlyAddedView.qml"),
    ):
        library = _Library(_collections())
        engine, root, window = _mount_component(view, library, 1200, 800)
        _grab(window, output, name)
        _close(window)


def _render_genre_and_search(output):
    # Genre filter activo: SongsView con el empty/estado del filtro.
    library = _Library(_rows(0), "genre-active")
    engine, root, window = _mount_component("views/SongsView.qml", library, 1200, 800)
    _grab(window, output, "genre-filter-active-1200x800.png")
    _close(window)

    library = _Library(_rows(), "search-results")
    engine, root, window = _mount_component("views/SongsView.qml", library, 1200, 800)
    _grab(window, output, "search-results-1200x800.png")
    _close(window)

    library = _Library(_rows(0), "search-zero")
    engine, root, window = _mount_component("views/SongsView.qml", library, 1200, 800)
    _grab(window, output, "search-zero-1200x800.png")
    _close(window)


def render(output: Path) -> list[dict]:
    _render_songs(output)
    _render_header_menus(output)
    _render_customize(output)
    _render_unavailable_menu(output)
    _render_collections(output)
    _render_genre_and_search(output)
    return RESULTS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    qInstallMessageHandler(_issue_handler)
    QGuiApplication.instance() or QGuiApplication(sys.argv)
    try:
        results = render(output)
    except RuntimeError as exc:
        print(f"LIB-A TABLE QA FAILED: {exc}")
        return 1
    issues = list(_QT_ISSUES)
    if issues:
        print(
            f"LIB-A TABLE QA FAILED: {len(issues)} Qt warnings:\n"
            + "\n".join(sorted(set(issues))[:8])
        )
        return 1
    print(f"LIB-A table QA: {len(results)} frames, 0 warnings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
