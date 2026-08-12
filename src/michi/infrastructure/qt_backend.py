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
        self._acc: list[Callable[[Path], None]] = []
        self._rej: list[Callable[[Path, str], None]] = []
        self._current_source: Path | None = None
        self._media_status_connected = False

    def load(self, file_path: Path) -> None:
        self._current_source = file_path
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

    # ── media status wiring (shared by eom/accepted/rejected) ─────

    def _ensure_media_status_wired(self) -> None:
        if not self._media_status_connected and (self._eom or self._acc or self._rej):
            self._player.mediaStatusChanged.connect(self._on_media_status)
            self._media_status_connected = True

    def _ensure_media_status_unwired(self) -> None:
        if self._media_status_connected and not (self._eom or self._acc or self._rej):
            self._player.mediaStatusChanged.disconnect(self._on_media_status)
            self._media_status_connected = False

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.EndOfMedia:
            for cb in list(self._eom):
                cb()
        elif status == QMediaPlayer.LoadedMedia and self._current_source is not None:
            for cb in list(self._acc):
                cb(self._current_source)
        elif status == QMediaPlayer.InvalidMedia and self._current_source is not None:
            for cb in list(self._rej):
                cb(self._current_source, "invalid media")

    # ── end-of-media (idempotent) ────────────────────────────────

    def subscribe_end_of_media(self, cb: Callable[[], None]) -> None:
        if cb in self._eom:
            return
        self._eom.append(cb)
        self._ensure_media_status_wired()

    def unsubscribe_end_of_media(self, cb: Callable[[], None]) -> None:
        if cb not in self._eom:
            return
        self._eom.remove(cb)
        self._ensure_media_status_unwired()

    # ── media accepted (idempotent) ────────────────────────────────

    def subscribe_media_accepted(self, cb: Callable[[Path], None]) -> None:
        if cb in self._acc:
            return
        self._acc.append(cb)
        self._ensure_media_status_wired()

    def unsubscribe_media_accepted(self, cb: Callable[[Path], None]) -> None:
        if cb not in self._acc:
            return
        self._acc.remove(cb)
        self._ensure_media_status_unwired()

    # ── media rejected (idempotent) ────────────────────────────────

    def subscribe_media_rejected(self, cb: Callable[[Path, str], None]) -> None:
        if cb in self._rej:
            return
        was_empty = not self._rej
        self._rej.append(cb)
        if was_empty:
            self._player.errorOccurred.connect(self._on_error)
        self._ensure_media_status_wired()

    def unsubscribe_media_rejected(self, cb: Callable[[Path, str], None]) -> None:
        if cb not in self._rej:
            return
        self._rej.remove(cb)
        if not self._rej:
            self._player.errorOccurred.disconnect(self._on_error)
        self._ensure_media_status_unwired()

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        logger.warning("Media error: %s", error_string)
        if self._current_source is None:
            return
        for cb in list(self._rej):
            cb(self._current_source, error_string)

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
