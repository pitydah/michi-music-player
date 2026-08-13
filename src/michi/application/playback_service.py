"""Playback use case — the single mutation authority for PlaybackState."""

from collections.abc import Callable
from pathlib import Path

from michi.application.ports import AudioPort
from michi.domain.playback import PlaybackState, PlaybackStatus


class PlaybackService:
    """Sole canonical authority over PlaybackState. Publishes changes.

    Playback acceptance is asynchronous: `load_and_play` only *requests* a
    candidate. The candidate becomes canonical when the backend reports media
    acceptance (`subscribe_media_accepted`); it is dropped when the backend
    reports rejection. Until then the service owns the pending candidate
    locally and PlaybackState reflects the last committed track as STOPPED.

    Acceptance commits track identity only — never PLAYING. LoadedMedia means
    the media is loaded while the player is in the StoppedState; actual
    playback state follows the backend `playbackStateChanged` signal, which
    this service self-subscribes to and maps truthfully (PlayingState →
    PLAYING, PausedState → PAUSED, StoppedState → STOPPED, idempotently).

    Two minimal guards keep stale lifecycle events honest:
    - `_intent`: True after a successful request (also armed by play()/
      resume()), set False by `stop()` and rejection. Active state events
      (PLAYING, PAUSED) are applied only while intent holds; STOPPED is
      always applied (idempotently), so a late PlayingState cannot
      resurrect playback after stop/rejection.
    - `_accepted`: True only once the current candidate has been accepted,
      reset on each new request and on rejection. PLAYING is never published
      for a track whose identity was not committed — stale PlayingState
      events from superseded candidates are ignored.

    Commands express intent only: play()/pause()/resume() never mutate
    PlaybackStatus or notify; PLAYING/PAUSED/STOPPED are published
    exclusively from backend state events. `stop()` is the single
    optimistic exception (safety command: STOPPED immediately).
    """

    def __init__(self, audio_port: AudioPort) -> None:
        self._audio = audio_port
        self._state = PlaybackState()
        self._subscribers: list[Callable[[], None]] = []
        self._pending_path: Path | None = None
        self._pending_on_accepted: Callable[[Path], None] | None = None
        self._intent = False
        self._accepted = False
        self._audio.subscribe_media_accepted(self._on_media_accepted)
        self._audio.subscribe_media_rejected(self._on_media_rejected)
        self._audio.subscribe_playback_state_changed(self._on_playback_state_changed)

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
        self._audio.set_volume(clamped)
        self._audio.set_muted(muted)
        self._state.volume = clamped
        self._state.muted = muted

    def report_error(self, message: str) -> None:
        self._state.error_message = message
        self._notify()

    def load_and_play(
        self, file_path: Path, on_accepted: Callable[[Path], None] | None = None
    ) -> None:
        """Request playback of a candidate. Commits nothing synchronously.

        The candidate becomes canonical only when the backend reports media
        acceptance for its path; `on_accepted` is then invoked exactly once
        with the accepted path. A new request supersedes the previous pending
        candidate; `stop()` invalidates it. Synchronous backend failures
        propagate, leave no pending candidate behind, and restore the
        previous intent/acceptance flags.
        """
        previous_intent = self._intent
        previous_accepted = self._accepted
        self._pending_path = file_path
        self._pending_on_accepted = on_accepted
        self._accepted = False
        self._intent = True
        try:
            self._audio.load(file_path)
            self._audio.play()
        except Exception:
            self._pending_path = None
            self._pending_on_accepted = None
            self._intent = previous_intent
            self._accepted = previous_accepted
            raise
        self._state.status = PlaybackStatus.STOPPED
        self._state.error_message = None
        self._notify()

    def _on_media_accepted(self, file_path: Path) -> None:
        if self._pending_path is None or file_path != self._pending_path:
            return
        on_accepted = self._pending_on_accepted
        self._pending_path = None
        self._pending_on_accepted = None
        self._state.file_path = file_path
        self._state.error_message = None
        self._accepted = True
        self._notify()
        if on_accepted is not None:
            on_accepted(file_path)

    def _on_media_rejected(self, file_path: Path, message: str) -> None:
        if self._pending_path is not None and file_path == self._pending_path:
            self._pending_path = None
            self._pending_on_accepted = None
            self._intent = False
            self._accepted = False
            self._state.status = PlaybackStatus.STOPPED
            self._state.error_message = message
            self._notify()
        elif (
            self._state.file_path is not None
            and file_path == self._state.file_path
            and (
                self._state.status != PlaybackStatus.STOPPED
                or self._state.error_message != message
            )
        ):
            self._intent = False
            self._accepted = False
            self._state.status = PlaybackStatus.STOPPED
            self._state.error_message = message
            self._notify()
        # Anything else is a stale, unknown, or duplicate callback: ignored.

    def _on_playback_state_changed(self, status: PlaybackStatus) -> None:
        if not self._intent and status != PlaybackStatus.STOPPED:
            return
        if status == PlaybackStatus.PLAYING and not self._accepted:
            return
        if self._state.status == status:
            return
        self._state.status = status
        self._notify()

    def play(self) -> None:
        previous_intent = self._intent
        self._intent = True
        try:
            self._audio.play()
        except Exception:
            self._intent = previous_intent
            raise

    def pause(self) -> None:
        self._audio.pause()

    def resume(self) -> None:
        previous_intent = self._intent
        self._intent = True
        try:
            self._audio.resume()
        except Exception:
            self._intent = previous_intent
            raise

    def stop(self) -> None:
        self._pending_path = None
        self._pending_on_accepted = None
        self._intent = False
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
        self._audio.set_volume(clamped)
        self._state.volume = clamped
        self._notify()

    def set_muted(self, muted: bool) -> None:
        self._audio.set_muted(muted)
        self._state.muted = muted
        self._notify()

    def update_position(self, position_ms: int) -> None:
        if self._state.position_ms != position_ms:
            self._state.position_ms = position_ms
            self._notify()

    def update_duration(self, duration_ms: int) -> None:
        if self._state.duration_ms != duration_ms:
            self._state.duration_ms = duration_ms
            self._notify()

    def snapshot_volume(self) -> tuple[int, bool]:
        return (self._state.volume, self._state.muted)

    def switch_track(self, file_path: Path) -> None:
        self._audio.stop()
        self._state.status = PlaybackStatus.STOPPED
        self._state.error_message = None
        self.load_and_play(file_path)
