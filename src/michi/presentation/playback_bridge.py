"""QML bridge — exposes PlaybackState and receives user intents.

QML observes state read-only via Qt properties.
QML sends intents via invokable methods. Bridge delegates to Application.
"""

from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from michi.application.playback_service import PlaybackService
from michi.domain.playback import PlaybackStatus


class PlaybackBridge(QObject):
    """Thin adapter: QML intent → Application Service → Domain State → QML observation."""

    _status_map = {
        PlaybackStatus.STOPPED: "stopped",
        PlaybackStatus.PLAYING: "playing",
        PlaybackStatus.PAUSED: "paused",
    }

    state_changed = Signal()

    def __init__(self, service: PlaybackService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service

    def _get_status(self) -> str:
        return self._status_map.get(self._service.state.status, "stopped")

    def _get_file_name(self) -> str:
        path = self._service.state.file_path
        return path.name if path else ""

    def _get_position(self) -> int:
        return self._service.state.position_ms // 1000

    def _get_duration(self) -> int:
        return self._service.state.duration_ms // 1000

    def _get_volume(self) -> int:
        return self._service.state.volume

    def _get_muted(self) -> bool:
        return self._service.state.muted

    def notify_state(self) -> None:
        """Call after service changes state to push to QML."""
        self.state_changed.emit()

    # Qt properties — read-only from QML
    status = Property(str, _get_status, notify=state_changed)
    fileName = Property(str, _get_file_name, notify=state_changed)
    position = Property(int, _get_position, notify=state_changed)
    duration = Property(int, _get_duration, notify=state_changed)
    volume = Property(int, _get_volume, notify=state_changed)
    muted = Property(bool, _get_muted, notify=state_changed)

    @Slot(str)
    def play_file(self, file_path: str) -> None:
        self._service.load_and_play(Path(file_path))
        self.state_changed.emit()

    @Slot()
    def play(self) -> None:
        self._service.play()
        self.state_changed.emit()

    @Slot()
    def pause(self) -> None:
        self._service.pause()
        self.state_changed.emit()

    @Slot()
    def resume(self) -> None:
        self._service.resume()
        self.state_changed.emit()

    @Slot()
    def stop(self) -> None:
        self._service.stop()
        self.state_changed.emit()

    @Slot(int)
    def set_volume(self, value: int) -> None:
        self._service.set_volume(value)
        self.state_changed.emit()

    @Slot(bool)
    def set_muted(self, muted: bool) -> None:
        self._service.set_muted(muted)
        self.state_changed.emit()
