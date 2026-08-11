"""Playback use case — the single mutation authority for PlaybackState."""

from collections.abc import Callable
from pathlib import Path

from michi.application.ports import AudioPort
from michi.domain.playback import PlaybackState, PlaybackStatus


class PlaybackService:
    """Sole canonical authority over PlaybackState. Publishes changes."""

    def __init__(self, audio_port: AudioPort) -> None:
        self._audio = audio_port
        self._state = PlaybackState()
        self._subscribers: list[Callable[[], None]] = []

    @property
    def state(self) -> PlaybackState:
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

    def restore_volume(self, volume: int, muted: bool) -> None:
        clamped = max(0, min(100, volume))
        self._state.volume = clamped
        self._state.muted = muted
        self._audio.set_volume(clamped)
        self._audio.set_muted(muted)

    def report_error(self, message: str) -> None:
        self._state.error_message = message
        self._notify()

    def load_and_play(self, file_path: Path) -> None:
        self._audio.load(file_path)
        self._audio.play()
        self._state.status = PlaybackStatus.PLAYING
        self._state.file_path = file_path
        self._state.error_message = None
        self._notify()

    def play(self) -> None:
        self._audio.play()
        self._state.status = PlaybackStatus.PLAYING
        self._notify()

    def pause(self) -> None:
        self._audio.pause()
        self._state.status = PlaybackStatus.PAUSED
        self._notify()

    def resume(self) -> None:
        self._audio.resume()
        self._state.status = PlaybackStatus.PLAYING
        self._notify()

    def stop(self) -> None:
        self._audio.stop()
        self._state.status = PlaybackStatus.STOPPED
        self._state.position_ms = 0
        self._notify()

    def seek(self, position_ms: int) -> None:
        self._audio.seek(position_ms)
        self._state.position_ms = position_ms
        self._notify()

    def set_volume(self, value: int) -> None:
        clamped = max(0, min(100, value))
        self._state.volume = clamped
        self._audio.set_volume(clamped)
        self._notify()

    def set_muted(self, muted: bool) -> None:
        self._state.muted = muted
        self._audio.set_muted(muted)
        self._notify()

    def update_position(self, position_ms: int, duration_ms: int) -> None:
        changed = (
            self._state.position_ms != position_ms
            or self._state.duration_ms != duration_ms
        )
        self._state.position_ms = position_ms
        self._state.duration_ms = duration_ms
        if changed:
            self._notify()

    def snapshot_volume(self) -> tuple[int, bool]:
        return (self._state.volume, self._state.muted)

    def switch_track(self, file_path: Path) -> None:
        self._audio.stop()
        self._state.status = PlaybackStatus.STOPPED
        self._state.error_message = None
        self.load_and_play(file_path)
