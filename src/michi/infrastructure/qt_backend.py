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
        self._end_callbacks: list[Callable[[], None]] = []

    def load(self, file_path: Path) -> None:
        url = QUrl.fromLocalFile(str(file_path))
        self._player.setSource(url)

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

    def on_end_of_media(self, callback: Callable[[], None]) -> None:
        """Register a callback. Translates Qt signal to pure Python callback."""
        if not self._end_callbacks:
            self._player.mediaStatusChanged.connect(self._on_media_status)
        self._end_callbacks.append(callback)

    def remove_end_of_media_callbacks(self) -> None:
        self._end_callbacks.clear()
        try:
            self._player.mediaStatusChanged.disconnect(self._on_media_status)
        except (TypeError, RuntimeError):
            pass

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.EndOfMedia:
            for cb in self._end_callbacks:
                cb()
