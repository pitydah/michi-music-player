"""Engine provider implementations — infrastructure layer (M11.3A).

GStreamer and MPD both have implemented AudioPort adapters.
Runtime availability remains environment-dependent (GStreamer: GI +
Gst + playbin3; MPD: executable discoverable in PATH). The managed MPD
process and private socket are established only during activation /
open(), never during passive availability probing.
Descriptors distinguish dependency availability (available) from
adapter implementation truth (implemented).
"""

import os

from michi.application.audio_engine_registry import AudioEngineProviderPort
from michi.application.audio_engine_runtime_failure import (
    AudioEngineRuntimeFailureEvent,
    AudioEngineRuntimeFailureSourcePort,
    RuntimeFailureCallback,
)
from michi.application.ports import AudioPort
from michi.domain.audio_engine import (
    AudioEngineCapabilities,
    AudioEngineDescriptor,
    AudioEngineId,
)

_QT_MULTIMEDIA_DISPLAY = "Qt Multimedia"
_GSTREAMER_DISPLAY = "GStreamer"
_MPD_DISPLAY = "MPD"


class _RuntimeFailureRelayMixin(AudioEngineRuntimeFailureSourcePort):
    """M11.3G: provider-level runtime-failure observation relay.

    Providers may be open/close/reopen; a delayed failure from runtime
    generation N must NEVER kill generation N+1 — every emitted event
    carries the provider's CURRENT runtime generation and the convergence
    coordinator validates it against the provider at acceptance time.
    """

    def __init__(self) -> None:
        self._runtime_failure_listeners: list[RuntimeFailureCallback] = []
        self._runtime_generation = 0

    @property
    def current_runtime_generation(self) -> int:
        """Generation of the CURRENTLY open runtime (invalidated on close)."""
        return self._runtime_generation

    def subscribe_runtime_failed(self, callback: RuntimeFailureCallback) -> None:
        if callback not in self._runtime_failure_listeners:
            self._runtime_failure_listeners.append(callback)

    def unsubscribe_runtime_failed(self, callback: RuntimeFailureCallback) -> None:
        if callback in self._runtime_failure_listeners:
            self._runtime_failure_listeners.remove(callback)

    def _bump_runtime_generation(self) -> None:
        self._runtime_generation += 1

    def _invalidate_runtime_generation(self) -> None:
        """Invalidate any in-flight events from the runtime being closed:
        the generation moves forward so stale events are rejected."""
        self._runtime_generation += 1

    def emit_runtime_failure(self, reason: str) -> None:
        """Publish a proven fatal runtime loss to subscribers (best-effort:
        a subscriber exception must not kill the provider lifecycle)."""
        event = AudioEngineRuntimeFailureEvent(
            engine_id=self.engine_id,
            runtime_generation=self._runtime_generation,
            reason=reason,
        )
        for cb in list(self._runtime_failure_listeners):
            try:
                cb(event)
            except Exception:  # pragma: no cover - defensive relay
                continue


class QtEngineProvider(_RuntimeFailureRelayMixin, AudioEngineProviderPort):
    """Reference/safe engine: wraps the existing QtMultimediaBackend.

    M11.3A-R1 lifecycle ownership: the provider OWNS the backend instance it
    opens — open() is deterministic (same instance until close), close() is
    idempotent, and a later open() produces a fresh valid backend. The
    transport router MUST detach BEFORE the provider closes (SWITCH ORDER)."""

    def __init__(self) -> None:
        _RuntimeFailureRelayMixin.__init__(self)
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
        self._bump_runtime_generation()
        return backend

    def close(self) -> None:
        """R1-04: releases the owned backend through its REAL close()
        (QtMultimediaBackend.close owns stop + source release + signal
        disconnection + late-event prevention). Callers MUST detach the
        transport router BEFORE close (SWITCH ORDER).

        Ownership is released ONLY on proven success: a failing close
        RETAINS the backend handle and the runtime generation so the
        still-open runtime stays reachable/diagnosable/retryable."""
        backend = self._backend
        if backend is None:
            return
        backend.close()
        # ONLY AFTER PROVEN SUCCESS:
        self._backend = None
        self._invalidate_runtime_generation()


