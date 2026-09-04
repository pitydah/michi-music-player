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
        assert "columnProfile: \"album\"" in detail
        assert "numberingMode: \"disc-track\"" in detail

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
