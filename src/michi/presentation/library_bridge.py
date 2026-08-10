"""QML bridge for library — delegates to LibraryService."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.library_service import LibraryService


class LibraryBridge(QObject):
    """Thin adapter: QML intent → LibraryService → QML observation."""

    library_changed = Signal()

    def __init__(self, service: LibraryService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service

    def _get_files(self) -> list[str]:
        return [t.display_name for t in self._service.state.visible_tracks]

    def _get_paths(self) -> list[str]:
        return [str(t.file_path) for t in self._service.state.visible_tracks]

    def _get_count(self) -> int:
        return len(self._service.state.visible_tracks)

    def _get_current_dir(self) -> str:
        return self._service.state.current_directory

    def notify(self) -> None:
        self.library_changed.emit()

    files = Property(list, _get_files, notify=library_changed)
    fileCount = Property(int, _get_count, notify=library_changed)
    currentDir = Property(str, _get_current_dir, notify=library_changed)

    @Slot(str)
    def scan(self, directory: str) -> None:
        self._service.scan(directory)
        self.library_changed.emit()

    @Slot(str)
    def search(self, query: str) -> None:
        self._service.search(query)
        self.library_changed.emit()

    @Slot(int)
    def activate(self, visible_index: int) -> None:
        """User requested to play or enqueue the visible track at index."""
        self._service.activate(visible_index)
