"""Library use case — owns LibraryState, coordinates scan and search."""

from pathlib import Path

from michi.application.library_port import LibraryScannerPort
from michi.application.queue_service import QueueService
from michi.domain.library import LibraryState, TrackRef


class LibraryService:
    """Sole authority over LibraryState. QML emits intent, this decides."""

    def __init__(
        self,
        scanner: LibraryScannerPort,
        queue_service: QueueService,
    ) -> None:
        self._scanner = scanner
        self._queue = queue_service
        self._state = LibraryState()

    @property
    def state(self) -> LibraryState:
        return self._state

    def scan(self, directory: str) -> None:
        paths = self._scanner.scan(Path(directory))
        self._state.tracks = [TrackRef(file_path=p) for p in paths]
        self._state.query = ""
        self._state.current_directory = directory

    def search(self, query: str) -> None:
        self._state.query = query.strip().lower()

    def activate(self, visible_index: int) -> None:
        """User activated a track from the visible list. App decides play logic."""
        tracks = self._state.visible_tracks
        if 0 <= visible_index < len(tracks):
            ref = tracks[visible_index]
            was_empty = self._queue.state.count == 0
            self._queue.add(ref.file_path)
            if was_empty:
                self._queue.play_index(0)
