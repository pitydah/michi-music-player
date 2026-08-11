"""Qt Multimedia backend — implements AudioPort using QMediaPlayer."""

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from michi.application.ports import AudioPort

logger = logging.getLogger(__name__)


class QtMultimediaBackend(AudioPort):
    """Infrastructure adapter wrapping Qt Multimedia."""

    def __init__(self) -> None:
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)
        self._eom: list[Callable[[], None]] = []
        self._pos: list[Callable[[int], None]] = []
        self._dur: list[Callable[[int], None]] = []
        self._err: list[Callable[[str], None]] = []

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

    # ── end-of-media (idempotent) ────────────────────────────────

    def subscribe_end_of_media(self, cb: Callable[[], None]) -> None:
        if cb in self._eom:
            return
        was_empty = not self._eom
        self._eom.append(cb)
        if was_empty:
            self._player.mediaStatusChanged.connect(self._on_media_status)

    def unsubscribe_end_of_media(self, cb: Callable[[], None]) -> None:
        if cb not in self._eom:
            return
        self._eom.remove(cb)
        if not self._eom:
            self._player.mediaStatusChanged.disconnect(self._on_media_status)

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.EndOfMedia:
            for cb in list(self._eom):
                cb()

    # ── position (idempotent) ────────────────────────────────────

    def subscribe_position_changed(self, cb: Callable[[int], None]) -> None:
        if cb in self._pos:
            return
        was_empty = not self._pos
        self._pos.append(cb)
        if was_empty:
            self._player.positionChanged.connect(self._on_position_changed)

    def unsubscribe_position_changed(self, cb: Callable[[int], None]) -> None:
        if cb not in self._pos:
            return
        self._pos.remove(cb)
        if not self._pos:
            self._player.positionChanged.disconnect(self._on_position_changed)

    def _on_position_changed(self, position_ms: int) -> None:
        for cb in list(self._pos):
            cb(position_ms)

    # ── duration (idempotent) ────────────────────────────────────

    def subscribe_duration_changed(self, cb: Callable[[int], None]) -> None:
        if cb in self._dur:
            return
        was_empty = not self._dur
        self._dur.append(cb)
        if was_empty:
            self._player.durationChanged.connect(self._on_duration_changed)

    def unsubscribe_duration_changed(self, cb: Callable[[int], None]) -> None:
        if cb not in self._dur:
            return
        self._dur.remove(cb)
        if not self._dur:
            self._player.durationChanged.disconnect(self._on_duration_changed)

    def _on_duration_changed(self, duration_ms: int) -> None:
        for cb in list(self._dur):
            cb(duration_ms)

    # ── error (idempotent) ───────────────────────────────────────

    def subscribe_error(self, cb: Callable[[str], None]) -> None:
        if cb in self._err:
            return
        was_empty = not self._err
        self._err.append(cb)
        if was_empty:
            self._player.errorOccurred.connect(self._on_error)

    def unsubscribe_error(self, cb: Callable[[str], None]) -> None:
        if cb not in self._err:
            return
        self._err.remove(cb)
        if not self._err:
            self._player.errorOccurred.disconnect(self._on_error)

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        logger.warning("Media error: %s", error_string)
        for cb in list(self._err):
            cb(error_string)
