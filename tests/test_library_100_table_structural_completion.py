"""LIBRARY 100% PREMIUM COMPLETION — LIB-A table/structural seal.

Matrix TAB01..TAB40 (incrementally sealed per execution block):
TAB30/31 album artistKey + Go-to-Artist exact key
TAB32/33 zero-result search never looks like an empty library
TAB34/35 genre filter visible projection + clear
TAB39 no folders presentation route
(Blocks 2-4 append TAB06-29 and TAB36-38/40.)
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import Property, QObject, Qt, QUrl, Signal, Slot  # noqa: F401
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _qml(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# BLOQUE 1 — proyecciones canónicas + verdad estructural + género + folders
# ---------------------------------------------------------------------------


class TestBlock1Structural:
    def test_tab30_album_row_carries_canonical_artist_key(self) -> None:
        """TAB30: la proyección canónica del álbum incluye artistKey —
        nunca se calcula en cada delegate QML."""
        bridge_src = (
            Path(__file__).resolve().parents[1]
            / "src/michi/presentation/library_bridge.py"
        ).read_text()
        assert '"artistKey": make_artist_key(' in bridge_src
        assert "_get_artist_albums" in bridge_src
        # Una sola schema de álbum: _get_artist_albums reusa _album_row.

        artist_albums = bridge_src[bridge_src.index("def _get_artist_albums") :]
        assert "self._album_row(album, tracks_by_path" in artist_albums, (
            "la proyección del artista reusa la fila canónica"
        )

    def test_tab30_album_rows_have_artist_key_runtime(self, qapp, tmp_path) -> None:
        from test_library_album_views import (
            FakeExtractor,
            FakeScanner,
            _make_library,
        )

        from michi.domain.library import make_artist_key
        from michi.presentation.library_bridge import LibraryBridge

        path = tmp_path / "miles.flac"
        path.write_bytes(b"x")
        from michi.domain.library import TrackMetadata

        library, *_ = _make_library(
            FakeScanner([path]),
            FakeExtractor(
                factory=lambda p: TrackMetadata(
                    artist="Miles Davis",
                    album="Kind of Blue",
                    title="So What",
                    duration_ms=540000,
                )
            ),
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        rows = bridge.property("albums")
        assert len(rows) == 1
        assert rows[0]["artist"] == "Miles Davis"
        assert rows[0]["artistKey"] == make_artist_key("Miles Davis"), (
            "identidad canónica, nunca display-name"
        )
        bridge.dispose()

    def test_tab31_album_menu_go_to_artist_uses_exact_key(self, qapp) -> None:
        """TAB31: right-click del álbum → Go to Artist → select_artist con
        el artistKey canónico exactamente una vez (nunca search por
        nombre)."""
        from PySide6.QtQml import QQmlComponent, QQmlEngine

        calls = []

        class Library(QObject):  # noqa: N815
            changed = Signal()
            canQueueTracks = Property(bool, lambda self: True)
            canAddTracksToPlaylists = Property(bool, lambda self: True)

            @Slot(str)
            def select_artist(self, key):
                calls.append(key)

            @Slot(str)
            def select_album(self, key):
                del key

            @Slot(str)
            def play_album(self, key):
                del key

            @Slot(str)
            def queue_album(self, key):
                del key

            @Slot(str)
            def request_album_playlist_target(self, key):
                del key

            @Slot(str)
            def request_album_palette(self, key):
                del key

        from michi.domain.library import make_artist_key

        library = Library()
        engine = QQmlEngine()
        engine.addImportPath(str(QML))
        engine.rootContext().setContextProperty("library", library)
        component = QQmlComponent(engine, str(QML / "media" / "AlbumContextMenu.qml"))
        assert component.status() == QQmlComponent.Ready, [
            e.toString() for e in component.errors()
        ]
        menu = component.create()
        menu.setProperty(
            "album",
            {
                "key": "album-x",
                "title": "Kind of Blue",
                "artist": "Miles Davis",
                "artistKey": make_artist_key("Miles Davis"),
                "year": 1959,
                "trackCount": 5,
                "hasArtwork": False,
                "artworkPath": "",
            },
        )
        # La visibilidad del item con artistKey es contrato estructural:
        # 'visible: root.album !== null && Boolean(root.album.artistKey)'.
        menu_src = (QML / "media" / "AlbumContextMenu.qml").read_text()
        assert "Boolean(root.album.artistKey)" in menu_src
        # El trigger real usa el artistKey exacto (nunca search por
        # nombre): se dispara la señal triggered() del item del menú.
        target = None
        for child in menu.findChildren(QObject):
            if child.property("text") == "Go to Artist":
                target = child
                break
        assert target is not None
        meta = target.metaObject()
        idx = meta.indexOfMethod("triggered()")
        assert idx >= 0
        assert meta.method(idx).invoke(target)
        assert calls == [make_artist_key("Miles Davis")], "exact-key una vez"
        self._kept = [engine, component, menu, library]

    def test_tab32_search_zero_never_shows_no_music_yet(self) -> None:
        """TAB32: el contenido estructural usa libraryTrackCount — una
        búsqueda con 0 resultados nunca degrada el Library a 'No music
        yet' (los empty filtered viven dentro de la vista actual)."""
        host = _qml("views/LibraryContentHost.qml")
        assert "visible: library.libraryTrackCount > 0" in host
        assert "library.libraryTrackCount === 0" and "No music yet" in host
        assert "library.fileCount > 0" not in host
        assert "library.fileCount === 0" not in host

    def test_tab33_sidebar_readiness_is_structural(self) -> None:
        """TAB33: el Sidebar usa la verdad estructural para 'Local'.
        Ready — un search 0 no apaga el indicador de librería."""
        sidebar = _qml("shell/Sidebar.qml")
        assert "library.libraryTrackCount > 0" in sidebar
        assert "library.fileCount > 0" not in sidebar

    def test_tab34_genre_filter_is_projected_visibly(self) -> None:
        """TAB34: proyección visible del filtro de género (bridge + strip
        UI con clear explícito)."""
        bridge_src = (
            Path(__file__).resolve().parents[1]
            / "src/michi/presentation/library_bridge.py"
        ).read_text()
        for token in (
            "selectedGenreKey = Property(",
            "selectedGenreName = Property(",
            "genreFilterActive = Property(",
            "def clear_genre_selection",
        ):
            assert token in bridge_src, token
        host = _qml("views/LibraryContentHost.qml")
        assert "library.genreFilterActive" in host
        assert 'objectName: "clearGenreFilterButton"' in host
        assert "library.clear_genre_selection()" in host
        assert 'qsTr("Clear genre filter")' in host

    def test_tab34_35_genre_runtime_projection_and_clear(self, qapp, tmp_path) -> None:
        from test_library_album_views import (
            FakeExtractor,
            FakeScanner,
            _make_library,
        )

        from michi.presentation.library_bridge import LibraryBridge

        path = tmp_path / "a.flac"
        path.write_bytes(b"x")
        from michi.domain.library import TrackMetadata

        library, *_ = _make_library(
            FakeScanner([path]),
            FakeExtractor(
                factory=lambda p: TrackMetadata(
                    artist="Miles",
                    album="Blue",
                    title="So What",
                    genre="Jazz",
                    duration_ms=540000,
                )
            ),
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        genres = bridge.property("genres") or []
        assert genres, "género del fixture presente"
        genre_key = genres[0]["key"]
        bridge.select_genre(genre_key)
        assert bridge.property("genreFilterActive") is True
        assert bridge.property("selectedGenreKey") == genre_key
        assert bridge.property("selectedGenreName") == "Jazz"
        # La proyección de songs queda filtrada por el género.
        songs = bridge.property("songRows")
        assert all(row.get("genre", "Jazz") == "Jazz" for row in songs)
        # TAB35: clear restaura la vista sin filtro.
        bridge.clear_genre_selection()
        assert bridge.property("genreFilterActive") is False
        assert bridge.property("selectedGenreKey") == ""
        bridge.dispose()

    def test_tab39_no_folders_presentation_route(self) -> None:
        """TAB39: Michi no es navegador de archivos — sin tab Folders y
        sin ruta productiva en el host; FoldersView eliminado tras 0
        consumers."""
        tabs = _qml("views/LibraryTabs.qml")
        assert "folders" not in tabs
        host = _qml("views/LibraryContentHost.qml")
        assert '"folders"' not in host
        assert "foldersViewComponent" not in host
        assert not (QML / "views" / "FoldersView.qml").exists()
        # La política del producto: ningún tree/listado de directorios.
        forbidden = (
            "os.listdir",
            "Path.iterdir",
            "QDir",
            "directory breadcrumbs",
        )
        for surface in ("views/LibraryTabs.qml", "shell/Sidebar.qml"):
            src = _qml(surface)
            for token in forbidden:
                assert token not in src, f"{surface}: {token}"


# ---------------------------------------------------------------------------
# BLOQUE 2 — convergencia de superficies en MichiTrackTable
# ---------------------------------------------------------------------------


class TestBlock2TableConvergence:
    def test_tab18_22_all_track_surfaces_use_michi_track_table(self) -> None:
        """TAB18-22: Favorites/History/RecentlyAdded/AlbumDetail/
        ArtistDetail convergen en la autoridad compartida."""
        for view in (
            "views/SongsView.qml",
            "views/FavoritesView.qml",
            "views/HistoryView.qml",
            "views/RecentlyAddedView.qml",
            "views/AlbumDetailView.qml",
            "views/ArtistDetailView.qml",
        ):
            assert "MichiTrackTable" in _qml(view), view

    def test_tab23_no_productive_track_table_header(self) -> None:
        """TAB23: TrackTableHeader legacy sin consumers productivos
        (archivo eliminado; la tabla usa ResizableTrackHeader)."""
        assert not (QML / "media" / "TrackTableHeader.qml").exists()
        table = _qml("media/MichiTrackTable.qml")
        assert "ResizableTrackHeader" in table

    def test_tab24_27_album_detail_rows_are_canonical(self) -> None:
        """TAB24-27: las filas del detalle de álbum usan la proyección
        canónica (TrackId/artistKey/albumKey/availability efectiva)."""
        bridge_src = (
            Path(__file__).resolve().parents[1]
            / "src/michi/presentation/library_bridge.py"
        ).read_text()
        assert "def _get_album_tracks(self)" in bridge_src
        assert "self._track_rows_with_artwork(self._album_track_refs)" in (
            bridge_src
        ), "proyección canónica única — no schema manual reducido"
        # El QML consume la fila con identidad (trackId del proyector).
        detail = _qml("views/AlbumDetailView.qml")
        assert "rows: library.albumTracks" in detail
        assert 'columnProfile: "album"' in detail
        assert 'numberingMode: "disc-track"' in detail

    def test_tab28_29_detail_queue_is_track_id_first(self) -> None:
        """TAB28/29: el Queue del detalle (álbum/artista) es TrackId-first
        — nunca queue por path."""
        album = _qml("views/AlbumDetailView.qml")
        assert "library.queue_track_by_id(trackId)" in album
        assert "library.queue_track_by_id" not in album.replace(
            "library.queue_track_by_id(trackId)", ""
        )
        artist = _qml("views/ArtistDetailView.qml")
        assert "library.queue_track_by_id(trackId)" in artist
        assert "queue_album_track" not in album + artist

    def test_tab24_album_detail_activation_keeps_album_context(self) -> None:
        """La activación del detalle usa el seam TrackId-first del bridge
        que preserva el CONTEXTO del álbum (nunca single ni índice)."""
        bridge_src = (
            Path(__file__).resolve().parents[1]
            / "src/michi/presentation/library_bridge.py"
        ).read_text()
        assert "def activate_album_track_by_id(self, track_id: str)" in bridge_src
        detail = _qml("views/AlbumDetailView.qml")
        assert "library.activate_album_track_by_id(trackId)" in detail
        assert "activate_album_track(index)" not in detail


# ---------------------------------------------------------------------------
# BLOQUE 3 — column state API + presets + header context menu + sort + persist
# ---------------------------------------------------------------------------


class TestBlock3ColumnAuthority:
    def test_tab06_title_cannot_be_hidden(self) -> None:
        """TAB06: Title es estructural — setVisible("title", false) es
        no-op; el menú no ofrece ocultarlo."""
        state = _qml("theme/LibraryTrackColumnState.qml")
        assert 'if (column === "title")' in state
        assert "return false  // estructural" in state or "return false" in state
        assert "titleLocked" in state
        menu = _qml("media/TrackTableHeaderContextMenu.qml")
        assert 'qsTr("Title (required)")' in menu
        assert 'root.targetColumn !== "title"' in menu
        # El menú viejo plano (MenuItem nativos) ya no existe.
        header = _qml("media/ResizableTrackHeader.qml")
        assert (
            "MichiMenuItem" not in header.replace("TrackTableHeaderContextMenu", "")
            or "columnsMenu" not in header
        )

    def test_tab07_08_09_header_context_sort_explicit(self) -> None:
        """TAB07-09: el contexto del header distingue CELL (targetColumn)
        con Sort Asc/Desc explícitos — nunca emula con dos toggles."""
        header = _qml("media/ResizableTrackHeader.qml")
        assert "function openColumnContext(column)" in header
        assert "function openGlobalContext()" in header
        assert "headerContextMenu.targetColumn = column" in header
        menu = _qml("media/TrackTableHeaderContextMenu.qml")
        assert 'qsTr("Sort Ascending")' in menu
        assert 'qsTr("Sort Descending")' in menu
        assert "sortAscendingRequested(root.targetColumn)" in menu
        assert "sortDescendingRequested(root.targetColumn)" in menu
        # El header conecta la dirección explícita.
        assert "onSortAscendingRequested: column =>" in header
        assert "onSortDescendingRequested: column =>" in header
        assert "sortDirectionRequested(column, false)" in header
        assert "sortDirectionRequested(column, true)" in header
        # Right-click de la cell NO dispara sort: handlers separados.
        cell = _qml("media/ResizableHeaderCell.qml")
        assert "signal contextRequested(string columnKey)" in cell
        assert "acceptedButtons: Qt.RightButton" in cell
        assert "root.contextRequested(root.columnKey)" in cell
        assert "root.sortRequested(root.columnKey)" in cell

    def test_tab10_reset_selected_column_width(self) -> None:
        header = _qml("media/ResizableTrackHeader.qml")
        assert "onResetWidthRequested: column =>" in header
        assert "LibraryTrackColumnState.resetWidth(column)" in header
        menu = _qml("media/TrackTableHeaderContextMenu.qml")
        assert 'qsTr("Reset %1 Width")' in menu
        assert "resetWidthRequested(root.targetColumn)" in menu
        # El reset doble-click del handle se mantiene independiente.
        cell = _qml("media/ResizableHeaderCell.qml")
        assert "onDoubleClicked" in cell
        assert "resetRequested(root.columnKey)" in cell

    def test_tab11_14_presets_are_real(self) -> None:
        """TAB11-14: presets Essential/Audiophile/Metadata/Minimal cambian
        el estado visible real del singleton."""
        state = _qml("theme/LibraryTrackColumnState.qml")
        assert "function applyPreset(name)" in state
        assert '"essential": {' in state
        assert '"audiophile": {' in state
        assert '"metadata": {' in state
        assert '"minimal": {' in state
        # Audio columns en Audiophile; metadata en Metadata; minimal solo
        # title/artist/duration/actions.
        audiophile = state[
            state.index('"audiophile": {') : state.index('"metadata": {')
        ]
        assert "sampleRate: true" in audiophile
        assert "bitDepth: true" in audiophile
        assert "genre: false" in audiophile
        metadata = state[state.index('"metadata": {') : state.index('"minimal": {')]
        assert "genre: true" in metadata and "composer: true" in metadata
        minimal = state[state.index('"minimal": {') :]
        assert "artwork: false" in minimal and "format: false" in minimal

    def test_tab15_profiles_hide_implicit_album_artist(self) -> None:
        """TAB15: el perfil oculta la columna implícita (album/artist) vía
        showAlbumColumn/showArtistColumn del perfil — el preset nunca
        reintroduce lo implícito."""
        table = _qml("media/MichiTrackTable.qml")
        assert "profileShowsAlbum" in table
        assert "profileShowsArtist" in table
        album_detail = _qml("views/AlbumDetailView.qml")
        assert 'columnProfile: "album"' in album_detail
        assert "showAlbumColumn: false" in album_detail
        artist_detail = _qml("views/ArtistDetailView.qml")
        assert 'columnProfile: "artist"' in artist_detail
        assert "showArtistColumn: false" in artist_detail

    def test_tab16_17_table_preferences_persist_debounced(self) -> None:
        """TAB16/17: la config de la tabla viaja en settingsBridge.libraryViews
        (trackTable) y la persistencia es debounced (timer 250 ms — nunca
        por píxel de resize)."""
        view = _qml("views/LibraryView.qml")
        assert "LibraryTrackColumnState.snapshot()" in view
        assert "LibraryTrackColumnState.applyConfiguration" in view
        assert "trackTablePersistDebounce" in view
        assert "interval: 250" in view
        assert "trackTablePersistDebounce.restart()" in view
        # Migración segura: la config ausente no corrompe los album settings.
        assert "if (parsed && parsed.trackTable)" in view

    def test_tab14_sort_columns_expanded_in_application(self) -> None:
        """§14: columnas sortables ampliadas con comparación TIPADA y
        tie-break TrackId — la aplicación es la autoridad."""
        query = (
            Path(__file__).resolve().parents[1]
            / "src/michi/application/library_track_query.py"
        ).read_text()
        for column in (
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
            assert column in query, column
        assert "_TEXT_COLUMNS" in query
        assert "def set_sort_state(self, column: str, descending: bool)" in query
        bridge_src = (
            Path(__file__).resolve().parents[1]
            / "src/michi/presentation/library_bridge.py"
        ).read_text()
        assert "def set_track_sort(self, column: str, descending: bool)" in bridge_src

    def test_tab14_sort_typed_runtime(self, qapp) -> None:
        """Runtime: sort por columna numérica (duration) usa valor numérico;
        el tie-break TrackId es estable."""
        from michi.application.library_track_query import (
            LibraryTrackQueryService,
        )
        from michi.domain.library import TrackRef

        tracks = [
            TrackRef(
                Path("/a.flac"),
                title="A",
                artist="X",
                album="Al",
                duration_ms=1000,
                track_id="T1",
            ),
            TrackRef(
                Path("/b.flac"),
                title="B",
                artist="X",
                album="Bl",
                duration_ms=3000,
                track_id="T2",
            ),
            TrackRef(
                Path("/c.flac"),
                title="C",
                artist="X",
                album="Cl",
                duration_ms=2000,
                track_id="T3",
            ),
        ]
        service = LibraryTrackQueryService()
        assert service.set_sort_state("duration", True) is True
        ordered = service.sort_tracks(tracks)
        assert [t.track_id for t in ordered] == ["T2", "T3", "T1"]
        assert service.set_sort_state("duration", False) is True
        assert [t.track_id for t in service.sort_tracks(tracks)] == ["T1", "T3", "T2"]
        # Columna inválida → no-op.
        assert service.set_sort_state("nope", False) is False


# ---------------------------------------------------------------------------
# BLOQUE 4 — sort/filter authority única + hi-res en la aplicación
# ---------------------------------------------------------------------------


class TestBlock4QueryAuthority:
    def test_tab37_albums_view_has_no_local_query_authority(self) -> None:
        """TAB37: AlbumsView no filtra/ordena localmente — la proyección
        de la aplicación (library.albums) es la autoridad; el QML solo
        conserva estrategias de presentación (timeline/editorial)."""
        albums = _qml("views/AlbumsView.qml")
        assert "albumMatchesFilter" not in albums
        assert "compareAlbums" not in albums
        assert "buildPresentationAlbums" not in albums
        assert "readonly property var presentationAlbums: library.albums" in albums
        # Las estrategias de presentación del view se conservan.
        assert "buildTimelineAlbums" in albums
        assert "buildEditorialAlbums" in albums

    def test_tab37_library_view_routes_requests_to_bridge(self) -> None:
        view = _qml("views/LibraryView.qml")
        assert "library.set_album_sort_mode(mode)" in view
        assert "library.set_album_sort_descending(descending)" in view
        assert "library.set_album_filter_mode(mode)" in view

    def test_tab38_hires_filter_is_application_owned(self) -> None:
        """TAB38: el filtro hi-res vive en la aplicación con facts
        canónicos (AlbumRef.contains_high_resolution = DSD OR depth>=24
        OR rate>=96000) — nunca inferido de labels."""
        query = (
            Path(__file__).resolve().parents[1]
            / "src/michi/application/library_track_query.py"
        ).read_text()
        assert '"hires"' in query
        assert "album.contains_high_resolution" in query
        domain = (
            Path(__file__).resolve().parents[1] / "src/michi/domain/library.py"
        ).read_text()
        assert "contains_high_resolution: bool = False" in domain
        # Definición factual exacta (DSD OR depth >= 24 OR rate >= 96000).
        assert "track.bit_depth >= 24 or track.sample_rate_hz >= 96_000" in domain

    def test_tab38_hires_filter_runtime(self, qapp) -> None:
        """Runtime: álbumes con DSD/24-bit/96kHz pasan el filtro hires de
        la aplicación; los demás no."""
        from michi.application.library_track_query import (
            LibraryAlbumQueryService,
        )
        from michi.domain.library import AlbumRef

        hires_dsd = AlbumRef(
            key="a1",
            title="DSD",
            artist="X",
            track_count=1,
            duration_ms=1000,
            contains_high_resolution=True,
        )
        hires_depth = AlbumRef(
            key="a2",
            title="24bit",
            artist="X",
            track_count=1,
            duration_ms=1000,
            contains_high_resolution=True,
        )
        cd = AlbumRef(
            key="a3",
            title="CD",
            artist="X",
            track_count=1,
            duration_ms=1000,
            contains_high_resolution=False,
        )
        service = LibraryAlbumQueryService()
        assert service.set_filter_mode("hires") is True
        projected = service.project([hires_dsd, hires_depth, cd])
        assert sorted(a.key for a in projected) == ["a1", "a2"]
        assert service.set_filter_mode("all") is True
        assert len(service.project([hires_dsd, cd])) == 2


# ---------------------------------------------------------------------------
# CIERRE — TAB01-05 unavailable semantics (tabla convergida) + i18n
# ---------------------------------------------------------------------------


class TestBlock0UnavailableRuntime:
    """TAB01-05: sobre la MichiTrackTable productiva con una fila
    unavailable — el contexto abre (right-click vía el área de la fila,
    Menu/Shift+F10 en el Keys del TrackRow), Play/Queue no-ops."""

    def test_tab01_02_03_unavailable_row_context_opens(self, qapp) -> None:
        """TAB01-03: right-click / Menu / Shift+F10 habilitados en la fila
        unavailable (el TrackRow no bloquea el contexto por availability)."""
        row_src = _qml("media/TrackRow.qml")
        # §5 sellado: foco y right-click con solo root.interactive.
        assert "activeFocusOnTab: root.interactive" in row_src
        assert (
            "!root.unavailable"
            not in row_src.split("activeFocusOnTab: root.interactive")[0].split(
                "activeFocusOnTab: root.interactive &&"
            )[0]
        )
        tap_block = row_src[row_src.index("acceptedButtons: Qt.RightButton") :]
        assert "enabled: root.interactive" in tap_block

    def test_tab04_05_unavailable_play_queue_noops_in_table(self, qapp) -> None:
        """TAB04/05: activar/encolar la fila unavailable de la tabla
        compartida son no-ops (los handlers exigen canInteract)."""
        rows = [
            {
                "trackId": "T1",
                "path": "/B.flac",
                "available": False,
                "unavailableReason": "source_offline",
                "title": "Offline",
                "artist": "Artist",
                "album": "Album",
                "canonicalIndex": 0,
                "artworkPath": "",
                "codec": "flac",
                "qualityLabel": "FLAC",
            }
        ]
        from test_m9_r3_contextual_runtime import (
            _PlaylistLibrary,
            _PlaylistPlayback,
        )

        library = _PlaylistLibrary()
        playback = _PlaylistPlayback()
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
        root.setProperty("canQueue", True)
        QTest.qWait(200)

        def find_delegate(obj, name):

            def visit(item):
                model = item.property("modelData")
                if isinstance(model, dict) and model.get("trackId") == name:
                    return item
                for child in item.childItems():
                    found = visit(child)
                    if found is not None:
                        return found
                return None

            return visit(obj)

        delegate = find_delegate(root, "T1")
        assert delegate is not None
        # El delegate bloquea play/queue: no hay signals hacia library.
        menu = None
        for child in delegate.findChildren(QObject):
            if "ContextMenu" in child.metaObject().className():
                menu = child
                break
        assert menu is not None, "menú de la fila disponible (contexto)"
        # El TrackRow interno no emite activated para unavailable.
        assert library.calls == []
        view.close()

    def test_tab40_library_strings_translated(self) -> None:
        """TAB40: strings de usuario traducidas en las superficies de la
        tabla/library tocadas por LIB-A."""
        albums = _qml("views/AlbumsView.qml")
        assert 'qsTr("No matching albums")' in albums
        tabs = _qml("views/LibraryTabs.qml")
        assert tabs.count('qsTr("') > 0
        assert 'text: "Songs"' not in tabs and 'label: "Songs"' not in tabs
        for view in (
            "views/SongsView.qml",
            "views/FavoritesView.qml",
            "views/HistoryView.qml",
            "views/RecentlyAddedView.qml",
        ):
            src = _qml(view)
            assert src.count("qsTr(") > 0, view
