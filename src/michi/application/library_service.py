"""Library use case — owns LibraryState, coordinates scan and search."""

import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from michi.application.library_port import (
    LibraryFilesystemError,
    LibraryScannerPort,
)
from michi.application.ports import (
    ArtworkCachePort,
    ArtworkProviderPort,
    LibraryPrefsPort,
    MetadataExtractionError,
    MetadataExtractorPort,
)
from michi.application.queue_service import QueueService
from michi.domain.library import (
    HISTORY_CAP,
    RECENT_CAP,
    AlbumRef,
    LibraryDiagnostic,
    LibraryDiagnosticCode,
    LibraryPrefs,
    LibraryState,
    TrackMetadata,
    TrackRef,
    build_folder_model,
    build_music_model,
    merge_recently_added,
)

logger = logging.getLogger(__name__)


def _user_message(code, path=None, affected_count=0) -> str:
    """User-facing message for a library diagnostic code (spec §26)."""
    if code is LibraryDiagnosticCode.TRACK_MISSING:
        return f"File is no longer available: {path.name if path else ''}"
    if code is LibraryDiagnosticCode.DIRECTORY_MISSING:
        return f"Music directory is no longer available: {path}"
    if code is LibraryDiagnosticCode.ACCESS_FAILURE:
        return "Cannot access the library path."
    if code is LibraryDiagnosticCode.IO_FAILURE:
        return "The library filesystem reported an I/O error."
    if code is LibraryDiagnosticCode.UNKNOWN_FAILURE:
        return "The library path could not be validated."
    if code is LibraryDiagnosticCode.STALE_ENTRIES_REMOVED:
        return f"Removed {affected_count} unavailable file(s) from the library."
    return ""


