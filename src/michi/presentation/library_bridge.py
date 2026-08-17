"""QML bridge for library — observes LibraryService."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.library_service import LibraryService
from michi.domain.library import AlbumRef, TrackRef


class LibraryBridge(QObject):
    """Thin adapter: LibraryService state → QML properties, QML intent → service."""

    library_changed = Signal()

    def __init__(self, service: LibraryService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._selected_album_key: str = ""
        self._selected_album: AlbumRef | None = None
        self._album_track_refs: list[TrackRef] = []
        service.subscribe_changed(self._on_service_changed)

    def dispose(self) -> None:
        self._service.unsubscribe_changed(self._on_service_changed)

    def _on_service_changed(self) -> None:
        self.library_changed.emit()

    def _get_files(self) -> list[str]:
        return [t.display_name for t in self._service.state.visible_tracks]

    def _get_count(self) -> int:
        return len(self._service.state.visible_tracks)

    def _get_current_dir(self) -> str:
        return self._service.state.current_directory

    def _get_search_query(self) -> str:
        return self._service.state.query

    def _get_diagnostic_code(self) -> str:
        diagnostic = self._service.state.diagnostic
        return diagnostic.code.value if diagnostic else ""

    def _get_diagnostic_message(self) -> str:
        diag = self._service.state.diagnostic
        return (diag.message or "") if diag else ""

    def _get_has_diagnostic(self) -> bool:
        return self._service.state.diagnostic is not None

    def _get_album_count(self) -> int:
        return len(self._service.state.albums)

    def _get_artist_count(self) -> int:
        return len(self._service.state.artists)

    def _album_rows(self) -> list[dict]:
        rows = []
        for album in self._service.state.albums:
            rows.append(
                {
                    "key": album.key,
                    "title": album.title,
                    "artist": album.artist,
                    "trackCount": album.track_count,
                    "durationMs": album.duration_ms,
                    "hasArtwork": album.has_artwork,
                    "artworkPath": self._service.artwork_path_for(album.key) or "",
                }
            )
        return rows

    def _artist_rows(self) -> list[dict]:
        return [
            {
                "key": a.key,
                "name": a.name,
                "trackCount": a.track_count,
                "albumCount": a.album_count,
            }
            for a in self._service.state.artists
        ]

    def _genre_rows(self) -> list[dict]:
        return [
            {"key": g.key, "name": g.name, "trackCount": g.track_count}
            for g in self._service.state.genres
        ]

    def _folder_rows(self) -> list[dict]:
        return [
            {"key": f.key, "path": f.path, "trackCount": f.track_count}
            for f in self._service.state.folders
        ]

    def _get_albums(self) -> list[dict]:
        return self._album_rows()

    def _get_artists(self) -> list[dict]:
        return self._artist_rows()

    def _get_genres(self) -> list[dict]:
        return self._genre_rows()

    def _get_folders(self) -> list[dict]:
        return self._folder_rows()

    def _get_selected_album_key(self) -> str:
        return self._selected_album_key

    def _get_album_title(self) -> str:
        return self._selected_album.title if self._selected_album is not None else ""

    def _get_album_artist(self) -> str:
        return self._selected_album.artist if self._selected_album is not None else ""

    def _get_album_artwork(self) -> str:
        return self._service.artwork_path_for(self._selected_album_key) or ""

    def _get_album_tracks(self) -> list[dict]:
        return [
            {
                "displayName": ref.display_name,
                "title": ref.title,
                "artist": ref.artist,
                "durationMs": ref.duration_ms,
                "path": str(ref.file_path),
            }
            for ref in self._album_track_refs
        ]

    files = Property(list, _get_files, notify=library_changed)
    fileCount = Property(int, _get_count, notify=library_changed)
    currentDir = Property(str, _get_current_dir, notify=library_changed)
    searchQuery = Property(str, _get_search_query, notify=library_changed)
    diagnosticCode = Property(str, _get_diagnostic_code, notify=library_changed)
    diagnosticMessage = Property(str, _get_diagnostic_message, notify=library_changed)
    hasDiagnostic = Property(bool, _get_has_diagnostic, notify=library_changed)
    albumCount = Property(int, _get_album_count, notify=library_changed)
    artistCount = Property(int, _get_artist_count, notify=library_changed)
    albums = Property(list, _get_albums, notify=library_changed)
    artists = Property(list, _get_artists, notify=library_changed)
    genres = Property(list, _get_genres, notify=library_changed)
    folders = Property(list, _get_folders, notify=library_changed)
    selectedAlbumKey = Property(str, _get_selected_album_key, notify=library_changed)
    albumTitle = Property(str, _get_album_title, notify=library_changed)
    albumArtist = Property(str, _get_album_artist, notify=library_changed)
    albumArtwork = Property(str, _get_album_artwork, notify=library_changed)
    albumTracks = Property(list, _get_album_tracks, notify=library_changed)

    @Slot(str)
    def scan(self, directory: str) -> None:
        self._service.scan(directory)

    @Slot(str)
    def search(self, query: str) -> None:
        self._service.search(query)

    @Slot(int)
    def activate(self, visible_index: int) -> None:
        self._service.activate(visible_index)

    @Slot(str)
    def select_album(self, key: str) -> None:
        album = next((a for a in self._service.state.albums if a.key == key), None)
        if album is None:
            return
        self._selected_album_key = key
        self._selected_album = album
        self._album_track_refs = [
            ref
            for path in album.track_paths
            if (ref := self._service.resolve_trackref(path)) is not None
        ]
        self.library_changed.emit()

    @Slot()
    def clear_album_selection(self) -> None:
        self._selected_album_key = ""
        self._selected_album = None
        self._album_track_refs = []
        self.library_changed.emit()

    @Slot(int)
    def activate_album_track(self, index: int) -> None:
        if not (0 <= index < len(self._album_track_refs)):
            return
        self._service.activate_track(self._album_track_refs[index])