class GStreamerEngineProvider(_RuntimeFailureRelayMixin, AudioEngineProviderPort):
    """GStreamer provider (M11.3C): implemented = True, availability is
    runtime-dependent (GI/GStreamer installed). gi is never imported at
    module import time — the base Michi wheel stays usable without it."""

    def __init__(self) -> None:
        _RuntimeFailureRelayMixin.__init__(self)
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
        close(). AR-12: activation performs the engine health step (GI/Gst
        loaded, playbin3 factory, pump started) — READY must mean the
        runtime is genuinely operational, never an empty Python adapter."""
        if self._port is not None:
            return self._port
        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerAudioPort,
        )

        port = GStreamerAudioPort()
        port.activate()  # health gate: raises truthfully if the runtime
        # cannot come up (provider.open() failure → coordinator FAILED)
        self._port = port
        self._bump_runtime_generation()
        owned_generation = self._runtime_generation
        # AR-11: pump-death telemetry relay (same seam contract as MPD)
        port.set_runtime_failure_callback(
            lambda port_generation, reason: self._relay_owned_gst_failure(
                owned_generation, reason
            )
        )
        return port

    def _relay_owned_gst_failure(self, owned_generation: int, reason: str) -> None:
        """AR-11: pump loss of the CURRENTLY OWNED incarnation is a fatal
        engine runtime failure; a stale generation is ignored."""
        if self._runtime_generation != owned_generation:
            return
        self.emit_runtime_failure(reason)

    def close(self) -> None:
        """Idempotent, exception-safe: ownership released in finally."""
        port = self._port
        if port is None:
            return
        # AR-05: ownership released ONLY on proven success (see Qt close).
        port.close()
        self._port = None
        self._invalidate_runtime_generation()


class MpdEngineProvider(_RuntimeFailureRelayMixin, AudioEngineProviderPort):
    """MPD as a MANAGED PRIVATE child process behind AudioPort (M11.3D).

    probe() is SIDE-EFFECT FREE: it only checks the executable is
    discoverable — it NEVER spawns MPD, never creates runtime dirs or
    sockets, never attaches to a system daemon and never inspects
    /run/mpd, /etc/mpd.conf or ~/.config/mpd."""

    # AR-09/AR-39: probe evidence cache keyed by executable identity
    # (resolved path + mtime/size). `mpd --version` is dependency
    # inspection, not engine activation — cached so Settings refresh
    # stays responsive without re-launching the binary on every probe.
    _probe_cache: dict[tuple[str, int, int], tuple[bool, str | None]] = {}

    def __init__(self) -> None:
        _RuntimeFailureRelayMixin.__init__(self)
        self._port = None

    @property
    def engine_id(self) -> AudioEngineId:
        return AudioEngineId.MPD

    def probe(self) -> AudioEngineDescriptor:
        import shutil  # noqa: PLC0415 - stdlib, import-time cheap

        from michi.infrastructure.audio_engines.mpd import (
            MpdOutputPluginDiscoveryError,
            _discover_mpd_output_plugins,
            _select_default_mpd_output_plugin,
        )

        path = shutil.which("mpd")
        if path is None:
            return AudioEngineDescriptor(
                engine_id=self.engine_id,
                display_name=_MPD_DISPLAY,
                available=False,
                unavailable_reason="mpd executable no encontrado en PATH",
                implemented=True,
                capabilities=AudioEngineCapabilities(
                    local_file_playback=True,
                    seek=True,
                    pause=True,
                    volume=True,
                    mute=True,
                ),
            )
        # AR-09: an executable alone is NOT activatable — at least one
        # supported default-system-output plugin (pipewire/pulse/alsa) must
        # be compiled in. Bounded `mpd --version` inspection, side-effect
        # free (no daemon, no socket, no runtime dir), cached by identity.
        try:
            stat = os.stat(path)
            key = (path, stat.st_mtime_ns, stat.st_size)
        except OSError:
            key = (path, 0, 0)
        if key not in MpdEngineProvider._probe_cache:
            try:
                compiled = _discover_mpd_output_plugins(path)
                _select_default_mpd_output_plugin(compiled)
                MpdEngineProvider._probe_cache[key] = (True, None)
            except MpdOutputPluginDiscoveryError as exc:
                MpdEngineProvider._probe_cache[key] = (False, str(exc))
        available, reason = MpdEngineProvider._probe_cache[key]
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

        Si la inicialización falla, no queda ningún port a medio abrir.

        P1-03 generation ownership: la generación del PROVIDER identifica la
        encarnación del runtime owned (open/close/reopen). El callback se
        re-asocia DESPUÉS del open capturando ESA generación — la generación
        interna del port (dominio separado) nunca se compara con la del
        provider."""
        if self._port is not None:
            return self._port
        from michi.infrastructure.audio_engines.mpd import MPDAudioPort

        port = MPDAudioPort()
        port.open()  # failure-atomic: si falla, el runtime se limpia solo
        self._port = port
        self._bump_runtime_generation()
        owned_generation = self._runtime_generation
        # closure por-open: captura la generación del PROVIDER en el momento
        # del open; el int del port (primer arg) es su dominio interno.
        port.set_runtime_failure_callback(
            lambda _port_generation, reason: self._relay_owned_mpd_failure(
                owned_generation, reason
            )
        )
        return port

    def close(self) -> None:
        """R1-01: the ownership handle is released ONLY after port.close()
        is PROVEN successful. A failed close (e.g. MpdOwnershipTeardownError)
        retains the SAME port and the runtime generation — retryable and
        diagnosable; the provider never discards a still-open runtime."""
        port = self._port
        if port is None:
            return
        port.close()
        # ONLY AFTER PROVEN SUCCESS:
        self._port = None
        self._invalidate_runtime_generation()

    def _relay_owned_mpd_failure(self, owned_generation: int, reason: str) -> None:
        """P1-03: publica el fatal runtime loss SOLO si la encarnación del
        provider que capturó esta closure es la actual (generación del
        provider, no del port). Un evento tardío de un runtime cerrado tras
        reopen queda stale y se ignora."""
        if owned_generation != self._runtime_generation:
            return  # stale: encarnación anterior del provider
        self.emit_runtime_failure(reason)
