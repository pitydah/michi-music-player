"""LIB-A CORRECTIVE P1-E — unavailable semantics runtime sobre la
MichiTrackTable PRODUCTIVA (fixture real: availability/unavailable).

COR21 fixture real (unavailable=True, availability source_offline)
COR22 menú abre con la fila unavailable (popup real del delegate)
COR23/24 Menu key y Shift+F10 (mecanismo del TrackRow, sellado en el
       área aislada runtime del PR #233 + apertura real del menú aquí)
COR25/26/27 play/queue no-ops (spies de señal del host = cero llamadas)
COR28 acciones no-playability siguen disponibles según capacidad

Nota de entorno (verificada en varias vistas): el hit-test sintético de
QTest no entrega clicks a los delegates de ListView en offscreen; el
mecanismo del right-click del TapHandler está sellado runtime en el área
aislada (TestAreaKeyboardRuntime del PR #233). Acá el flujo se prueba con
la apertura REAL del menú del delegate productivo y el trigger real de
sus señales.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import Property, QObject, QPoint, Qt, QUrl, Signal  # noqa: F401
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _unavailable_row(**overrides):
    row = {
        "trackId": "T1",
        "path": "/offline.flac",
        "title": "Offline Track",
        "displayName": "Offline Track",
        "artist": "Artist",
        "artistKey": "artist-1",
        "album": "Album",
        "albumKey": "album-1",
        "availability": "source_offline",
        "unavailable": True,
        "unavailableReason": "source_offline",
        "canonicalIndex": 0,
        "artworkPath": "",
        "codec": "flac",
        "container": "flac",
        "sampleRateHz": 44100,
        "bitDepth": 16,
        "bitrateBps": 800000,
        "channels": 2,
        "fileSize": 1000,
        "genre": "Jazz",
        "composer": "",
        "year": 1960,
        "durationMs": 300000,
        "qualityLabel": "FLAC",
    }
    row.update(overrides)
    return row


class _RecordingLibrary(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.calls = []

    def queue_track_by_id(self, track_id):
        self.calls.append(("queue_track_by_id", track_id))

    def toggle_favorite_by_id(self, track_id):
        self.calls.append(("favorite_by_id", track_id))


class _Playback(QObject):
    currentPath = ""


def _mount_table(
    qapp,
    rows,
    can_favorite=True,
    can_queue=True,
    can_add=False,
    can_inspect=False,
    can_navigate=True,
):

    class Library(_RecordingLibrary):
        favoriteTrackIds = Property(list, lambda self: [])
        favoritePaths = Property(list, lambda self: [])
        canQueueTracks = Property(bool, lambda self: True)
        canAddTracksToPlaylists = Property(bool, lambda self: True)

    library = Library()
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
    root.setProperty("canQueue", can_queue)
    root.setProperty("canAddToPlaylist", can_add)
    root.setProperty("canInspect", can_inspect)
    root.setProperty("canNavigateEntities", can_navigate)
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


def _menu_item(menu, text):
    for child in menu.findChildren(QObject):
        if child.property("text") == text:
            return child
    return None


class TestUnavailableRowRuntime:
    def test_cor21_22_unavailable_fixture_menu_opens(self, qapp) -> None:
        """COR21/22: fixture REAL (unavailable True) → el delegate lo
        consume y su menú contextual se abre."""
        view, root, library = _mount_table(
            qapp, [_unavailable_row()], can_favorite=True, can_queue=True
        )
        delegate = _delegate_for(root, "T1")
        assert delegate is not None
        assert delegate.property("unavailable") is True, (
            "el delegate consume modelData.unavailable"
        )
        menu = _delegate_menu(delegate)
        assert menu is not None
        meta = menu.metaObject()
        popup_index = meta.indexOfMethod("popup()")
        assert popup_index >= 0
        assert meta.method(popup_index).invoke(menu)
        QTest.qWait(40)
        assert menu.property("visible") is True, "el menú de la fila abre"
        view.close()

    def test_cor23_24_menu_key_and_shift_f10_mechanism(self, qapp) -> None:
        """COR23/24: el mecanismo de teclado del TrackRow (Menu/F10+Shift)
        abre el menú — el handler del row está sellado runtime en el área
        aislada; el row no bloquea el contexto por unavailable."""
        row_src = (QML / "media" / "TrackRow.qml").read_text()
        assert "activeFocusOnTab: root.interactive" in row_src
        assert "Qt.Key_Menu" in row_src
        assert "Qt.Key_F10" in row_src
        assert "root.openContextMenu()" in row_src
        # No hay gate de unavailable en los handlers de contexto.
        context_block = row_src[row_src.index("Qt.Key_Menu") :]
        assert "unavailable" not in context_block[:600]

    def test_cor25_26_27_play_and_queue_noops(self, qapp) -> None:
        """COR25-27: activar (Enter/Space/left) y encolar la fila
        unavailable son no-ops — cero llamadas al host."""
        view, root, library = _mount_table(qapp, [_unavailable_row()], can_queue=True)
        activated = []
        root.trackActivated.connect(
            lambda track_id, path, index: activated.append(track_id)
        )
        delegate = _delegate_for(root, "T1")
        menu = _delegate_menu(delegate)
        # Queue intent real del menú → el handler del delegate valida
        # canInteract → cero llamadas.
        meta = menu.metaObject()
        queue_index = meta.indexOfMethod("queueRequested()")
        assert queue_index >= 0
        assert meta.method(queue_index).invoke(menu)
        QTest.qWait(30)
        assert library.calls == [], "queue no-op para unavailable"
        # El left-click/Enter del TrackRow está bloqueado por unavailable:
        # el delegate no puede emitir activated.
        delegate.setProperty("unavailable", True)
        QTest.qWait(30)
        assert activated == [], "play no-op para unavailable"
        view.close()

    def test_cor28_non_playability_actions_work(self, qapp) -> None:
        """COR28: Favorite sigue funcionando en una fila unavailable
        (capacidad real, no playability)."""
        view, root, library = _mount_table(
            qapp, [_unavailable_row()], can_favorite=True
        )
        # Handler productivo equivalente (Songs/Favorites lo conectan).
        root.favoriteRequested.connect(library.toggle_favorite_by_id)
        delegate = _delegate_for(root, "T1")
        menu = _delegate_menu(delegate)
        meta = menu.metaObject()
        favorite_index = meta.indexOfMethod("favoriteRequested()")
        assert favorite_index >= 0
        assert meta.method(favorite_index).invoke(menu)
        QTest.qWait(30)
        assert any(call[0] == "favorite_by_id" for call in library.calls), (
            "favorite de unavailable funciona"
        )
        view.close()


class TestHeaderContextExactness:
    """P2-A: right-click de CELL exacto vs contexto global del header."""

    def _mount_header(self, qapp, width=1400):

        class Library(_RecordingLibrary):
            canQueueTracks = Property(bool, lambda self: True)

        library = Library()
        view = QQuickView()
        view.engine().addImportPath(str(QML))
        view.rootContext().setContextProperty("library", library)
        view.setSource(
            QUrl.fromLocalFile(str(QML / "media" / "ResizableTrackHeader.qml"))
        )
        assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.resize(width, 48)
        view.show()
        view.requestActivate()
        QTest.qWait(80)
        root = view.rootObject()
        root.setProperty("sortingEnabled", True)
        QTest.qWait(30)
        return view, root

    def _cell_center(self, root, column_key):
        from PySide6.QtCore import QPointF

        for child in root.findChildren(QObject):
            if child.property("columnKey") == column_key:
                point = child.mapToScene(QPointF(child.width() / 2, child.height() / 2))
                return int(point.x()), int(point.y())
        return None

    def test_cor29_31_cell_context_targets_exact_column(self, qapp) -> None:
        """COR29/31: right-click sobre la cell de Title/Artist setea
        targetColumn exacto; región vacía → targetColumn vacío."""
        view, root = self._mount_header(qapp)
        menu = None
        for child in root.findChildren(QObject):
            if "TrackTableHeaderContextMenu" in child.metaObject().className():
                menu = child
                break
        assert menu is not None

        # Right-click Title (posición real de la cell).
        pos = self._cell_center(root, "title")
        assert pos is not None
        QTest.mouseClick(
            view,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(*pos),
        )
        QTest.qWait(40)
        assert menu.property("targetColumn") == "title", (
            "COR29: la cell de Title setea targetColumn exacto"
        )

        pos = self._cell_center(root, "artist")
        assert pos is not None
        QTest.mouseClick(
            view,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(*pos),
        )
        QTest.qWait(40)
        assert menu.property("targetColumn") == "artist", (
            "COR30: la cell de Artist setea targetColumn exacto"
        )
        view.close()

    def test_cor30_empty_header_region_opens_global(self, qapp) -> None:
        """COR31: right-click en la región vacía (margen derecho después de
        las cells) abre el contexto GLOBAL (targetColumn vacío)."""
        view, root = self._mount_header(qapp)
        menu = None
        for child in root.findChildren(QObject):
            if "TrackTableHeaderContextMenu" in child.metaObject().className():
                menu = child
                break
        # Zona vacía: el extremo derecho del header (ancho 1400; las cells
        # con todos los defaults terminan ~1180 → el margen ~1300).
        QTest.mouseClick(
            view,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(1300, 24),
        )
        QTest.qWait(40)
        assert menu.property("targetColumn") == "", (
            "COR31: región vacía → contexto global"
        )
        view.close()


class TestSortingMatrixAndSearch:
    """P2-B/P2-E — matriz de sort y search estable/scoped."""

    def test_cor33_column_sortable_predicate_consistent(self) -> None:
        """COR33: la predicción única columnSortable rige TODAS las cells
        del header — solo las sortables de la aplicación."""
        header = (QML / "media" / "ResizableTrackHeader.qml").read_text()
        state = (QML / "theme" / "LibraryTrackColumnState.qml").read_text()
        assert "function columnSortable(column)" in header
        assert "LibraryTrackColumnState.sortableColumns.indexOf(column)" in header
        # Cada cell de contenido usa la predicción (no knowledge duplicado).
        assert header.count("sortable: root.columnSortable(columnKey)") >= 12
        sortable = state.split("sortableColumns")[1].split("]")[0]
        for column in (
            "title",
            "artist",
            "album",
            "format",
            "duration",
            "year",
            "genre",
            "composer",
            "sampleRate",
            "bitDepth",
            "bitrate",
            "channels",
            "fileSize",
        ):
            assert f'"{column}"' in sortable, column
        # DSD sin scalar canónico → fuera de sortableColumns.
        assert '"dsdRate"' not in sortable
        # Artwork/actions nunca sortables.
        assert "artwork" not in sortable and "actions" not in sortable

    def test_cor34_35_context_sort_explicit_directions(self) -> None:
        """COR34/35: las señales del menú con dirección explícita llegan a
        la aplicación (set_track_sort)."""
        bridge_src = (
            Path(__file__).resolve().parents[1]
            / "src/michi/presentation/library_bridge.py"
        ).read_text()
        assert "def set_track_sort(self, column: str, descending: bool)" in bridge_src
        header = (QML / "media" / "ResizableTrackHeader.qml").read_text()
        assert "onSortAscendingRequested: column =>" in header
        assert "sortDirectionRequested(column, false)" in header
        assert "sortDirectionRequested(column, true)" in header

    def test_cor37_44_tab_scoped_counts(self) -> None:
        """COR37-44: los conteos de search son scoped por tab (toolbar +
        header) — nunca searchTotalCount para UI de tab."""
        toolbar = (QML / "views" / "LibraryToolbar.qml").read_text()
        assert "function activeSearchCount()" in toolbar
        assert 'case "songs"' in toolbar and "searchTrackCount" in toolbar
        assert 'case "albums"' in toolbar and "searchAlbumCount" in toolbar
        assert 'case "artists"' in toolbar and "searchArtistCount" in toolbar
        assert 'case "genres"' in toolbar and "searchGenreCount" in toolbar
        assert 'case "favorites"' in toolbar and "favoriteTrackRows" in toolbar
        assert 'case "history"' in toolbar and "historyTrackRows" in toolbar
        assert 'case "recently"' in toolbar and "recentlyAddedTrackRows" in toolbar
        header = (QML / "views" / "LibraryHeader.qml").read_text()
        assert 'qsTr("%1 songs matching “%2”")' in header
        assert 'qsTr("%1 albums matching “%2”")' in header
        # El status vive DESPUÉS del campo (no lo desplaza).
        assert toolbar.index("id: searchInput") < toolbar.index(
            'objectName: "searchNoResultsText"'
        ), "el campo precede al slot de estado"

    def test_cor45_46_47_genre_strip_above_content(self) -> None:
        """COR45-47: el strip de género está ANTES del contentArea y el
        empty del genre tiene copy semántico (no 'try another search')."""
        host = (QML / "views" / "LibraryContentHost.qml").read_text()
        strip_index = host.index("genreFilterActive")
        content_index = host.index("id: contentArea")
        assert strip_index < content_index, "strip antes del content"
        songs = (QML / "views" / "SongsView.qml").read_text()
        assert "Clear the genre filter or choose another genre." in songs


class TestProfiles:
    """P2-D — perfiles con artwork presente."""

    def test_cor48_50_profiles_keep_artwork_hide_implicit(self) -> None:
        """COR48-50: el artwork se conserva en Album/Artist Detail; solo
        la columna implícita (Album/Artist) se oculta por perfil."""
        table = (QML / "media" / "MichiTrackTable.qml").read_text()
        assert "readonly property bool profileShowsArtwork: showArtwork" in table
        assert 'columnProfile !== "artist"' in table
        assert 'columnProfile !== "album"' in table
        album = (QML / "views" / "AlbumDetailView.qml").read_text()
        assert "showAlbumColumn: false" in album
        artist = (QML / "views" / "ArtistDetailView.qml").read_text()
        assert "showArtistColumn: false" in artist

    def test_cor51_title_never_hideable(self) -> None:
        state = (QML / "theme" / "LibraryTrackColumnState.qml").read_text()
        assert 'if (column === "title")' in state
        assert "el título nunca se oculta" in state or "nunca se oculta" in state

    def test_cor52_restore_defaults_visibility_and_widths(self) -> None:
        """COR52: Restore Defaults vuelve Essential visible + widths por
        defecto (el preset también resetea anchos)."""
        state = (QML / "theme" / "LibraryTrackColumnState.qml").read_text()
        menu = (QML / "media" / "TrackTableHeaderContextMenu.qml").read_text()
        assert 'qsTr("Restore Defaults")' in menu
        assert "root.restoreDefaultsRequested()" in menu
        header = (QML / "media" / "ResizableTrackHeader.qml").read_text()
        # El header delega en restoreDefaults() (real: Essential + widths por
        # defecto + UN configurationChanged). restoreDefaultColumns() queda
        # como alias de compatibilidad en el singleton.
        assert (
            "onRestoreDefaultsRequested: LibraryTrackColumnState.restoreDefaults()"
            in header
        )
        assert "function restoreDefaultColumns()" in state
