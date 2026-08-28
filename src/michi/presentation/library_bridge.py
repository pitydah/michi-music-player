"""QML bridge for library — observes LibraryService."""

from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from michi.application.library_collection_coordinators import (
    LibraryPlaylistCoordinator,
    LibraryQueueCoordinator,
)
from michi.application.library_service import LibraryService
from michi.application.library_track_query import (
    LibraryAlbumQueryService,
    LibraryTrackQueryService,
)
from michi.domain.library import (
    AlbumRef,
    ArtistRef,
    LibraryScanStatus,
    TrackRef,
    build_timeline_projection,
    make_artist_key,
)
from michi.presentation.track_projection import project_track_row


class LibraryBridge(QObject):
    """Thin adapter: LibraryService state → QML properties, QML intent → service."""

    library_changed = Signal()
    playlist_target_requested = Signal(dict)
    new_playlist_target_requested = Signal(dict)
    album_properties_requested = Signal(dict)
    genre_selected = Signal(str)

    def __init__(
        self,
        service: LibraryService,
        playback_coordinator=None,
        track_query: LibraryTrackQueryService | None = None,
        album_query: LibraryAlbumQueryService | None = None,
        queue_coordinator: LibraryQueueCoordinator | None = None,
        playlist_coordinator: LibraryPlaylistCoordinator | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._playback_coordinator = playback_coordinator
        self._track_query = track_query or LibraryTrackQueryService()
        self._album_query = album_query or LibraryAlbumQueryService()
        self._queue_coordinator = queue_coordinator
        self._playlist_coordinator = playlist_coordinator
        self._selected_album_key: str = ""
        self._selected_album: AlbumRef | None = None
        self._album_track_refs: list[TrackRef] = []
        self._selected_artist_key: str = ""
        self._selected_artist: ArtistRef | None = None
        self._artist_track_refs: list[TrackRef] = []
        self._selected_genre_key = ""
        service.subscribe_changed(self._on_service_changed)

    def dispose(self) -> None:
        self._service.unsubscribe_changed(self._on_service_changed)

    def _on_service_changed(self) -> None:
        # M6.6: the selection identity is the canonical album key; a selected
        # album that leaves the library clears the detail safely.
        if self._selected_album_key:
            album = next(
                (
                    candidate
                    for candidate in self._service.state.albums
                    if candidate.key == self._selected_album_key
                ),
                None,
            )
            if album is None:
                self._selected_album_key = ""
                self._selected_album = None
                self._album_track_refs = []
            else:
                self._selected_album = album
                self._album_track_refs = [
                    ref
                    for path in album.track_paths
                    if (ref := self._service.resolve_trackref(path)) is not None
                ]
        if self._selected_artist_key:
            artist = next(
                (
                    candidate
                    for candidate in self._service.state.artists
                    if candidate.key == self._selected_artist_key
                ),
                None,
            )
            if artist is None:
                self._selected_artist_key = ""
                self._selected_artist = None
                self._artist_track_refs = []
            else:
                self._selected_artist = artist
                self._artist_track_refs = [
                    ref
                    for ref in self._service.state.tracks
                    if make_artist_key(ref.artist.strip() or "Unknown Artist")
                    == self._selected_artist_key
                ]
        self.library_changed.emit()

    def _get_files(self) -> list[str]:
        return [t.display_name for t in self._visible_track_refs()]

    def _get_count(self) -> int:
        return len(self._visible_track_refs())

    def _visible_track_refs(self) -> list[TrackRef]:
        return self._track_query.filter_genre(
            self._service.state.visible_tracks, self._selected_genre_key
        )

    def _get_current_dir(self) -> str:
        return self._service.state.current_directory

    def _get_search_query(self) -> str:
        return self._service.state.query  # RAW query (presentation form)

    def _get_search_active(self) -> bool:
        return self._service.state.search_active

    def _get_search_track_count(self) -> int:
        projection = self._service.state.search_projection
        return projection.track_count if projection is not None else 0

    def _get_search_album_count(self) -> int:
        projection = self._service.state.search_projection
        return projection.album_count if projection is not None else 0

    def _get_search_artist_count(self) -> int:
        projection = self._service.state.search_projection
        return projection.artist_count if projection is not None else 0

    def _get_search_genre_count(self) -> int:
        projection = self._service.state.search_projection
        return projection.genre_count if projection is not None else 0

    def _get_search_composer_count(self) -> int:
        projection = self._service.state.search_projection
        return projection.composer_count if projection is not None else 0

    def _get_search_total_count(self) -> int:
        projection = self._service.state.search_projection
        return projection.total_count if projection is not None else 0

    def _get_search_display_total_count(self) -> int:
        """M9-R1: playlist results are projected by the PlaylistsBridge; the
        Library total covers only the M7 entity ranker (the SearchOverlay
        adds the playlist section count from playlists.searchPlaylistCount)."""
        return self._get_search_total_count()

    def _get_diagnostic_code(self) -> str:
        diagnostic = self._service.state.diagnostic
        return diagnostic.code.value if diagnostic else ""

    def _get_diagnostic_message(self) -> str:
        diag = self._service.state.diagnostic
        return (diag.message or "") if diag else ""

    def _get_has_diagnostic(self) -> bool:
        return self._service.state.diagnostic is not None

    def _get_scan_status(self) -> str:
        """M6.7: scan-state projection — the enum NAME while a scan is in
        flight (DISCOVERING/INDEXING/...), "" when IDLE. The QML toolbar
        shows the name only when it is not IDLE."""
        status = self._service.state.scan_status
        return status.name if status is not LibraryScanStatus.IDLE else ""

    def _get_scan_processed(self) -> int:
        return self._service.state.scan_processed

    def _get_scan_total(self) -> int:
        return self._service.state.scan_total

    def _get_scan_progress(self) -> float:
        return self._service.state.scan_progress or 0.0

    def _get_scan_current_path(self) -> str:
        return self._service.state.scan_current_path or ""

    def _get_album_count(self) -> int:
        return len(self._service.state.albums)

    def _get_artist_count(self) -> int:
        return len(self._service.state.artists)

    def _album_row(self, album: AlbumRef) -> dict:
        return {
            "key": album.key,
            "albumKey": album.key,
            "title": album.title,
            "artist": album.artist,
            "artistKey": make_artist_key(album.artist.strip() or "Unknown Artist"),
            "trackCount": album.track_count,
            "durationMs": album.duration_ms,
            "hasArtwork": album.has_artwork,
            "artworkPath": self._service.artwork_path_for(album.key) or "",
            "year": album.year,
            "genres": list(album.genres),
            "technicalSummary": album.technical_summary,
        }

    def _album_properties_row(self, album: AlbumRef) -> dict:
        refs = [
            ref
            for path in album.track_paths
            if (ref := self._service.resolve_trackref(path)) is not None
        ]
        formats = []
        sample_rates = set()
        bit_depths = set()
        dsd_rates = set()
        for ref in refs:
            row = project_track_row(ref)
            label = row["formatLabel"]
            if label not in formats:
                formats.append(label)
            if ref.sample_rate_hz > 0:
                sample_rates.add(ref.sample_rate_hz)
            if ref.bit_depth > 0:
                bit_depths.add(ref.bit_depth)
            if row["dsdRate"]:
                dsd_rates.add(row["dsdRate"])
        row = self._album_row(album)
        row.update(
            {
                "formatsPresent": formats,
                "sampleRatesPresent": sorted(sample_rates),
                "bitDepthsPresent": sorted(bit_depths),
                "dsdRatesPresent": sorted(dsd_rates),
            }
        )
        return row

    def _album_rows(self) -> list[dict]:
        # M7: the unified search projection filters the album surface; the
        # canonical collections are the passthrough when search is inactive.
        albums = self._album_query.project(
            self._service.state.search_projection.albums
            if self._service.state.search_active
            else self._service.state.albums
        )
        return [self._album_row(album) for album in albums]

    def _get_timeline_albums(self) -> list[dict]:
        # M7: the timeline receives the SAME filtered album set as the other
        # five views — it never recomputes matching itself.
        albums = self._album_query.project(
            self._service.state.search_projection.albums
            if self._service.state.search_active
            else self._service.state.albums
        )
        rows = []
        albums_by_key = {a.key: a for a in albums}
        for projection in build_timeline_projection(albums):
            album = albums_by_key.get(projection.album_key)
            rows.append(
                {
                    "key": projection.album_key,
                    "title": projection.title,
                    "artist": projection.artist,
                    "artistKey": make_artist_key(
                        projection.artist.strip() or "Unknown Artist"
                    ),
                    "year": projection.year,
                    "decade": projection.decade,
                    "hasArtwork": album.has_artwork if album is not None else False,
                    "artworkPath": (
                        self._service.artwork_path_for(projection.album_key) or ""
                    ),
                }
            )
        return rows

    def _artist_rows(self) -> list[dict]:
        artists = (
            self._service.state.search_projection.artists
            if self._service.state.search_active
            else self._service.state.artists
        )
        # The domain intentionally owns no speculative artist portraits.  Use
        # the first canonical album artwork as an honest visual representative
        # and let QML render an initial when the local library has none.
        artwork_by_artist: dict[str, str] = {}
        for album in self._service.state.albums:
            artist_key = make_artist_key(album.artist.strip() or "Unknown Artist")
            if artist_key in artwork_by_artist or not album.has_artwork:
                continue
            artwork_path = self._service.artwork_path_for(album.key) or ""
            if artwork_path:
                artwork_by_artist[artist_key] = artwork_path
        return [
            {
                "key": a.key,
                "name": a.name,
                "trackCount": a.track_count,
                "albumCount": a.album_count,
                "hasArtwork": a.key in artwork_by_artist,
                "artworkPath": artwork_by_artist.get(a.key, ""),
            }
            for a in artists
        ]

    def _genre_rows(self) -> list[dict]:
        genres = (
            self._service.state.search_projection.genres
            if self._service.state.search_active
            else self._service.state.genres
        )
        return [
            {"key": g.key, "name": g.name, "trackCount": g.track_count} for g in genres
        ]

    def _composer_rows(self) -> list[dict]:
        composers = (
            self._service.state.search_projection.composers
            if self._service.state.search_active
            else self._service.state.composers
        )
        return [
            {"key": c.key, "name": c.name, "trackCount": c.track_count}
            for c in composers
        ]

    def _folder_rows(self) -> list[dict]:
        return [
            {"key": f.key, "path": f.path, "trackCount": f.track_count}
            for f in self._service.state.folders
        ]

    def _get_composers(self) -> list[dict]:
        """M7-CANONICAL-SEMANTICS: composer entity rows are consumable like
        albums/artists/genres (canonical passthrough; filtered by the same
        projection when search is active)."""
        return self._composer_rows()

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

    def _get_album_year(self) -> int:
        return self._selected_album.year if self._selected_album is not None else 0

    def _get_album_genres(self) -> str:
        if self._selected_album is None:
            return ""
        return " · ".join(self._selected_album.genres)

    def _get_album_duration(self) -> int:
        return (
            self._selected_album.duration_ms if self._selected_album is not None else 0
        )

    def _get_album_technical_summary(self) -> str:
        return (
            self._selected_album.technical_summary
            if self._selected_album is not None
            else ""
        )

    def _get_album_artwork(self) -> str:
        return self._service.artwork_path_for(self._selected_album_key) or ""

    def _get_album_tracks(self) -> list[dict]:
        return [project_track_row(ref) for ref in self._album_track_refs]

    def _get_selected_artist_key(self) -> str:
        return self._selected_artist_key

    def _get_artist_name(self) -> str:
        return self._selected_artist.name if self._selected_artist is not None else ""

    def _get_artist_track_count(self) -> int:
        return (
            self._selected_artist.track_count
            if self._selected_artist is not None
            else 0
        )

    def _get_artist_album_count(self) -> int:
        return (
            self._selected_artist.album_count
            if self._selected_artist is not None
            else 0
        )

    def _get_artist_tracks(self) -> list[dict]:
        return [self._track_row(ref) for ref in self._artist_track_refs]

    def _get_artist_albums(self) -> list[dict]:
        artist_paths = {ref.file_path for ref in self._artist_track_refs}
        albums = [
            album
            for album in self._service.state.albums
            if artist_paths.intersection(album.track_paths)
        ]
        return [
            {
                "key": album.key,
                "title": album.title,
                "artist": album.artist,
                "trackCount": album.track_count,
                "durationMs": album.duration_ms,
                "hasArtwork": album.has_artwork,
                "artworkPath": self._service.artwork_path_for(album.key) or "",
                "year": album.year,
                "technicalSummary": album.technical_summary,
            }
            for album in albums
        ]

    def _get_favorite_paths(self) -> list[str]:
        return list(self._reference_paths(self._service.state.favorite_paths))

    def _get_history_paths(self) -> list[str]:
        return list(self._reference_paths(self._service.state.history_paths))

    def _get_recently_added_paths(self) -> list[str]:
        return list(self._reference_paths(self._service.state.recently_added_paths))

    def _reference_paths(self, paths) -> tuple[str, ...]:
        """M7: reference surfaces (favorites/history/recently-added) are
        filtered by the SAME matched track ids when search is active."""
        state = self._service.state
        if not state.search_active:
            return tuple(paths)
        matched = state.search_projection.matched_track_ids
        return tuple(p for p in paths if p in matched)

    def _get_song_paths(self) -> list[str]:
        return [str(t.file_path) for t in self._visible_track_refs()]

    @staticmethod
    def _track_row(ref: TrackRef) -> dict:
        """Map one canonical TrackRef to display facts without UI inference."""
        return project_track_row(ref)

    def _track_row_with_artwork(self, ref: TrackRef) -> dict:
        path = ref.file_path
        artwork_path = ""
        for album in self._service.state.albums:
            if path in album.track_paths:
                artwork_path = self._service.artwork_path_for(album.key) or ""
                break
        return project_track_row(ref, artwork_path=artwork_path)

    def _get_song_rows(self) -> list[dict]:
        return [
            self._track_row_with_artwork(ref)
            for ref in self._track_query.sort_tracks(self._visible_track_refs())
        ]

    def _get_track_sort_column(self) -> str:
        return self._track_query.state.column

    def _get_track_sort_descending(self) -> bool:
        return self._track_query.state.descending

    def _get_album_sort_mode(self) -> str:
        return self._album_query.state.sort_mode

    def _get_album_sort_descending(self) -> bool:
        return self._album_query.state.descending

    def _get_album_filter_mode(self) -> str:
        return self._album_query.state.filter_mode

    def _get_favorite_rows(self) -> list[dict]:
        return self._rows_for(self._reference_paths(self._service.state.favorite_paths))

    def _get_favorite_track_rows(self) -> list[dict]:
        return self._track_rows_for(
            self._reference_paths(self._service.state.favorite_paths)
        )

    def _get_history_rows(self) -> list[dict]:
        return self._rows_for(self._reference_paths(self._service.state.history_paths))

    def _get_history_track_rows(self) -> list[dict]:
        return self._track_rows_for(
            self._reference_paths(self._service.state.history_paths)
        )

    def _get_recently_added_rows(self) -> list[dict]:
        return self._rows_for(
            self._reference_paths(self._service.state.recently_added_paths)
        )

    def _get_recently_added_track_rows(self) -> list[dict]:
        return self._track_rows_for(
            self._reference_paths(self._service.state.recently_added_paths)
        )

    def _rows_for(self, paths) -> list[dict]:
        rows = []
        for path in paths:
            ref = self._service.resolve_trackref(Path(path))
            if ref is not None:
                rows.append(
                    {"displayName": ref.display_name, "path": str(ref.file_path)}
                )
        return rows

    def _track_rows_for(self, paths) -> list[dict]:
        rows = []
        for path in paths:
            ref = self._service.resolve_trackref(Path(path))
            if ref is not None:
                rows.append(self._track_row_with_artwork(ref))
        return rows

    files = Property(list, _get_files, notify=library_changed)
    fileCount = Property(int, _get_count, notify=library_changed)
    currentDir = Property(str, _get_current_dir, notify=library_changed)
    searchQuery = Property(str, _get_search_query, notify=library_changed)
    searchActive = Property(bool, _get_search_active, notify=library_changed)
    searchTrackCount = Property(int, _get_search_track_count, notify=library_changed)
    searchAlbumCount = Property(int, _get_search_album_count, notify=library_changed)
    searchArtistCount = Property(int, _get_search_artist_count, notify=library_changed)
    searchGenreCount = Property(int, _get_search_genre_count, notify=library_changed)
    searchComposerCount = Property(
        int, _get_search_composer_count, notify=library_changed
    )
    searchTotalCount = Property(int, _get_search_total_count, notify=library_changed)
    searchDisplayTotalCount = Property(
        int, _get_search_display_total_count, notify=library_changed
    )
    diagnosticCode = Property(str, _get_diagnostic_code, notify=library_changed)
    diagnosticMessage = Property(str, _get_diagnostic_message, notify=library_changed)
    hasDiagnostic = Property(bool, _get_has_diagnostic, notify=library_changed)
    scanStatus = Property(str, _get_scan_status, notify=library_changed)
    scanProcessed = Property(int, _get_scan_processed, notify=library_changed)
    scanTotal = Property(int, _get_scan_total, notify=library_changed)
    scanProgress = Property(float, _get_scan_progress, notify=library_changed)
    scanCurrentPath = Property(str, _get_scan_current_path, notify=library_changed)
    albumCount = Property(int, _get_album_count, notify=library_changed)
    artistCount = Property(int, _get_artist_count, notify=library_changed)
    albums = Property(list, _get_albums, notify=library_changed)
    artists = Property(list, _get_artists, notify=library_changed)
    genres = Property(list, _get_genres, notify=library_changed)
    composers = Property(list, _get_composers, notify=library_changed)
    timelineAlbums = Property(list, _get_timeline_albums, notify=library_changed)
    folders = Property(list, _get_folders, notify=library_changed)
    selectedAlbumKey = Property(str, _get_selected_album_key, notify=library_changed)
    albumTitle = Property(str, _get_album_title, notify=library_changed)
    albumArtist = Property(str, _get_album_artist, notify=library_changed)
    albumYear = Property(int, _get_album_year, notify=library_changed)
    albumGenres = Property(str, _get_album_genres, notify=library_changed)
    albumDurationMs = Property(int, _get_album_duration, notify=library_changed)
    albumTechnicalSummary = Property(
        str, _get_album_technical_summary, notify=library_changed
    )
    albumArtwork = Property(str, _get_album_artwork, notify=library_changed)
    albumTracks = Property(list, _get_album_tracks, notify=library_changed)
    selectedArtistKey = Property(str, _get_selected_artist_key, notify=library_changed)
    artistName = Property(str, _get_artist_name, notify=library_changed)
    artistTrackCount = Property(int, _get_artist_track_count, notify=library_changed)
    artistAlbumCount = Property(int, _get_artist_album_count, notify=library_changed)
    artistTracks = Property(list, _get_artist_tracks, notify=library_changed)
    artistAlbums = Property(list, _get_artist_albums, notify=library_changed)
    favoritePaths = Property(list, _get_favorite_paths, notify=library_changed)
    historyPaths = Property(list, _get_history_paths, notify=library_changed)
    recentlyAddedPaths = Property(
        list, _get_recently_added_paths, notify=library_changed
    )
    songPaths = Property(list, _get_song_paths, notify=library_changed)
    songRows = Property(list, _get_song_rows, notify=library_changed)
    trackSortColumn = Property(str, _get_track_sort_column, notify=library_changed)
    trackSortDescending = Property(
        bool, _get_track_sort_descending, notify=library_changed
    )
    albumSortMode = Property(str, _get_album_sort_mode, notify=library_changed)
    albumSortDescending = Property(
        bool, _get_album_sort_descending, notify=library_changed
    )
    albumFilterMode = Property(str, _get_album_filter_mode, notify=library_changed)
    canQueueTracks = Property(
        bool, lambda self: self._queue_coordinator is not None, constant=True
    )
    canAddTracksToPlaylists = Property(
        bool, lambda self: self._playlist_coordinator is not None, constant=True
    )
    favoriteRows = Property(list, _get_favorite_rows, notify=library_changed)
    historyRows = Property(list, _get_history_rows, notify=library_changed)
    recentlyAddedRows = Property(list, _get_recently_added_rows, notify=library_changed)
    favoriteTrackRows = Property(list, _get_favorite_track_rows, notify=library_changed)
    historyTrackRows = Property(list, _get_history_track_rows, notify=library_changed)
    recentlyAddedTrackRows = Property(
        list, _get_recently_added_track_rows, notify=library_changed
    )

    @Slot(str)
    def scan(self, directory: str) -> None:
        self._service.start_scan(directory)

    @Slot(QUrl)
    def scan_url(self, directory: QUrl) -> None:
        """Adapt a native folder-picker URL to the application path contract."""
        if not directory.isLocalFile():
            return
        local_path = directory.toLocalFile()
        if local_path:
            self._service.start_scan(local_path)

    @Slot()
    def cancel_scan(self) -> None:
        """M6-PRODUCTION-INTEGRATION: delegate to the service (no progress
        logic in the bridge)."""
        self._service.cancel_scan()

    @Slot(str)
    def search(self, query: str) -> None:
        self._selected_genre_key = ""
        self._service.search(query)

    @Slot()
    def clear_search(self) -> None:
        """M7: deactivate search; the canonical collections are restored."""
        self._service.clear_search()

    @Slot(str)
    def select_genre(self, genre_key: str) -> None:
        genre = next(
            (item for item in self._service.state.genres if item.key == genre_key), None
        )
        if genre is None:
            return
        search_was_active = self._service.state.search_active
        self._selected_album_key = ""
        self._selected_album = None
        self._album_track_refs = []
        self._selected_artist_key = ""
        self._selected_artist = None
        self._artist_track_refs = []
        self._selected_genre_key = genre_key
        if search_was_active:
            self._service.clear_search()
        else:
            self.library_changed.emit()
        self.genre_selected.emit(genre_key)

    @Slot()
    def clear_genre_selection(self) -> None:
        if not self._selected_genre_key:
            return
        self._selected_genre_key = ""
        self.library_changed.emit()

    @Slot(int)
    def activate(self, visible_index: int) -> None:
        """M4-R1 final seal: Library playback intents route ONLY through the
        LibraryPlaybackCoordinator (validate → SINGLE). LibraryService never
        regains playback authority. A missing coordinator no-ops in isolated
        presentation tests."""
        if self._playback_coordinator is not None:
            self._playback_coordinator.play_visible_track(visible_index)

    @Slot(str)
    def activate_path(self, path: str) -> None:
        ref = self._service.resolve_trackref(Path(path))
        if ref is None:
            return
        if self._playback_coordinator is not None:
            self._playback_coordinator.play_track(ref.file_path, title=ref.title or "")
        # P2-01 final seal: no fallback to LibraryService playback authority.
        # Without a coordinator (isolated presentation test) this no-ops.

    @Slot()
    def play_selected_album(self) -> None:
        if self._playback_coordinator is not None and self._selected_album_key:
            self._playback_coordinator.play_album(self._selected_album_key)

    @Slot(str)
    def play_album(self, album_key: str) -> None:
        if self._playback_coordinator is not None:
            self._playback_coordinator.play_album(album_key)

    @Slot(str)
    def toggle_favorite(self, path: str) -> None:
        self._service.toggle_favorite(path)

    @Slot(str)
    def sort_tracks(self, column: str) -> None:
        previous = self._track_query.state
        self._track_query.set_sort(column)
        if self._track_query.state != previous:
            self.library_changed.emit()

    @Slot(str)
    def set_album_sort_mode(self, mode: str) -> None:
        if self._album_query.set_sort_mode(mode):
            self.library_changed.emit()

    @Slot(bool)
    def set_album_sort_descending(self, descending: bool) -> None:
        if self._album_query.set_sort_descending(descending):
            self.library_changed.emit()

    @Slot(str)
    def set_album_filter_mode(self, mode: str) -> None:
        if self._album_query.set_filter_mode(mode):
            self.library_changed.emit()

    @Slot(str, result=int)
    def queue_track(self, track_id: str) -> int:
        if self._queue_coordinator is None:
            return 0
        return self._queue_coordinator.queue_tracks((track_id,))

    @Slot(list, result=int)
    def queue_tracks(self, track_ids: list) -> int:
        if self._queue_coordinator is None:
            return 0
        return self._queue_coordinator.queue_tracks(str(item) for item in track_ids)

    @Slot(str, result=int)
    def queue_album(self, album_key: str) -> int:
        if self._queue_coordinator is None:
            return 0
        return self._queue_coordinator.queue_album(album_key)

    @Slot(str, result=int)
    def queue_artist(self, artist_key: str) -> int:
        if self._queue_coordinator is None:
            return 0
        return self._queue_coordinator.queue_artist(artist_key)

    @Slot(str, list, result=int)
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: list) -> int:
        if self._playlist_coordinator is None:
            return 0
        return self._playlist_coordinator.add_tracks(
            playlist_id, (str(item) for item in track_ids)
        )

    @Slot(str, str, result=int)
    def add_album_to_playlist(self, playlist_id: str, album_key: str) -> int:
        if self._playlist_coordinator is None:
            return 0
        return self._playlist_coordinator.add_album(playlist_id, album_key)

    @Slot(str, str, result=int)
    def add_artist_to_playlist(self, playlist_id: str, artist_key: str) -> int:
        if self._playlist_coordinator is None:
            return 0
        return self._playlist_coordinator.add_artist(playlist_id, artist_key)

    @Slot(str)
    def request_album_playlist_target(self, album_key: str) -> None:
        if self._playlist_coordinator is None:
            return
        if any(album.key == album_key for album in self._service.state.albums):
            self.playlist_target_requested.emit(
                {"kind": "album", "albumKey": album_key}
            )

    @Slot(str)
    def request_artist_playlist_target(self, artist_key: str) -> None:
        if self._playlist_coordinator is None:
            return
        if any(artist.key == artist_key for artist in self._service.state.artists):
            self.playlist_target_requested.emit(
                {"kind": "artist", "artistKey": artist_key}
            )

    @Slot(list)
    def request_tracks_playlist_target(self, track_ids: list) -> None:
        if self._playlist_coordinator is None:
            return
        valid = [
            str(item)
            for item in track_ids
            if self._service.resolve_trackref(Path(str(item))) is not None
        ]
        if valid:
            self.playlist_target_requested.emit({"kind": "tracks", "trackIds": valid})

    @Slot(str)
    def request_new_playlist_for_album(self, album_key: str) -> None:
        if self._playlist_coordinator is None:
            return
        if any(album.key == album_key for album in self._service.state.albums):
            self.new_playlist_target_requested.emit(
                {"kind": "album", "albumKey": album_key}
            )

    @Slot(list)
    def request_new_playlist_for_tracks(self, track_ids: list) -> None:
        if self._playlist_coordinator is None:
            return
        valid = [
            str(item)
            for item in track_ids
            if self._service.resolve_trackref(Path(str(item))) is not None
        ]
        if valid:
            self.new_playlist_target_requested.emit(
                {"kind": "tracks", "trackIds": valid}
            )

    @Slot(str, str, result=str)
    def create_playlist_from_album(self, name: str, album_key: str) -> str:
        if self._playlist_coordinator is None:
            return ""
        try:
            playlist = self._playlist_coordinator.create_from_album(name, album_key)
        except ValueError:
            return ""
        return playlist.playlist_id if playlist is not None else ""

    @Slot(str, list, result=str)
    def create_playlist_from_tracks(self, name: str, track_ids: list) -> str:
        if self._playlist_coordinator is None:
            return ""
        try:
            playlist = self._playlist_coordinator.create_from_tracks(
                name, (str(item) for item in track_ids)
            )
        except ValueError:
            return ""
        return playlist.playlist_id if playlist is not None else ""

    @Slot(str, str, result=str)
    def create_playlist_from_artist(self, name: str, artist_key: str) -> str:
        if self._playlist_coordinator is None:
            return ""
        try:
            playlist = self._playlist_coordinator.create_from_artist(name, artist_key)
        except ValueError:
            return ""
        return playlist.playlist_id if playlist is not None else ""

    @Slot(str)
    def request_album_properties(self, album_key: str) -> None:
        album = next(
            (item for item in self._service.state.albums if item.key == album_key), None
        )
        if album is not None:
            self.album_properties_requested.emit(self._album_properties_row(album))

    @Slot(str)
    def select_album(self, key: str) -> None:
        album = next((a for a in self._service.state.albums if a.key == key), None)
        if album is None:
            return
        self._selected_album_key = key
        self._selected_album = album
        self._selected_genre_key = ""
        self._selected_artist_key = ""
        self._selected_artist = None
        self._artist_track_refs = []
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

    @Slot(str)
    def select_artist(self, key: str) -> None:
        artist = next((a for a in self._service.state.artists if a.key == key), None)
        if artist is None:
            return
        self._selected_artist_key = key
        self._selected_artist = artist
        self._selected_genre_key = ""
        self._selected_album_key = ""
        self._selected_album = None
        self._album_track_refs = []
        self._artist_track_refs = [
            ref
            for ref in self._service.state.tracks
            if make_artist_key(ref.artist.strip() or "Unknown Artist") == key
        ]
        self.library_changed.emit()

    @Slot()
    def clear_artist_selection(self) -> None:
        self._selected_artist_key = ""
        self._selected_artist = None
        self._artist_track_refs = []
        self.library_changed.emit()

    @Slot(int)
    def activate_artist_track(self, index: int) -> None:
        """Artist track activation → SINGLE via the library coordinator."""
        if not (0 <= index < len(self._artist_track_refs)):
            return
        ref = self._artist_track_refs[index]
        if self._playback_coordinator is not None:
            self._playback_coordinator.play_artist_track_as_single(
                ref.file_path, title=ref.title or ""
            )
        # P2-01 final seal: no LibraryService playback fallback.

    @Slot(int)
    def activate_album_track(self, index: int) -> None:
        """Album Detail track click → ALBUM context at the clicked index
        (NOT SINGLE)."""
        if not (0 <= index < len(self._album_track_refs)):
            return
        if self._playback_coordinator is not None and self._selected_album_key:
            self._playback_coordinator.play_album_track(self._selected_album_key, index)
        # P2-01 final seal: no LibraryService playback fallback.
