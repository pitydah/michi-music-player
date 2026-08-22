"""GStreamer AudioPort transport (M11.3C).

Lazy PyGObject/GI bindings, infrastructure-only. The adapter owns a
dedicated GLib MainContext/MainLoop + pump thread for its bus; all GStreamer
messages are translated into the canonical AudioPort events and delivered
through a Qt signal bridge (QueuedConnection) so consumers receive callbacks
on the OWNER thread — the same thread-affinity as QtMultimediaBackend.

STALE ISOLATION: a per-source generation token guards every event type
(acceptance/rejection/EOS/state/duration/position/error); messages from an
old generation or after close() are ignored.

TEST SEAM: the bindings object is injectable. The production bindings load
gi/Gst lazily and provide a real pump; the test fake provides the same
object surface but delivers messages directly via the adapter's
`_process_message` (deterministic unit tests without a GStreamer runtime).

NO GStreamer types leave this module.
"""

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from michi.application.ports import AudioPort
from michi.domain.playback import PlaybackStatus

_POSITION_POLL_MS = 500


class GStreamerBindings:
    """Lazy GObject Introspection facade for GStreamer (production)."""

    def __init__(self) -> None:
        self._gst = None
        self._glib = None
        self._init_error: Exception | None = None

    def ensure_loaded(self) -> None:
        """Lazy GI load — never called at import time. Raises ImportError
        with the truthful cause when gi/GStreamer is unavailable."""
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

    # -- pipeline / bus surface (objects are opaque; duck-typed) --

    def make_playbin3(self):
        self.ensure_loaded()
        return self._gst.ElementFactory.make("playbin3", "michi_gst_port")

    def set_state(self, pipeline, state) -> bool:
        self.ensure_loaded()
        return pipeline.set_state(state) != self._gst.StateChangeReturn.FAILURE

    def get_bus(self, pipeline):
        return pipeline.get_bus()

    def bus_add_watch(self, bus, callback):
        return bus.add_watch(self._glib.PRIORITY_DEFAULT, callback, None)

    def bus_remove_watch(self, bus, watch_id=None):
        try:
            if watch_id is not None:
                return bus.remove_watch(watch_id)
            return bus.remove_watch()
        except Exception:
            return False

    def new_main_context(self):
        return self._glib.MainContext.new()

    def new_main_loop(self, context):
        return self._glib.MainLoop.new(context, False)

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
        return message.src == pipeline

    def state_of(self, message):
        """Nuevo estado de un mensaje STATE_CHANGED (o None si no aplica)."""
        try:
            return message.parse_state_changed().new
        except Exception:
            return None

    # -- enums (production values) --

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
    owner thread (QueuedConnection via AutoConnection cross-thread)."""

    sig_eom = Signal()
    sig_pos = Signal(int)
    sig_dur = Signal(int)
    sig_acc = Signal(object)
    sig_rej = Signal(object, str)
    sig_state = Signal(object)


class GStreamerAudioPort(AudioPort):
    """playbin3 transport behind the canonical AudioPort contract.

    The Qt event bridge is COMPOSED (not inherited) to avoid a metaclass
    conflict between the ABC AudioPort and QObject."""

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
        self._watch_id = None
        self._context = None
        self._loop = None
        self._pump: threading.Thread | None = None
        self._stop_pump = threading.Event()
        # consumer registrations
        self._eom: list = []
        self._pos: list = []
        self._dur: list = []
        self._acc: list = []
        self._rej: list = []
        self._pst: list = []
        # wire the bridge (AutoConnection: direct from owner thread,
        # queued from the pump thread)
        self._bridge.sig_eom.connect(self._deliver_eom)
        self._bridge.sig_pos.connect(self._deliver_pos)
        self._bridge.sig_dur.connect(self._deliver_dur)
        self._bridge.sig_acc.connect(self._deliver_acc)
        self._bridge.sig_rej.connect(self._deliver_rej)
        self._bridge.sig_state.connect(self._deliver_state)

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def _teardown_pipeline(self) -> None:
        """Release the current pipeline (bus watch detach + NULL). The pump
        and its MainContext stay alive for the next pipeline."""
        if self._pipeline is None:
            return
        if self._bus is not None:
            if self._watch_id is not None:
                self._bindings.bus_remove_watch(self._bus, self._watch_id)
            else:
                self._bindings.bus_remove_watch(self._bus)
            self._watch_id = None
            self._bus = None
        self._bindings.set_state(self._pipeline, 0)  # GST_STATE_NULL
        self._pipeline = None

    def _ensure_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        if self._closed:
            raise RuntimeError("GStreamerAudioPort cerrado")
        self._bindings.ensure_loaded()
        pipeline = self._bindings.make_playbin3()
        if pipeline is None:
            raise RuntimeError("playbin3 no disponible")
        self._pipeline = pipeline
        self._bindings.set_volume(pipeline, self._volume)
        self._bindings.set_muted(pipeline, self._muted)
        self._bus = self._bindings.get_bus(pipeline)
        if self._bindings.supports_pump():
            self._start_pump()
        else:
            # test seam: mensajes entregados manualmente vía _process_message
            self._watch_id = None
        return pipeline

    def _start_pump(self) -> None:
        self._context = self._bindings.new_main_context()
        self._loop = self._bindings.new_main_loop(self._context)

        def bus_callback(bus, message, user_data=None):
            self._process_message(message)
            return True  # keep watch

        self._watch_id = self._bindings.bus_add_watch(self._bus, bus_callback)

        # bounded position polling
        def _poll_position():
            if self._pipeline is not None and self._current_path is not None:
                ok, ns = self._bindings.query_position(self._pipeline)
                if ok:
                    self._bridge.sig_pos.emit(gst_time_to_millis(ns))
            return True  # keep timer

        self._context.timeout_add(_POSITION_POLL_MS, _poll_position)
        self._stop_pump.clear()
        self._pump = threading.Thread(
            target=self._pump_run, name="michi-gst-pump", daemon=True
        )
        self._pump.start()

    def _pump_run(self) -> None:
        import gi  # noqa: PLC0415

        gi.require_version("GLib", "2.0")
        from gi.repository import GLib  # noqa: PLC0415

        self._context.push_thread_default()
        try:
            GLib.MainContext.iteration(self._context, True)
            self._loop.run()
        finally:
            self._context.pop_thread_default()

    # ------------------------------------------------------------------
    # AudioPort — transport commands
    # ------------------------------------------------------------------

    def load(self, file_path: Path) -> None:
        if self._closed:
            return
        self._generation += 1
        self._pending_path = Path(file_path)
        self._current_path = None
        self._eos_emitted = False
        self._pending_play = False
        # pipeline NUEVO por fuente: la identidad del pipeline ES el token de
        # generación — los mensajes en vuelo del pipeline anterior jamás se
        # traducen (guard por message.src)
        self._teardown_pipeline()
        pipeline = self._ensure_pipeline()
        self._bindings.set_uri(pipeline, Path(file_path).resolve().as_uri())
        # preroll: ASYNC_DONE (misma generación) es la evidencia de aceptación
        self._bindings.set_state(pipeline, 2)  # GST_STATE_PAUSED

    def play(self) -> None:
        if self._closed or self._pipeline is None:
            return
        self._pending_play = True
        self._bindings.set_state(self._pipeline, 4)  # GST_STATE_PLAYING

    def pause(self) -> None:
        if self._closed or self._pipeline is None:
            return
        self._pending_play = False
        self._bindings.set_state(self._pipeline, 2)  # GST_STATE_PAUSED

    def resume(self) -> None:
        self.play()

    def stop(self) -> None:
        if self._closed or self._pipeline is None:
            return
        self._pending_play = False
        self._pending_path = None
        self._current_path = None
        self._bindings.set_state(self._pipeline, 0)  # GST_STATE_NULL
        if self._current_state is not PlaybackStatus.STOPPED:
            self._current_state = PlaybackStatus.STOPPED
            self._bridge.sig_state.emit(PlaybackStatus.STOPPED)

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
        self._bindings.seek(self._pipeline, millis_to_gst_time(position_ms))

    def position(self) -> int:
        if self._closed or self._pipeline is None:
            return 0
        ok, ns = self._bindings.query_position(self._pipeline)
        return gst_time_to_millis(ns) if ok else 0

    def duration(self) -> int:
        if self._closed or self._pipeline is None:
            return 0
        ok, ns = self._bindings.query_duration(self._pipeline)
        return gst_time_to_millis(ns) if ok else 0

    # ------------------------------------------------------------------
    # close / teardown
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Terminal lifecycle: invalidate generation, stop the pump, detach
        the watch, pipeline → NULL, release references. No callbacks after
        close."""
        if self._closed:
            return
        self._closed = True
        self._generation += 1  # invalidate any in-flight message
        if self._pump is not None:
            self._stop_pump.set()
            if self._loop is not None:
                self._loop.quit()
            self._pump.join(timeout=2.0)
            self._pump = None
            self._loop = None
            self._context = None
        self._teardown_pipeline()
        self._pending_path = None
        self._current_path = None
        self._eom = []
        self._pos = []
        self._dur = []
        self._acc = []
        self._rej = []
        self._pst = []

    # ------------------------------------------------------------------
    # bus message translation (generation-guarded, owner-thread delivery)
    # ------------------------------------------------------------------

    def _process_message(self, message) -> None:
        """Translate one bus message (called from the pump thread in
        production, or directly from the owner thread in tests).

        STALE GUARD (global): only messages from the CURRENT pipeline are
        translated. Each load() replaces the pipeline, so messages from a
        previous source (EOS/ERROR/ASYNC_DONE/STATE_CHANGED still in
        flight) are ignored by identity — the generation token."""
        if self._closed:
            return
        if self._pipeline is None:
            return
        if not self._bindings.message_is_from_pipeline(message, self._pipeline):
            return  # stale source / old pipeline
        msg_type = self._bindings.message_type(message)
        mt = self._bindings.MESSAGE_TYPE
        if msg_type == mt.EOS:
            if (
                self._pending_path is None
                and self._current_path is not None
                and not self._eos_emitted
            ):
                self._eos_emitted = True
                self._bridge.sig_eom.emit()
        elif msg_type == mt.ERROR:
            reason = self._bindings.parse_error(message)
            candidate = self._pending_path or self._current_path
            if candidate is not None:
                self._pending_path = None
                self._current_path = None
                self._bridge.sig_rej.emit(candidate, reason)
        elif msg_type == mt.ASYNC_DONE:
            # preroll completado → evidencia de aceptación (misma generación)
            if self._pending_path is not None:
                self._current_path = self._pending_path
                self._pending_path = None
                self._bridge.sig_acc.emit(self._current_path)
                if self._pending_play:
                    self._deliver_state_if(PlaybackStatus.PLAYING)
        elif msg_type == mt.STATE_CHANGED:
            self._on_pipeline_state(message)
        elif msg_type == mt.DURATION_CHANGED and self._pipeline is not None:
            ok, ns = self._bindings.query_duration(self._pipeline)
            if ok:
                self._bridge.sig_dur.emit(gst_time_to_millis(ns))
        # _ = gen — la generación se captura al crear mensajes en el fake;
        # el adapter nunca entrega tras close() (guard superior)

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

    def _deliver_state_if(self, status: PlaybackStatus) -> None:
        if self._current_state is status:
            return
        self._current_state = status
        self._bridge.sig_state.emit(status)

    # ------------------------------------------------------------------
    # bridge slots (owner thread)
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
