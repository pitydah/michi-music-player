"""QML bridge for queue — observes QueueService."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.library_service import LibraryService
from michi.application.queue_service import QueueService


class QueueBridge(QObject):
    """Thin adapter: QueueService state → QML properties, QML intent → service."""

    queue_changed = Signal()

    def __init__(
        self,
        service: QueueService,
        library_service: LibraryService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._library_service = library_service
        service.subscribe_changed(self._on_service_changed)
        if library_service is not None:
            library_service.subscribe_changed(self._on_service_changed)

    def dispose(self) -> None:
        self._service.unsubscribe_changed(self._on_service_changed)
        if self._library_service is not None:
            self._library_service.unsubscribe_changed(self._on_service_changed)

    def _on_service_changed(self) -> None:
        self.queue_changed.emit()

    def _get_track_names(self) -> list[str]:
        return [t.title for t in self._service.state.tracks]

    def _get_track_rows(self) -> list[dict]:
        """Presentation-only queue projection.

        Queue identity and ordering remain owned by ``QueueService``.  The
        bridge only exposes stable, display-ready facts already present on
        each canonical queue entry.
        """
        rows = []
        for track in self._service.state.tracks:
            row = {
                "title": track.title or track.file_path.stem,
                "path": str(track.file_path),
            }
            if self._library_service is not None:
                ref = self._library_service.resolve_trackref(track.file_path)
                if ref is not None:
                    row.update(
                        artist=ref.artist,
                        album=ref.album,
                        durationMs=ref.duration_ms,
                    )
            rows.append(row)
        return rows

    def _get_current_index(self) -> int:
        return self._service.state.current_index

    def _get_count(self) -> int:
        return self._service.state.count

    def _get_has_next(self) -> bool:
        return self._service.has_next

    def _get_has_previous(self) -> bool:
        return self._service.has_previous

    def _get_repeat_mode(self) -> str:
        return self._service.state.repeat_mode.name

    def _get_shuffle_enabled(self) -> bool:
        return self._service.state.shuffle_enabled

    trackNames = Property(list, _get_track_names, notify=queue_changed)
    trackRows = Property(list, _get_track_rows, notify=queue_changed)
    currentIndex = Property(int, _get_current_index, notify=queue_changed)
    count = Property(int, _get_count, notify=queue_changed)
    hasNext = Property(bool, _get_has_next, notify=queue_changed)
    hasPrevious = Property(bool, _get_has_previous, notify=queue_changed)
    repeatMode = Property(str, _get_repeat_mode, notify=queue_changed)
    shuffleEnabled = Property(bool, _get_shuffle_enabled, notify=queue_changed)

    @Slot(int)
    def play_index(self, index: int) -> None:
        self._service.play_index(index)

    @Slot(int, int)
    def move_track(self, from_index: int, to_index: int) -> None:
        self._service.move(from_index, to_index)

    @Slot(int)
    def remove_track(self, index: int) -> None:
        self._service.remove(index)

    @Slot(int, str)
    def insert_at(self, index: int, file_path: str) -> None:
        """Restore a track at a position (undo for remove-from-queue)."""
        from pathlib import Path

        self._service.insert_at(index, Path(file_path))

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

    @Slot(bool)
    def set_shuffle_enabled(self, enabled: bool) -> None:
        self._service.set_shuffle_enabled(enabled)

    @Slot()
    def clear_queue(self) -> None:
        self._service.clear()
