"""HybridAudioManager — selects and switches between audio backends.

GStreamer is always the default. MPD is selected when the profile demands it.
The manager ensures queue continuity, safe shutdown, and normalized snapshots.
"""

import logging
from typing import TYPE_CHECKING

from audio.backends.types import (
    BackendCapabilities,
    PlaybackSnapshot,
    AudioDiagnostics,
)
from audio.backends.errors import (
    BackendNotAvailableError,
)

if TYPE_CHECKING:
    from audio.backends.base import AudioBackend

logger = logging.getLogger("michi.hybrid")


MPD_PROFILES = {
    "michi_hifi_mpd",
    "michi_bitperfect_mpd",
    "michi_dsd_mpd",
    "michi_server_renderer_mpd",
}


class HybridAudioManager:
    """Orchestrates multiple AudioBackend instances and selects the active one."""

    def __init__(self, default_backend: "AudioBackend" = None):
        self._backends: dict[str, "AudioBackend"] = {}
        self._active_id: str = "gstreamer"
        self._fallback_active: bool = False
        self._saved_queue: list[str] = []
        self._saved_queue_index: int = -1

        if default_backend:
            self.register(default_backend)
            self._active_id = default_backend.backend_id

    def register(self, backend: "AudioBackend"):
        self._backends[backend.backend_id] = backend

    def unregister(self, backend_id: str):
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

    def choose_backend_for_profile(self, profile_key: str) -> str:
        if profile_key in MPD_PROFILES:
            if "mpd" in self._backends:
                return "mpd"
            logger.warning("MPD backend requested (%s) but not registered — falling back to GStreamer", profile_key)
            self._fallback_active = True
            return "gstreamer"
        self._fallback_active = False
        return "gstreamer"

    def switch_to(self, backend_id: str) -> bool:
        if backend_id == self._active_id:
            return True
        if backend_id not in self._backends:
            logger.error("Cannot switch to unknown backend: %s", backend_id)
            return False

        old_backend = self.active
        self._save_queue_state()

        if old_backend:
            old_backend.stop()

        self._active_id = backend_id
        self._fallback_active = False

        new_backend = self.active
        if new_backend and self._saved_queue:
            new_backend.set_queue(self._saved_queue, self._saved_queue_index)

        logger.info("Switched audio backend: %s → %s",
                     old_backend.backend_id if old_backend else "none",
                     backend_id)
        return True

    def switch_for_profile(self, profile_key: str) -> bool:
        target = self.choose_backend_for_profile(profile_key)
        if target == self._active_id and not self._fallback_active:
            return True
        if target not in self._backends:
            logger.error("Target backend %s is not registered", target)
            return False
        return self.switch_to(target)

    def _save_queue_state(self):
        backend = self.active
        if backend:
            self._saved_queue = [
                item.get("filepath", "")
                for item in backend.get_queue()
                if item.get("filepath")
            ]
            self._saved_queue_index = backend.get_queue_index()

    # ── Delegated methods ──

    def play(self, path_or_uri: str):
        b = self.active
        if b:
            b.play(path_or_uri)

    def pause(self):
        b = self.active
        if b:
            b.pause()

    def resume(self):
        b = self.active
        if b:
            b.resume()

    def toggle(self):
        b = self.active
        if b:
            b.toggle()

    def stop(self):
        b = self.active
        if b:
            b.stop()

    def seek(self, seconds: float):
        b = self.active
        if b:
            b.seek(seconds)

    def set_volume(self, volume: int):
        b = self.active
        if b:
            b.set_volume(volume)

    def set_queue(self, paths: list[str], start_index: int = 0):
        self._saved_queue = list(paths)
        self._saved_queue_index = start_index
        b = self.active
        if b:
            b.set_queue(paths, start_index)

    def enqueue(self, paths: list[str], play_now: bool = True):
        self._saved_queue.extend(paths)
        b = self.active
        if b:
            b.enqueue(paths, play_now)

    def enqueue_next(self, paths: list[str]):
        b = self.active
        if b:
            b.enqueue_next(paths)

    def clear_queue(self):
        self._saved_queue = []
        self._saved_queue_index = -1
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

    def shutdown(self):
        for bid, backend in self._backends.items():
            logger.info("Shutting down backend: %s", bid)
            backend.shutdown()
