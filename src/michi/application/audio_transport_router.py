"""AudioTransportRouter — stable AudioPort identity across engine switches.

PlaybackService and PlaybackCoordinator subscribe ONCE to the router. When
the concrete engine changes, the router object stays the same; only its
bound concrete AudioPort changes (attach/detach with full event
re-routing). No duplicate delivery; no old-engine callbacks after detach;
no callback loss after attach.

The router owns ONLY forwarding; engine choice/persistence/availability/
spawning/DAC selection belong to other authorities (AudioEngineService and
later M11.4 components)."""

from collections.abc import Callable
from pathlib import Path

from michi.application.ports import AudioPort
from michi.domain.audio_engine import AudioEngineId
from michi.domain.playback import PlaybackStatus


class AudioTransportUnavailableError(RuntimeError):
    """Raised when a transport command requires a bound backend and none is
    bound. Never silently no-op play/load/seek; never fabricate 0."""


class AudioTransportBindingPort:
    """Management boundary for engine binding — deliberately NOT part of
    AudioPort (AudioPort stays transport-only)."""

    def bind(self, engine_id: AudioEngineId, audio_port: AudioPort) -> None: ...
    def unbind(self) -> None: ...


class AudioTransportRouter(AudioPort, AudioTransportBindingPort):
    """AudioPort facade + binding management. Framework-free."""

    def __init__(self) -> None:
        self._bound: AudioPort | None = None
        self._bound_engine_id: AudioEngineId | None = None
        # consumer registrations (what PlaybackService/Coordinator registered)
        self._end_of_media: list[Callable[[], None]] = []
        self._position_changed: list[Callable[[int], None]] = []
        self._duration_changed: list[Callable[[int], None]] = []
        self._media_accepted: list[Callable[[Path], None]] = []
        self._media_rejected: list[Callable[[Path, str], None]] = []
        self._playback_state_changed: list[Callable[[PlaybackStatus], None]] = []

    # ------------------------------------------------------------------
    # Binding management (AudioTransportBindingPort)
    # ------------------------------------------------------------------

    def bind(self, engine_id: AudioEngineId, audio_port: AudioPort) -> None:
        """Attach a concrete backend and re-route every event to consumers.

        Idempotent for the same backend; re-binding a different backend first
        detaches the previous one (no duplicate delivery)."""
        if self._bound is audio_port and self._bound_engine_id == engine_id:
            return
        self._detach()
        self._bound = audio_port
        self._bound_engine_id = engine_id
        self._attach()

    def unbind(self) -> None:
        """Detach the backend; consumers keep their router subscription."""
        self._detach()

    @property
    def bound_engine_id(self) -> AudioEngineId | None:
        return self._bound_engine_id

    def _attach(self) -> None:
        assert self._bound is not None
        backend = self._bound
        backend.subscribe_end_of_media(self._fwd_end_of_media)
        backend.subscribe_position_changed(self._fwd_position_changed)
        backend.subscribe_duration_changed(self._fwd_duration_changed)
        backend.subscribe_media_accepted(self._fwd_media_accepted)
        backend.subscribe_media_rejected(self._fwd_media_rejected)
        backend.subscribe_playback_state_changed(self._fwd_playback_state_changed)

    def _detach(self) -> None:
        if self._bound is None:
            return
        backend = self._bound
        backend.unsubscribe_end_of_media(self._fwd_end_of_media)
        backend.unsubscribe_position_changed(self._fwd_position_changed)
        backend.unsubscribe_duration_changed(self._fwd_duration_changed)
        backend.unsubscribe_media_accepted(self._fwd_media_accepted)
        backend.unsubscribe_media_rejected(self._fwd_media_rejected)
        backend.unsubscribe_playback_state_changed(self._fwd_playback_state_changed)
        self._bound = None
        self._bound_engine_id = None

    # ------------------------------------------------------------------
    # Forwarding callbacks (internal — one per event type)
    # ------------------------------------------------------------------

    def _fwd_end_of_media(self) -> None:
        for cb in list(self._end_of_media):
            cb()

    def _fwd_position_changed(self, position_ms: int) -> None:
        for cb in list(self._position_changed):
            cb(position_ms)

    def _fwd_duration_changed(self, duration_ms: int) -> None:
        for cb in list(self._duration_changed):
            cb(duration_ms)

    def _fwd_media_accepted(self, path: Path) -> None:
        for cb in list(self._media_accepted):
            cb(path)

    def _fwd_media_rejected(self, path: Path, reason: str) -> None:
        for cb in list(self._media_rejected):
            cb(path, reason)

    def _fwd_playback_state_changed(self, status: PlaybackStatus) -> None:
        for cb in list(self._playback_state_changed):
            cb(status)

    # ------------------------------------------------------------------
    # AudioPort — command delegation with deterministic unavailable failure
    # ------------------------------------------------------------------

    def _require_backend(self) -> AudioPort:
        if self._bound is None:
            raise AudioTransportUnavailableError(
                "no audio engine bound to the transport router"
            )
        return self._bound

    def load(self, file_path: Path) -> None:
        self._require_backend().load(file_path)

    def play(self) -> None:
        self._require_backend().play()

    def pause(self) -> None:
        self._require_backend().pause()

    def resume(self) -> None:
        self._require_backend().resume()

    def stop(self) -> None:
        self._require_backend().stop()

    def seek(self, position_ms: int) -> None:
        self._require_backend().seek(position_ms)

    def set_volume(self, value: int) -> None:
        self._require_backend().set_volume(value)

    def set_muted(self, muted: bool) -> None:
        self._require_backend().set_muted(muted)

    def position(self) -> int:
        return self._require_backend().position()

    def duration(self) -> int:
        return self._require_backend().duration()

    # ------------------------------------------------------------------
    # AudioPort — consumer subscription (registered ONCE on the router)
    # ------------------------------------------------------------------

    def subscribe_end_of_media(self, callback: Callable[[], None]) -> None:
        if callback not in self._end_of_media:
            self._end_of_media.append(callback)

    def unsubscribe_end_of_media(self, callback: Callable[[], None]) -> None:
        if callback in self._end_of_media:
            self._end_of_media.remove(callback)

    def subscribe_position_changed(self, callback: Callable[[int], None]) -> None:
        if callback not in self._position_changed:
            self._position_changed.append(callback)

    def unsubscribe_position_changed(self, callback: Callable[[int], None]) -> None:
        if callback in self._position_changed:
            self._position_changed.remove(callback)

    def subscribe_duration_changed(self, callback: Callable[[int], None]) -> None:
        if callback not in self._duration_changed:
            self._duration_changed.append(callback)

    def unsubscribe_duration_changed(self, callback: Callable[[int], None]) -> None:
        if callback in self._duration_changed:
            self._duration_changed.remove(callback)

    def subscribe_media_accepted(self, callback: Callable[[Path], None]) -> None:
        if callback not in self._media_accepted:
            self._media_accepted.append(callback)

    def unsubscribe_media_accepted(self, callback: Callable[[Path], None]) -> None:
        if callback in self._media_accepted:
            self._media_accepted.remove(callback)

    def subscribe_media_rejected(self, callback: Callable[[Path, str], None]) -> None:
        if callback not in self._media_rejected:
            self._media_rejected.append(callback)

    def unsubscribe_media_rejected(self, callback: Callable[[Path, str], None]) -> None:
        if callback in self._media_rejected:
            self._media_rejected.remove(callback)

    def subscribe_playback_state_changed(
        self, callback: Callable[[PlaybackStatus], None]
    ) -> None:
        if callback not in self._playback_state_changed:
            self._playback_state_changed.append(callback)

    def unsubscribe_playback_state_changed(
        self, callback: Callable[[PlaybackStatus], None]
    ) -> None:
        if callback in self._playback_state_changed:
            self._playback_state_changed.remove(callback)
