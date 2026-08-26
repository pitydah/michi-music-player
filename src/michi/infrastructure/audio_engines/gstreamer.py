"""GStreamer AudioPort transport (M11.3C / M11.3C-R1 / M11.3C-R4).

Lazy PyGObject/GI bindings, infrastructure-only. The adapter owns ONE GLib
MainContext/MainLoop/pump thread per port; the bounded position timer is an
explicitly attached GSource on that custom context, and the current Gst.Bus
watch is installed with Gst.Bus.add_watch while the port's custom
MainContext is thread-default (removed with Gst.Bus.remove_watch(), which
takes NO watch-id argument). Bus messages are translated with a
GENERATION-AWARE provenance policy (per message type), delivered to the
owner thread via a Qt signal bridge (QueuedConnection) — same
thread-affinity as QtMultimediaBackend.

NO GStreamer types leave this module.
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal

from michi.application.ports import (
    AudioPort,
    AudioTransportCommandError,
    AudioTransportUnavailableError,  # canonical (ports.py)
)
from michi.domain.playback import PlaybackStatus

_logger = logging.getLogger(__name__)

_POSITION_POLL_MS = 500


class GStreamerBindings:
    """Lazy GObject Introspection facade for GStreamer (production).

    Encapsulates ALL GI-specific mechanics: state enums, MainContext/GSource
    attachment, bus watches, timeout sources, message parsing. The adapter
    orchestrates lifecycle through this surface only."""

    def __init__(self) -> None:
        self._gst = None
        self._glib = None
        self._init_error: Exception | None = None

    def ensure_loaded(self) -> None:
        """Lazy GI load — never at import time. Raises ImportError with the
        truthful cause when gi/GStreamer is unavailable."""
        if self._gst is not None:
            return
        if self._init_error is not None:
            raise self._init_error
        try:
            import gi  # noqa: PLC0415 - lazy optional system capability

            gi.require_version("Gst", "1.0")
            gi.require_version("GLib", "2.0")
            from gi.repository import GLib, Gst  # noqa: PLC0415

            Gst.init(None)
            self._gst = Gst
            self._glib = GLib
        except (ImportError, ValueError) as exc:
            self._init_error = exc
            raise

    def supports_pump(self) -> bool:
        """Production bindings own a GLib pump; test fakes deliver directly."""
        return True

    # ------------------------------------------------------------------
    # GStreamer runtime truth (M11.3C-R1)
    # ------------------------------------------------------------------

    def playbin3_available(self) -> bool:
        """playbin3 factory exists in the installed runtime."""
        return self.element_factory_find("playbin3") is not None

    def element_factory_find(self, name):
        """ElementFactory.find del runtime real (None si la factory falta)."""
        self.ensure_loaded()
        return self._gst.ElementFactory.find(name)

    # ------------------------------------------------------------------
    # pipeline / bus surface (objects are opaque; duck-typed)
    # ------------------------------------------------------------------

    def make_playbin3(self):
        self.ensure_loaded()
        return self._gst.ElementFactory.make("playbin3", "michi_gst_port")

    def set_state(self, pipeline, state) -> bool:
        self.ensure_loaded()
        return pipeline.set_state(state) != self._gst.StateChangeReturn.FAILURE

    def get_bus(self, pipeline):
        return pipeline.get_bus()

    # -- GLib event machinery (M11.3C-R1: explicit GSource ownership) --

    def create_context(self):
        return self._glib.MainContext.new()

    def create_loop(self, context):
        return self._glib.MainLoop.new(context, False)

    def run_loop(self, loop):
        loop.run()

    def quit_loop(self, loop):
        loop.quit()

    def push_thread_default(self, context):
        context.push_thread_default()

    def pop_thread_default(self, context):
        context.pop_thread_default()

    def create_bus_source(self, bus, callback, context=None) -> int:
        """Bus watch canónico attachado al context indicado.

        M11.3C-R3: bus.create_watch()+source.set_callback() NUNCA entrega
        el message en PyGObject — el dispatch de GstBusSource invoca la
        GSourceFunc como (user_data) y el mensaje se pierde (llega None),
        silenciando TODO el runtime real. bus.add_watch() registra la
        GstBusFunc con el marshaller correcto; ejecutado con el
        thread-default del context custom (el pump), el source queda
        attachado a ESE context y el pump lo despacha. Devuelve el watch
        id; quitar con remove_bus_watch()."""
        self.ensure_loaded()
        if context is not None:
            context.push_thread_default()
        try:
            return bus.add_watch(self._glib.PRIORITY_DEFAULT, callback)
        finally:
            if context is not None:
                context.pop_thread_default()

    def remove_bus_watch(self, bus) -> bool:
        """Gst.Bus.remove_watch() contract — NO watch-id argument (M11.3C-R4).

        The add_watch() return value is a source ID for bookkeeping only;
        Gst.Bus.remove_watch() takes no argument and returns True on
        success. Passing an id raises TypeError — NEVER suppressed: a
        lifecycle API mismatch must not silently become success."""
        self.ensure_loaded()
        return bool(bus.remove_watch())

    def attach_source(self, source, context) -> int:
        return source.attach(context)

    def destroy_source(self, source) -> None:
        from contextlib import suppress

        with suppress(Exception):
            source.destroy()  # source ya destruido o contexto muerto

    def create_timeout_source(self, interval_ms: int, callback):
        source = self._glib.timeout_source_new(interval_ms)
        source.set_callback(callback)
        return source

    def iteration(self, context, blocking: bool) -> bool:
        return self._glib.MainContext.iteration(context, blocking)

    def query_position(self, pipeline):
        ok, position = pipeline.query_position(self._gst.Format.TIME)
        return bool(ok), int(position)

    def query_duration(self, pipeline):
        ok, duration = pipeline.query_duration(self._gst.Format.TIME)
        return bool(ok), int(duration)

    def seek(self, pipeline, position_ns: int) -> bool:
        return bool(
            pipeline.seek_simple(
                self._gst.Format.TIME,
                self._gst.SeekFlags.FLUSH | self._gst.SeekFlags.KEY_UNIT,
                position_ns,
            )
        )

    def set_uri(self, pipeline, uri: str) -> None:
        pipeline.set_property("uri", uri)

    def set_volume(self, pipeline, value: float) -> None:
        pipeline.set_property("volume", value)

    def set_muted(self, pipeline, muted: bool) -> None:
        pipeline.set_property("mute", muted)

    # -- message parsing --

    def message_type(self, message) -> str:
        return message.type

    def parse_error(self, message):
        err, _debug = message.parse_error()
        return str(err.message) if err is not None else "gstreamer error"

    def message_is_from_pipeline(self, message, pipeline) -> bool:
        return message.src is pipeline

    def state_of(self, message):
        """Nuevo estado de un mensaje STATE_CHANGED (o None si no aplica).

        M11.3C-R6.2: PyGObject devuelve una TUPLA (old, new, pending) —
        `parse_state_changed().new` falla siempre (AttributeError → None) y
        ningún estado real se publicaba. Desempaquetar la tupla.
        M11.3C-R6.3: un fallo INESPERADO del parse no desaparece sin
        diagnóstico (log warning con la causa)."""
        try:
            _old, new, _pending = message.parse_state_changed()
            return new
        except Exception as exc:  # noqa: BLE001 — defensive parse boundary
            _logger.warning("gstreamer state_of: parse_state_changed failed: %s", exc)
            return None

    # -- enums (canonical real GStreamer values) --

    @property
    def STATE(self):  # noqa: N802 — GStreamer enum surface
        return self._gst.State

    @property
    def MESSAGE_TYPE(self):  # noqa: N802 — GStreamer enum surface
        return self._gst.MessageType


def millis_to_gst_time(ms: int) -> int:
    """Michi milliseconds → GStreamer TIME nanoseconds (1 ms = 1e6 ns)."""
    return int(ms) * 1_000_000


def gst_time_to_millis(ns: int) -> int:
    """GStreamer TIME nanoseconds → Michi milliseconds."""
    return int(ns) // 1_000_000


class _GstEventKind(Enum):
    """Tipos de observación backend normalizada (M11.3C-R6.5)."""

    ASYNC_DONE = auto()
    STATE_CHANGED = auto()
    ERROR = auto()
    EOS = auto()
    DURATION_CHANGED = auto()
    POSITION_TICK = auto()


@dataclass(frozen=True, slots=True)
class _GstEvent:
    """Envelope inmutable de observación backend (M11.3C-R6.5).

    El pump GLib SOLO observa/normaliza y encola este snapshot; el commit
    semántico ocurre en el hilo owner tras revalidar la generación."""

    generation: int | None
    kind: _GstEventKind
    status: PlaybackStatus | None = None
    reason: str | None = None


class _EventBridge(QObject):
    """Qt signal bridge: ONE asynchronous boundary (M11.3C-R6.5.1).

    El pump emite sig_event con QueuedConnection explícito (única frontera
    asíncrona pump → owner). Tras el commit del owner, los callbacks
    públicos se publican DIRECTAMENTE (misma transacción del owner) — no
    existe segunda cola sin provenance."""

    sig_event = Signal(object)
    # AR-11: pump death telemetry (pump thread → owner thread).
    sig_pump_died = Signal(int, str)


class GStreamerAudioPort(AudioPort):
    """playbin3 transport behind the canonical AudioPort contract.

    ONE GLib MainContext/MainLoop/pump thread per port (created once);
    each load() replaces the pipeline and its Gst.Bus watch installed
    through Gst.Bus.add_watch() while the port's custom MainContext is
    thread-default, capturing the current generation in the bus callback.
    The bounded position timer remains an explicit GSource owned by the
    custom context. Messages are processed by a type-aware provenance
    policy. close() terminates everything (best-effort, first-error-wins).
    """

    def __init__(self, bindings: GStreamerBindings | None = None) -> None:
        super().__init__()
        self._bridge = _EventBridge()
        self._bindings = bindings if bindings is not None else GStreamerBindings()
        self._generation = 0
        self._closed = False
        self._pending_path: Path | None = None
        self._current_path: Path | None = None
        self._pending_play = False
        self._current_state = PlaybackStatus.STOPPED
        self._eos_emitted = False
        # observaciones diferidas owner-thread, generación-escoped (R6.5)
        self._deferred_playing_generation: int | None = None
        self._deferred_eos_generation: int | None = None
        self._duration_refresh_generation: int | None = None
        self._volume = 1.0
        self._muted = False
        self._pipeline = None
        self._bus = None
        self._bus_source = None
        self._bus_source_attached = False
        self._timer_source = None
        self._context = None
        self._loop = None
        self._pump: threading.Thread | None = None
        self._pump_start_count = 0
        self._closing = False  # R1-03: close in progress (retryable)
        # load-command ownership epoch (GATE 1)
        self._load_epoch = 0
        # consumer registrations
        self._eom: list = []
        self._pos: list = []
        self._dur: list = []
        self._acc: list = []
        self._rej: list = []
        self._pst: list = []
        # explicit QueuedConnection: pump thread → owner thread — LA ÚNICA
        # frontera asíncrona (M11.3C-R6.5.1). Los callbacks públicos se
        # publican directo desde el owner (sin segunda cola).
        self._bridge.sig_event.connect(self._on_backend_event, Qt.QueuedConnection)
        # AR-11: runtime-failure telemetry seam (provider relays it into the
        # convergence coordinator through the canonical event type).
        self._runtime_failure_callback: Callable[[int, str], None] | None = None
        self._bridge.sig_pump_died.connect(self._on_pump_died, Qt.QueuedConnection)

    # ------------------------------------------------------------------
    # runtime-failure telemetry (AR-11)
    # ------------------------------------------------------------------

    def set_runtime_failure_callback(
        self, callback: Callable[[int, str], None] | None
    ) -> None:
        """Re-asocia el seam de fallo de runtime (mismo contrato que MPD):
        recibe (generación del port, razón). El provider captura SU
        generación en el closure y decide si el evento es stale."""
        self._runtime_failure_callback = callback

    def _on_pump_died(self, generation: int, reason: str) -> None:
        if self._closed:
            return  # expected close-time exit — never a runtime failure
        if generation != self._generation:
            return  # stale generation — ignored
        cb = self._runtime_failure_callback
        if cb is not None:
            cb(generation, reason)

    def activate(self) -> None:
        """AR-12: activation health — READY must mean the engine runtime is
        genuinely operational. Ensures GI/Gst loaded, the playbin3 factory
        exists and the pump context/loop/thread are started. Never loads
        music; never opens a DAC; no M11.4 work."""
        if self._closed:
            raise RuntimeError("GStreamerAudioPort cerrado")
        self._bindings.ensure_loaded()
        if not self._bindings.playbin3_available():
            raise RuntimeError(
                "GStreamer activation failed: playbin3 factory not available"
            )
        self._ensure_pump()
        if self._pump is None or not self._pump.is_alive():
            raise RuntimeError("GStreamer activation failed: pump did not start")

    # ------------------------------------------------------------------
    # lifecycle — ONE pump per port (M11.3C-R1)
    # ------------------------------------------------------------------

    def _ensure_pump(self):
        """Create the pump/context/loop ONCE (never per load)."""
        if self._pump is not None:
            return
        if self._closed:
            raise RuntimeError("GStreamerAudioPort cerrado")
        self._bindings.ensure_loaded()
        self._context = self._bindings.create_context()
        self._loop = self._bindings.create_loop(self._context)
        self._pump_start_count += 1
        self._pump_entered_run = threading.Event()
        self._pump = threading.Thread(
            target=self._pump_run, name="michi-gst-pump", daemon=True
        )
        self._pump.start()

    def _pump_run(self) -> None:
        self._bindings.push_thread_default(self._context)
        try:
            # AR-12 race fix: GLib quit() before run_loop is a no-op — the
            # close path waits (bounded) for this event before quitting.
            self._pump_entered_run.set()
            self._bindings.run_loop(self._loop)
        finally:
            self._bindings.pop_thread_default(self._context)
            # AR-11: a pump that exits while the port is NOT closing is an
            # unexpected engine runtime loss — telemetry is emitted once on
            # the owner thread (QueuedConnection) with the current
            # generation; stale/close-time exits are ignored by the owner.
            if not self._closed:
                self._bridge.sig_pump_died.emit(
                    self._generation, "gstreamer pump exited unexpectedly"
                )

    def _attach_pipeline_sources(self, pipeline, bus, generation: int) -> None:
        """Instala el bus watch y el timer de posición en el context custom.

        El bus se instala con Gst.Bus.add_watch() (GstBusFunc correcta en
        PyGObject) mientras el context del pump es thread-default; el timer
        de posición es un GSource GLib explícito attachado al mismo context.
        El callback del bus captura la generación vigente."""

        def on_bus_message(bus_, message, user_data=None):
            # el callback captura pipeline Y generación del watch (R6.5):
            # la provenance top-level usa el pipeline CAPTURADO, nunca un
            # self._pipeline que pueda cambiar concurrentemente
            self._process_message(message, generation, pipeline)
            return True  # keep source

        self._bus_source = self._bindings.create_bus_source(
            bus, on_bus_message, self._context
        )
        self._bus_source_attached = True
        if self._timer_source is None:

            def on_timer():
                self._poll_position()
                return True  # keep timer

            self._timer_source = self._bindings.create_timeout_source(
                _POSITION_POLL_MS, on_timer
            )
            self._bindings.attach_source(self._timer_source, self._context)

    def _detach_pipeline_sources(self) -> None:
        """Remove the current bus watch with truthful result semantics.

        M11.3C-R4: a failed (or impossible) watch removal raises — the
        lifecycle cleanup must never be silently claimed as successful.
        Callers decide how the failure composes with their own errors."""
        if self._bus_source is not None:
            if self._bus is None:
                raise RuntimeError("GStreamer bus watch exists without owning bus")
            if not self._bindings.remove_bus_watch(self._bus):
                raise RuntimeError("GStreamer bus watch could not be removed")
            self._bus_source = None
            self._bus_source_attached = False
        self._bus = None

    def _poll_position(self) -> None:
        """GLib timer (pump): enqueue POSITION_TICK — el OWNER resuelve
        contra su verdad actual (nunca posición para media pendiente o
        pipelines no aceptados). Sin lecturas semánticas cross-thread."""
        if self._closed:
            return
        self._bridge.sig_event.emit(
            _GstEvent(generation=None, kind=_GstEventKind.POSITION_TICK)
        )

    # ------------------------------------------------------------------
    # AudioPort — transport commands (symbolic states only)
    # ------------------------------------------------------------------

    def load(self, file_path: Path) -> None:
        # KCR-008: a closed runtime rejects the command — never a silent
        # no-op return.
        if self._closed:
            raise AudioTransportUnavailableError(
                "GStreamer load on closed transport"
            )
        self._bindings.ensure_loaded()
        if not self._bindings.playbin3_available():
            raise RuntimeError("playbin3 no disponible en el runtime GStreamer")
        # GATE 1 — load-command ownership token
        self._load_epoch += 1
        my_load_epoch = self._load_epoch
        # PHASE A — REPLACE OLD (M11.3C-R3 transactional): la fuente actual
        # sigue siendo canónica HASTA que el teardown tenga éxito. NINGUNA
        # mutación de estado (generation/pending/current/pending_play) antes
        # del commit point: si el pipeline A no llega a NULL, A permanece
        # dueño (pipeline + bus observables) y NO se crea B.
        if not self._try_stop_pipeline():
            raise RuntimeError("pipeline anterior no pudo transicionar a NULL")
        self._current_path = None
        self._eos_emitted = False
        self._pending_play = False
        # token de transacción del load (M11.3C-R6.5.2): la convergencia
        # STOPPED es un callback DIRECTO — un subscriber puede reentrar con
        # load(C)/stop()/close() antes del ARM de B
        my_generation = self._generation
        # CONVERGENCIA (M11.3C-R6): el teardown del source activo A dejó el
        # transporte STOPPED. Converger AHORA (no depender de un
        # STATE_CHANGED del pipeline viejo ya desacoplado) para que un fallo
        # posterior del ARM de B no deje un PLAYING falso en la app.
        self._deliver_state_if(PlaybackStatus.STOPPED)
        # REVALIDACIÓN post-callback (M11.3C-R6.5.2 / GATE 1): el subscriber
        # del STOPPED pudo reentrar (load(C)/stop()/close()) y ya no somos
        # dueños de la transacción → NUNCA armar B sobre la transacción nueva
        if (
            self._closed
            or my_load_epoch != self._load_epoch
            or self._generation != my_generation
        ):
            return
        # PHASE B — ARM NEW (M11.3C-R6 exception-atomic): el commit point
        # (teardown OK de A) ya pasó. CUALQUIER excepción normal durante la
        # construcción/configuración/attach/preroll-request del pipeline B
        # dispara un rollback best-effort y re-lanza la excepción ORIGINAL
        # como primaria (los fallos de limpieza son secundarios).
        self._invalidate_generation()
        self._pending_path = Path(file_path)
        self._current_path = None
        self._eos_emitted = False
        self._pending_play = False
        timer_before = self._timer_source
        paused_accepted = False
        try:
            self._ensure_pump()
            pipeline = self._bindings.make_playbin3()
            if pipeline is None:
                raise RuntimeError("playbin3 no disponible")
            self._pipeline = pipeline
            self._bindings.set_volume(pipeline, self._volume)
            self._bindings.set_muted(pipeline, self._muted)
            self._bus = self._bindings.get_bus(pipeline)
            self._bindings.set_uri(pipeline, Path(file_path).resolve().as_uri())
            if self._bindings.supports_pump():
                self._attach_pipeline_sources(pipeline, self._bus, self._generation)
            else:
                # test seam: mensajes entregados manualmente
                self._bus_source = None
                self._bus_source_attached = False
            # preroll request: un RAISE aquí es un ARM exception (rollback);
            # un False controlado es el preroll failure path (abajo)
            paused_accepted = self._request_state(self._bindings.STATE.PAUSED)
        except Exception as arm_exc:  # noqa: BLE001 — ARM transaction boundary
            self._rollback_failed_arm(arm_exc, timer_before)
            # M11.3C-R6.1: el PHASE A (teardown del source viejo) ya cruzó
            # su commit point destructivo → la fuente previa NO está
            # garantizada. La disposición debe ser explícita para que
            # PlaybackService no restaure aceptación falsa.
            from michi.application.ports import AudioLoadError

            raise AudioLoadError(
                Path(file_path),
                str(arm_exc),
                previous_source_preserved=False,
            ) from arm_exc
        if not paused_accepted:
            reason = "GStreamer failed to enter PAUSED during preroll"
            candidate = self._pending_path
            self._pending_path = None
            self._current_path = None
            self._pending_play = False
            self._eos_emitted = False
            # M11.3C-R6.5.2 (BLOCKER A): el CLEANUP COMPLETO de B ocurre
            # ANTES del callback media_rejected — un subscriber reentrante
            # puede arrancar C y el cleanup viejo NUNCA debe tocar campos
            # globales nuevos (self._pipeline/_bus/_bus_source ya serían de
            # C). El cleanup opera sobre el ownership LOCAL de B.
            # FIRST LIFECYCLE CLEANUP ERROR WINS (M11.3C-R5 P1-02): el NULL
            # cleanup es PRIMARIO; el detach es SECUNDARIO.
            primary_cleanup_error = None
            if not self._bindings.set_state(pipeline, self._bindings.STATE.NULL):
                primary_cleanup_error = RuntimeError(
                    "pipeline fallido no pudo transicionar a NULL durante la "
                    "limpieza de preroll"
                )
            try:
                self._detach_pipeline_sources()
            except Exception as exc:  # noqa: BLE001 — deliberate best-effort
                # cleanup boundary: ANY normal infrastructure exception must
                # be recorded, never allowed to replace the primary cleanup
                # error. BaseException is NOT caught.
                if primary_cleanup_error is None:
                    primary_cleanup_error = exc
                # si el NULL ya falló, el error del bus queda como falla
                # secundaria: no reemplaza al primario
            if primary_cleanup_error is None:
                self._pipeline = None
            # cleanup COMPLETO → recién ahora el callback público (R6.5.2):
            # ningún código viejo de B se ejecutará después del callback
            if candidate is not None:
                self._deliver_rej(candidate, reason)
            # un cleanup error capturado puede raise DESPUÉS del callback
            # (no muta estado, no daña una transacción C reentrante)
            if primary_cleanup_error is not None:
                raise primary_cleanup_error
            return

    def play(self) -> None:
        if self._closed or self._pipeline is None:
            raise AudioTransportUnavailableError(
                "GStreamer play on closed/uninitialized transport"
            )
        if self._eos_emitted:
            # REPLAY desde EOS (M11.3C-R6 P1-02): un pipeline en EOS no
            # reinicia solo con PLAYING — restart controlado NULL → PLAYING,
            # sin pipeline nuevo ni segundo media_accepted (la fuente ya fue
            # aceptada). Failure-atomic: el marcador EOS se resetea SOLO
            # cuando el request PLAYING tuvo éxito (retryable en ambos
            # fallos).
            if not self._request_state(self._bindings.STATE.NULL):
                return  # _eos_emitted queda True; retry posterior posible
            if not self._request_state(self._bindings.STATE.PLAYING):
                return  # sin intención commiteada; retry posterior posible
            self._pending_play = True
            self._eos_emitted = False
            return
        if self._pending_path is not None and self._current_path is None:
            # CASO A — CANDIDATE PENDING (M11.3C-R6.3/R6.4): un fallo del
            # request PLAYING — por RAISE de excepción O por retorno
            # Gst.StateChangeReturn.FAILURE (False) — deja al candidato B
            # TERMINAL en el backend (failure-atomic). La falla de PLAYING
            # es PRIMARIA; los fallos de cleanup son SECUNDARIOS. Sin esto,
            # PlaybackService limpiaría B localmente pero el backend seguiría
            # poseyéndolo (pipeline/generación/bus vigentes → eventos
            # tardíos válidos, candidato pending indefinido).
            try:
                play_ok = self._request_state(self._bindings.STATE.PLAYING)
            except Exception as play_exc:  # noqa: BLE001 — command boundary
                self._cancel_pending_candidate_after_failure()
                raise play_exc
            if not play_ok:
                # CHANNEL B: GStreamer rechazó explícitamente la transición
                # (StateChangeReturn.FAILURE) — FAILURE return IS FAILURE.
                self._cancel_pending_candidate_after_failure()
                raise RuntimeError(
                    "GStreamer failed to enter PLAYING for pending candidate"
                )
            self._pending_play = True
            return
        # CASO B — ACCEPTED SOURCE: un fallo de play() sobre la fuente
        # aceptada NO cancela el candidato (no existe) ni descarga la
        # fuente (semánticas R6 stop/replay/EOS retryable intactas). La
        # intención NO se commitea sin éxito; y el fallo es EXPLÍCITO
        # (AR-13): el caller nunca ve un play() "exitoso" que no lo fue.
        if not self._request_state(self._bindings.STATE.PLAYING):
            raise AudioTransportCommandError(
                "GStreamer failed to enter PLAYING (accepted source)"
            )
        self._pending_play = True

    def _cancel_pending_candidate_after_failure(self) -> None:
        """Terminaliza un candidato pendiente tras un fallo del comando
        play() (M11.3C-R6.3/R6.4). Se invoca cuando el request PLAYING
        sobre el candidato O RAISE o REPORTA FAILURE (False). Misma
        semántica que la cancelación por stop() de un candidato pendiente,
        con first-error-wins: NO lanza (la falla del play es la primaria).
        La generación del candidato se invalida SIEMPRE — ningún evento
        tardío de B puede quedar autoritativo aunque el cleanup físico
        falle (ownership residual = ancla retryable, nunca media válida)."""
        self._invalidate_generation()
        self._pending_path = None
        self._current_path = None
        self._pending_play = False
        self._eos_emitted = False
        # Cleanup físico best-effort: NULL + detach. Tanto el retorno False
        # como un RAISE son fallos de limpieza — el ownership queda retenido
        # truthfully (retryable) y se registra un diagnóstico acotado.
        try:  # noqa: SIM105 — no se usa suppress: el ownership residual debe
            # seguir siendo observable en el bookkeeping (retryable)
            cleanup_ok = self._try_stop_pipeline()  # NULL + detach
        except Exception as exc:  # noqa: BLE001 — cleanup secondary
            _logger.warning(
                "gstreamer: pending candidate cleanup raised (retaining "
                "retryable ownership): %s",
                exc,
            )
            return
        if not cleanup_ok:
            _logger.warning(
                "gstreamer: pending candidate cleanup could not reach NULL; "
                "retaining retryable ownership"
            )

    def pause(self) -> None:
        if self._closed or self._pipeline is None:
            raise AudioTransportUnavailableError(
                "GStreamer pause on closed/uninitialized transport"
            )
        previous_intent = self._pending_play
        if not self._request_state(self._bindings.STATE.PAUSED):
            self._pending_play = previous_intent  # rollback de intención
            raise AudioTransportCommandError("GStreamer failed to enter PAUSED")
        self._pending_play = False

    def resume(self) -> None:
        self.play()

    def stop(self) -> None:
        self._load_epoch += 1
        if self._closed:
            raise AudioTransportUnavailableError("GStreamer stop on closed transport")
        if self._pipeline is None:
            # Vacuously stopped: nothing owned to stop (reentrancy-safe —
            # a stop arriving during a load transition has no pipeline yet;
            # stopping nothing IS stopping). AR-02 applies to an ACTIVE
            # pipeline whose NULL request fails.
            return
        if self._pending_path is not None and self._current_path is None:
            # CASE A — PENDING CANDIDATE (M11.3C-R6): stop = CANCEL del
            # candidato no aceptado. El pipeline candidato se libera y la
            # generación se invalida (mata aceptaciones tardías). Un fallo
            # del teardown es EXPLÍCITO (AR-02): stop() es safety-critical;
            # el caller debe poder distinguir "detenido" de "no pude".
            if not self._try_stop_pipeline():
                raise AudioTransportCommandError(
                    "GStreamer stop could not tear down the pending candidate"
                )
            self._invalidate_generation()
            self._pending_path = None
            self._pending_play = False
            self._eos_emitted = False
        else:
            # CASE B — ACCEPTED SOURCE (M11.3C-R6): stop = detener el
            # transporte, NO descargar la fuente. La fuente aceptada A
            # permanece cargada: current_path/generación/pipeline/bus watch
            # intactos → play()/resume() funcionan sin un nuevo load.
            if not self._request_state(self._bindings.STATE.NULL):
                # NULL falló: NO publicar STOPPED, NO limpiar el source como
                # si el stop hubiera tenido éxito; el fallo es EXPLÍCITO
                # (AR-02): el estado físico es incierto → fail closed.
                raise AudioTransportCommandError("GStreamer stop could not reach NULL")
            self._pending_play = False
            self._eos_emitted = False  # stop explícito resetea el marcador EOS
        self._deliver_state_if(PlaybackStatus.STOPPED)

    def set_volume(self, value: int) -> None:
        # KCR-008: closed runtime → typed error (never a silent commit)
        if self._closed:
            raise AudioTransportUnavailableError(
                "GStreamer set_volume on closed transport"
            )
        self._volume = value / 100.0
        if self._pipeline is not None:
            self._bindings.set_volume(self._pipeline, self._volume)

    def set_muted(self, muted: bool) -> None:
        if self._closed:
            raise AudioTransportUnavailableError(
                "GStreamer set_muted on closed transport"
            )
        self._muted = muted
        if self._pipeline is not None:
            self._bindings.set_muted(self._pipeline, muted)

    def seek(self, position_ms: int) -> None:
        if self._closed or self._pipeline is None:
            raise AudioTransportUnavailableError(
                "GStreamer seek on closed/uninitialized transport"
            )
        # AR-13: seek que el backend rechaza es un fallo EXPLÍCITO (nunca
        # éxito silencioso); la posición confirmada llega por observación.
        ok = self._bindings.seek(self._pipeline, millis_to_gst_time(position_ms))
        if not ok:
            raise AudioTransportCommandError("GStreamer seek rejected by the pipeline")

    def position(self) -> int:
        # KCR-008 table: CLOSED → UnavailableError; LIVE + NO SOURCE → real 0
        if self._closed:
            raise AudioTransportUnavailableError(
                "GStreamer position on closed transport"
            )
        if self._pipeline is None:
            return 0
        ok, ns = self._bindings.query_position(self._pipeline)
        if not ok or ns < 0:
            return 0
        return gst_time_to_millis(ns)

    def duration(self) -> int:
        if self._closed:
            raise AudioTransportUnavailableError(
                "GStreamer duration on closed transport"
            )
        if self._pipeline is None:
            return 0
        ok, ns = self._bindings.query_duration(self._pipeline)
        if not ok or ns < 0:
            return 0
        return gst_time_to_millis(ns)

    # ------------------------------------------------------------------
    # close / teardown
    # ------------------------------------------------------------------

    def close(self) -> None:
        """R1-03: retryable, failure-atomic close. `_closed == True` only
        after ALL teardown succeeded; a failure raises with ownership
        retained and `_closed` still False so a SECOND close retries the
        remaining teardown (resources already released are None-guarded)."""
        self._load_epoch += 1
        if self._closed:
            return
        self._closing = True
        self._invalidate_generation()  # in-flight messages stale
        # FIRST-ERROR-WINS (M11.3C-R3/R5): la secuencia canónica es
        # 1) invalidar generación, 2) teardown del pipeline (bus watch +
        # NULL, best-effort — un fallo de remoción NUNCA salta el request
        # NULL), 3) limpieza de sources, 4) quit del pump, 5) join. La
        # PRIMERA falla cronológica es la autoritativa; las posteriores
        # NUNCA reemplazan a la primaria. El teardown terminal ya no puede
        # lanzar: devuelve su primer error.
        primary_error = self._teardown_pipeline_terminal()
        # destroy timer + sources
        if self._timer_source is not None:
            self._bindings.destroy_source(self._timer_source)
            self._timer_source = None
        if self._pump is not None:
            if self._loop is not None:
                # GLib race (AR-12 evidence): a g_main_loop_quit issued
                # before the loop is poll-blocking can be lost, leaving the
                # pump stuck in run(). quit() is idempotent and thread-safe
                # — retry quit + bounded join until the pump is proven dead
                # (bounded shutdown verification, max ~1.6s).
                entered = getattr(self, "_pump_entered_run", None)
                if entered is not None:
                    entered.wait(timeout=1.0)
                for _ in range(4):
                    self._bindings.quit_loop(self._loop)
                    self._pump.join(timeout=0.4)
                    if not self._pump.is_alive():
                        break
            else:
                self._pump.join(timeout=0.4)
            if self._pump.is_alive():
                # NUNCA perder el ownership mientras el thread viva:
                # retener referencias y reportar (R2 P1-03)
                pump_error = RuntimeError("GStreamer pump thread did not terminate")
                if primary_error is None:
                    primary_error = pump_error
                # si ya hay un error primario (teardown), el timeout del
                # pump queda como falla secundaria: NO lo reemplaza.
            else:
                self._pump = None
                self._loop = None
                self._context = None
        self._pending_path = None
        self._current_path = None
        self._eom = []
        self._pos = []
        self._dur = []
        self._acc = []
        self._rej = []
        self._pst = []
        if primary_error is not None:
            raise primary_error  # _closed stays False → retryable
        # ONLY after the full chain succeeded:
        self._closed = True
        self._closing = False

    def _try_stop_pipeline(self) -> bool:
        """Reemplazo normal (load): NULL PRIMERO, detach SOLO tras éxito.

        Orden conceptual: NULL success → detach source → clear ownership.
        Si el request NULL devuelve FAILURE, el pipeline ANTERIOR permanece
        dueño con su bus source attachado (observabilidad intacta) y la
        generación/current_path siguen válidos — nunca un pipeline vivo sin
        su bus. Devuelve True si llegó a NULL (o no había pipeline)."""
        if self._pipeline is None:
            return True
        if not self._bindings.set_state(self._pipeline, self._bindings.STATE.NULL):
            return False
        self._detach_pipeline_sources()
        self._pipeline = None
        return True

    def _rollback_failed_arm(self, primary_exc, timer_before) -> None:
        """Rollback best-effort de un ARM de pipeline fallido (M11.3C-R6).

        El error ORIGINAL del arm (primary_exc) es la autoridad y lo
        re-lanza el caller; los fallos de limpieza aquí son SECUNDARIOS y
        nunca lo reemplazan. Deja el adapter coherente: sin candidato
        fantasma, sin watch huérfano, sin timer roto, sin ownership perdido.
        """
        # 1. invalidar la generación del candidato fallido: cualquier
        #    callback del bus ya attachado queda stale (captured != current)
        self._invalidate_generation()
        # 2. identidad semántica del candidato: sin media falsa
        self._pending_path = None
        self._current_path = None
        self._pending_play = False
        self._eos_emitted = False
        # 3. timer creado POR ESTE arm que nunca quedó válido/reutilizable:
        #    no dejar _timer_source != None con un timer nunca attachado
        if timer_before is None and self._timer_source is not None:
            self._bindings.destroy_source(self._timer_source)
            self._timer_source = None
        # 4. NULL best-effort del pipeline candidato (si existe)
        null_ok = True
        if self._pipeline is not None:
            try:
                null_ok = self._bindings.set_state(
                    self._pipeline, self._bindings.STATE.NULL
                )
            except Exception:  # noqa: BLE001 — best-effort rollback
                null_ok = False
        # 5. detach del bus watch best-effort; si falla, el bookkeeping del
        #    watch queda retenido (observable) para reintentar más tarde
        detach_ok = True
        try:  # noqa: SIM105 — no se usa suppress: la limpieza pendiente debe
            # seguir siendo observable en el bookkeeping del bus
            self._detach_pipeline_sources()
        except Exception:  # noqa: BLE001 — best-effort rollback
            detach_ok = False
        # 6. ownership truthful (M11.3C-R6.1): el pipeline es el ANCLA de
        #    limpieza retryable — se libera SOLO cuando el NULL Y el detach
        #    del watch completaron. NULL OK + detach FAIL → el pipeline se
        #    retiene (aunque su transporte ya esté NULL) para que close() o
        #    un próximo load() puedan reintentar la remoción del watch.
        #    Invariante: _pipeline is None IMPLICA _bus_source is None.
        if null_ok and detach_ok:
            self._pipeline = None

    def _teardown_pipeline_terminal(self) -> Exception | None:
        """Teardown TERMINAL best-effort (close). Devuelve el PRIMER error
        cronológico de limpieza, o None.

        M11.3C-R5: un error de cleanup NUNCA corta la secuencia. Aunque el
        detach del bus watch falle, el pipeline SIEMPRE recibe su request
        NULL; la referencia se retiene solo si NULL falla (ownership
        truthful). El pump/timer cleanup ocurre en close() después."""
        if self._pipeline is None:
            return None
        first_error = None
        try:
            self._detach_pipeline_sources()
        except Exception as exc:  # noqa: BLE001 — deliberate best-effort
            # cleanup boundary: ANY normal infrastructure exception (TypeError,
            # ValueError, GLib.Error, ...) must be recorded so the NULL
            # request is still attempted. BaseException is NOT caught.
            first_error = exc  # bus watch removal failure (o watch sin bus)
        # NON-NEGOTIABLE: el request NULL se intenta aunque el detach falle
        try:
            null_ok = self._bindings.set_state(
                self._pipeline, self._bindings.STATE.NULL
            )
        except Exception as exc:  # noqa: BLE001 — best-effort terminal
            if first_error is None:
                first_error = exc
        else:
            if null_ok:
                # transport detenido: el pipeline se libera aunque el
                # bookkeeping del bus watch quede como evidencia
                self._pipeline = None
            elif first_error is None:
                first_error = RuntimeError(
                    "pipeline no pudo transicionar a NULL durante close"
                )
        return first_error

    # ------------------------------------------------------------------
    # backend event pipeline — M11.3C-R6.5 owner-thread seal
    #
    # GLib PUMP = backend observation ONLY (translate → enqueue immutable
    # _GstEvent); QT OWNER = AudioPort semantic authority (revalidate
    # generation + lifecycle → commit → publish callbacks). El pump NUNCA
    # muta estado semántico: _pending_path/_current_path/_pending_play/
    # _current_state/_eos_emitted/_generation son owner-thread state.
    # ------------------------------------------------------------------

    def _process_message(
        self, message, captured_generation: int, captured_pipeline=None
    ) -> None:
        """PUMP (translate-only): normaliza una observación de bus en un
        _GstEvent inmutable y lo encola. CERO mutación semántica.

        PROVENANCE POLICY (no catch-all src rule):
        - STATE_CHANGED: top-level del pipeline CAPTURADO por este watch.
        - ERROR: cualquier elemento del grafo actual es válido (child-error).
        - EOS / ASYNC_DONE / DURATION_CHANGED: llevan la generación
          capturada; el owner decide en el commit point.
        """
        if self._closed:
            return
        if message is None:
            return  # bus source teardown puede entregar un mensaje null
        # check temprano de stale SOLO como optimización: la corrección la
        # garantiza el recheck del owner en el commit (R6.5)
        if captured_generation != self._generation:
            return
        msg_type = self._bindings.message_type(message)
        mt = self._bindings.MESSAGE_TYPE
        if msg_type == mt.EOS:
            self._bridge.sig_event.emit(
                _GstEvent(generation=captured_generation, kind=_GstEventKind.EOS)
            )
        elif msg_type == mt.ERROR:
            # child-element errors are valid for the current graph:
            # normalización de la razón en el pump, decisión en el owner
            reason = self._bindings.parse_error(message)
            self._bridge.sig_event.emit(
                _GstEvent(
                    generation=captured_generation,
                    kind=_GstEventKind.ERROR,
                    reason=reason,
                )
            )
        elif msg_type == mt.ASYNC_DONE:
            # NUNCA publica PLAYING y NUNCA commitea el candidato aquí:
            # la aceptación es un commit del owner (R6.5)
            self._bridge.sig_event.emit(
                _GstEvent(generation=captured_generation, kind=_GstEventKind.ASYNC_DONE)
            )
        elif msg_type == mt.STATE_CHANGED:
            # top-level del pipeline capturado por ESTE watch (no el
            # self._pipeline actual, que puede cambiar concurrentemente)
            if self._bindings.message_is_from_pipeline(message, captured_pipeline):
                status = self._normalize_state(message)
                if status is not None:
                    self._bridge.sig_event.emit(
                        _GstEvent(
                            generation=captured_generation,
                            kind=_GstEventKind.STATE_CHANGED,
                            status=status,
                        )
                    )
        elif msg_type == mt.DURATION_CHANGED:
            # sin query en el pump: el owner consulta en el commit point
            self._bridge.sig_event.emit(
                _GstEvent(
                    generation=captured_generation, kind=_GstEventKind.DURATION_CHANGED
                )
            )

    def _normalize_state(self, message) -> PlaybackStatus | None:
        """PUMP: Gst.State → PlaybackStatus normalizado (o None)."""
        state = self._bindings.state_of(message)
        if state is None:
            return None
        if state == self._bindings.STATE.PLAYING:
            return PlaybackStatus.PLAYING
        if state == self._bindings.STATE.PAUSED:
            return PlaybackStatus.PAUSED
        if state in (self._bindings.STATE.NULL, self._bindings.STATE.READY):
            return PlaybackStatus.STOPPED
        return None

    def _on_backend_event(self, event) -> None:
        """OWNER (único commit semántico): revalida closed + generación +
        lifecycle, commitea estado interno ANTES de publicar callbacks.

        Un evento que pasó el check temprano del pump pero quedó encolado
        mientras la generación cambiaba muere aquí (provenance en commit)."""
        if self._closed:
            return
        if event.generation is not None and event.generation != self._generation:
            return  # stale queued event
        kind = event.kind
        if kind == _GstEventKind.ASYNC_DONE:
            self._commit_acceptance(event)
        elif kind == _GstEventKind.STATE_CHANGED:
            self._commit_state(event)
        elif kind == _GstEventKind.EOS:
            self._commit_eos(event)
        elif kind == _GstEventKind.ERROR:
            self._commit_error(event)
        elif kind == _GstEventKind.DURATION_CHANGED:
            if self._pending_path is not None and self._current_path is None:
                # duración observada antes de la aceptación: refrescar
                # post-acceptance para esa generación (nunca antes)
                self._duration_refresh_generation = event.generation
                return
            self._publish_duration()
        elif kind == _GstEventKind.POSITION_TICK:
            self._publish_position()

    def _commit_acceptance(self, event) -> None:
        """OWNER: ASYNC_DONE = commit de aceptación del media.

        Orden (M11.3C-R6.5.1 NON-NEGOTIABLE): validar → capturar → commit
        interno → PUBLICACIÓN DIRECTA → revalidar tras el callback (el
        subscriber puede hacer load/stop/close) → solo entonces aplicar el
        trabajo diferido de la generación (sin segunda cola Qt)."""
        if self._pending_path is None:
            return  # duplicado o ya commiteado (idempotente)
        candidate = self._pending_path
        generation = event.generation
        self._current_path = candidate
        self._pending_path = None
        # estado interno ANTES del callback público (reentrancy-safe)
        self._deliver_acc(candidate)
        # REVALIDACIÓN post-callback: el subscriber pudo cambiar la
        # transacción (load/stop/close)
        if (
            self._closed
            or self._generation != generation
            or self._current_path != candidate
        ):
            return
        # PLAYING observado antes de la aceptación: aplicado directo solo
        # si la intención sigue permitiendo la publicación
        if self._pending_play and self._deferred_playing_generation == generation:
            self._apply_deferred_playing(generation)
        if self._deferred_eos_generation == generation:
            self._apply_deferred_eos(generation)
        if self._duration_refresh_generation == generation:
            self._apply_deferred_duration(generation)

    def _apply_deferred_playing(self, generation) -> None:
        """OWNER (directo, sin re-enqueue): PLAYING diferido tras la
        aceptación — revalidado contra la transacción vigente."""
        if self._closed or self._generation != generation:
            return
        if self._current_path is None:
            return
        self._deferred_playing_generation = None
        self._deliver_state_if(PlaybackStatus.PLAYING)

    def _apply_deferred_eos(self, generation) -> None:
        """OWNER (directo): EOS diferido hasta la aceptación — STOPPED
        primero, revalidación, y EOM como ÚLTIMA acción (un subscriber del
        STOPPED pudo cargar B/cerrar → EOM suprimido)."""
        if self._closed or self._generation != generation:
            return
        if self._current_path is None:
            return
        self._deferred_eos_generation = None
        self._eos_emitted = True
        self._pending_play = False
        self._deliver_state_if(PlaybackStatus.STOPPED)
        if (
            self._closed
            or self._generation != generation
            or self._current_path is None
            or not self._eos_emitted
        ):
            return
        self._deliver_eom()

    def _apply_deferred_duration(self, generation) -> None:
        """OWNER (directo): refresco de duración diferido hasta la
        aceptación, revalidado."""
        if self._closed or self._generation != generation:
            return
        if self._current_path is None:
            return
        self._duration_refresh_generation = None
        self._publish_duration()

    def _commit_state(self, event) -> None:
        """OWNER: STATE_CHANGED normalizado → PlaybackStatus canónico.

        PLAYING nunca es autoritativo antes de la aceptación del media
        (se difiere por generación). Preroll PAUSED con candidato pendiente
        no es user PAUSED."""
        status = event.status
        if status == PlaybackStatus.PLAYING:
            if self._pending_path is not None and self._current_path is None:
                # PLAYING temprano: diferir hasta la aceptación (R6.5)
                self._deferred_playing_generation = event.generation
                return
            self._deliver_state_if(PlaybackStatus.PLAYING)
        elif status == PlaybackStatus.PAUSED:
            if not self._pending_play and self._pending_path is None:
                self._deliver_state_if(PlaybackStatus.PAUSED)
        elif status == PlaybackStatus.STOPPED:
            self._deliver_state_if(PlaybackStatus.STOPPED)

    def _commit_eos(self, event) -> None:
        """OWNER: EOS = fin natural del media ACEPTADO actual — converge a
        STOPPED antes del EOM (guard de late-EOS vía _pending_play). Un EOS
        observado con el candidato aún pendiente se difiere por generación
        (nunca EOM antes de la aceptación)."""
        if self._pending_path is not None and self._current_path is None:
            self._deferred_eos_generation = event.generation
            return
        if (
            self._current_path is not None
            and self._pending_play
            and not self._eos_emitted
        ):
            generation = event.generation
            current = self._current_path
            self._eos_emitted = True
            self._pending_play = False
            self._deliver_state_if(PlaybackStatus.STOPPED)
            # REVALIDACIÓN (M11.3C-R6.5.1): el subscriber del STOPPED pudo
            # cargar B/cerrar/superseder A → EOM(A) suprimido. EOM es la
            # ÚLTIMA acción del commit EOS (sin mutación posterior).
            if (
                self._closed
                or self._generation != generation
                or self._current_path != current
                or not self._eos_emitted
            ):
                return
            self._deliver_eom()

    def _commit_error(self, event) -> None:
        """OWNER: ERROR de la generación vigente → rejection del candidato
        o de la fuente actual (child-error provenance preservado)."""
        reason = event.reason or "gstreamer error"
        candidate = self._pending_path or self._current_path
        if candidate is not None:
            self._pending_path = None
            self._current_path = None
            self._deliver_rej(candidate, reason)

    def _publish_duration(self) -> None:
        """OWNER: consulta la duración del pipeline VIGENTE y publica."""
        if self._pipeline is None:
            return
        ok, ns = self._bindings.query_duration(self._pipeline)
        if ok:
            self._deliver_dur(gst_time_to_millis(ns))

    def _publish_position(self) -> None:
        """OWNER: posición del source ACEPTADO actual únicamente (nunca
        media pendiente); se resuelve contra la verdad actual del owner."""
        pipeline = self._pipeline
        if pipeline is None or self._current_path is None:
            return
        ok, ns = self._bindings.query_position(pipeline)
        if ok:
            self._deliver_pos(gst_time_to_millis(ns))

    def _invalidate_generation(self) -> None:
        """OWNER: avanza la generación (monotónica, nunca decrece) y limpia
        las observaciones diferidas de la generación anterior (R6.5).

        La invalidación es para supersesión de transacciones, cancelación
        terminal de candidatos, reemplazo destructivo y close — NUNCA para
        stop/replay de un source aceptado."""
        self._generation += 1
        self._deferred_playing_generation = None
        self._deferred_eos_generation = None
        self._duration_refresh_generation = None

    def _request_state(self, state) -> bool:
        """State request failure-atomic: devuelve True solo si GStreamer
        aceptó la transición (no FAILURE)."""
        if self._pipeline is None:
            return False
        return self._bindings.set_state(self._pipeline, state)

    def _deliver_state_if(self, status: PlaybackStatus) -> None:
        if self._current_state is status:
            return
        self._current_state = status
        self._deliver_state(status)

    # ------------------------------------------------------------------
    # bridge slots (owner thread — QueuedConnection)
    # ------------------------------------------------------------------

    def _deliver_eom(self) -> None:
        for cb in list(self._eom):
            cb()

    def _deliver_pos(self, ms: int) -> None:
        for cb in list(self._pos):
            cb(ms)

    def _deliver_dur(self, ms: int) -> None:
        for cb in list(self._dur):
            cb(ms)

    def _deliver_acc(self, path) -> None:
        for cb in list(self._acc):
            cb(path)

    def _deliver_rej(self, path, reason: str) -> None:
        for cb in list(self._rej):
            cb(path, reason)

    def _deliver_state(self, status) -> None:
        for cb in list(self._pst):
            cb(status)

    # ------------------------------------------------------------------
    # AudioPort subscriptions (idempotent, symmetric unsubscribe)
    # ------------------------------------------------------------------

    def subscribe_end_of_media(self, cb) -> None:
        if cb not in self._eom:
            self._eom.append(cb)

    def unsubscribe_end_of_media(self, cb) -> None:
        if cb in self._eom:
            self._eom.remove(cb)

    def subscribe_position_changed(self, cb) -> None:
        if cb not in self._pos:
            self._pos.append(cb)

    def unsubscribe_position_changed(self, cb) -> None:
        if cb in self._pos:
            self._pos.remove(cb)

    def subscribe_duration_changed(self, cb) -> None:
        if cb not in self._dur:
            self._dur.append(cb)

    def unsubscribe_duration_changed(self, cb) -> None:
        if cb in self._dur:
            self._dur.remove(cb)

    def subscribe_media_accepted(self, cb) -> None:
        if cb not in self._acc:
            self._acc.append(cb)

    def unsubscribe_media_accepted(self, cb) -> None:
        if cb in self._acc:
            self._acc.remove(cb)

    def subscribe_media_rejected(self, cb) -> None:
        if cb not in self._rej:
            self._rej.append(cb)

    def unsubscribe_media_rejected(self, cb) -> None:
        if cb in self._rej:
            self._rej.remove(cb)

    def subscribe_playback_state_changed(self, cb) -> None:
        if cb not in self._pst:
            self._pst.append(cb)

    def unsubscribe_playback_state_changed(self, cb) -> None:
        if cb in self._pst:
            self._pst.remove(cb)


# ---------------------------------------------------------------------------
# Real-runtime smoke helpers (M11.3C-R3) — truthful SKIP/FAIL classification
# ---------------------------------------------------------------------------


def _probe_missing_runtime_dependencies(bindings) -> str | None:
    """First mandatory test-runtime factory absent from the real runtime.

    The real adapter smoke may SKIP only when a dependency is PROVEN
    missing before running the runtime expectation: a bare timeout does not
    prove missing plugins (M11.3C-R3 P1-04)."""
    for name in ("playbin3", "fakesink", "typefind", "wavparse"):
        if bindings.element_factory_find(name) is None:
            return name
    return None


def _smoke_outcome(missing_dependency, accepted, rejected) -> tuple:
    """Truthful real-smoke classification (testable seam, no real waits).

    - ("skip", dep) when a dependency is proven absent;
    - ("fail", reason) when dependencies exist but the real runtime did not
      accept (rejected, or acceptance timeout);
    - ("pass", None) otherwise.
    """
    if missing_dependency is not None:
        return ("skip", missing_dependency)
    if rejected:
        return (
            "fail",
            f"Real GStreamerAudioPort rejected smoke WAV: {rejected[0][1]}",
        )
    if not accepted:
        return (
            "fail",
            "Real GStreamerAudioPort did not accept the WAV within 2 seconds "
            "despite required runtime factories being available",
        )
    return ("pass", None)
