"""HybridAudioManager — selects and switches between audio backends.

GStreamer is always the default. MPD is selected when the profile demands it.
The manager ensures queue continuity, safe shutdown, and normalized snapshots.

Re-emits position_changed, state_changed, duration_changed from the active
backend so PlayerService can listen to a single source of truth.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from audio.backends.types import (
    BackendCapabilities,
    PlaybackSnapshot,
    AudioDiagnostics,
)

if TYPE_CHECKING:
    from audio.backends.base import AudioBackend
    from audio.backends.backend_factory import AudioBackendFactory

logger = logging.getLogger("michi.hybrid")


MPD_PROFILES = {
    "michi_hifi_mpd",
    "michi_bitperfect_mpd",
    "michi_dsd_mpd",
    "michi_server_renderer_mpd",
}

# Backend lifecycle states for the active backend.
BACKEND_STATE_UNINITIALIZED = "uninitialized"
BACKEND_STATE_INITIALIZING = "initializing"
BACKEND_STATE_READY = "ready"
BACKEND_STATE_DEGRADED = "degraded"
BACKEND_STATE_FAILED = "failed"


@dataclass
class _SwitchState:
    queue: list[str] = field(default_factory=list)
    index: int = -1
    play_state: str = "stopped"
    position: float = 0.0


class HybridAudioManager(QObject):
    """Orchestrates multiple AudioBackend instances and selects the active one."""

    position_changed = Signal(float)
    state_changed = Signal(str)
    duration_changed = Signal(float)
    queue_progressed = Signal(int, str, str, object)
    backend_changed = Signal(str, str)

    def __init__(self, default_backend: "AudioBackend" = None, parent=None):
        super().__init__(parent)
        self._backends: dict[str, "AudioBackend"] = {}
        self._active_id: str = "gstreamer"
        self._fallback_active: bool = False
        self._switch_state = _SwitchState()
        self._connected_signals: list = []
        self._backend_state: str = BACKEND_STATE_UNINITIALIZED
        self._factory: "AudioBackendFactory | None" = None

        if default_backend:
            self.register(default_backend)
            self._active_id = default_backend.backend_id
            self._connect_backend_signals(default_backend)

    def set_factory(self, factory: "AudioBackendFactory") -> None:
        """Inject the single backend construction authority.

        When set, :meth:`ensure_backend_available` creates backends through the
        factory instead of ad-hoc construction (which previously produced a
        ``MpdBackend(service_manager=...)`` TypeError).
        """
        self._factory = factory

    def register(self, backend: "AudioBackend") -> None:
        self._backends[backend.backend_id] = backend
        if self._backend_state == BACKEND_STATE_UNINITIALIZED and backend.is_ready():
            self._backend_state = BACKEND_STATE_READY

    def unregister(self, backend_id: str) -> None:
        self._backends.pop(backend_id, None)

    @property
    def active(self) -> "AudioBackend | None":
        return self._backends.get(self._active_id)

    @property
    def active_id(self) -> str:
        return self._active_id

    @property
    def is_fallback(self) -> bool:
        return self._fallback_active

    @property
    def backend_state(self) -> str:
        return self._backend_state

    def _connect_backend_signals(self, backend):
        self._disconnect_backend_signals()
        if hasattr(backend, 'position_changed'):
            self._connected_signals.append(
                backend.position_changed.connect(self.position_changed))
        if hasattr(backend, 'state_changed'):
            self._connected_signals.append(
                backend.state_changed.connect(self.state_changed))
        if hasattr(backend, 'duration_changed'):
            self._connected_signals.append(
                backend.duration_changed.connect(self.duration_changed))
        if hasattr(backend, "queue_progressed"):
            self._connected_signals.append(
                backend.queue_progressed.connect(self.queue_progressed)
            )

    def _disconnect_backend_signals(self):
        import contextlib
        for conn in self._connected_signals:
            with contextlib.suppress(Exception):
                QObject.disconnect(conn)
        self._connected_signals = []

    def choose_backend_for_profile(self, profile_key: str) -> str:
        """Return the desired backend id for ``profile_key``.

        Does NOT decide fallback before attempting initialization — that is
        handled by :meth:`switch_for_profile` via :meth:`ensure_backend_available`.
        MPD profiles target "mpd"; everything else targets "gstreamer".
        """
        if profile_key in MPD_PROFILES:
            return "mpd"
        return "gstreamer"

    def ensure_backend_available(self, backend_id: str) -> dict:
        """Ensure a backend is registered and available, creating it if needed.

        Backend creation is delegated to :class:`AudioBackendFactory` (the single
        construction authority) when one has been injected via
        :meth:`set_factory`. Without a factory the request fails with
        ``NO_FACTORY`` so callers can fall back deterministically instead of
        silently swallowing a constructor ``TypeError``.
        """
        if backend_id in self._backends:
            return {"ok": True, "backend": backend_id, "registered": True}
        if not self._factory:
            return {"ok": False, "backend": backend_id, "error": "NO_FACTORY"}
        backend, result = self._factory.create_backend(backend_id)
        if not result.ok or backend is None:
            return {"ok": False, "backend": backend_id, "error": result.error}
        self.register(backend)
        return {"ok": True, "backend": backend_id, "registered": True,
                "state": result.state}

    def switch_to(self, backend_id: str) -> bool:
        if backend_id == self._active_id:
            return True
        if backend_id not in self._backends:
            logger.error("Cannot switch to unknown backend: %s", backend_id)
            return False

        self._save_switch_state()

        old_backend = self.active
        if old_backend:
            old_backend.stop()

        self._active_id = backend_id
        self._fallback_active = False

        new_backend = self.active
        if new_backend:
            if self._switch_state.queue:
                new_backend.set_queue(self._switch_state.queue, self._switch_state.index)
            self._connect_backend_signals(new_backend)

        logger.info("Switched audio backend: %s → %s",
                     old_backend.backend_id if old_backend else "none",
                     backend_id)
        self._backend_state = BACKEND_STATE_READY
        return True

    def switch_for_profile(self, profile_key: str) -> bool:
        """Switch to the backend required by ``profile_key`` transactionally.

        Ensures the target backend is available before switching. On failure
        the previously active backend is restored so the manager never ends up
        pointing at a half-initialized backend.
        """
        old_id = self._active_id
        old_fallback = self._fallback_active
        old_state = self._backend_state
        try:
            target = self.choose_backend_for_profile(profile_key)
            if target == self._active_id and not self._fallback_active:
                self._backend_state = BACKEND_STATE_READY
                return True

            availability = self.ensure_backend_available(target)
            if not availability.get("ok"):
                # Target backend could not be made available. Fall back to
                # GStreamer when it is registered and differs from the target;
                # otherwise mark the switch as failed.
                if target != "gstreamer" and "gstreamer" in self._backends:
                    logger.warning(
                        "Backend %s unavailable (%s) — falling back to GStreamer",
                        target, availability.get("error", ""))
                    self._fallback_active = True
                    if not self.switch_to("gstreamer"):
                        raise RuntimeError("fallback switch_to(gstreamer) failed")
                    self._backend_state = BACKEND_STATE_DEGRADED
                    return True
                logger.error("Target backend %s unavailable: %s",
                             target, availability.get("error", ""))
                self._backend_state = BACKEND_STATE_FAILED
                return False

            self._backend_state = BACKEND_STATE_INITIALIZING
            if not self.switch_to(target):
                raise RuntimeError(f"switch_to({target}) failed")

            new_backend = self.active
            if new_backend is None or not new_backend.is_ready():
                raise RuntimeError(f"Backend {target} failed to initialize")

            self._backend_state = BACKEND_STATE_READY
            return True
        except Exception as exc:
            logger.error("Backend switch for profile '%s' failed, rolling back: %s",
                         profile_key, exc)
            self._active_id = old_id
            self._fallback_active = old_fallback
            self._backend_state = old_state
            restored = self.active
            if restored is not None:
                self._connect_backend_signals(restored)
            return False

    def fallback_to_default(self, reason: str = "") -> bool:
        self._fallback_active = True
        logger.warning("Falling back to GStreamer: %s", reason)
        result = self.switch_to("gstreamer")
        if result:
            self._backend_state = BACKEND_STATE_DEGRADED
        return result

    def mark_fallback(self, active: bool = True) -> None:
        self._fallback_active = active

    def _save_switch_state(self):
        backend = self.active
        if backend:
            queue = [
                item.get("filepath", "")
                for item in backend.get_queue()
                if item.get("filepath")
            ]
            snap = backend.get_snapshot()
            self._switch_state = _SwitchState(
                queue=queue,
                index=backend.get_queue_index(),
                play_state=snap.state,
                position=snap.position_seconds,
            )

    # ── Delegated methods ──

    def assert_single_playback(self) -> int:
        """Count playing backends. Invariant: must be <= 1.

        Logs (never raises) when more than one backend reports playing, so the
        guard is safe to invoke in production before ``play()`` and after
        ``stop()``.
        """
        playing = [bid for bid, b in self._backends.items()
                   if getattr(b, "is_playing", lambda: False)()]
        if len(playing) > 1:
            logger.error("INVARIANT VIOLATION: %d backends playing: %s",
                         len(playing), playing)
        return len(playing)

    def play(self, path_or_uri: str) -> str:
        """Play ``path_or_uri`` on the appropriate backend.

        Stream URLs (``http://``, ``https://``, ``icy://``) always force
        GStreamer regardless of the active backend (MPD is for local Hi-Fi files
        only). Any other playing backend is stopped, the active backend switches
        to GStreamer, and ``backend_changed`` is emitted with the ``streaming``
        reason so consumers can track the effective backend.

        Returns the effective backend id that handled the call.
        """
        self.assert_single_playback()

        is_stream = isinstance(path_or_uri, str) and path_or_uri.startswith(
            ("http://", "https://", "icy://"))
        if is_stream:
            gst = self._backends.get("gstreamer")
            if gst is not None and self._active_id != "gstreamer":
                # Stop ANY playing backend (e.g. MPD) before switching.
                old = self.active
                if old is not None and old is not gst:
                    import contextlib
                    with contextlib.suppress(Exception):
                        old.stop()
                self._active_id = "gstreamer"
                self._fallback_active = False
                self._connect_backend_signals(gst)
                logger.info("Stream playback forced GStreamer backend (reason=streaming)")
                self.backend_changed.emit("gstreamer", "streaming")

        b = self.active
        if b is None:
            return self._active_id
        if b.is_playing():
            b.stop()
        b.play(path_or_uri)
        return self._active_id

    def pause(self) -> None:
        b = self.active
        if b:
            b.pause()

    def resume(self) -> None:
        b = self.active
        if b:
            b.resume()

    def toggle(self) -> None:
        b = self.active
        if b:
            b.toggle()

    def stop(self) -> None:
        b = self.active
        if b:
            b.stop()
        self.assert_single_playback()

    def seek(self, seconds: float) -> None:
        b = self.active
        if b:
            b.seek(seconds)

    def set_volume(self, volume: int) -> None:
        b = self.active
        if b:
            b.set_volume(volume)

    def set_repeat(self, mode: str) -> str:
        backend = self.active
        if backend and hasattr(backend, "set_repeat"):
            return backend.set_repeat(mode)
        return mode

    def set_shuffle(self, enabled: bool) -> bool:
        backend = self.active
        if backend and hasattr(backend, "set_shuffle"):
            return backend.set_shuffle(enabled)
        return bool(enabled)

    def set_queue(self, paths: list[str], start_index: int = 0,
                  revision: int | None = None) -> None:
        self._switch_state.queue = list(paths)
        self._switch_state.index = start_index
        b = self.active
        if b:
            try:
                b.set_queue(paths, start_index, revision=revision)
            except TypeError as exc:
                if "revision" not in str(exc):
                    raise
                b.set_queue(paths, start_index)

    def play_queue_index(self, index: int) -> bool:
        backend = self.active
        if backend and hasattr(backend, "play_queue_index"):
            return bool(backend.play_queue_index(index))
        return False

    def enqueue(self, paths: list[str], play_now: bool = True) -> None:
        self._switch_state.queue.extend(paths)
        b = self.active
        if b:
            b.enqueue(paths, play_now)

    def enqueue_next(self, paths: list[str]) -> None:
        b = self.active
        if b:
            b.enqueue_next(paths)

    def clear_queue(self) -> None:
        self._switch_state = _SwitchState()
        b = self.active
        if b:
            b.clear_queue()

    def play_next(self) -> bool:
        b = self.active
        return b.play_next() if b else False

    def play_prev(self) -> bool:
        b = self.active
        return b.play_prev() if b else False

    def get_queue(self) -> list[dict]:
        b = self.active
        return b.get_queue() if b else []

    def get_queue_index(self) -> int:
        b = self.active
        return b.get_queue_index() if b else -1

    def get_snapshot(self) -> PlaybackSnapshot:
        b = self.active
        if b:
            return b.get_snapshot()
        return PlaybackSnapshot(backend_id="none", state="stopped", error="No active backend")

    def get_diagnostics(self) -> AudioDiagnostics:
        b = self.active
        if b:
            return b.get_diagnostics()
        return AudioDiagnostics(backend_id="none", profile="none")

    def get_capabilities(self) -> BackendCapabilities:
        b = self.active
        if b:
            return b.capabilities
        return BackendCapabilities(backend_id="none", display_name="None")

    def shutdown(self) -> None:
        self._disconnect_backend_signals()
        for bid, backend in self._backends.items():
            logger.info("Shutting down backend: %s", bid)
            backend.shutdown()
