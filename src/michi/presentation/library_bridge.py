"""QML bridge for library — observes LibraryService."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.library_service import LibraryService


class LibraryBridge(QObject):
    """Thin adapter: LibraryService state → QML properties, QML intent → service."""

    library_changed = Signal()

    def __init__(self, service: LibraryService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
        service.subscribe_changed(self._on_service_changed)

    def _on_service_changed(self) -> None:
        self.library_changed.emit()

    def _get_files(self) -> list[str]:
        return [t.display_name for t in self._service.state.visible_tracks]

    def _get_count(self) -> int:
        return len(self._service.state.visible_tracks)

    def _get_current_dir(self) -> str:
        return self._service.state.current_directory

    files = Property(list, _get_files, notify=library_changed)
    fileCount = Property(int, _get_count, notify=library_changed)
    currentDir = Property(str, _get_current_dir, notify=library_changed)

    @Slot(str)
    def scan(self, directory: str) -> None:
        self._service.scan(directory)

    @Slot(str)
    def search(self, query: str) -> None:
        self._service.search(query)

    @Slot(int)
    def activate(self, visible_index: int) -> None:
        self._service.activate(visible_index)
