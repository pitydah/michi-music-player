"""QML bridge for queue — observes QueueService CONTENT (M4-R1).

QueueBridge is a projection of Queue content ONLY. Playback/navigation
intents (play_index/next/previous/repeat/shuffle/currentIndex) belong to
PlaybackSessionBridge. If the Queue UI needs a playing-row highlight it
derives it from playbackSession.contextType == "queue" →
playbackSession.currentIndex (never from QueueState)."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.library_service import LibraryService
from michi.application.queue_service import QueueService
from michi.presentation.track_projection import (
    project_track_row,
    project_unavailable_track,
)


class QueueBridge(QObject):
    """Thin adapter: QueueService content → QML properties, QML intent →
    service content mutation."""

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
            row = project_unavailable_track(track.file_path)
            if track.title:
                row["title"] = track.title
            if self._library_service is not None:
                ref = self._library_service.resolve_trackref(track.file_path)
                if ref is not None:
                    row = project_track_row(ref)
            rows.append(row)
        return rows

    def _get_count(self) -> int:
        return self._service.state.count

    trackNames = Property(list, _get_track_names, notify=queue_changed)
    trackRows = Property(list, _get_track_rows, notify=queue_changed)
    count = Property(int, _get_count, notify=queue_changed)

    @Slot(int, int)
    def move_track(self, from_index: int, to_index: int) -> None:
        self._service.move(from_index, to_index)

    @Slot(int)
    def remove_track(self, index: int) -> None:
        self._service.remove(index)

    @Slot(str)
    def add_file(self, file_path: str) -> None:
        from pathlib import Path

        self._service.add(Path(file_path))

    @Slot()
    def clear_queue(self) -> None:
        self._service.clear()
