"""Playback coordination — connects audio events to application logic."""

from michi.application.playback_service import PlaybackService
from michi.application.ports import AudioPort
from michi.application.queue_service import QueueService


class PlaybackCoordinator:
    """Wires audio-port events to application services. Idempotent start/stop."""

    def __init__(
        self,
        audio_port: AudioPort,
        queue_service: QueueService,
        playback_service: PlaybackService,
    ) -> None:
        self._audio = audio_port
        self._queue = queue_service
        self._playback = playback_service
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._audio.subscribe_end_of_media(self._on_track_ended)
        self._audio.subscribe_position_changed(self._on_position_changed)
        self._audio.subscribe_duration_changed(self._on_duration_changed)
        self._audio.subscribe_error(self._on_error)

    def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        self._audio.unsubscribe_end_of_media(self._on_track_ended)
        self._audio.unsubscribe_position_changed(self._on_position_changed)
        self._audio.unsubscribe_duration_changed(self._on_duration_changed)
        self._audio.unsubscribe_error(self._on_error)

    def _on_track_ended(self) -> None:
        if self._queue.state.has_next:
            self._queue.next()
        else:
            self._playback.stop()

    def _on_position_changed(self, position_ms: int) -> None:
        self._playback.update_position(position_ms)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._playback.update_duration(duration_ms)

    def _on_error(self, message: str) -> None:
        self._playback.report_error(message)
