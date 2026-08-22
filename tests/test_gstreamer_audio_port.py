"""M11.3C-R1: GStreamerAudioPort transport gates.

Deterministic unit tests through a fake GStreamer surface that models the
REAL Gst.State semantics (NULL=1, READY=2, PAUSED=3, PLAYING=4), plus a
real-GI smoke test that skips truthfully when the runtime is absent.

Covers: symbolic state usage, single-pump lifecycle, generation-aware bus
provenance (child errors accepted, stale generations ignored), truthful
playbin3 probe, explicit QueuedConnection thread affinity, post-close queued
event isolation, teardown.
"""

import os
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication

from michi.application.audio_transport_router import AudioTransportRouter
from michi.domain.audio_engine import AudioEngineId
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.audio_engines.gstreamer import (
    GStreamerAudioPort,
    gst_time_to_millis,
    millis_to_gst_time,
)


# REAL GStreamer State values (verified: NULL=1, READY=2, PAUSED=3, PLAYING=4)
class _FakeState:
    NULL = 1
    READY = 2
    PAUSED = 3
    PLAYING = 4


class _FakeMsgType:
    EOS = 0
    ERROR = 1
    STATE_CHANGED = 2
    ASYNC_DONE = 3
    DURATION_CHANGED = 4


class FakePipeline:
    def __init__(self, name="P"):
        self.name = name
        self.uri = None
        self.state = _FakeState.NULL
        self.volume = 1.0
        self.muted = False
        self.seek_calls = []
        self.closed = False
        self.bus = FakeBus(self)
        self.children = []

    def set_state(self, state):
        self.state = state
        if state == _FakeState.NULL:
            self.closed = True
        return state

    def get_bus(self):
        return self.bus

    def set_property(self, prop, value):
        if prop == "uri":
            self.uri = value
        elif prop == "volume":
            self.volume = value
        elif prop == "mute":
            self.muted = value

    def query_position(self, fmt):
        return True, 1_234_000_000

    def query_duration(self, fmt):
        return True, 5_000_000_000

    def seek_simple(self, fmt, flags, ns):
        self.seek_calls.append(ns)
        return True


class FakeBus:
    """Modela la ownership del bus watch como Gst.Bus (M11.3C-R4).

    add_watch instala un watch y devuelve un id sintético; remove_watch()
    NO recibe id (paridad con el contrato real) y devuelve False si no hay
    watch instalado o si fail_remove_watch está activo."""

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.sources_created = 0
        self.watch_installed = False
        self.watch_callback = None
        self.remove_watch_count = 0
        self.fail_remove_watch = False

    def create_watch(self):
        self.sources_created += 1
        return FakeSource()

    def add_watch(self, priority, callback):
        self.watch_installed = True
        self.watch_callback = callback
        return 42  # id sintético (bookkeeping only)

    def remove_watch(self):
        if self.fail_remove_watch or not self.watch_installed:
            return False
        self.watch_installed = False
        self.remove_watch_count += 1
        return True


class FakeSource:
    def __init__(self):
        self.destroyed = False
        self.attached = False
        self._callback = None

    def set_callback(self, callback, *args):
        self._callback = callback

    def attach(self, context):
        self.attached = True
        return 1

    def destroy(self):
        self.destroyed = True


def msg_state(port, src, state):
    """FakeMessage STATE_CHANGED con generación capturada."""
    msg, gen = _msg(port, _FakeMsgType.STATE_CHANGED, src, new_state=state)
    return msg, gen


class FakeMessage:
    def __init__(self, msg_type, src, error_text=None, new_state=None):
        self.type = msg_type
        self.src = src
        self._error_text = error_text
        self._new_state = new_state

    def parse_error(self):
        from gi.repository import GLib

        return GLib.Error(self._error_text or "err"), ""

    def parse_state_changed(self):
        return None, None, self._new_state


