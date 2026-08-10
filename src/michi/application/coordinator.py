"""Playback coordination — connects audio events to application logic."""

from collections.abc import Callable

from michi.application.playback_service import PlaybackService
from michi.application.ports import AudioPort
from michi.application.queue_service import QueueService


class PlaybackCoordinator:
    """Wires audio-port events to application services.

    EndOfMedia → advance queue or stop.
    Position changes → update playback state.
    Errors → update playback state.
    """

    def __init__(
        self,
        audio_port: AudioPort,
        queue_service: QueueService,
        playback_service: PlaybackService,
    ) -> None:
        self._audio = audio_port
        self._queue = queue_service
        self._playback = playback_service
        self._on_state_change: Callable[[], None] | None = None

    def on_state_change(self, callback: Callable[[], None]) -> None:
        self._on_state_change = callback

    def start(self) -> None:
        self._audio.subscribe_end_of_media(self._on_track_ended)
        self._audio.subscribe_position_changed(self._on_position_changed)
        self._audio.subscribe_error(self._on_error)

    def stop(self) -> None:
        self._audio.unsubscribe_end_of_media(self._on_track_ended)
        self._audio.unsubscribe_position_changed(self._on_position_changed)
        self._audio.unsubscribe_error(self._on_error)

    def _notify(self) -> None:
        if self._on_state_change:
            self._on_state_change()

    def _on_track_ended(self) -> None:
        if self._queue.state.has_next:
            self._queue.next()
        else:
            self._playback.stop()  # authoritative → STOPPED, position=0
        self._notify()

    def _on_position_changed(self, position_ms: int, duration_ms: int) -> None:
        self._playback.update_position(position_ms, duration_ms)
        self._notify()

    def _on_error(self, message: str) -> None:
        self._playback.state.error_message = message
        self._notify()
