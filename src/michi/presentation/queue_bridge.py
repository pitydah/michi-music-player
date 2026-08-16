"""QML bridge for queue — observes QueueService."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.queue_service import QueueService


class QueueBridge(QObject):
    """Thin adapter: QueueService state → QML properties, QML intent → service."""

    queue_changed = Signal()

    def __init__(self, service: QueueService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
        service.subscribe_changed(self._on_service_changed)

    def dispose(self) -> None:
        self._service.unsubscribe_changed(self._on_service_changed)

    def _on_service_changed(self) -> None:
        self.queue_changed.emit()

    def _get_track_names(self) -> list[str]:
        return [t.title for t in self._service.state.tracks]

    def _get_current_index(self) -> int:
        return self._service.state.current_index

    def _get_count(self) -> int:
        return self._service.state.count

    def _get_has_next(self) -> bool:
        return self._service.state.has_next

    def _get_has_previous(self) -> bool:
        return self._service.state.has_previous

    def _get_repeat_mode(self) -> str:
        return self._service.state.repeat_mode.name

    trackNames = Property(list, _get_track_names, notify=queue_changed)
    currentIndex = Property(int, _get_current_index, notify=queue_changed)
    count = Property(int, _get_count, notify=queue_changed)
    hasNext = Property(bool, _get_has_next, notify=queue_changed)
    hasPrevious = Property(bool, _get_has_previous, notify=queue_changed)
    repeatMode = Property(str, _get_repeat_mode, notify=queue_changed)

    @Slot(int)
    def play_index(self, index: int) -> None:
        self._service.play_index(index)

    @Slot()
    def next_track(self) -> None:
        self._service.next()

    @Slot()
    def previous_track(self) -> None:
        self._service.previous()

    @Slot(str)
    def add_file(self, file_path: str) -> None:
        from pathlib import Path

        self._service.add(Path(file_path))

    @Slot(str)
    def set_repeat_mode(self, mode_name: str) -> None:
        from michi.domain.queue import RepeatMode

        try:
            mode = RepeatMode[mode_name.upper()]
        except KeyError:
            return
        self._service.set_repeat_mode(mode)

    @Slot()
    def clear_queue(self) -> None:
        self._service.clear()