class FakeBindings:
    """Test seam: same object surface as GStreamerBindings, no GI needed.

    The pump is SIMULATED (run_loop blocks until quit_loop) so the adapter
    lifecycle (sources attach/destroy, single pump, join) is exercised for
    real; messages are still delivered directly via _deliver()."""

    def __init__(self, playbin3_present=True):
        self.pipelines = []
        self.playbin3_present = playbin3_present
        self.missing_factories: set = set()
        self.timer_sources = []
        self.timer_callback = None
        self._quit = threading.Event()
        self.failed_states: set = set()
        self.fail_next_states: list = []
        self.ignore_quit = False  # simula pump que no termina

    def supports_pump(self):
        return True

    def ensure_loaded(self):
        pass

    def playbin3_available(self):
        return self.playbin3_present and "playbin3" not in self.missing_factories

    def element_factory_find(self, name):
        return None if name in self.missing_factories else object()

    def make_playbin3(self):
        p = FakePipeline(f"P{len(self.pipelines)}")
        self.pipelines.append(p)
        return p

    def set_state(self, pipeline, state):
        if self.fail_next_states:
            expected = self.fail_next_states.pop(0)
            if state == expected:
                return False
        if state in self.failed_states:
            return False
        return pipeline.set_state(state)

    def get_bus(self, pipeline):
        return pipeline.get_bus()

    def create_context(self):
        return "ctx"

    def create_loop(self, context):
        return "loop"

    def run_loop(self, loop):
        self._quit.wait()  # simula el pump real hasta quit_loop

    def quit_loop(self, loop):
        if not self.ignore_quit:
            self._quit.set()

    def push_thread_default(self, context):
        pass

    def pop_thread_default(self, context):
        pass

    def create_bus_source(self, bus, callback, context=None):
        """Paridad fake/real (M11.3C-R4): instala el watch vía add_watch y
        devuelve el id sintético (bookkeeping only)."""
        return bus.add_watch(0, callback)

    def remove_bus_watch(self, bus) -> bool:
        """Misma forma que GStreamerBindings.remove_bus_watch(bus): un solo
        argumento; si el productivo llamara con un id extra, esto reventaría
        con TypeError (paridad de firma)."""
        if bus is None:
            return True
        return bus.remove_watch()

    def attach_source(self, source, context):
        return source.attach(context)

    def destroy_source(self, source):
        if source is not None:
            source.destroy()

    def create_timeout_source(self, interval_ms, callback):
        source = FakeSource()
        source.set_callback(callback)
        self.timer_sources.append(source)
        self.timer_callback = callback
        return source

    def iteration(self, context, blocking):
        return False

    def query_position(self, pipeline):
        return pipeline.query_position(None)

    def query_duration(self, pipeline):
        return pipeline.query_duration(None)

    def seek(self, pipeline, position_ns):
        return pipeline.seek_simple(None, None, position_ns)

    def set_uri(self, pipeline, uri):
        pipeline.set_property("uri", uri)

    def set_volume(self, pipeline, value):
        pipeline.set_property("volume", value)

    def set_muted(self, pipeline, muted):
        pipeline.set_property("mute", muted)

    def message_type(self, message):
        return message.type

    def parse_error(self, message):
        return message._error_text or "gstreamer error"

    def message_is_from_pipeline(self, message, pipeline):
        return message.src is pipeline

    def state_of(self, message):
        return message._new_state

    @property
    def STATE(self):  # noqa: N802 — GStreamer enum surface
        return _FakeState

    @property
    def MESSAGE_TYPE(self):  # noqa: N802 — GStreamer enum surface
        return _FakeMsgType


def _port(bindings=None):
    return GStreamerAudioPort(bindings if bindings is not None else FakeBindings())


def _msg(port, msg_type, pipeline, error_text=None, new_state=None):
    """FakeMessage con la generación vigente capturada."""
    return FakeMessage(msg_type, pipeline, error_text, new_state), port._generation


def _deliver(port, message, generation):
    """Entrega directa (test seam) + procesa la cola Qt: en producción el
    pump emite con QueuedConnection explícito; en tests el hilo del owner
    debe drenar la cola para que los callbacks lleguen."""
    port._process_message(message, generation)
    for _ in range(5):
        QCoreApplication.processEvents()


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    yield app


