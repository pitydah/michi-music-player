"""Qt Multimedia backend — implements AudioPort using QMediaPlayer."""

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from michi.application.ports import (
    AudioPort,
    AudioTransportUnavailableError,
)
from michi.domain.playback import PlaybackStatus

logger = logging.getLogger(__name__)

_PLAYBACK_STATE_TO_STATUS = {
    QMediaPlayer.PlaybackState.PlayingState: PlaybackStatus.PLAYING,
    QMediaPlayer.PlaybackState.PausedState: PlaybackStatus.PAUSED,
    QMediaPlayer.PlaybackState.StoppedState: PlaybackStatus.STOPPED,
}


class QtMultimediaBackend(AudioPort):
    """Infrastructure adapter wrapping Qt Multimedia."""

    def __init__(self) -> None:
        # LAZY native media objects: opening the engine must NOT enumerate
        # audio devices or create QtMultimedia objects. They are created on
        # first real media use. This also avoids QtMultimedia backend crashes
        # in headless engines that are opened but never used for playback.
        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None
        self._pending_volume = 100
        self._pending_muted = False
        self._pos_connected = False
        self._dur_connected = False
        self._error_connected = False
        self._eom: list[Callable[[], None]] = []
        self._pos: list[Callable[[int], None]] = []
        self._dur: list[Callable[[int], None]] = []
        self._acc: list[Callable[[Path], None]] = []
        self._rej: list[Callable[[Path, str], None]] = []
        self._pstate: list[Callable[[PlaybackStatus], None]] = []
        self._current_source: Path | None = None
        self._media_status_connected = False
        self._playback_state_connected = False
        self._closing = False  # R1-05: close in progress (retryable)
        # AR-21: source-generation provenance. Qt delivers signals serially
        # from one player, but a media-status event must never be attributed
        # to a source that is no longer current — every handler verifies
        # source identity against the player's ACTUAL current source.
        self._closed = False

    def _ensure_media(self) -> QMediaPlayer:
        """Create the native player on FIRST USE (never at construction)."""
        self._require_open()
        if self._player is None:
            player = QMediaPlayer()
            output = QAudioOutput()
            player.setAudioOutput(output)
            output.setVolume(self._pending_volume / 100.0)
            output.setMuted(self._pending_muted)
            self._player = player
            self._audio_output = output
            self._wire_all()
        return self._player

    def _wire_all(self) -> None:
        if self._player is None:
            return
        if self._eom or self._acc or self._rej:
            self._player.mediaStatusChanged.connect(self._on_media_status)
            self._media_status_connected = True
        if self._rej:
            self._player.errorOccurred.connect(self._on_error)
            self._error_connected = True
        if self._pstate:
            self._player.playbackStateChanged.connect(self._on_playback_state_changed)
            self._playback_state_connected = True
        if self._pos:
            self._player.positionChanged.connect(self._on_position_changed)
            self._pos_connected = True
        if self._dur:
            self._player.durationChanged.connect(self._on_duration_changed)
            self._dur_connected = True

    def _require_open(self) -> None:
        """KCR-008: a closed Qt runtime rejects every command/query with a
        typed AudioTransportUnavailableError — never silent success."""
        if self._closed:
            raise AudioTransportUnavailableError("Qt multimedia backend is closed")

    def load(self, file_path: Path) -> None:
        self._ensure_media()
        self._current_source = file_path
        self._player.setSource(QUrl.fromLocalFile(str(file_path)))

    def backend_state(self) -> str | None:
        if self._player is None:
            return None
        try:
            state = self._player.playbackState()
        except RuntimeError:
            return None
        return {
            QMediaPlayer.PlayingState: "playing",
            QMediaPlayer.PausedState: "paused",
            QMediaPlayer.StoppedState: "stopped",
        }.get(state)

    def play(self) -> None:
        self._ensure_media().play()

    def pause(self) -> None:
        self._ensure_media().pause()

    def resume(self) -> None:
        self._ensure_media().play()

    def stop(self) -> None:
        self._require_open()
        if self._player is None:
            return
        if self._player.playbackState() != QMediaPlayer.StoppedState:
            self._player.stop()

    def close(self) -> None:
        """R1-05: retryable, failure-atomic release. `_closed == True` only
        after the whole release chain completed; a failure (injectable via
        the player seam) raises with the backend fully reachable and
        `_closed` still False so a SECOND close retries the remaining
        teardown."""
        if self._closed:
            return
        if self._player is None:
            self._closed = True
            self._current_source = None
            return
        self._closing = True
        self._player.stop()
        self._player.setSource(QUrl())
        self._current_source = None
        if self._media_status_connected:
            self._player.mediaStatusChanged.disconnect(self._on_media_status)
            self._media_status_connected = False
        if self._playback_state_connected:
            self._player.playbackStateChanged.disconnect(
                self._on_playback_state_changed
            )
            self._playback_state_connected = False
        if self._rej:
            # only disconnect when it was actually connected (lazy wiring)
            try:
                self._player.errorOccurred.disconnect(self._on_error)
            except (RuntimeError, TypeError):
                pass
        # ONLY after the release chain completed:
        self._closed = True
        self._closing = False

    def set_volume(self, value: int) -> None:
        self._require_open()
        self._pending_volume = int(value)
        if self._audio_output is not None:
            self._audio_output.setVolume(self._pending_volume / 100.0)

    def set_muted(self, muted: bool) -> None:
        self._require_open()
        self._pending_muted = bool(muted)
        if self._audio_output is not None:
            self._audio_output.setMuted(self._pending_muted)

    def seek(self, position_ms: int) -> None:
        self._ensure_media().setPosition(position_ms)

    def position(self) -> int:
        return self._ensure_media().position()

    def duration(self) -> int:
        return self._ensure_media().duration()

    # ── media status wiring (shared by eom/accepted/rejected) ─────

    def _ensure_media_status_wired(self) -> None:
        if self._player is None:
            return
        if not self._media_status_connected and (self._eom or self._acc or self._rej):
            self._player.mediaStatusChanged.connect(self._on_media_status)
            self._media_status_connected = True

    def _ensure_media_status_unwired(self) -> None:
        if self._player is None:
            return
        if self._media_status_connected and not (self._eom or self._acc or self._rej):
            self._player.mediaStatusChanged.disconnect(self._on_media_status)
            self._media_status_connected = False

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        # AR-21 provenance: only events for the CURRENT source are
        # authoritative — the player emits serially for its current source,
        # and this guard makes a stale attribution impossible (a queued
        # event for a superseded source would fail the identity check).
        if self._current_source is None:
            return
        current = self._player.source().toLocalFile()
        if current and Path(current) != self._current_source:
            return  # stale event for a source that is no longer current
        if status == QMediaPlayer.EndOfMedia:
            for cb in list(self._eom):
                cb()
        elif status == QMediaPlayer.LoadedMedia:
            for cb in list(self._acc):
                cb(self._current_source)
        elif status == QMediaPlayer.InvalidMedia:
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
        if was_empty and self._player is not None:
            self._player.errorOccurred.connect(self._on_error)
            self._error_connected = True
        self._ensure_media_status_wired()

    def unsubscribe_media_rejected(self, cb: Callable[[Path, str], None]) -> None:
        if cb not in self._rej:
            return
        self._rej.remove(cb)
        if not self._rej and self._player is not None and self._error_connected:
            self._player.errorOccurred.disconnect(self._on_error)
            self._error_connected = False
        self._ensure_media_status_unwired()

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        logger.warning("Media error: %s", error_string)
        if self._current_source is None:
            return
        for cb in list(self._rej):
            cb(self._current_source, error_string)

    # ── playback state (idempotent) ───────────────────────────────
    #
    # playbackStateChanged carries no source identity: state events apply
    # to the player's current source. Qt forces StoppedState on setSource
    # and delivers signals from one player serially, so LoadedMedia
    # (which implies StoppedState per the Qt docs) precedes PlayingState.

    def _ensure_playback_state_wired(self) -> None:
        if self._player is None:
            return
        if not self._playback_state_connected and self._pstate:
            self._player.playbackStateChanged.connect(self._on_playback_state_changed)
            self._playback_state_connected = True

    def _ensure_playback_state_unwired(self) -> None:
        if self._player is None:
            return
        if self._playback_state_connected and not self._pstate:
            self._player.playbackStateChanged.disconnect(
                self._on_playback_state_changed
            )
            self._playback_state_connected = False

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        status = _PLAYBACK_STATE_TO_STATUS.get(state)
        if status is None:
            return
        for cb in list(self._pstate):
            cb(status)

    def subscribe_playback_state_changed(
        self, cb: Callable[[PlaybackStatus], None]
    ) -> None:
        if cb in self._pstate:
            return
        self._pstate.append(cb)
        self._ensure_playback_state_wired()

    def unsubscribe_playback_state_changed(
        self, cb: Callable[[PlaybackStatus], None]
    ) -> None:
        if cb not in self._pstate:
            return
        self._pstate.remove(cb)
        self._ensure_playback_state_unwired()

    # ── position (idempotent) ────────────────────────────────────

    def subscribe_position_changed(self, cb: Callable[[int], None]) -> None:
        if cb in self._pos:
            return
        was_empty = not self._pos
        self._pos.append(cb)
        if was_empty and self._player is not None:
            self._player.positionChanged.connect(self._on_position_changed)
            self._pos_connected = True

    def unsubscribe_position_changed(self, cb: Callable[[int], None]) -> None:
        if cb not in self._pos:
            return
        self._pos.remove(cb)
        if not self._pos and self._player is not None and self._pos_connected:
            self._player.positionChanged.disconnect(self._on_position_changed)
            self._pos_connected = False

    def _on_position_changed(self, position_ms: int) -> None:
        for cb in list(self._pos):
            cb(position_ms)

    # ── duration (idempotent) ────────────────────────────────────

    def subscribe_duration_changed(self, cb: Callable[[int], None]) -> None:
        if cb in self._dur:
            return
        was_empty = not self._dur
        self._dur.append(cb)
        if was_empty and self._player is not None:
            self._player.durationChanged.connect(self._on_duration_changed)
            self._dur_connected = True

    def unsubscribe_duration_changed(self, cb: Callable[[int], None]) -> None:
        if cb not in self._dur:
            return
        self._dur.remove(cb)
        if not self._dur and self._player is not None and self._dur_connected:
            self._player.durationChanged.disconnect(self._on_duration_changed)
            self._dur_connected = False

    def _on_duration_changed(self, duration_ms: int) -> None:
        for cb in list(self._dur):
            cb(duration_ms)
