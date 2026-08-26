"""AudioTransportRouter — stable AudioPort identity across engine switches.

PlaybackService and PlaybackCoordinator subscribe ONCE to the router. When
the concrete engine changes, the router object stays the same; only its
bound concrete AudioPort changes (attach/detach with full event
re-routing). No duplicate delivery; no old-engine callbacks after detach;
no callback loss after attach.

The router owns ONLY forwarding; engine choice/persistence/availability/
spawning/DAC selection belong to other authorities (AudioEngineService and
later M11.4 components).

Reliability seal (AR-10/AR-31/AR-32): binding is transactional. Every
forwarded callback carries the binding generation + backend identity it
was captured under; late events from a superseded backend are dropped even
if its unsubscribe could not be physically completed. A partial attach
failure rolls back the already-registered subscriptions and never reports
a clean new binding.
"""

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)
from pathlib import Path

from michi.application.ports import (
    AudioPort,
    AudioTransportUnavailableError,  # R1-06: canonical class from ports.py
)
from michi.domain.audio_engine import AudioEngineId
from michi.domain.playback import PlaybackStatus


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
        # AR-31: binding generation — incremented on every successful bind.
        # Forwarded callbacks capture it; late events from superseded
        # bindings are dropped even if their unsubscribe could not complete.
        self._binding_generation = 0
        # per-binding forwarding wrappers (identity for subscribe/unsubscribe)
        self._wrappers: list[Callable[..., None]] = []
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
        detaches the previous one (no duplicate delivery). TRANSACTIONAL:
        if the attach fails partway, the already-registered subscriptions are
        rolled back best-effort and no clean binding is reported (the router
        stays unbound — the coordinator's failure path then releases the
        target provider truthfully)."""
        if self._bound is audio_port and self._bound_engine_id == engine_id:
            return
        self._detach()
        gen = self._binding_generation + 1
        self._bound = audio_port
        self._bound_engine_id = engine_id
        try:
            self._attach(gen)
        except Exception:
            # AR-32: rollback best-effort of what already registered; the
            # router must NOT report a clean new binding after a partial
            # attach. Ownership evidence (which backend was attempted)
            # remains visible for diagnosis.
            self._rollback_attach()
            self._bound = None
            self._bound_engine_id = None
            raise
        self._binding_generation = gen

    def unbind(self) -> None:
        """Detach the backend; consumers keep their router subscription."""
        self._detach()

    @property
    def bound_engine_id(self) -> AudioEngineId | None:
        return self._bound_engine_id

    @property
    def bound_port(self) -> AudioPort | None:
        """KCR-010: read-only runtime introspection (no ownership transfer).

        Observability only — the provider remains the lifecycle owner and
        the router the binding owner."""
        return self._bound

    @property
    def binding_generation(self) -> int:
        return self._binding_generation

    def _attach(self, generation: int) -> None:
        """Subscribe per-binding wrappers capturing (backend, generation).

        AR-32: if subscription k fails, subscriptions 0..k-1 are rolled back
        best-effort and the failure propagates — a partially authoritative
        binding is never published."""
        assert self._bound is not None
        backend = self._bound
        pairs = [
            ("subscribe_end_of_media", lambda cb: backend.subscribe_end_of_media(cb)),
            (
                "subscribe_position_changed",
                lambda cb: backend.subscribe_position_changed(cb),
            ),
            (
                "subscribe_duration_changed",
                lambda cb: backend.subscribe_duration_changed(cb),
            ),
            (
                "subscribe_media_accepted",
                lambda cb: backend.subscribe_media_accepted(cb),
            ),
            (
                "subscribe_media_rejected",
                lambda cb: backend.subscribe_media_rejected(cb),
            ),
            (
                "subscribe_playback_state_changed",
                lambda cb: backend.subscribe_playback_state_changed(cb),
            ),
        ]
        wrapper_factories = [
            self._make_wrapper("eom", generation, backend),
            self._make_wrapper("position", generation, backend),
            self._make_wrapper("duration", generation, backend),
            self._make_wrapper("accepted", generation, backend),
            self._make_wrapper("rejected", generation, backend),
            self._make_wrapper("state", generation, backend),
        ]
        for (_name, subscribe), wrapper in zip(pairs, wrapper_factories, strict=True):
            subscribe(wrapper)
            self._wrappers.append(wrapper)

    def _rollback_attach(self) -> None:
        """Best-effort unsubscribe of the wrappers registered by a failed
        attach. Secondary diagnostics: rollback failures are logged, never
        raised (the primary attach failure propagates)."""
        backend = self._bound
        for wrapper in list(self._wrappers):
            try:
                self._unsubscribe_wrapper(backend, wrapper)
            except Exception:  # noqa: BLE001 — cleanup is best-effort
                logger.warning(
                    "audio router unsubscribe failed; generation guard remains active",
                    exc_info=True,
                )
        self._wrappers = []

    def _unsubscribe_wrapper(self, backend: AudioPort, wrapper: Callable) -> None:
        kind = getattr(wrapper, "_kind", "")
        if kind == "eom":
            backend.unsubscribe_end_of_media(wrapper)
        elif kind == "position":
            backend.unsubscribe_position_changed(wrapper)
        elif kind == "duration":
            backend.unsubscribe_duration_changed(wrapper)
        elif kind == "accepted":
            backend.unsubscribe_media_accepted(wrapper)
        elif kind == "rejected":
            backend.unsubscribe_media_rejected(wrapper)
        elif kind == "state":
            backend.unsubscribe_playback_state_changed(wrapper)

    def _detach(self) -> None:
        if self._bound is None:
            return
        backend = self._bound
        for wrapper in list(self._wrappers):
            try:
                self._unsubscribe_wrapper(backend, wrapper)
            except Exception:  # noqa: BLE001 — best-effort detach
                # AR-31: an unsubscribe that fails is NOT fatal — the
                # binding-generation provenance in the wrappers drops any
                # late event it could still deliver. KCR-006: the cleanup
                # failure is LOGGED, never a silent continue.
                logger.warning(
                    "audio router detach unsubscribe failed; generation "
                    "guard remains active",
                    exc_info=True,
                )
        self._wrappers = []
        self._bound = None
        self._bound_engine_id = None

    def _make_wrapper(self, kind: str, generation: int, backend: AudioPort):
        """Per-binding forwarding wrapper: drops events whose captured
        (generation, backend) no longer match the current binding."""

        def forward(*args):
            if self._bound is not backend or self._binding_generation != generation:
                return  # stale event from a superseded binding
            if kind == "eom":
                self._fwd_end_of_media()
            elif kind == "position":
                self._fwd_position_changed(args[0])
            elif kind == "duration":
                self._fwd_duration_changed(args[0])
            elif kind == "accepted":
                self._fwd_media_accepted(args[0])
            elif kind == "rejected":
                self._fwd_media_rejected(args[0], args[1])
            elif kind == "state":
                self._fwd_playback_state_changed(args[0])

        forward._kind = kind  # type: ignore[attr-defined]
        return forward

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