class TestStateSemantics:
    """P1-01: el transporte usa los estados SIMBÓLICOS del bindings."""

    def test_no_raw_state_integers(self):
        import inspect

        from michi.infrastructure.audio_engines import gstreamer as mod

        src = inspect.getsource(mod)
        # ningún set_state con enteros crudos
        assert "set_state(pipeline, 0)" not in src
        assert "set_state(pipeline, 2)" not in src
        assert "set_state(pipeline, 4)" not in src
        # los estados se toman del bindings
        assert "self._bindings.STATE.PAUSED" in src
        assert "self._bindings.STATE.PLAYING" in src
        assert "self._bindings.STATE.NULL" in src

    def test_load_uses_paused(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        assert pipeline.state == _FakeState.PAUSED  # preroll
        port.close()

    def test_play_uses_playing(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port.play()
        assert pipeline.state == _FakeState.PLAYING
        port.close()

    def test_pause_uses_paused(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port.pause()
        assert pipeline.state == _FakeState.PAUSED
        port.close()

    def test_stop_and_close_use_null(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port.stop()
        assert pipeline.state == _FakeState.NULL
        port.load(Path("/m/b.flac"))
        pipeline2 = bindings.pipelines[-1]
        port.close()
        assert pipeline2.state == _FakeState.NULL


class TestTimeConversion:
    def test_millis_to_ns(self):
        assert millis_to_gst_time(1000) == 1_000_000_000

    def test_ns_to_millis(self):
        assert gst_time_to_millis(1_234_000_000) == 1234


class TestSinglePump:
    """P1-03: un solo pump por port; los pipelines se reemplazan."""

    def test_one_pump_many_loads(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        port.load(Path("/m/b.flac"))
        port.load(Path("/m/c.flac"))
        assert port._pump_start_count == 1
        assert len(bindings.pipelines) == 3
        assert port._pump is not None  # un solo thread
        # el bus source actual está adjunto
        assert port._bus_source_attached is True
        port.close()

    def test_old_bus_sources_destroyed(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        bus_a = port._bus
        assert bus_a.watch_installed is True
        port.load(Path("/m/b.flac"))
        assert bus_a.watch_installed is False  # watch de A removido
        assert bus_a.remove_watch_count == 1
        assert port._bus is not None
        assert port._bus.watch_installed is True  # watch de B vivo
        port.close()

    def test_close_terminates_pump(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pump = port._pump
        port.close()
        assert port._pump is None
        assert not pump.is_alive()
        port.close()  # idempotente


class TestMediaAcceptance:
    def test_acceptance_only_after_async_done(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        path = Path("/m/a.flac")
        port.load(path)
        assert accepted == []
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
        _deliver(port, msg, gen)
        assert accepted == [path]
        _deliver(port, msg, gen)  # dup
        assert accepted == [path]
        port.close()

    def test_stop_cancels_pending_acceptance(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.load(Path("/m/a.flac"))
        old_gen = port._generation
        pipeline = bindings.pipelines[-1]
        port.stop()  # invalida la generación
        _deliver(port, FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline), old_gen)
        assert accepted == []  # ASYNC_DONE tardío NO acepta
        port.close()


class TestRejection:
    def test_error_rejects_once(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        rejected = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.load(Path("/m/bad.flac"))
        pipeline = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ERROR, pipeline, error_text="decode failed")
        _deliver(port, msg, gen)
        assert rejected == [(Path("/m/bad.flac"), "decode failed")]
        _deliver(port, msg, gen)  # dup
        assert len(rejected) == 1
        port.close()

    def test_child_error_accepted(self, qapp):
        """P1-04: un error de un HIJO del grafo actual es válido."""
        bindings = FakeBindings()
        port = _port(bindings)
        rejected = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.load(Path("/m/a.flac"))
        child = FakePipeline("child")  # src != playbin
        msg, gen = _msg(port, _FakeMsgType.ERROR, child, error_text="decoder died")
        _deliver(port, msg, gen)
        assert rejected == [(Path("/m/a.flac"), "decoder died")]
        port.close()

    def test_old_generation_child_error_ignored(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        rejected = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.load(Path("/m/a.flac"))
        old_gen = port._generation
        child = FakePipeline("oldchild")
        port.load(Path("/m/b.flac"))  # generación nueva
        _deliver(
            port,
            FakeMessage(_FakeMsgType.ERROR, child, error_text="stale"),
            old_gen,
        )
        assert rejected == []
        port.close()


class TestStateProvenance:
    def test_child_state_changed_ignored(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        child = FakePipeline("child")
        msg, gen = msg_state(port, child, _FakeState.PLAYING)
        _deliver(port, msg, gen)
        assert states == []  # STATE_CHANGED solo top-level
        port.close()

    def test_pipeline_state_processed(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        msg, gen = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, msg, gen)
        assert states == [PlaybackStatus.PLAYING]
        port.close()

    def test_stale_eos_ignored(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        eom = []
        port.subscribe_end_of_media(lambda: eom.append(1))
        port.load(Path("/m/a.flac"))
        old_gen = port._generation
        pipeline = bindings.pipelines[-1]
        port.load(Path("/m/b.flac"))
        _deliver(port, FakeMessage(_FakeMsgType.EOS, pipeline), old_gen)
        assert eom == []
        port.close()


class TestPrerollVsUserPause:
    def test_preroll_paused_not_user_pause(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        port.play()
        pipeline = bindings.pipelines[-1]
        msg, gen = msg_state(port, pipeline, _FakeState.PAUSED)
        _deliver(port, msg, gen)
        assert PlaybackStatus.PAUSED not in states
        msg2, gen2 = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline)
        _deliver(port, msg2, gen2)
        msg3, gen3 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, msg3, gen3)
        assert states[-1] == PlaybackStatus.PLAYING
        port.close()


class TestSeekPositionDuration:
    def test_seek_conversion(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port.seek(1500)
        assert pipeline.seek_calls == [1_500_000_000]
        port.close()

    def test_position_duration_units_and_failure_safety(self, qapp):
        class NoQueryPipeline(FakePipeline):
            def query_position(self, fmt):
                return False, 0

            def query_duration(self, fmt):
                return False, 0

        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        assert port.position() == 1234
        assert port.duration() == 5000
        # fallo de query → valor seguro 0 (nunca clock_time_none/negativo)
        bindings.pipelines[-1] = NoQueryPipeline()
        port._pipeline = NoQueryPipeline()
        assert port.position() == 0
        assert port.duration() == 0
        port.close()


class TestStaleAfterClose:
    def test_no_callbacks_after_close(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        events = []
        port.subscribe_end_of_media(lambda: events.append("eom"))
        port.subscribe_media_accepted(lambda p: events.append(f"acc:{p.name}"))
        port.subscribe_media_rejected(lambda p, r: events.append(f"rej:{r}"))
        port.subscribe_playback_state_changed(lambda s: events.append("st"))
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        gen = port._generation
        port.close()
        _deliver(port, FakeMessage(_FakeMsgType.EOS, pipeline), gen)
        _deliver(port, FakeMessage(_FakeMsgType.ERROR, pipeline, error_text="x"), gen)
        msg, g = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, msg, g)
        assert events == []


class TestTeardown:
    def test_close_requests_null_and_releases(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port.close()
        assert pipeline.closed is True
        assert port._pipeline is None
        port.close()  # idempotente

    def test_stop_keeps_transport_usable(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        port.stop()
        assert port._pipeline is not None
        assert port.duration() == 5000
        port.close()


class TestRouterParity:
    def test_bind_and_forward_all_events(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        router = AudioTransportRouter()
        router.bind(AudioEngineId.GSTREAMER, port)
        events = []
        router.subscribe_end_of_media(lambda: events.append("eom"))
        router.subscribe_position_changed(lambda ms: events.append(f"pos:{ms}"))
        router.subscribe_duration_changed(lambda ms: events.append(f"dur:{ms}"))
        router.subscribe_media_accepted(lambda p: events.append(f"acc:{p.name}"))
        router.subscribe_media_rejected(lambda p, r: events.append(f"rej:{r}"))
        router.subscribe_playback_state_changed(lambda s: events.append("st"))
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        m1, g1 = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline)
        _deliver(port, m1, g1)
        m2, g2 = _msg(port, _FakeMsgType.DURATION_CHANGED, pipeline)
        _deliver(port, m2, g2)
        m3, g3 = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m3, g3)
        m4, g4 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, m4, g4)
        assert events == ["acc:a.flac", "dur:5000", "eom", "st"]
        router.unbind()
        m5, g5 = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m5, g5)
        assert events == ["acc:a.flac", "dur:5000", "eom", "st"]
        port.close()


class TestPlaybin3Probe:
    """P2-02: ejerce el probe PRODUCTIVO real vía monkeypatch de su
    dependencia (GStreamerBindings), nunca reemplazando provider.probe."""

    def test_real_probe_missing_playbin3(self, monkeypatch):
        import michi.infrastructure.audio_engines.gstreamer as gst_mod

        class NoPlaybinBindings:
            def ensure_loaded(self):
                pass

            def playbin3_available(self):
                return False

        monkeypatch.setattr(gst_mod, "GStreamerBindings", NoPlaybinBindings)
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
        )

        desc = GStreamerEngineProvider().probe()
        assert desc.available is False
        assert desc.implemented is True
        assert desc.can_activate is False
        assert "playbin3" in desc.unavailable_reason

    def test_real_probe_missing_gi(self, monkeypatch):
        import michi.infrastructure.audio_engines.gstreamer as gst_mod

        class NoGiBindings:
            def ensure_loaded(self):
                raise ImportError("gi not installed")

        monkeypatch.setattr(gst_mod, "GStreamerBindings", NoGiBindings)
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
        )

        desc = GStreamerEngineProvider().probe()
        assert desc.available is False
        assert desc.implemented is True
        assert desc.can_activate is False
        assert "GStreamer" in desc.unavailable_reason

    def test_real_probe_available(self, monkeypatch):
        import michi.infrastructure.audio_engines.gstreamer as gst_mod

        class FullBindings:
            def ensure_loaded(self):
                pass

            def playbin3_available(self):
                return True

        monkeypatch.setattr(gst_mod, "GStreamerBindings", FullBindings)
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
        )

        desc = GStreamerEngineProvider().probe()
        assert desc.available is True
        assert desc.implemented is True
        assert desc.can_activate is True
        assert desc.activation_blocker is None

    def test_open_fails_without_playbin3(self, qapp):
        bindings = FakeBindings(playbin3_present=False)
        port = _port(bindings)
        with pytest.raises(RuntimeError, match="playbin3"):
            port.load(Path("/m/a.flac"))
        port.close()


class TestThreadAffinity:
    """P2-02: los callbacks llegan en el hilo del OWNER vía QueuedConnection."""

    def test_callback_on_owner_thread(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        owner_thread_id = threading.get_ident()
        callback_threads = []

        def on_acc(p):
            callback_threads.append(threading.get_ident())

        port.subscribe_media_accepted(on_acc)

        # WORKER: emite a través del puente del adapter (ruta del pump)
        worker_thread_id = []

        def worker():
            worker_thread_id.append(threading.get_ident())
            port._bridge.sig_acc.emit(Path("/m/a.flac"))

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        # OWNER procesa los eventos Qt
        for _ in range(10):
            QCoreApplication.processEvents()
        assert worker_thread_id[0] != owner_thread_id
        assert callback_threads == [owner_thread_id]
        port.close()

    def test_post_close_queued_event_isolated(self, qapp):
        """P2-02: evento encolado ANTES de close → cero delivery tras close."""
        bindings = FakeBindings()
        port = _port(bindings)
        callbacks = []
        port.subscribe_media_accepted(lambda p: callbacks.append(p))

        # worker encola ANTES de close
        def worker():
            port._bridge.sig_acc.emit(Path("/m/queued.flac"))

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        port.close()  # limpia callbacks ANTES de que el owner procese
        for _ in range(10):
            QCoreApplication.processEvents()
        assert callbacks == []
        port.close()  # idempotente


class TestAsyncStateTruth:
    """P1-01: ASYNC_DONE acepta pero NUNCA publica PLAYING."""

    def test_async_done_accepts_without_claiming_playing(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        accepted = []
        states = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        port.play()
        pipeline = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline)
        _deliver(port, msg, gen)
        assert accepted == [Path("/m/a.flac")]
        assert states == []  # ASYNC_DONE NO publica PLAYING
        # solo STATE_CHANGED PLAYING publica
        msg2, gen2 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, msg2, gen2)
        assert states == [PlaybackStatus.PLAYING]
        port.close()


class TestStateRequestFailureAtomicity:
    """P1-02: los requests de estado son failure-atomic."""

    def test_preroll_failure_rejects_and_recovers(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        rejected = []
        accepted = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        bindings.failed_states.add(_FakeState.PAUSED)
        port.load(Path("/m/a.flac"))
        for _ in range(5):
            QCoreApplication.processEvents()
        assert rejected == [
            (Path("/m/a.flac"), "GStreamer failed to enter PAUSED during preroll")
        ]
        assert accepted == []
        assert port._pending_path is None
        assert port._current_path is None
        # recuperación: sin fallo, el port sigue usable
        bindings.failed_states.clear()
        port.load(Path("/m/b.flac"))
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
        _deliver(port, msg, gen)
        assert accepted == [Path("/m/b.flac")]
        port.close()

    def test_play_failure_does_not_commit_play_intent(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline)
        _deliver(port, msg, gen)
        bindings.failed_states.add(_FakeState.PLAYING)
        port.play()
        assert states == []  # sin PLAYING falso
        assert port._pending_play is False  # intención NO commiteada
        # retry con éxito
        bindings.failed_states.clear()
        port.play()
        msg2, gen2 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, msg2, gen2)
        assert states == [PlaybackStatus.PLAYING]
        port.close()

    def test_pause_failure_rolls_back_pause_intent(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline)
        _deliver(port, msg, gen)
        port.play()
        msg2, gen2 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, msg2, gen2)
        # fallo de PAUSED → intención de play preservada
        bindings.failed_states.add(_FakeState.PAUSED)
        port.pause()
        assert port._pending_play is True  # rollback
        # retry con éxito
        bindings.failed_states.clear()
        port.pause()
        assert port._pending_play is False
        msg3, gen3 = msg_state(port, pipeline, _FakeState.PAUSED)
        _deliver(port, msg3, gen3)
        port.close()

    def test_stop_failure_does_not_claim_stopped(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline)
        _deliver(port, msg, gen)
        msg2, gen2 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, msg2, gen2)
        assert states[-1] == PlaybackStatus.PLAYING
        # NULL falla → sin STOPPED, source intacto
        bindings.failed_states.add(_FakeState.NULL)
        port.stop()
        assert PlaybackStatus.STOPPED not in states
        assert port._current_path == Path("/m/a.flac")
        # retry con éxito
        bindings.failed_states.clear()
        port.stop()
        for _ in range(5):
            QCoreApplication.processEvents()
        assert states[-1] == PlaybackStatus.STOPPED
        assert port._current_path is None
        port.close()

    def test_pipeline_replacement_aborts_if_old_null_fails(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        # el teardown del pipeline A falla durante load(B) → abortar
        bindings.fail_next_states.append(_FakeState.NULL)
        with pytest.raises(RuntimeError, match="NULL"):
            port.load(Path("/m/b.flac"))
        assert len(bindings.pipelines) == 1  # B nunca se creó
        port.close()

    def test_close_teardown_failure_observable(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        bindings.failed_states.add(_FakeState.NULL)
        with pytest.raises(RuntimeError, match="NULL"):
            port.close()
        assert port._closed is True  # terminal, sin comandos posteriores


class TestPumpTerminationIntegrity:
    """P1-03: join timeout NO pierde el ownership del worker vivo."""

    def test_close_pump_timeout_retains_live_worker(self, qapp):
        bindings = FakeBindings()
        bindings.ignore_quit = True  # pump que no termina
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pump = port._pump
        assert pump is not None
        with pytest.raises(RuntimeError, match="did not terminate"):
            port.close()
        assert port._closed is True
        assert port._pump is pump  # referencia viva retenida
        assert pump.is_alive() is True
        # limpieza determinística del test: liberar el pump forzado
        bindings.ignore_quit = False
        bindings.quit_loop(port._loop or "loop")
        pump.join(timeout=2.0)
        assert pump.is_alive() is False
        port._pump = None
        port._loop = None
        port._context = None


class TestLoadReplacementTransaction:
    """M11.3C-R3 P1-01: load(B) es transaccional — el teardown de A es el
    commit point; ninguna mutación de estado ocurre antes de NULL exitoso."""

    def _port_playing_a(self, bindings):
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline)
        _deliver(port, msg, gen)
        port.play()
        msg2, gen2 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, msg2, gen2)
        return port, pipeline

    def test_failed_replacement_preserves_old_source_transaction(self, qapp):
        bindings = FakeBindings()
        port, old_pipeline = self._port_playing_a(bindings)
        old_generation = port._generation
        old_bus = port._bus
        old_current_path = port._current_path
        old_pending_play = port._pending_play
        old_current_state = port._current_state
        bindings.fail_next_states.append(_FakeState.NULL)
        with pytest.raises(RuntimeError, match="NULL"):
            port.load(Path("/m/b.flac"))
        # la fuente vieja sigue siendo canónica en TODO sentido
        assert port._pipeline is old_pipeline
        assert port._current_path == old_current_path == Path("/m/a.flac")
        assert port._pending_path is None  # B nunca se arma
        assert port._generation == old_generation  # sin avance falso
        assert port._pending_play is old_pending_play  # intención de play intacta
        assert port._current_state is old_current_state == PlaybackStatus.PLAYING
        # el bus viejo sigue attachado y observable (watch vivo)
        assert port._bus is old_bus
        assert old_bus.watch_installed is True
        assert old_bus.remove_watch_count == 0
        assert len(bindings.pipelines) == 1  # B nunca se creó
        port.close()

    def test_failed_replacement_preserves_generation(self, qapp):
        bindings = FakeBindings()
        port, _ = self._port_playing_a(bindings)
        bindings.fail_next_states.append(_FakeState.NULL)
        with pytest.raises(RuntimeError, match="NULL"):
            port.load(Path("/m/b.flac"))
        assert port._generation == 1  # el intento fallido NO avanza la generación
        port.close()

    def test_failed_replacement_preserves_old_bus_source(self, qapp):
        bindings = FakeBindings()
        port, _ = self._port_playing_a(bindings)
        old_bus = port._bus
        old_watch_id = port._bus_source
        bindings.fail_next_states.append(_FakeState.NULL)
        with pytest.raises(RuntimeError, match="NULL"):
            port.load(Path("/m/b.flac"))
        # pipeline vivo sin bus = zombie: prohibido en reemplazo normal
        assert port._bus is old_bus
        assert port._bus_source == old_watch_id
        assert old_bus.watch_installed is True
        assert old_bus.remove_watch_count == 0
        port.close()

    def test_replacement_recovers_after_null_failure(self, qapp):
        bindings = FakeBindings()
        port, _ = self._port_playing_a(bindings)
        old_generation = port._generation
        bindings.fail_next_states.append(_FakeState.NULL)
        with pytest.raises(RuntimeError, match="NULL"):
            port.load(Path("/m/b.flac"))
        # recuperación: el retry reemplaza A y arma B normalmente
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.load(Path("/m/b.flac"))
        assert port._generation == old_generation + 1  # avanza EXACTAMENTE una vez
        assert len(bindings.pipelines) == 2  # B creado
        pipeline_b = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_b)
        _deliver(port, msg, gen)
        assert accepted == [Path("/m/b.flac")]
        assert port._current_path == Path("/m/b.flac")
        assert port._pipeline is pipeline_b
        port.close()


class TestPrerollCleanupAtomicity:
    """M11.3C-R3 P1-02: la limpieza del preroll fallido es failure-atomic —
    nunca fingir que el pipeline fallido desapareció."""

    def test_preroll_failure_with_successful_cleanup_reusable(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        rejected = []
        accepted = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        bindings.failed_states.add(_FakeState.PAUSED)
        port.load(Path("/m/a.flac"))
        for _ in range(5):
            QCoreApplication.processEvents()
        assert rejected == [
            (Path("/m/a.flac"), "GStreamer failed to enter PAUSED during preroll")
        ]
        assert accepted == []
        # limpieza exitosa: pipeline liberado, bus destruido, port reutilizable
        assert port._pipeline is None
        assert port._bus_source is None
        assert port._pending_path is None
        assert port._current_path is None
        bindings.failed_states.clear()
        port.load(Path("/m/b.flac"))
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
        _deliver(port, msg, gen)
        assert accepted == [Path("/m/b.flac")]
        port.close()

    def test_preroll_failure_and_null_cleanup_failure_retains_pipeline(self, qapp):
        bindings = FakeBindings()
        bindings.failed_states.update({_FakeState.PAUSED, _FakeState.NULL})
        port = _port(bindings)
        rejected = []
        accepted = []
        states = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        with pytest.raises(RuntimeError, match="limpieza de preroll"):
            port.load(Path("/m/b.flac"))
        for _ in range(5):
            QCoreApplication.processEvents()
        # el rechazo es el evento semántico primario, exactamente una vez
        assert rejected == [
            (Path("/m/b.flac"), "GStreamer failed to enter PAUSED during preroll")
        ]
        assert accepted == []
        assert states == []
        # el pipeline fallido queda RETENIDO (no fingir limpieza exitosa)
        failed_pipeline = bindings.pipelines[-1]
        assert port._pipeline is failed_pipeline
        assert port._current_path is None  # sin media actual falsa
        assert port._pending_path is None
        # close() con NULL ya exitoso limpia el pipeline retenido
        bindings.failed_states.discard(_FakeState.NULL)
        port.close()
        assert port._pipeline is None


class TestCloseFirstErrorWins:
    """M11.3C-R3 P1-03: en close() la PRIMERA falla cronológica es la
    autoritativa (teardown antes que pump); la secundaria no la reemplaza."""

    def test_close_first_error_wins_over_pump_timeout(self, qapp):
        bindings = FakeBindings()
        bindings.failed_states.add(_FakeState.NULL)
        bindings.ignore_quit = True  # el pump además no termina
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = port._pipeline
        pump = port._pump
        assert pipeline is not None and pump is not None
        with pytest.raises(RuntimeError, match="NULL"):
            port.close()
        # el error primario (teardown) gana sobre el timeout del pump
        assert port._closed is True
        assert port._pipeline is pipeline  # ownership retenido si NULL falló
        assert port._pump is pump  # worker vivo retenido
        assert pump.is_alive() is True
        # liberar el fake pump para que el test termine limpio
        bindings.ignore_quit = False
        bindings.quit_loop(port._loop or "loop")
        pump.join(timeout=2.0)
        assert pump.is_alive() is False
        port._pump = None
        port._loop = None
        port._context = None

    def test_close_pump_timeout_when_no_prior_error(self, qapp):
        # H: sin error previo, el timeout del pump es el primario (R2 green)
        bindings = FakeBindings()
        bindings.ignore_quit = True
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pump = port._pump
        with pytest.raises(RuntimeError, match="did not terminate"):
            port.close()
        assert port._closed is True
        assert port._pump is pump
        assert pump.is_alive() is True
        bindings.ignore_quit = False
        bindings.quit_loop(port._loop or "loop")
        pump.join(timeout=2.0)
        assert pump.is_alive() is False
        port._pump = None
        port._loop = None
        port._context = None


class TestRealSmokeTruthfulSeam:
    """M11.3C-R3 P1-04: clasificación truthful del smoke real — SKIP solo
    con dependencia probada ausente; timeout con deps = FAIL (sin waits)."""

    def test_real_smoke_missing_dependency_skips_truthfully(self):
        from michi.infrastructure.audio_engines.gstreamer import (
            _probe_missing_runtime_dependencies,
            _smoke_outcome,
        )

        bindings = FakeBindings()
        assert _probe_missing_runtime_dependencies(bindings) is None
        bindings.missing_factories.add("wavparse")
        missing = _probe_missing_runtime_dependencies(bindings)
        assert missing == "wavparse"  # nombra la dependencia real ausente
        outcome, detail = _smoke_outcome(missing, [], [])
        assert outcome == "skip"
        assert detail == "wavparse"

    def test_real_smoke_timeout_with_dependencies_present_fails(self):
        from michi.infrastructure.audio_engines.gstreamer import (
            _probe_missing_runtime_dependencies,
            _smoke_outcome,
        )

        bindings = FakeBindings()  # sin dependencias ausentes
        missing = _probe_missing_runtime_dependencies(bindings)
        assert missing is None
        # timeout sin dependencia probada ausente = FAIL (no SKIP)
        outcome, detail = _smoke_outcome(missing, [], [])
        assert outcome == "fail"
        assert "did not accept" in detail
        # rejected también es FAIL con la razón visible
        outcome2, detail2 = _smoke_outcome(missing, [], [(Path("/m/x.wav"), "boom")])
        assert outcome2 == "fail"
        assert "boom" in detail2


class TestBusWatchLifecycleSeal:
    """M11.3C-R4: Gst.Bus.remove_watch() contract — NO watch-id argument;
    el ciclo de vida del watch (install/remove) debe ser exacto y las
    fallas de remoción deben ser observables (sin suppress silencioso)."""

    @staticmethod
    def _buses_of(port, bindings):
        return [p.get_bus() for p in bindings.pipelines]

    def test_signature_parity_no_watch_id(self):
        import inspect

        params = list(inspect.signature(FakeBindings.remove_bus_watch).parameters)
        assert params == ["self", "bus"]  # paridad con GStreamerBindings
        # el camino productivo debe fallar ruidosamente si alguien reintroduce
        # el id: la firma del fake no acepta un segundo argumento
        with pytest.raises(TypeError):
            FakeBindings().remove_bus_watch("somebus", 42)

    def test_single_load_close_removes_watch_once(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        bus_a = port._bus
        assert bus_a.watch_installed is True
        port.close()
        assert bus_a.remove_watch_count == 1
        assert bus_a.watch_installed is False

    def test_a_to_b_removes_a_watch(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        bus_a = port._bus
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
        _deliver(port, msg, gen)
        port.load(Path("/m/b.flac"))
        bus_b = port._bus
        assert bus_a.remove_watch_count == 1
        assert bus_a.watch_installed is False
        assert bus_b.watch_installed is True
        # exactamente UN watch activo a la vez
        active = sum(b.watch_installed for b in self._buses_of(port, bindings))
        assert active == 1
        port.close()

    def test_a_b_c_close_full_lifecycle(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        for name in ("a", "b", "c"):
            port.load(Path(f"/m/{name}.flac"))
            msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
            _deliver(port, msg, gen)
        buses = self._buses_of(port, bindings)
        assert buses[0].remove_watch_count == 1  # A removido al armar B
        assert buses[1].remove_watch_count == 1  # B removido al armar C
        assert buses[0].watch_installed is False
        assert buses[1].watch_installed is False
        assert buses[2].watch_installed is True  # C vivo
        port.close()
        assert buses[2].remove_watch_count == 1  # C removido en close
        assert buses[2].watch_installed is False
        assert sum(b.watch_installed for b in buses) == 0  # 0 watches activos

    def test_remove_failure_during_replacement(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        bus_a = port._bus
        bus_a.fail_remove_watch = True
        with pytest.raises(RuntimeError, match="bus watch"):
            port.load(Path("/m/b.flac"))
        # NO se arma B: ni pipeline ni watch nuevos
        assert len(bindings.pipelines) == 1
        assert bus_a.watch_installed is True  # bookkeeping retenido
        assert bus_a.remove_watch_count == 0
        assert port._pipeline is bindings.pipelines[0]
        # A ya no está productivamente reproduciendo (NULL OK antes del
        # fallo de remoción) — pero no hay estado falso de B: A sigue como
        # fuente pendiente canónica (la transacción abortó sin mutarla)
        assert port._pending_path == Path("/m/a.flac")
        assert port._current_path is None

    def test_retry_close_after_remove_failure(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        bus_a = port._bus
        bus_a.fail_remove_watch = True
        with pytest.raises(RuntimeError, match="bus watch"):
            port.load(Path("/m/b.flac"))
        # el fallo fue transitorio: close() debe poder limpiar sin crash
        bus_a.fail_remove_watch = False
        port.close()
        assert bus_a.remove_watch_count == 1
        assert bus_a.watch_installed is False
        assert port._pipeline is None

    def test_close_remove_failure_is_first_error(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        bus_a = port._bus
        bus_a.fail_remove_watch = True
        with pytest.raises(RuntimeError, match="bus watch"):
            port.close()
        assert port._closed is True
        # el fallo de remoción (cronológicamente primero en el teardown
        # terminal) es el error primario; el pipeline queda retenido
        assert port._pipeline is bindings.pipelines[0]
        assert port._pump is None  # la limpieza del pump continuó
        # liberación manual del bookkeeping retenido para salir limpio
        bus_a.fail_remove_watch = False
        port._detach_pipeline_sources()
        port._pipeline = None


@pytest.mark.gstreamer_runtime
class TestRealRuntimeSmoke:
    """P2-01/P1-04: smoke real de GI/GStreamer — SKIP truthful solo con
    dependencia probada ausente; timeout con deps presentes = FAIL."""

    def _tiny_wav(self, tmp_path):
        """WAV determinístico minúsculo (44.1kHz mono 16-bit, ~50ms)."""
        import struct
        import wave

        path = tmp_path / "tone.wav"
        sample_rate = 44100
        duration_frames = int(sample_rate * 0.05)
        with wave.open(str(path), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            frames = b"".join(struct.pack("<h", 0) for _ in range(duration_frames))
            w.writeframes(frames)
        return path

    def test_real_gstreamer_audioport_smoke(self, qapp, tmp_path):
        """P2-01/P1-04: el ADAPTER real completo — pump GLib real, bus watch
        real, fakesink, preroll de un WAV local, close/join.

        SKIP solo con una dependencia PROBADA ausente (preflight de
        factories); timeout con dependencias presentes = FAIL genuino."""
        try:
            import gi  # noqa: PLC0415

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # noqa: PLC0415

            Gst.init(None)
        except (ImportError, ValueError):
            pytest.skip("GI/GStreamer runtime no disponible")

        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerAudioPort,
            GStreamerBindings,
            _probe_missing_runtime_dependencies,
            _smoke_outcome,
        )

        class RealSmokeBindings(GStreamerBindings):
            def make_playbin3(self):
                pipeline = super().make_playbin3()
                if pipeline is None:
                    pytest.skip("playbin3 no disponible")
                fakesink = self._gst.ElementFactory.make(
                    "fakesink", "michi_test_audio_sink"
                )
                if fakesink is None:
                    pytest.skip("GStreamer fakesink no disponible")
                pipeline.set_property("audio-sink", fakesink)
                return pipeline

        bindings = RealSmokeBindings()
        bindings.ensure_loaded()
        # PREFLIGHT truthful: SKIP solo si una dependencia probada está ausente
        missing = _probe_missing_runtime_dependencies(bindings)
        if missing is not None:
            pytest.skip(f"dependency absent: {missing} element factory not available")
        wav = self._tiny_wav(tmp_path)
        port = GStreamerAudioPort(bindings)
        accepted = []
        rejected = []
        states = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(wav)
        # pump real corriendo: bounded wait por la aceptación
        import time

        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            QCoreApplication.processEvents()
            if accepted or rejected:
                break
            time.sleep(0.02)
        outcome, detail = _smoke_outcome(missing, accepted, rejected)
        if outcome != "pass":
            pytest.fail(
                detail + f" (accepted={accepted}, rejected={rejected}, states={states})"
            )
        assert accepted == [wav]
        pump = port._pump
        assert pump is not None and pump.is_alive()
        port.close()
        assert port._pipeline is None
        assert port._pump is None
        assert pump.is_alive() is False

    def test_real_repeated_watch_lifecycle(self, qapp, tmp_path):
        """M11.3C-R4: ciclo REAL repetido add_watch/remove_watch con
        Gst.Bus real — load(A)→load(B)→load(C)→close sin watches viejos."""
        try:
            import gi  # noqa: PLC0415

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # noqa: PLC0415

            Gst.init(None)
        except (ImportError, ValueError):
            pytest.skip("GI/GStreamer runtime no disponible")

        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerAudioPort,
            GStreamerBindings,
            _probe_missing_runtime_dependencies,
        )

        class TrackingRealBindings(GStreamerBindings):
            add_count = 0
            remove_count = 0

            def create_bus_source(self, bus, callback, context=None):
                watch_id = super().create_bus_source(bus, callback, context)
                TrackingRealBindings.add_count += 1
                return watch_id

            def remove_bus_watch(self, bus):
                result = super().remove_bus_watch(bus)
                if result:
                    TrackingRealBindings.remove_count += 1
                return result

            def make_playbin3(self):
                pipeline = super().make_playbin3()
                if pipeline is None:
                    pytest.skip("playbin3 no disponible")
                fakesink = self._gst.ElementFactory.make(
                    "fakesink", "michi_test_audio_sink"
                )
                pipeline.set_property("audio-sink", fakesink)
                return pipeline

        bindings = TrackingRealBindings()
        bindings.ensure_loaded()
        missing = _probe_missing_runtime_dependencies(bindings)
        if missing is not None:
            pytest.skip(f"dependency absent: {missing} element factory not available")
        wav = self._tiny_wav(tmp_path)
        port = GStreamerAudioPort(bindings)
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        import time

        for i, _name in enumerate(("a", "b", "c")):
            accepted.clear()
            port.load(wav)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                QCoreApplication.processEvents()
                if accepted:
                    break
                time.sleep(0.02)
            if not accepted:
                pytest.fail(
                    f"Real GStreamerAudioPort did not accept the WAV on the "
                    f"{i + 1}-th replacement within 2 seconds despite required "
                    f"runtime factories being available"
                )
            # tras cada reemplazo: un watch viejo removido, el nuevo vivo
            assert TrackingRealBindings.add_count == i + 1
            assert TrackingRealBindings.remove_count == i
        port.close()
        assert TrackingRealBindings.add_count == 3
        assert TrackingRealBindings.remove_count == 3
        assert port._pipeline is None
        assert port._bus is None

    def test_real_gi_smoke(self):
        try:
            import gi  # noqa: PLC0415

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # noqa: PLC0415

            Gst.init(None)
        except (ImportError, ValueError):
            pytest.skip("GI/GStreamer runtime no disponible")

        from michi.infrastructure.audio_engines.gstreamer import GStreamerBindings

        bindings = GStreamerBindings()
        bindings.ensure_loaded()
        # enums reales
        assert bindings.STATE.NULL.value == 1
        assert bindings.STATE.PAUSED.value == 3
        assert bindings.STATE.PLAYING.value == 4
        # playbin3 real
        assert bindings.playbin3_available() is True
        pipeline = bindings.make_playbin3()
        assert pipeline is not None
        # contexto custom + bus watch real (M11.3C-R3: add_watch canónico)
        ctx = bindings.create_context()
        bus = bindings.get_bus(pipeline)

        def on_bus(b, m, d=None):
            return True

        watch_id = bindings.create_bus_source(bus, on_bus, ctx)
        assert watch_id is not None
        # M11.3C-R4: Gst.Bus.remove_watch() NO acepta watch-id
        removed = bindings.remove_bus_watch(bus)
        assert removed is True
        # M11.3C-R4: remove_watch() sin watch instalado devuelve False (bool)
        assert bindings.remove_bus_watch(bus) is False
        # teardown real
        bindings.set_state(pipeline, bindings.STATE.NULL)
        assert pipeline.get_state(0).state == Gst.State.NULL
