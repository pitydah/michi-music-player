"""Engine provider implementations — infrastructure layer (M11.3A).

GStreamer has an IMPLEMENTED adapter (M11.3C/M11.3C-R1) with runtime-
dependent availability (GI + Gst + playbin3 required). MPD remains
availability-probe only (M11.3D). Descriptors distinguish dependency
availability (installed) from implementation readiness (implemented).
"""

from michi.application.audio_engine_registry import AudioEngineProviderPort
from michi.application.ports import AudioPort
from michi.domain.audio_engine import (
    AudioEngineCapabilities,
    AudioEngineDescriptor,
    AudioEngineId,
)

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
        provider close → target open → bind → validate).

        Exception safety: ownership is released in `finally`, so a failing
        stop() can never leave a phantom "owned" engine behind; the error is
        propagated to the caller (best-effort shutdown policy applies at the
        container level)."""
        backend = self._backend
        if backend is None:
            return
        try:
            backend.stop()
        finally:
            self._backend = None


class GStreamerEngineProvider(AudioEngineProviderPort):
    """GStreamer provider (M11.3C): implemented = True, availability is
    runtime-dependent (GI/GStreamer installed). gi is never imported at
    module import time — the base Michi wheel stays usable without it."""

    def __init__(self) -> None:
        self._port: AudioPort | None = None

    @property
    def engine_id(self) -> AudioEngineId:
        return AudioEngineId.GSTREAMER

    def probe(self) -> AudioEngineDescriptor:
        """Truthful availability (M11.3C-R1): GI + Gst 1.0 + playbin3
        factory must ALL exist — the adapter depends on playbin3."""
        available = False
        reason = None
        try:
            from michi.infrastructure.audio_engines.gstreamer import (
                GStreamerBindings,
            )

            bindings = GStreamerBindings()
            bindings.ensure_loaded()
            if not bindings.playbin3_available():
                reason = "playbin3 no disponible en el runtime GStreamer"
            else:
                available = True
        except (ImportError, ValueError) as exc:
            reason = f"PyGObject/GStreamer no disponible: {exc}"
        return AudioEngineDescriptor(
            engine_id=self.engine_id,
            display_name=_GSTREAMER_DISPLAY,
            available=available,
            unavailable_reason=reason,
            implemented=True,
            capabilities=AudioEngineCapabilities(
                local_file_playback=True,
                seek=True,
                pause=True,
                volume=True,
                mute=True,
            ),
        )

    def open(self) -> AudioPort:
        """Deterministic: repeated open returns the SAME owned port until
        close()."""
        if self._port is not None:
            return self._port
        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerAudioPort,
        )

        port = GStreamerAudioPort()
        self._port = port
        return port

    def close(self) -> None:
        """Idempotent, exception-safe: ownership released in finally."""
        port = self._port
        if port is None:
            return
        try:
            port.close()
        finally:
            self._port = None


class MpdEngineProvider(AudioEngineProviderPort):
    """MPD as a MANAGED PRIVATE child process behind AudioPort (M11.3D).

    probe() is SIDE-EFFECT FREE: it only checks the executable is
    discoverable — it NEVER spawns MPD, never creates runtime dirs or
    sockets, never attaches to a system daemon and never inspects
    /run/mpd, /etc/mpd.conf or ~/.config/mpd."""

    def __init__(self) -> None:
        self._port = None

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
            implemented=True,
            implementation_reason=None,
            capabilities=AudioEngineCapabilities(
                local_file_playback=True,
                seek=True,
                pause=True,
                volume=True,
                mute=True,
            ),
        )

    def open(self) -> AudioPort:
        """Abre el runtime gestionado y devuelve el MISMO port hasta close.

        Si la inicialización falla, no queda ningún port a medio abrir."""
        if self._port is not None:
            return self._port
        from michi.infrastructure.audio_engines.mpd import MPDAudioPort

        port = MPDAudioPort()
        port.open()  # failure-atomic: si falla, el runtime se limpia solo
        self._port = port
        return port

    def close(self) -> None:
        port = self._port
        self._port = None
        if port is not None:
            port.close()
