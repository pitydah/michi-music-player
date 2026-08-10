"""Playback use case — the single mutation authority for PlaybackState."""

from pathlib import Path

from michi.application.ports import AudioPort
from michi.domain.playback import PlaybackState, PlaybackStatus


class PlaybackService:
    """Sole canonical authority over PlaybackState. QML never mutates directly."""

    def __init__(self, audio_port: AudioPort) -> None:
        self._audio = audio_port
        self._state = PlaybackState()

    @property
    def state(self) -> PlaybackState:
        return self._state

    def load_and_play(self, file_path: Path) -> None:
        self._audio.load(file_path)
        self._audio.play()
        self._state.status = PlaybackStatus.PLAYING
        self._state.file_path = file_path
        self._state.error_message = None

    def play(self) -> None:
        self._audio.play()
        self._state.status = PlaybackStatus.PLAYING

    def pause(self) -> None:
        self._audio.pause()
        self._state.status = PlaybackStatus.PAUSED

    def resume(self) -> None:
        self._audio.resume()
        self._state.status = PlaybackStatus.PLAYING

    def stop(self) -> None:
        self._audio.stop()
        self._state.status = PlaybackStatus.STOPPED
        self._state.position_ms = 0

    def set_volume(self, value: int) -> None:
        clamped = max(0, min(100, value))
        self._state.volume = clamped
        self._audio.set_volume(clamped)

    def set_muted(self, muted: bool) -> None:
        self._state.muted = muted
        self._audio.set_muted(muted)

    def update_position(self, position_ms: int, duration_ms: int) -> None:
        self._state.position_ms = position_ms
        self._state.duration_ms = duration_ms