class LibraryService:
    """Sole authority over LibraryState. Publishes changes."""

    def __init__(
        self,
        scanner: LibraryScannerPort,
        queue_service: QueueService,
        metadata_extractor: MetadataExtractorPort | None = None,
        artwork_provider: ArtworkProviderPort | None = None,
        artwork_cache: ArtworkCachePort | None = None,
        library_prefs: LibraryPrefsPort | None = None,
    ) -> None:
        self._scanner = scanner
        self._queue = queue_service
        self._metadata_extractor = metadata_extractor
        self._artwork_provider = artwork_provider
        self._artwork_cache = artwork_cache
        self._artwork_paths: dict[str, Path] = {}
        self._state = LibraryState()
        self._subscribers: list[Callable[[], None]] = []
        self._library_prefs = library_prefs
        if library_prefs is not None:
            prefs = library_prefs.load()
            self._state.favorite_paths = prefs.favorite_paths
            self._state.history_paths = prefs.history_paths
            self._state.recently_added_paths = prefs.recently_added_paths
        queue_service.subscribe_changed(self._on_queue_changed)

    @property
    def state(self) -> LibraryState:
        return self._state

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        for cb in self._subscribers:
            cb()

    def scan(self, directory: str) -> None:
        try:
            paths = self._scanner.scan(Path(directory))
        except LibraryFilesystemError as exc:
            self._state.diagnostic = LibraryDiagnostic(
                code=exc.code,
                message=_user_message(exc.code, path=exc.path),
                path=exc.path,
            )
            self._notify()
            return
        old_paths = {t.file_path for t in self._state.tracks}
        removed = old_paths - {p for p in paths}
        same_dir = self._state.current_directory == directory
        new_tracks = []
        for p in paths:
            new_tracks.append(self._make_trackref(p))
        previous_paths = {str(t.file_path) for t in self._state.tracks}
        self._state.tracks = new_tracks
        self._state.query = ""
        self._state.current_directory = directory
        self._rebuild_derived_library_state()
        if same_dir and removed:
            self._state.diagnostic = LibraryDiagnostic(
                code=LibraryDiagnosticCode.STALE_ENTRIES_REMOVED,
                message=_user_message(
                    LibraryDiagnosticCode.STALE_ENTRIES_REMOVED,
                    affected_count=len(removed),
                ),
                affected_count=len(removed),
            )
        else:
            self._state.diagnostic = None
        new_paths = [
            str(t.file_path)
            for t in self._state.tracks
            if str(t.file_path) not in previous_paths
        ]
        previous_recent = self._state.recently_added_paths
        self._state.recently_added_paths = merge_recently_added(
            new_paths,
            previous_recent,
            current_library_paths={str(t.file_path) for t in self._state.tracks},
            cap=RECENT_CAP,
        )
        self._persist_prefs()
        self._notify()

    def _make_trackref(self, file_path: Path) -> TrackRef:
        if self._metadata_extractor is None:
            return TrackRef(file_path=file_path)
        try:
            meta: TrackMetadata = self._metadata_extractor.extract(file_path)
        except MetadataExtractionError as exc:
            logger.warning("Metadata extraction failed for %s: %s", file_path, exc)
            return TrackRef(file_path=file_path)
        return TrackRef(
            file_path=file_path,
            display_name=meta.title or file_path.stem,
            title=meta.title,
            artist=meta.artist,
            album=meta.album,
            duration_ms=meta.duration_ms,
            genre=meta.genre,
            year=meta.year,
            album_artist=meta.album_artist,
            track_number=meta.track_number,
            disc_number=meta.disc_number,
            composer=meta.composer,
            compilation=meta.compilation,
        )

    def _enrich_albums(self, albums: tuple[AlbumRef, ...]) -> tuple[AlbumRef, ...]:
        """Mark albums with artwork: first track whose embedded art is both
        readable (provider) and cacheable (cache.store) wins.

        Without a provider or cache the albums are returned unchanged, i.e.
        has_artwork stays False (artwork absence is never an error)."""
        if self._artwork_provider is None or self._artwork_cache is None:
            return albums
        enriched = []
        for album in albums:
            has_artwork = False
            for track_path in album.track_paths:
                artwork = self._artwork_provider.get_embedded_artwork(track_path)
                if artwork is None:
                    continue
                stored_path = self._artwork_cache.store(album.key, artwork)
                if stored_path is not None:
                    self._artwork_paths[album.key] = stored_path
                    has_artwork = True
                    break
            enriched.append(replace(album, has_artwork=has_artwork))
        return tuple(enriched)

    def _rebuild_derived_library_state(self) -> None:
        """Recompute albums/artists/genres/folders from the canonical tracks
        and enrich albums with artwork. Called after ANY structural track
        mutation (successful scan, TRACK_MISSING removal, future mutations)."""
        model = build_music_model(self._state.tracks)
        self._state.albums = self._enrich_albums(model.albums)
        self._state.artists = model.artists
        self._state.genres = model.genres
        self._state.folders = build_folder_model(self._state.tracks)

    def restore_directory_hint(self, directory: str) -> None:
        """Restore a persisted path as context. No scan. Idempotent."""
        if not directory:
            return
        if self._state.current_directory == directory:
            return
        self._state.current_directory = directory
        self._notify()

    def search(self, query: str) -> None:
        self._state.query = query.strip().lower()
        self._notify()

    def _persist_prefs(self) -> None:
        if self._library_prefs is not None:
            self._library_prefs.save(
                LibraryPrefs(
                    favorite_paths=self._state.favorite_paths,
                    history_paths=self._state.history_paths,
                    recently_added_paths=self._state.recently_added_paths,
                )
            )

    def toggle_favorite(self, file_path) -> None:
        key = str(Path(file_path))
        updated = set(self._state.favorite_paths)
        if key in updated:
            updated.discard(key)
        else:
            updated.add(key)
        new_tuple = tuple(sorted(updated))
        if new_tuple == self._state.favorite_paths:
            return
        self._state.favorite_paths = new_tuple
        self._persist_prefs()
        self._notify()

    def set_favorite(self, file_path, favorite: bool) -> None:
        key = str(Path(file_path))
        updated = set(self._state.favorite_paths)
        if favorite:
            updated.add(key)
        else:
            updated.discard(key)
        new_tuple = tuple(sorted(updated))
        if new_tuple == self._state.favorite_paths:
            return
        self._state.favorite_paths = new_tuple
        self._persist_prefs()
        self._notify()

    def _on_queue_changed(self) -> None:
        current = self._queue.state.current_track
        if current is None:
            return
        path = str(current.file_path)
        if self._state.history_paths and self._state.history_paths[0] == path:
            return  # consecutive dedupe
        self._state.history_paths = (path, *self._state.history_paths)[:HISTORY_CAP]
        self._persist_prefs()
        self._notify()

    def activate(self, visible_index: int) -> None:
        tracks = self._state.visible_tracks
        if not (0 <= visible_index < len(tracks)):
            return
        self.activate_track(tracks[visible_index])

    def activate_track(self, track: TrackRef) -> None:
        """TD-013 activation contract for an exact TrackRef: validate the
        filesystem through the port BEFORE any queue mutation; TRACK_MISSING
        removes the exact reference; ACCESS/IO/UNKNOWN preserve it; success
        keeps the existing queue behavior."""
        try:
            self._scanner.validate_file(track.file_path)
        except LibraryFilesystemError as exc:
            if exc.code is LibraryDiagnosticCode.TRACK_MISSING:
                self._state.tracks = [t for t in self._state.tracks if t is not track]
                self._rebuild_derived_library_state()
                self._state.diagnostic = LibraryDiagnostic(
                    code=LibraryDiagnosticCode.TRACK_MISSING,
                    message=_user_message(
                        LibraryDiagnosticCode.TRACK_MISSING, path=track.file_path
                    ),
                    path=track.file_path,
                )
            else:
                self._state.diagnostic = LibraryDiagnostic(
                    code=exc.code,
                    message=_user_message(exc.code, path=track.file_path),
                    path=track.file_path,
                )
            self._notify()
            return
        was_empty = self._queue.state.count == 0
        self._queue.add(track.file_path, title=track.title or "")
        if was_empty:
            self._queue.play_index(0)

    def artwork_path_for(self, album_key: str) -> str | None:
        """Cached artwork path for an album key, or None when unavailable."""
        path = self._artwork_paths.get(album_key)
        return str(path) if path is not None else None

    def resolve_trackref(self, file_path: Path) -> TrackRef | None:
        """First TrackRef whose file_path equals ``file_path``, else None."""
        for t in self._state.tracks:
            if t.file_path == file_path:
                return t
        return None
