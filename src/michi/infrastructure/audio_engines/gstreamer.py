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

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal

from michi.application.ports import AudioPort
from michi.domain.playback import PlaybackStatus

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
        ningún estado real se publicaba. Desempaquetar la tupla."""
        try:
            _old, new, _pending = message.parse_state_changed()
            return new
        except Exception:
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


class _EventBridge(QObject):
    """Qt signal bridge: emitted from the pump thread, delivered on the
    owner thread via EXPLICIT QueuedConnection (M11.3C-R1)."""

    sig_eom = Signal()
    sig_pos = Signal(int)
    sig_dur = Signal(int)
    sig_acc = Signal(object)
    sig_rej = Signal(object, str)
    sig_state = Signal(object)


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
        # consumer registrations
        self._eom: list = []
        self._pos: list = []
        self._dur: list = []
        self._acc: list = []
        self._rej: list = []
        self._pst: list = []
        # explicit QueuedConnection: pump thread → owner thread
        self._bridge.sig_eom.connect(self._deliver_eom, Qt.QueuedConnection)
        self._bridge.sig_pos.connect(self._deliver_pos, Qt.QueuedConnection)
        self._bridge.sig_dur.connect(self._deliver_dur, Qt.QueuedConnection)
        self._bridge.sig_acc.connect(self._deliver_acc, Qt.QueuedConnection)
        self._bridge.sig_rej.connect(self._deliver_rej, Qt.QueuedConnection)
        self._bridge.sig_state.connect(self._deliver_state, Qt.QueuedConnection)

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
        self._pump = threading.Thread(
            target=self._pump_run, name="michi-gst-pump", daemon=True
        )
        self._pump.start()

    def _pump_run(self) -> None:
        self._bindings.push_thread_default(self._context)
        try:
            self._bindings.run_loop(self._loop)
        finally:
            self._bindings.pop_thread_default(self._context)

    def _attach_pipeline_sources(self, pipeline, bus, generation: int) -> None:
        """Instala el bus watch y el timer de posición en el context custom.

        El bus se instala con Gst.Bus.add_watch() (GstBusFunc correcta en
        PyGObject) mientras el context del pump es thread-default; el timer
        de posición es un GSource GLib explícito attachado al mismo context.
        El callback del bus captura la generación vigente."""

        def on_bus_message(bus_, message, user_data=None):
            self._process_message(message, generation)
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
        """Bounded position polling for the CURRENT accepted source only."""
        if self._closed:
            return
        pipeline = self._pipeline
        if pipeline is None or self._current_path is None:
            return
        ok, ns = self._bindings.query_position(pipeline)
        if ok:
            self._bridge.sig_pos.emit(gst_time_to_millis(ns))

    # ------------------------------------------------------------------
    # AudioPort — transport commands (symbolic states only)
    # ------------------------------------------------------------------

    def load(self, file_path: Path) -> None:
        if self._closed:
            return
        self._bindings.ensure_loaded()
        if not self._bindings.playbin3_available():
            raise RuntimeError("playbin3 no disponible en el runtime GStreamer")
        # PHASE A — REPLACE OLD (M11.3C-R3 transactional): la fuente actual
        # sigue siendo canónica HASTA que el teardown tenga éxito. NINGUNA
        # mutación de estado (generation/pending/current/pending_play) antes
        # del commit point: si el pipeline A no llega a NULL, A permanece
        # dueño (pipeline + bus observables) y NO se crea B.
        if not self._try_stop_pipeline():
            raise RuntimeError("pipeline anterior no pudo transicionar a NULL")
        # CONVERGENCIA (M11.3C-R6): el teardown del source activo A dejó el
        # transporte STOPPED. Converger AHORA (no depender de un
        # STATE_CHANGED del pipeline viejo ya desacoplado) para que un fallo
        # posterior del ARM de B no deje un PLAYING falso en la app.
        self._deliver_state_if(PlaybackStatus.STOPPED)
        # PHASE B — ARM NEW (M11.3C-R6 exception-atomic): el commit point
        # (teardown OK de A) ya pasó. CUALQUIER excepción normal durante la
        # construcción/configuración/attach/preroll-request del pipeline B
        # dispara un rollback best-effort y re-lanza la excepción ORIGINAL
        # como primaria (los fallos de limpieza son secundarios).
        self._generation += 1
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
            if candidate is not None:
                self._bridge.sig_rej.emit(candidate, reason)
            # Limpieza del pipeline fallido — FIRST LIFECYCLE CLEANUP ERROR
            # WINS (M11.3C-R5 P1-02): el NULL cleanup es PRIMARIO; el
            # detach del bus watch es SECUNDARIO y NUNCA reemplaza al error
            # de NULL. media_rejected ya fue emitido (evento semántico).
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
            if primary_cleanup_error is not None:
                raise primary_cleanup_error
            return

    def play(self) -> None:
        if self._closed or self._pipeline is None:
            return
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
        if self._request_state(self._bindings.STATE.PLAYING):
            self._pending_play = True
        # si falla: la intención NO se commitea; sin estado falso

    def pause(self) -> None:
        if self._closed or self._pipeline is None:
            return
        previous_intent = self._pending_play
        if self._request_state(self._bindings.STATE.PAUSED):
            self._pending_play = False
        else:
            self._pending_play = previous_intent  # rollback de intención

    def resume(self) -> None:
        self.play()

    def stop(self) -> None:
        if self._closed or self._pipeline is None:
            return
        if self._pending_path is not None and self._current_path is None:
            # CASE A — PENDING CANDIDATE (M11.3C-R6): stop = CANCEL del
            # candidato no aceptado. El pipeline candidato se libera y la
            # generación se invalida (mata aceptaciones tardías).
            if not self._try_stop_pipeline():
                return  # teardown del candidato falló: no fingir cancelación
            self._generation += 1
            self._pending_path = None
            self._pending_play = False
            self._eos_emitted = False
        else:
            # CASE B — ACCEPTED SOURCE (M11.3C-R6): stop = detener el
            # transporte, NO descargar la fuente. La fuente aceptada A
            # permanece cargada: current_path/generación/pipeline/bus watch
            # intactos → play()/resume() funcionan sin un nuevo load.
            if not self._request_state(self._bindings.STATE.NULL):
                # NULL falló: no publicar STOPPED, no limpiar el source como
                # si el stop hubiera tenido éxito; el estado sigue
                # diagnosticable (R2 failure atomicity)
                return
            self._pending_play = False
            self._eos_emitted = False  # stop explícito resetea el marcador EOS
        self._deliver_state_if(PlaybackStatus.STOPPED)

    def set_volume(self, value: int) -> None:
        self._volume = value / 100.0
        if self._pipeline is not None:
            self._bindings.set_volume(self._pipeline, self._volume)

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        if self._pipeline is not None:
            self._bindings.set_muted(self._pipeline, muted)

    def seek(self, position_ms: int) -> None:
        if self._closed or self._pipeline is None:
            return
        # failure no commitea éxito falso (sin evento de posición inventado)
        self._bindings.seek(self._pipeline, millis_to_gst_time(position_ms))

    def position(self) -> int:
        if self._closed or self._pipeline is None:
            return 0
        ok, ns = self._bindings.query_position(self._pipeline)
        if not ok or ns < 0:
            return 0
        return gst_time_to_millis(ns)

    def duration(self) -> int:
        if self._closed or self._pipeline is None:
            return 0
        ok, ns = self._bindings.query_duration(self._pipeline)
        if not ok or ns < 0:
            return 0
        return gst_time_to_millis(ns)

    # ------------------------------------------------------------------
    # close / teardown
    # ------------------------------------------------------------------

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._generation += 1  # invalidate any in-flight message
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
                self._bindings.quit_loop(self._loop)
            self._pump.join(timeout=2.0)
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
            raise primary_error

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
        self._generation += 1
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
    # bus message translation — TYPE-AWARE provenance (M11.3C-R1)
    # ------------------------------------------------------------------

    def _process_message(self, message, captured_generation: int) -> None:
        """Translate one bus message.

        PROVENANCE POLICY (no catch-all src rule):
        - generation MUST match the current one (stale isolation).
        - STATE_CHANGED: top-level pipeline only.
        - ERROR: ANY child element of the CURRENT graph is valid.
        - EOS / ASYNC_DONE / DURATION_CHANGED: current generation, once.
        """
        if self._closed:
            return
        if message is None:
            return  # bus source teardown puede entregar un mensaje null
        if captured_generation != self._generation:
            return  # stale source / old pipeline
        msg_type = self._bindings.message_type(message)
        mt = self._bindings.MESSAGE_TYPE
        if msg_type == mt.EOS:
            # EOS = fin natural del media ACTUAL (M11.3C-R6 P1-02): converge
            # a STOPPED antes del EOM y retiene la fuente para replay. El
            # guard _pending_play evita que un EOS tardío (ya encolado antes
            # de un stop explícito del usuario) cree un fin natural falso.
            if (
                self._pending_path is None
                and self._current_path is not None
                and self._pending_play
                and not self._eos_emitted
            ):
                self._eos_emitted = True
                self._pending_play = False
                # orden: STOPPED (convergencia) ANTES de EOM (QueueService
                # decide el siguiente load/repeat sobre estado ya convergido)
                self._deliver_state_if(PlaybackStatus.STOPPED)
                self._bridge.sig_eom.emit()
        elif msg_type == mt.ERROR:
            # child-element errors are valid for the current graph
            reason = self._bindings.parse_error(message)
            candidate = self._pending_path or self._current_path
            if candidate is not None:
                self._pending_path = None
                self._current_path = None
                self._bridge.sig_rej.emit(candidate, reason)
        elif msg_type == mt.ASYNC_DONE:
            # COMMAND = intención; ASYNC_DONE = aceptación del media/transición
            # asíncrona completada. NUNCA publica PLAYING: el estado runtime
            # solo proviene de STATE_CHANGED (R2).
            if self._pending_path is not None:
                self._current_path = self._pending_path
                self._pending_path = None
                self._bridge.sig_acc.emit(self._current_path)
        elif msg_type == mt.STATE_CHANGED:
            # top-level pipeline only (children transition constantly)
            if self._bindings.message_is_from_pipeline(message, self._pipeline):
                self._on_pipeline_state(message)
        elif msg_type == mt.DURATION_CHANGED and self._pipeline is not None:
            ok, ns = self._bindings.query_duration(self._pipeline)
            if ok:
                self._bridge.sig_dur.emit(gst_time_to_millis(ns))

    def _on_pipeline_state(self, message) -> None:
        state = self._bindings.state_of(message)
        if state is None:
            return
        if state == self._bindings.STATE.PLAYING:
            self._deliver_state_if(PlaybackStatus.PLAYING)
        elif state == self._bindings.STATE.PAUSED:
            # preroll PAUSED (sin intención de pausa) no es user PAUSED
            if not self._pending_play and self._pending_path is None:
                self._deliver_state_if(PlaybackStatus.PAUSED)
        elif state in (self._bindings.STATE.NULL, self._bindings.STATE.READY):
            self._deliver_state_if(PlaybackStatus.STOPPED)

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
        self._bridge.sig_state.emit(status)

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
