"""Playback coordination — connects audio events to queue logic.

Lives in Application layer. Depends on Application ports and services only.
Never depends on Infrastructure or Presentation.
"""

from collections.abc import Callable

from michi.application.ports import AudioPort
from michi.application.queue_service import QueueService


class PlaybackCoordinator:
    """Wires audio-port events to application services.

    EndOfMedia → advance queue (or stop).
    Bootstrap supplies a callback to notify presentation bridges.
    """

    def __init__(
        self,
        audio_port: AudioPort,
        queue_service: QueueService,
    ) -> None:
        self._audio = audio_port
        self._queue = queue_service
        self._on_state_change: Callable[[], None] | None = None

    def on_state_change(self, callback: Callable[[], None]) -> None:
        self._on_state_change = callback

    def start(self) -> None:
        self._audio.on_end_of_media(self._on_track_ended)

    def stop(self) -> None:
        self._audio.remove_end_of_media_callbacks()

    def _on_track_ended(self) -> None:
        if self._queue.state.has_next:
            self._queue.next()
        if self._on_state_change:
            self._on_state_change()
