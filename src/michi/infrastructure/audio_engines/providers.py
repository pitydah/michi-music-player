"""Engine provider implementations — infrastructure layer (M11.3A).

GStreamer and MPD are AVAILABILITY-PROBE ONLY in this WP: their adapters are
deliberately NOT implemented (M11.3C / M11.3D). The descriptors distinguish
dependency availability (installed) from implementation readiness
(implemented), so nothing falsely claims READY.
"""

from michi.application.audio_engine_registry import AudioEngineProviderPort
from michi.application.ports import AudioPort
from michi.domain.audio_engine import AudioEngineDescriptor, AudioEngineId

_QT_MULTIMEDIA_DISPLAY = "Qt Multimedia"
_GSTREAMER_DISPLAY = "GStreamer"
_MPD_DISPLAY = "MPD"

_GSTREAMER_NOT_IMPLEMENTED = (
    "GStreamer runtime disponible pero el adaptador AudioPort está pendiente (M11.3C)"
)
_MPD_NOT_IMPLEMENTED = (
    "MPD ejecutable disponible pero el adaptador AudioPort está pendiente (M11.3D)"
)


class QtEngineProvider(AudioEngineProviderPort):
    """Reference/safe engine: wraps the existing QtMultimediaBackend.

    M11.3A-R1 lifecycle ownership: the provider OWNS the backend instance it
    opens — open() is deterministic (same instance until close), close() is
    idempotent, and a later open() produces a fresh valid backend. The
    transport router MUST detach BEFORE the provider closes (SWITCH ORDER)."""

    def __init__(self) -> None:
        self._backend: AudioPort | None = None

    @property
    def engine_id(self) -> AudioEngineId:
        return AudioEngineId.QT_MULTIMEDIA

    def probe(self) -> AudioEngineDescriptor:
        try:
            from michi.infrastructure.qt_backend import (
                QtMultimediaBackend,  # noqa: F401
            )

            available = True
            reason = None
        except Exception as exc:  # pragma: no cover - import surface varies
            available = False
            reason = f"Qt Multimedia no disponible: {exc}"
        from michi.domain.audio_engine import AudioEngineCapabilities

        return AudioEngineDescriptor(
            engine_id=self.engine_id,
            display_name=_QT_MULTIMEDIA_DISPLAY,
            available=available,
            unavailable_reason=reason,
            # truthful transport capabilities of the implemented adapter
            capabilities=AudioEngineCapabilities(
                local_file_playback=True,
                seek=True,
                pause=True,
                volume=True,
                mute=True,
            ),
        )

    def open(self) -> AudioPort:
        """Deterministic: repeated open returns the SAME owned instance (no
        uncontrolled parallel Qt engines) until close()."""
        if self._backend is not None:
            return self._backend
        from michi.infrastructure.qt_backend import QtMultimediaBackend

        backend = QtMultimediaBackend()
        self._backend = backend
        return backend

    def close(self) -> None:
        """Idempotent: releases the owned backend. Callers MUST detach the
        transport router BEFORE close (SWITCH ORDER: stop → detach →
        provider close → target open → bind → validate)."""
        backend = self._backend
        self._backend = None
        if backend is None:
            return
        backend.stop()


class GStreamerEngineProvider(AudioEngineProviderPort):
    """Availability probe for GStreamer via PyGObject/GI (lazy, optional).

    The GStreamer AudioPort adapter is NOT implemented in M11.3A (M11.3C
    owns it). gi is never imported at module import time — the base Michi
    wheel must stay usable without GI/GStreamer."""

    @property
    def engine_id(self) -> AudioEngineId:
        return AudioEngineId.GSTREAMER

    def probe(self) -> AudioEngineDescriptor:
        available = False
        reason = None
        try:
            import gi  # noqa: PLC0415 - lazy optional system capability

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # noqa: PLC0415,F401

            available = True
        except (ImportError, ValueError) as exc:
            reason = f"PyGObject/GStreamer no disponible: {exc}"
        return AudioEngineDescriptor(
            engine_id=self.engine_id,
            display_name=_GSTREAMER_DISPLAY,
            available=available,
            unavailable_reason=reason,
            implemented=False,
            implementation_reason=_GSTREAMER_NOT_IMPLEMENTED,
        )

    def open(self) -> AudioPort:
        raise NotImplementedError("GStreamer AudioPort adapter pendiente (M11.3C)")

    def close(self) -> None:
        pass


class MpdEngineProvider(AudioEngineProviderPort):
    """Availability probe for MPD (private managed process, M11.3D).

    probe() only checks the executable is discoverable — it NEVER spawns
    MPD, never attaches to a system daemon and never inspects /run/mpd,
    /etc/mpd.conf or ~/.config/mpd."""

    @property
    def engine_id(self) -> AudioEngineId:
        return AudioEngineId.MPD

    def probe(self) -> AudioEngineDescriptor:
        import shutil  # noqa: PLC0415 - stdlib, import-time cheap

        path = shutil.which("mpd")
        available = path is not None
        reason = None if available else "mpd executable no encontrado en PATH"
        return AudioEngineDescriptor(
            engine_id=self.engine_id,
            display_name=_MPD_DISPLAY,
            available=available,
            unavailable_reason=reason,
            implemented=False,
            implementation_reason=_MPD_NOT_IMPLEMENTED,
        )

    def open(self) -> AudioPort:
        raise NotImplementedError("MPD AudioPort adapter pendiente (M11.3D)")

    def close(self) -> None:
        pass
