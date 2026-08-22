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
    """Reference/safe engine: wraps the existing QtMultimediaBackend."""

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
        return AudioEngineDescriptor(
            engine_id=self.engine_id,
            display_name=_QT_MULTIMEDIA_DISPLAY,
            available=available,
            unavailable_reason=reason,
        )

    def open(self) -> AudioPort:
        from michi.infrastructure.qt_backend import QtMultimediaBackend

        return QtMultimediaBackend()

    def close(self) -> None:
        # M11.3A foundation: the backend is released by its owner; the
        # provider owns no long-lived backend instance yet (full lifecycle
        # normalization belongs to M11.3B).
        pass


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
            # transport capabilities are nominal until M11.3C
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
        )

    def open(self) -> AudioPort:
        raise NotImplementedError("MPD AudioPort adapter pendiente (M11.3D)")

    def close(self) -> None:
        pass
