"""Qt Multimedia backend — implements AudioPort using QMediaPlayer."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from michi.application.ports import AudioPort


class QtMultimediaBackend(AudioPort):
    """Infrastructure adapter wrapping Qt Multimedia. Owns the player instance."""

    def __init__(self) -> None:
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)
        self._eom_callbacks: list[Callable[[], None]] = []
        self._pos_callbacks: list[Callable[[int, int], None]] = []
        self._err_callbacks: list[Callable[[str], None]] = []

    def load(self, file_path: Path) -> None:
        self._player.setSource(QUrl.fromLocalFile(str(file_path)))

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def resume(self) -> None:
        self._player.play()

    def stop(self) -> None:
        if self._player.playbackState() != QMediaPlayer.StoppedState:
            self._player.stop()

    def set_volume(self, value: int) -> None:
        self._audio_output.setVolume(value / 100.0)

    def set_muted(self, muted: bool) -> None:
        self._audio_output.setMuted(muted)

    def seek(self, position_ms: int) -> None:
        self._player.setPosition(position_ms)

    def position(self) -> int:
        return self._player.position()

    def duration(self) -> int:
        return self._player.duration()

    # ── end-of-media subscription ──────────────────────────────────

    def subscribe_end_of_media(self, callback: Callable[[], None]) -> None:
        if not self._eom_callbacks:
            self._player.mediaStatusChanged.connect(self._on_media_status)
        self._eom_callbacks.append(callback)

    def unsubscribe_end_of_media(self, callback: Callable[[], None]) -> None:
        self._eom_callbacks.remove(callback)
        if not self._eom_callbacks:
            self._player.mediaStatusChanged.disconnect(self._on_media_status)

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.EndOfMedia:
            for cb in list(self._eom_callbacks):
                cb()

    # ── position subscription ──────────────────────────────────────

    def subscribe_position_changed(self, callback: Callable[[int, int], None]) -> None:
        if not self._pos_callbacks:
            self._player.positionChanged.connect(self._on_position_changed)
        self._pos_callbacks.append(callback)

    def unsubscribe_position_changed(
        self, callback: Callable[[int, int], None]
    ) -> None:
        self._pos_callbacks.remove(callback)
        if not self._pos_callbacks:
            self._player.positionChanged.disconnect(self._on_position_changed)

    def _on_position_changed(self, position_ms: int) -> None:
        dur = self._player.duration()
        for cb in list(self._pos_callbacks):
            cb(position_ms, dur)

    # ── error subscription ─────────────────────────────────────────

    def subscribe_error(self, callback: Callable[[str], None]) -> None:
        if not self._err_callbacks:
            self._player.errorOccurred.connect(self._on_error)
        self._err_callbacks.append(callback)

    def unsubscribe_error(self, callback: Callable[[str], None]) -> None:
        self._err_callbacks.remove(callback)
        if not self._err_callbacks:
            self._player.errorOccurred.disconnect(self._on_error)

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        for cb in list(self._err_callbacks):
            cb(error_string)
