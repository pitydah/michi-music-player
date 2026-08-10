"""QML bridge for library — scan and browse audio files."""

from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from michi.application.library_port import LibraryScannerPort
from michi.application.queue_service import QueueService


class LibraryBridge(QObject):
    """Thin adapter: QML intent → LibraryScannerPort → QueueService."""

    library_changed = Signal()

    def __init__(
        self,
        scanner: LibraryScannerPort,
        queue_service: QueueService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._scanner = scanner
        self._queue = queue_service
        self._files: list[str] = []
        self._filtered: list[str] = []
        self._current_dir: str = ""
        self._query: str = ""

    def _get_files(self) -> list[str]:
        return self._filtered if self._query else self._files

    def _get_count(self) -> int:
        return len(self._get_files())

    def _get_current_dir(self) -> str:
        return self._current_dir

    files = Property(list, _get_files, notify=library_changed)
    fileCount = Property(int, _get_count, notify=library_changed)
    currentDir = Property(str, _get_current_dir, notify=library_changed)

    @Slot(str)
    def scan(self, directory: str) -> None:
        paths = self._scanner.scan(Path(directory))
        self._files = [str(p) for p in paths]
        self._filtered = []
        self._current_dir = directory
        self._query = ""
        self.library_changed.emit()

    @Slot(str)
    def search(self, query: str) -> None:
        self._query = query.strip().lower()
        if self._query:
            self._filtered = [f for f in self._files if self._query in Path(f).name.lower()]
        else:
            self._filtered = []
        self.library_changed.emit()

    @Slot(int)
    def add_to_queue(self, index: int) -> None:
        if 0 <= index < len(self._files):
            self._queue.add(Path(self._files[index]))
