"""AudioBackendFactory — single authority for backend creation.

Centralizes construction of :class:`AudioBackend` instances so there is exactly
one place that knows how to wire a backend's constructor arguments. Both
:class:`PlayerService` and :class:`HybridAudioManager` delegate backend creation
here, eliminating the dual MPD construction paths that previously diverged in
signature (``MpdBackend(host=...)`` vs the broken ``MpdBackend(service_manager=...)``).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("michi.backend_factory")


class BackendAvailabilityResult:
    """Outcome of a backend creation attempt.

    ``state`` follows the backend lifecycle vocabulary:
    unavailable / initializing / ready / degraded / failed.
    """

    def __init__(self, ok: bool, backend_id: str, error: str = "",
                 state: str = "unavailable"):
        self.ok = ok
        self.backend_id = backend_id
        self.error = error
        self.state = state

    def __repr__(self) -> str:
        return (
            f"BackendAvailabilityResult(ok={self.ok!r}, "
            f"backend_id={self.backend_id!r}, error={self.error!r}, "
            f"state={self.state!r})"
        )


class AudioBackendFactory:
    """Creates and registers audio backends. Single construction authority.

    The factory is configured once (typically by :class:`PlayerService`) with
    the MPD connection parameters and path mapper, then any consumer may request
    a backend by id without knowing its constructor signature.
    """

    def __init__(self) -> None:
        self._mpd_host: str = "127.0.0.1"
        self._mpd_port: int = 6600
        self._mpd_password: str = ""
        self._mpd_path_mapper: Any = None

    def configure_mpd(self, host: str, port: int, password: str = "",
                      path_mapper: Any = None) -> None:
        """Store the MPD connection parameters used by :meth:`create_backend`."""
        self._mpd_host = host
        self._mpd_port = port
        self._mpd_password = password
        self._mpd_path_mapper = path_mapper

    def create_backend(self, backend_id: str) -> tuple[Any, BackendAvailabilityResult]:
        """Create a backend instance without registering it.

        Returns ``(backend, result)``. On failure ``backend`` is ``None`` and
        ``result.ok`` is ``False`` with an explanatory ``error``.
        """
        if backend_id == "mpd":
            from audio.backends.mpd_backend import MpdBackend
            backend = MpdBackend(
                host=self._mpd_host,
                port=self._mpd_port,
                password=self._mpd_password,
                path_mapper=self._mpd_path_mapper,
            )
            return backend, BackendAvailabilityResult(True, "mpd", state="ready")
        if backend_id == "gstreamer":
            from audio.player import GStreamerEngine
            from audio.backends.engine_backend_adapter import EngineBackendAdapter
            engine = GStreamerEngine()
            return (EngineBackendAdapter(engine),
                    BackendAvailabilityResult(True, "gstreamer", state="ready"))
        return None, BackendAvailabilityResult(
            False, backend_id, error=f"UNKNOWN_BACKEND:{backend_id}")
