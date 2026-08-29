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
    make_album_key,
    make_artist_key,
    resolve_album_artist,
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
        source_coordinator=None,
        source_scan_lifecycle=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._playback_coordinator = playback_coordinator
        self._track_query = track_query or LibraryTrackQueryService()
        self._album_query = album_query or LibraryAlbumQueryService()
        self._queue_coordinator = queue_coordinator
        self._playlist_coordinator = playlist_coordinator
        self._source_coordinator = source_coordinator
        self._source_scan_lifecycle = source_scan_lifecycle
        if source_scan_lifecycle is not None:
            source_scan_lifecycle.subscribe_state(self._on_source_scan_state)
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

    def _source_scan_state(self):
        """The ONE productive source-scan lifecycle state (or None)."""
        if self._source_scan_lifecycle is None:
            return None
        return self._source_scan_lifecycle.state

    def _get_scan_status(self) -> str:
        """UNIFIED scan projection (CORRECTIVE SEAL §3): the ACTIVE
        authority wins — SourceScanLifecycle while running, the legacy
        LibraryService scan otherwise. QML never selects between them."""
        source_state = self._source_scan_state()
        if source_state is not None and source_state.active:
            return source_state.phase or "RUNNING"
        status = self._service.state.scan_status
        return status.name if status is not LibraryScanStatus.IDLE else ""

    def _get_scan_processed(self) -> int:
        source_state = self._source_scan_state()
        if source_state is not None and source_state.active:
            return source_state.processed
        return self._service.state.scan_processed

    def _get_scan_total(self) -> int:
        source_state = self._source_scan_state()
        if source_state is not None and source_state.active:
            return source_state.total
        return self._service.state.scan_total

    def _get_scan_progress(self) -> float:
        source_state = self._source_scan_state()
        if source_state is not None and source_state.active:
            if source_state.total > 0:
                return source_state.processed / source_state.total
            return 0.0
        return self._service.state.scan_progress or 0.0

    def _get_scan_current_path(self) -> str:
        source_state = self._source_scan_state()
        if source_state is not None and source_state.active:
            return source_state.current_path
        return self._service.state.scan_current_path or ""

    def _get_scan_diagnostic(self) -> str:
        source_state = self._source_scan_state()
        if source_state is not None:
            return source_state.diagnostic or ""
        return ""

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
            row = self._project_track_row(ref)
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
        return self._track_rows_with_artwork(self._album_track_refs)

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
        return self._track_rows_with_artwork(self._artist_track_refs)

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

    def _get_favorite_track_ids(self) -> list[str]:
        state = self._service.state
        if state.favorite_track_ids:
            return list(self._reference_ids(state.favorite_track_ids))
        return [
            f"legacy-path::{p}" for p in self._reference_paths(state.favorite_paths)
        ]

    def _get_history_track_ids(self) -> list[str]:
        state = self._service.state
        if state.history_track_ids:
            return list(self._reference_ids(state.history_track_ids))
        return [f"legacy-path::{p}" for p in self._reference_paths(state.history_paths)]

    def _get_recently_added_track_ids(self) -> list[str]:
        state = self._service.state
        if state.recently_added_track_ids:
            return list(self._reference_ids(state.recently_added_track_ids))
        return [
            f"legacy-path::{p}"
            for p in self._reference_paths(state.recently_added_paths)
        ]

    def _get_favorite_paths(self) -> list[str]:
        state = self._service.state
        if state.favorite_track_ids:
            return list(
                self._paths_for_ids(self._reference_ids(state.favorite_track_ids))
            )
        return list(self._reference_paths(state.favorite_paths))

    def _get_history_paths(self) -> list[str]:
        state = self._service.state
        if state.history_track_ids:
            return list(
                self._paths_for_ids(self._reference_ids(state.history_track_ids))
            )
        return list(self._reference_paths(state.history_paths))

    def _get_recently_added_paths(self) -> list[str]:
        state = self._service.state
        if state.recently_added_track_ids:
            return list(
                self._paths_for_ids(self._reference_ids(state.recently_added_track_ids))
            )
        return list(self._reference_paths(state.recently_added_paths))

    def _reference_paths(self, paths) -> tuple[str, ...]:
        """LEGACY path surface filter (M6-EXT-R4 freeze gate): pre-migration
        libraries with empty ID state keep the path-filtered behavior. New
        canonical filtering goes through ``_reference_ids``."""
        state = self._service.state
        if not state.search_active:
            return tuple(paths)
        matched = state.search_projection.matched_track_ids
        return tuple(p for p in paths if p in matched or f"legacy-path::{p}" in matched)

    def _reference_ids(self, ids) -> tuple[str, ...]:
        """CANONICAL user-state filter: stable TrackIds vs the matched set
        (M6-EXT-R4 freeze gate — UUID search within Favorites/History/
        Recent works)."""
        state = self._service.state
        if not state.search_active:
            return tuple(ids)
        matched = state.search_projection.matched_track_ids
        return tuple(track_id for track_id in ids if track_id in matched)

    def _paths_for_ids(self, ids) -> tuple[str, ...]:
        """DERIVED path projection of stable IDs (current resolved paths)."""
        paths = []
        for track_id in ids:
            ref = self._service.trackref_by_id(track_id)
            if ref is not None:
                paths.append(str(ref.file_path))
        return tuple(paths)

    def _get_song_paths(self) -> list[str]:
        return [str(t.file_path) for t in self._visible_track_refs()]

    def _effective_availability(self, ref: TrackRef) -> str:
        """Composed playability (M6-EXT-R4 freeze gate §11): source
        observation dominates the media observation — ONE authority via
        the shared domain composition."""
        if self._source_coordinator is not None and ref.library_source_id:
            from michi.domain.library_catalog import effective_availability

            return effective_availability(
                ref.availability,
                self._source_coordinator.observed_availability(ref.library_source_id),
            ).value
        return ref.availability.value

    @staticmethod
    def _track_row(ref: TrackRef) -> dict:
        """Map one canonical TrackRef to display facts without UI inference
        (static for legacy callers; effective availability is applied by
        the instance row builders)."""
        return project_track_row(ref)

    def _project_track_row(self, ref: TrackRef) -> dict:
        """THE ONE canonical TrackRef → UI row projector (P1-03).

        Every surface (Songs, Favorites, History, Recently Added, Albums,
        Artists, Search, tables, details) renders through this single
        function: canonical row facts + artwork + EFFECTIVE availability.
        QML only represents this truth — it never infers availability."""
        row = project_track_row(ref)
        row["availability"] = self._effective_availability(ref)
        return row

    def _track_row_with_artwork(self, ref: TrackRef) -> dict:
        path = ref.file_path
        artwork_path = ""
        for album in self._service.state.albums:
            if path in album.track_paths:
                artwork_path = self._service.artwork_path_for(album.key) or ""
                break
        row = self._project_track_row(ref)
        row["artworkPath"] = artwork_path
        return row

    def _track_rows_with_artwork(self, refs) -> list[dict]:
        """Project canonical album artwork once per represented album."""
        track_refs = list(refs)
        album_key_by_path = {
            ref.file_path: make_album_key(ref.album, resolve_album_artist(ref))
            for ref in track_refs
        }
        artwork_by_album_key = {
            album_key: self._service.artwork_path_for(album_key) or ""
            for album_key in set(album_key_by_path.values())
        }
        rows = []
        for ref in track_refs:
            row = self._project_track_row(ref)
            row["artworkPath"] = artwork_by_album_key.get(
                album_key_by_path[ref.file_path], ""
            )
            rows.append(row)
        return rows

    def _get_song_rows(self) -> list[dict]:
        return self._track_rows_with_artwork(
            self._track_query.sort_tracks(self._visible_track_refs())
        )

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

    def _refs_for_ids(self, ids) -> list[TrackRef]:
        """TrackId-native resolution: stable ids resolve through the live
        TrackRefs (current path projection); legacy-path:: ids resolve via
        the path fallback. Never rewrites identity."""
        refs = []
        for track_id in ids:
            ref = self._service.trackref_by_id(track_id)
            if ref is None and track_id.startswith("legacy-path::"):
                ref = self._service.resolve_trackref(
                    Path(track_id.removeprefix("legacy-path::"))
                )
            if ref is not None:
                refs.append(ref)
        return refs

    def _collection_track_rows(self, ids) -> list[dict]:
        """CANONICAL collection rows (P1-02): TrackId authority → matched
        filter → current TrackRef → the one row projector."""
        filtered = self._reference_ids(ids)
        return self._track_rows_with_artwork(self._refs_for_ids(filtered))

    def _get_favorite_rows(self) -> list[dict]:
        """LEGACY compatibility surface (path-based rows)."""
        return self._rows_for(self._reference_paths(self._service.state.favorite_paths))

    def _get_history_rows(self) -> list[dict]:
        """LEGACY compatibility surface (path-based rows)."""
        return self._rows_for(self._reference_paths(self._service.state.history_paths))

    def _get_recently_added_rows(self) -> list[dict]:
        """LEGACY compatibility surface (path-based rows)."""
        return self._rows_for(
            self._reference_paths(self._service.state.recently_added_paths)
        )

    def _get_favorite_track_rows(self) -> list[dict]:
        state = self._service.state
        if state.favorite_track_ids:
            return self._collection_track_rows(state.favorite_track_ids)
        # Legacy path-only state (pre-migration): derived ids projection.
        return self._track_rows_for(self._reference_paths(state.favorite_paths))

    def _get_history_track_rows(self) -> list[dict]:
        state = self._service.state
        if state.history_track_ids:
            return self._collection_track_rows(state.history_track_ids)
        return self._track_rows_for(self._reference_paths(state.history_paths))

    def _get_recently_added_track_rows(self) -> list[dict]:
        state = self._service.state
        if state.recently_added_track_ids:
            return self._collection_track_rows(state.recently_added_track_ids)
        return self._track_rows_for(self._reference_paths(state.recently_added_paths))

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
    favoriteTrackIds = Property(list, _get_favorite_track_ids, notify=library_changed)
    historyTrackIds = Property(list, _get_history_track_ids, notify=library_changed)
    recentlyAddedTrackIds = Property(
        list, _get_recently_added_track_ids, notify=library_changed
    )
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

    # ------------------------------------------------------------------
    # M6-EXT-R4-N: source management presentation (application half).
    # QML renders the projection; all intents land here.
    # ------------------------------------------------------------------

    def _on_source_scan_state(self, state) -> None:
        """Owner-thread lifecycle truth → presentation (scanning/progress)."""
        self.library_changed.emit()

    def _get_source_scan_status(self) -> str:
        if self._source_scan_lifecycle is None:
            return "IDLE"
        return self._source_scan_lifecycle.state.status

    def _get_source_scan_active(self) -> bool:
        if self._source_scan_lifecycle is None:
            return False
        return self._source_scan_lifecycle.state.active

    def _get_source_scan_progress(self) -> dict:
        if self._source_scan_lifecycle is None:
            return {}
        state = self._source_scan_lifecycle.state
        return {
            "generation": state.generation,
            "sourceId": state.current_source_id,
            "phase": state.phase,
            "processed": state.processed,
            "total": state.total,
            "currentPath": state.current_path,
            "diagnostic": state.diagnostic,
        }

    libraryScanDiagnostic = Property(str, _get_scan_diagnostic, notify=library_changed)
    sourceScanStatus = Property(str, _get_source_scan_status, notify=library_changed)
    sourceScanActive = Property(bool, _get_source_scan_active, notify=library_changed)
    sourceScanProgress = Property(
        dict, _get_source_scan_progress, notify=library_changed
    )

    def _track_id_resolvable(self, value: str) -> bool:
        """Stable identity first; the EXPLICIT legacy discriminator
        (legacy-path::<path>) is the only path fallback — a raw TrackId is
        never converted into a filesystem path."""
        if self._service.trackref_by_id(value) is not None:
            return True
        if value.startswith("legacy-path::"):
            return (
                self._service.resolve_trackref(
                    Path(value.removeprefix("legacy-path::"))
                )
                is not None
            )
        return False

    def _get_music_sources(self) -> list[dict]:
        """THIN adapter (M6-EXT-R4 freeze gate §21): presentation consumes
        the coordinator's PUBLIC surface — never a private repository."""
        if self._source_coordinator is None:
            return []
        counts = self._source_coordinator.source_counts(self._service)
        return [
            {
                "id": source.library_source_id,
                "name": source.display_name,
                "rootPath": source.root_path,
                "enabled": source.enabled,
                "lifecycle": source.lifecycle.value,
                "availability": self._source_coordinator.observed_availability(
                    source.library_source_id
                ).value,
                "trackCount": counts.get(source.library_source_id, 0),
            }
            for source in self._source_coordinator.list_sources()
        ]

    musicSources = Property(list, _get_music_sources, notify=library_changed)

    @Slot(str)
    def add_music_source(self, name: str, root_path: str) -> str:
        """Add a source; returns its id on success, or a typed error
        message on overlap/conflict (QML surfaces it honestly)."""
        if self._source_coordinator is None:
            return "Source management is not available."
        try:
            source = self._source_coordinator.add_source(name, root_path)
        except ValueError as exc:
            return str(exc)
        self.library_changed.emit()
        return source.library_source_id

    @Slot(str)
    def scan_source(self, source_id: str) -> None:
        """P1-01: reconcile ONE source ASYNC (worker compute, owner commit)
        — the GUI thread never touches the filesystem or SQLite here."""
        if self._source_scan_lifecycle is not None:
            self._source_scan_lifecycle.request_scan_source(source_id)

    @Slot()
    def scan_all_sources(self) -> None:
        """CANONICAL 'Scan library' intent: ALL active + enabled sources,
        serialized ASYNC through the one scan lifecycle."""
        if self._source_scan_lifecycle is not None:
            self._source_scan_lifecycle.request_scan_all()

    @Slot()
    def has_sources(self) -> bool:
        if self._source_coordinator is None:
            return False
        return any(
            s.lifecycle.value == "active" and s.enabled
            for s in self._source_coordinator.list_sources()
        )

    @Slot(str, str)
    def relocate_source(self, source_id: str, new_root: str) -> str:
        """Locate Source… (P1-01): remap the root synchronously (single
        cheap upsert) and reconcile ASYNC via the scan lifecycle."""
        if self._source_scan_lifecycle is None:
            return "Source management is not available."
        return self._source_scan_lifecycle.request_relocate(source_id, new_root)

    @Slot(str)
    def retire_source(self, source_id: str) -> None:
        """Remove from Michi: soft retirement (never a filesystem delete,
        never a cascade delete of identities)."""
        if self._source_coordinator is None:
            return
        from michi.domain.playlist import PlaylistPersistenceError  # noqa: F401

        self._source_coordinator.retire_source(source_id)
        self.library_changed.emit()

    @Slot(str)
    def disable_source(self, source_id: str, disabled: bool) -> None:
        """Enable/disable a configured source (source stays configured)."""
        if self._source_coordinator is None:
            return
        self._source_coordinator.set_source_enabled(source_id, not disabled)
        self.library_changed.emit()

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
        """UNIFIED cancel intent (CORRECTIVE SEAL §2): the bridge decides
        the ACTIVE productive authority — the source scan lifecycle when
        running, the legacy LibraryService scan otherwise."""
        source_state = self._source_scan_state()
        if source_state is not None and source_state.active:
            self._source_scan_lifecycle.cancel()
            return
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
        """CANONICAL queue intent by stable TrackId (CORRECTIVE SEAL §11)."""
        if self._queue_coordinator is None:
            return 0
        return self._queue_coordinator.queue_tracks((track_id,))

    @Slot(str)
    def queue_track_by_id(self, track_id: str) -> None:
        """Canonical queue intent (explicit alias for QML signal wiring)."""
        self.queue_track(track_id)

    @Slot(str)
    def activate_track_by_id(self, track_id: str) -> None:
        """CORRECTIVE SEAL §11: canonical activation by stable TrackId."""
        if self._playback_coordinator is not None:
            self._playback_coordinator.play_track_by_id(track_id)

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
        """CORRECTIVE SEAL §12: validate by STABLE TrackId — a TrackId is
        NEVER inferred to be a path."""
        if self._playlist_coordinator is None:
            return
        valid = [
            str(item) for item in track_ids if self._track_id_resolvable(str(item))
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
        """CORRECTIVE SEAL §12: validate by STABLE TrackId."""
        if self._playlist_coordinator is None:
            return
        valid = [
            str(item) for item in track_ids if self._track_id_resolvable(str(item))
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
