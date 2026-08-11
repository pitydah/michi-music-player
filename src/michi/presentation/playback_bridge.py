"""QML bridge for playback — observes PlaybackService."""

from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.playback_service import PlaybackService
from michi.domain.playback import PlaybackStatus


class PlaybackBridge(QObject):
    """Thin adapter: PlaybackService state → QML properties, QML intent → service."""

    _status_map = {
        PlaybackStatus.STOPPED: "stopped",
        PlaybackStatus.PLAYING: "playing",
        PlaybackStatus.PAUSED: "paused",
    }

    state_changed = Signal()

    def __init__(self, service: PlaybackService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
        service.subscribe_changed(self._on_service_changed)

    def dispose(self) -> None:
        self._service.unsubscribe_changed(self._on_service_changed)

    def _on_service_changed(self) -> None:
        self.state_changed.emit()

    def _get_status(self) -> str:
        return self._status_map.get(self._service.state.status, "stopped")

    def _get_file_name(self) -> str:
        p = self._service.state.file_path
        return p.name if p else ""

    def _get_position(self) -> int:
        return self._service.state.position_ms // 1000

    def _get_duration(self) -> int:
        return self._service.state.duration_ms // 1000

    def _get_volume(self) -> int:
        return self._service.state.volume

    def _get_muted(self) -> bool:
        return self._service.state.muted

    def _get_error(self) -> str:
        return self._service.state.error_message or ""

    status = Property(str, _get_status, notify=state_changed)
    fileName = Property(str, _get_file_name, notify=state_changed)
    position = Property(int, _get_position, notify=state_changed)
    duration = Property(int, _get_duration, notify=state_changed)
    volume = Property(int, _get_volume, notify=state_changed)
    muted = Property(bool, _get_muted, notify=state_changed)
    errorMessage = Property(str, _get_error, notify=state_changed)

    @Slot(str)
    def play_file(self, file_path: str) -> None:
        self._service.load_and_play(Path(file_path))

    @Slot()
    def play(self) -> None:
        self._service.play()

    @Slot()
    def pause(self) -> None:
        self._service.pause()

    @Slot()
    def resume(self) -> None:
        self._service.resume()

    @Slot()
    def stop(self) -> None:
        self._service.stop()

    @Slot(int)
    def seek_seconds(self, seconds: int) -> None:
        self._service.seek(seconds * 1000)

    @Slot(int)
    def set_volume(self, value: int) -> None:
        self._service.set_volume(value)

    @Slot(bool)
    def set_muted(self, muted: bool) -> None:
        self._service.set_muted(muted)

    @Slot(str)
    def switch_track(self, file_path: str) -> None:
        self._service.switch_track(Path(file_path))
