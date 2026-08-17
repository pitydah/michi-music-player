"""Library use case — owns LibraryState, coordinates scan and search."""

import logging
from collections.abc import Callable
from pathlib import Path

from michi.application.library_port import (
    LibraryFilesystemError,
    LibraryScannerPort,
)
from michi.application.ports import (
    MetadataExtractionError,
    MetadataExtractorPort,
)
from michi.application.queue_service import QueueService
from michi.domain.library import (
    LibraryDiagnostic,
    LibraryDiagnosticCode,
    LibraryState,
    TrackMetadata,
    TrackRef,
    build_music_model,
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
    ) -> None:
        self._scanner = scanner
        self._queue = queue_service
        self._metadata_extractor = metadata_extractor
        self._state = LibraryState()
        self._subscribers: list[Callable[[], None]] = []

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
        self._state.tracks = new_tracks
        self._state.query = ""
        self._state.current_directory = directory
        model = build_music_model(self._state.tracks)
        self._state.albums = model.albums
        self._state.artists = model.artists
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
        )

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

    def activate(self, visible_index: int) -> None:
        tracks = self._state.visible_tracks
        if not (0 <= visible_index < len(tracks)):
            return
        ref = tracks[visible_index]
        try:
            self._scanner.validate_file(ref.file_path)
        except LibraryFilesystemError as exc:
            if exc.code is LibraryDiagnosticCode.TRACK_MISSING:
                self._state.tracks = [t for t in self._state.tracks if t is not ref]
                self._state.diagnostic = LibraryDiagnostic(
                    code=LibraryDiagnosticCode.TRACK_MISSING,
                    message=_user_message(
                        LibraryDiagnosticCode.TRACK_MISSING, path=ref.file_path
                    ),
                    path=ref.file_path,
                )
            else:
                self._state.diagnostic = LibraryDiagnostic(
                    code=exc.code,
                    message=_user_message(exc.code, path=ref.file_path),
                    path=ref.file_path,
                )
            self._notify()
            return
        was_empty = self._queue.state.count == 0
        self._queue.add(ref.file_path, title=ref.title or "")
        if was_empty:
            self._queue.play_index(0)
