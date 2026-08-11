"""Library use case — owns LibraryState, coordinates scan and search."""

from collections.abc import Callable
from pathlib import Path

from michi.application.library_port import LibraryScannerPort
from michi.application.queue_service import QueueService
from michi.domain.library import LibraryState, TrackRef


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
        paths = self._scanner.scan(Path(directory))
        self._state.tracks = [TrackRef(file_path=p) for p in paths]
        self._state.query = ""
        self._state.current_directory = directory
        self._notify()

    def search(self, query: str) -> None:
        self._state.query = query.strip().lower()
        self._notify()

    def activate(self, visible_index: int) -> None:
        tracks = self._state.visible_tracks
        if 0 <= visible_index < len(tracks):
            ref = tracks[visible_index]
            was_empty = self._queue.state.count == 0
            self._queue.add(ref.file_path)
            if was_empty:
                self._queue.play_index(0)
