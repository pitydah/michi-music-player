"""Playback coordination — connects audio events to application logic."""

from michi.application.playback_service import PlaybackService
from michi.application.ports import AudioPort
from michi.application.queue_service import QueueService


class PlaybackCoordinator:
    """Wires audio-port events to application services (position/duration
    projection). Auto-advance on end-of-media is owned by QueueService
    (repeat-aware); PlaybackCoordinator no longer subscribes to end-of-media."""

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
        self._audio.subscribe_position_changed(self._on_position_changed)
        self._audio.subscribe_duration_changed(self._on_duration_changed)

    def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        self._audio.unsubscribe_position_changed(self._on_position_changed)
        self._audio.unsubscribe_duration_changed(self._on_duration_changed)

    def _on_position_changed(self, position_ms: int) -> None:
        self._playback.update_position(position_ms)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._playback.update_duration(duration_ms)
