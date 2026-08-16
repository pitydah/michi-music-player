"""Library use case — owns LibraryState, coordinates scan and search."""

from collections.abc import Callable
from pathlib import Path

from michi.application.library_port import (
    LibraryFilesystemError,
    LibraryScannerPort,
)
from michi.application.queue_service import QueueService
from michi.domain.library import (
    LibraryDiagnostic,
    LibraryDiagnosticCode,
    LibraryState,
    TrackRef,
)


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
        self, scanner: LibraryScannerPort, queue_service: QueueService
    ) -> None:
        self._scanner = scanner
        self._queue = queue_service
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
        self._state.tracks = [TrackRef(file_path=p) for p in paths]
        self._state.query = ""
        self._state.current_directory = directory
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
        self._queue.add(ref.file_path)
        if was_empty:
            self._queue.play_index(0)
