"""QML bridge for library — observes LibraryService."""

from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.library_service import LibraryService
from michi.application.playlist_service import PlaylistService
from michi.domain.library import AlbumRef, TrackRef


class LibraryBridge(QObject):
    """Thin adapter: LibraryService state → QML properties, QML intent → service."""

    library_changed = Signal()

    def __init__(
        self,
        service: LibraryService,
        playlist_service: PlaylistService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._playlist_service = playlist_service
        self._selected_album_key: str = ""
        self._selected_album: AlbumRef | None = None
        self._album_track_refs: list[TrackRef] = []
        self._selected_playlist: str = ""
        self._selected_playlist_index: int = -1
        service.subscribe_changed(self._on_service_changed)
        if playlist_service is not None:
            playlist_service.subscribe_changed(self._on_service_changed)

    def dispose(self) -> None:
        self._service.unsubscribe_changed(self._on_service_changed)
        if self._playlist_service is not None:
            self._playlist_service.unsubscribe_changed(self._on_service_changed)

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
                    "year": album.year,
                }
            )
        return rows

    def _get_timeline_albums(self) -> list[dict]:
        rows = []
        for album in sorted(self._service.state.albums, key=lambda a: (-a.year, a.key)):
            decade = f"{album.year // 10 * 10}s" if album.year > 0 else "Unknown era"
            rows.append(
                {
                    "key": album.key,
                    "title": album.title,
                    "artist": album.artist,
                    "year": album.year,
                    "decade": decade,
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

    def _get_favorite_paths(self) -> list[str]:
        return list(self._service.state.favorite_paths)

    def _get_history_paths(self) -> list[str]:
        return list(self._service.state.history_paths)

    def _get_recently_added_paths(self) -> list[str]:
        return list(self._service.state.recently_added_paths)

    def _get_song_paths(self) -> list[str]:
        return [str(t.file_path) for t in self._service.state.visible_tracks]

    def _get_favorite_rows(self) -> list[dict]:
        return self._rows_for(self._service.state.favorite_paths)

    def _get_history_rows(self) -> list[dict]:
        return self._rows_for(self._service.state.history_paths)

    def _get_recently_added_rows(self) -> list[dict]:
        return self._rows_for(self._service.state.recently_added_paths)

    def _get_playlists(self) -> list[dict]:
        if self._playlist_service is None:
            return []
        return [
            {"name": p.name, "trackCount": len(p.track_paths)}
            for p in self._playlist_service.playlists
        ]

    def _get_selected_playlist_name(self) -> str:
        return self._selected_playlist

    def _get_playlist_tracks(self) -> list[dict]:
        if self._playlist_service is None or not self._selected_playlist:
            return []
        playlist = next(
            (
                p
                for p in self._playlist_service.playlists
                if p.name == self._selected_playlist
            ),
            None,
        )
        if playlist is None:
            return []
        rows = []
        for path in playlist.track_paths:
            ref = self._service.resolve_trackref(Path(path))
            rows.append(
                {
                    "displayName": (
                        ref.display_name if ref is not None else Path(path).stem
                    ),
                    "path": path,
                }
            )
        return rows

    def _rows_for(self, paths) -> list[dict]:
        rows = []
        for path in paths:
            ref = self._service.resolve_trackref(Path(path))
            if ref is not None:
                rows.append(
                    {"displayName": ref.display_name, "path": str(ref.file_path)}
                )
        return rows

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
    timelineAlbums = Property(list, _get_timeline_albums, notify=library_changed)
    artists = Property(list, _get_artists, notify=library_changed)
    genres = Property(list, _get_genres, notify=library_changed)
    folders = Property(list, _get_folders, notify=library_changed)
    selectedAlbumKey = Property(str, _get_selected_album_key, notify=library_changed)
    albumTitle = Property(str, _get_album_title, notify=library_changed)
    albumArtist = Property(str, _get_album_artist, notify=library_changed)
    albumArtwork = Property(str, _get_album_artwork, notify=library_changed)
    albumTracks = Property(list, _get_album_tracks, notify=library_changed)
    favoritePaths = Property(list, _get_favorite_paths, notify=library_changed)
    historyPaths = Property(list, _get_history_paths, notify=library_changed)
    recentlyAddedPaths = Property(
        list, _get_recently_added_paths, notify=library_changed
    )
    songPaths = Property(list, _get_song_paths, notify=library_changed)
    favoriteRows = Property(list, _get_favorite_rows, notify=library_changed)
    historyRows = Property(list, _get_history_rows, notify=library_changed)
    recentlyAddedRows = Property(list, _get_recently_added_rows, notify=library_changed)
    playlists = Property(list, _get_playlists, notify=library_changed)
    selectedPlaylistName = Property(
        str, _get_selected_playlist_name, notify=library_changed
    )
    playlistTracks = Property(list, _get_playlist_tracks, notify=library_changed)

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
    def toggle_favorite(self, path: str) -> None:
        self._service.toggle_favorite(path)

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

    @Slot(str)
    def select_playlist(self, name: str) -> None:
        if self._playlist_service is None:
            return
        index = next(
            (
                i
                for i, p in enumerate(self._playlist_service.playlists)
                if p.name == name
            ),
            -1,
        )
        if index < 0:
            return
        self._selected_playlist = name
        self._selected_playlist_index = index
        self.library_changed.emit()

    @Slot()
    def clear_playlist_selection(self) -> None:
        self._selected_playlist = ""
        self._selected_playlist_index = -1
        self.library_changed.emit()

    @Slot(str)
    def create_playlist(self, name: str) -> None:
        if self._playlist_service is None:
            return
        try:
            self._playlist_service.create_playlist(name)
        except ValueError:
            return

    @Slot(str)
    def delete_playlist(self, name: str) -> None:
        if self._playlist_service is None:
            return
        if self._selected_playlist == name:
            self._selected_playlist = ""
            self._selected_playlist_index = -1
        self._playlist_service.delete_playlist(name)

    @Slot(str, str)
    def rename_playlist(self, old_name: str, new_name: str) -> None:
        if self._playlist_service is None:
            return
        try:
            self._playlist_service.rename_playlist(old_name, new_name)
        except ValueError:
            return
        if self._selected_playlist == old_name:
            self._selected_playlist = new_name

    @Slot(str, str)
    def add_to_playlist(self, name: str, path: str) -> None:
        if self._playlist_service is None:
            return
        self._playlist_service.add_track(name, Path(path))

    @Slot(int)
    def remove_playlist_track(self, index: int) -> None:
        if self._playlist_service is None or not self._selected_playlist:
            return
        self._playlist_service.remove_track(self._selected_playlist, index)

    @Slot(int, int)
    def move_playlist_track(self, from_index: int, to_index: int) -> None:
        if self._playlist_service is None or not self._selected_playlist:
            return
        self._playlist_service.move_track(self._selected_playlist, from_index, to_index)

    @Slot()
    def play_selected_playlist(self) -> None:
        if self._playlist_service is None or not self._selected_playlist:
            return
        self._playlist_service.play_playlist(self._selected_playlist)
