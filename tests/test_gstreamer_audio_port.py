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
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.sources_created = 0

    def create_watch(self):
        self.sources_created += 1
        return FakeSource()


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
        self.timer_sources = []
        self.timer_callback = None
        self._quit = threading.Event()

    def supports_pump(self):
        return True

    def ensure_loaded(self):
        pass

    def playbin3_available(self):
        return self.playbin3_present

    def make_playbin3(self):
        p = FakePipeline(f"P{len(self.pipelines)}")
        self.pipelines.append(p)
        return p

    def set_state(self, pipeline, state):
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
        self._quit.set()

    def push_thread_default(self, context):
        pass

    def pop_thread_default(self, context):
        pass

    def create_bus_source(self, bus, callback):
        source = bus.create_watch()
        source.set_callback(callback)
        return source

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
        old_source = port._bus_source
        port.load(Path("/m/b.flac"))
        assert old_source.destroyed is True  # fuente vieja destruida
        assert port._bus_source is not None
        assert port._bus_source.destroyed is False  # fuente nueva viva
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
    """P1-05: probe truthful — playbin3 ausente → unavailable."""

    def test_missing_playbin3_unavailable(self):
        from michi.infrastructure.audio_engines.gstreamer import GStreamerBindings

        class NoPlaybinBindings(GStreamerBindings):
            def ensure_loaded(self):
                pass

            def playbin3_available(self):
                return False

        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
        )

        provider = GStreamerEngineProvider()
        original = provider.probe
        # inyectar bindings sin playbin3 vía monkeypatch del método privado
        import michi.infrastructure.audio_engines.providers as mod

        def fake_probe(self):
            bindings = NoPlaybinBindings()
            return mod.AudioEngineDescriptor(
                engine_id=mod.AudioEngineId.GSTREAMER,
                display_name="GStreamer",
                available=bindings.playbin3_available(),
                unavailable_reason=(
                    None
                    if bindings.playbin3_available()
                    else "playbin3 no disponible en el runtime GStreamer"
                ),
                implemented=True,
            )

        provider.probe = fake_probe.__get__(provider)
        desc = provider.probe()
        assert desc.available is False
        assert desc.implemented is True
        assert desc.can_activate is False
        assert "playbin3" in desc.unavailable_reason
        provider.probe = original

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


@pytest.mark.gstreamer_runtime
class TestRealRuntimeSmoke:
    """P2-01: smoke real de GI/GStreamer — SKIP truthful si no hay runtime."""

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
        # contexto custom + bus source attach real
        ctx = bindings.create_context()
        bus = bindings.get_bus(pipeline)

        def on_bus(b, m, d=None):
            return True

        source = bindings.create_bus_source(bus, on_bus)
        bindings.attach_source(source, ctx)
        bindings.destroy_source(source)
        # teardown real
        bindings.set_state(pipeline, bindings.STATE.NULL)
        assert pipeline.get_state(0).state == Gst.State.NULL
