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
        self.remove_watch_exception: Exception | None = None

    def create_watch(self):
        self.sources_created += 1
        return FakeSource()

    def add_watch(self, priority, callback):
        self.watch_installed = True
        self.watch_callback = callback
        return 42  # id sintético (bookkeeping only)

    def remove_watch(self):
        if self.remove_watch_exception is not None:
            raise self.remove_watch_exception
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
        self.null_request_count = 0  # requests STATE.NULL emitidos
        self.fail_remove_watch = False  # buses nuevos heredan el fallo
        self.remove_watch_exception: Exception | None = None  # o la excepción
        # inyección de excepciones de ARM (M11.3C-R6 P1-03, TEST ONLY)
        self.arm_exception_stage: str | None = None
        self.arm_exception: Exception | None = None

    def _raise_if_arm_stage(self, stage):
        if self.arm_exception_stage == stage:
            raise self.arm_exception or ValueError(f"synthetic arm failure: {stage}")

    def supports_pump(self):
        return True

    def ensure_loaded(self):
        pass

    def playbin3_available(self):
        return self.playbin3_present and "playbin3" not in self.missing_factories

    def element_factory_find(self, name):
        return None if name in self.missing_factories else object()

    def make_playbin3(self):
        self._raise_if_arm_stage("make_playbin3")
        p = FakePipeline(f"P{len(self.pipelines)}")
        self.pipelines.append(p)
        return p

    def set_state(self, pipeline, state):
        if state == _FakeState.NULL:
            self.null_request_count += 1
        if state == _FakeState.PAUSED:
            self._raise_if_arm_stage("set_state_paused")
        if state == _FakeState.PLAYING:
            self._raise_if_arm_stage("set_state_playing")
        if self.fail_next_states:
            expected = self.fail_next_states.pop(0)
            if state == expected:
                return False
        if state in self.failed_states:
            return False
        return pipeline.set_state(state)

    def get_bus(self, pipeline):
        self._raise_if_arm_stage("get_bus")
        bus = pipeline.get_bus()
        bus.fail_remove_watch = self.fail_remove_watch
        bus.remove_watch_exception = self.remove_watch_exception
        return bus

    def create_context(self):
        self._raise_if_arm_stage("ensure_pump")
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
        self._raise_if_arm_stage("create_bus_source")
        return bus.add_watch(0, callback)

    def remove_bus_watch(self, bus) -> bool:
        """Misma forma que GStreamerBindings.remove_bus_watch(bus): un solo
        argumento; si el productivo llamara con un id extra, esto reventaría
        con TypeError (paridad de firma)."""
        if bus is None:
            return True
        return bus.remove_watch()

    def attach_source(self, source, context):
        self._raise_if_arm_stage("attach_source")
        return source.attach(context)

    def destroy_source(self, source):
        if source is not None:
            source.destroy()

    def create_timeout_source(self, interval_ms, callback):
        self._raise_if_arm_stage("create_timeout_source")
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
        self._raise_if_arm_stage("set_uri")
        pipeline.set_property("uri", uri)

    def set_volume(self, pipeline, volume):
        self._raise_if_arm_stage("set_volume")
        pipeline.set_property("volume", volume)

    def set_muted(self, pipeline, muted):
        self._raise_if_arm_stage("set_muted")
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
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
        _deliver(port, msg, gen)
        port.stop()
        # M11.3C-R6: la fuente aceptada permanece cargada tras stop
        assert port._pipeline is not None
        assert port._current_path == Path("/m/a.flac")
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
        port.play()
        m4, g4 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, m4, g4)
        m3, g3 = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m3, g3)
        # M11.3C-R6: EOS converge a STOPPED (st) ANTES de EOM (eom)
        assert events == ["acc:a.flac", "dur:5000", "st", "st", "eom"]
        router.unbind()
        m5, g5 = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m5, g5)
        assert events == ["acc:a.flac", "dur:5000", "st", "st", "eom"]
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
        # M11.3C-R6: la fuente aceptada permanece cargada tras stop
        assert port._current_path == Path("/m/a.flac")
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
        # R5: el fallo de remoción (cronológicamente primero en el teardown
        # terminal) es el error primario, pero el pipeline igual recibió
        # NULL y se liberó; el bookkeeping del bus watch queda como
        # evidencia de la remoción fallida
        assert port._pipeline is None  # NULL OK → transport detenido
        assert port._bus_source is not None  # bookkeeping retenido
        assert port._pump is None  # la limpieza del pump continuó
        # liberación manual del bookkeeping retenido para salir limpio
        bus_a.fail_remove_watch = False
        port._detach_pipeline_sources()
        assert bus_a.remove_watch_count == 1
        assert port._bus_source is None


class TestTerminalCleanupFirstErrorWins:
    """M11.3C-R5: el cleanup terminal es BEST-EFFORT — un error de limpieza
    NUNCA corta los pasos posteriores; el primer error cronológico gana."""

    def test_close_remove_failure_still_nulls_pipeline(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = port._pipeline
        bus_a = port._bus
        bus_a.fail_remove_watch = True
        with pytest.raises(RuntimeError, match="bus watch"):
            port.close()
        assert port._closed is True
        # el pipeline recibió NULL a pesar del fallo del watch
        assert bindings.null_request_count == 1
        assert pipeline.state == _FakeState.NULL
        assert port._pipeline is None  # NULL OK → transport detenido
        assert bus_a.remove_watch_count == 0  # la remoción falló (evidencia)
        assert port._pump is None  # pump terminó
        assert port._timer_source is None  # timer destruido
        bus_a.fail_remove_watch = False
        port._detach_pipeline_sources()

    def test_close_remove_and_null_double_failure(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = port._pipeline
        bus_a = port._bus
        bus_a.fail_remove_watch = True
        bindings.failed_states.add(_FakeState.NULL)
        with pytest.raises(RuntimeError, match="bus watch"):
            port.close()
        # first-error-wins: el watch falló primero → primario
        assert bindings.null_request_count == 1  # NULL igual se intentó
        assert port._pipeline is pipeline  # NULL falló → retenido
        assert port._pump is None  # pump cleanup continuó
        assert port._closed is True
        bus_a.fail_remove_watch = False
        bindings.failed_states.discard(_FakeState.NULL)
        port._detach_pipeline_sources()
        port._pipeline = None

    def test_close_null_failure_primary_over_pump_timeout(self, qapp):
        # R3 regression: remove OK + NULL FAIL + pump timeout → NULL primario
        bindings = FakeBindings()
        bindings.failed_states.add(_FakeState.NULL)
        bindings.ignore_quit = True
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pump = port._pump
        with pytest.raises(RuntimeError, match="NULL"):
            port.close()
        assert port._pump is pump  # worker vivo retenido (secundario)
        bindings.ignore_quit = False
        bindings.quit_loop(port._loop or "loop")
        pump.join(timeout=2.0)
        port._pump = None
        port._loop = None
        port._context = None

    def test_close_pump_only_failure(self, qapp):
        # R2/R4 regression: remove OK + NULL OK + pump timeout → pump primario
        bindings = FakeBindings()
        bindings.ignore_quit = True
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pump = port._pump
        with pytest.raises(RuntimeError, match="did not terminate"):
            port.close()
        assert port._pipeline is None  # NULL OK
        assert port._pump is pump
        bindings.ignore_quit = False
        bindings.quit_loop(port._loop or "loop")
        pump.join(timeout=2.0)
        port._pump = None
        port._loop = None
        port._context = None


class TestPrerollCleanupErrorOrder:
    """M11.3C-R5 P1-02: en la limpieza del preroll fallido, el NULL cleanup
    es PRIMARIO; el detach del bus es SECUNDARIO y nunca lo reemplaza."""

    def _port_with(self, bindings, fail_paused, fail_null, fail_remove):
        if fail_paused:
            bindings.failed_states.add(_FakeState.PAUSED)
        if fail_null:
            bindings.failed_states.add(_FakeState.NULL)
        bindings.fail_remove_watch = fail_remove
        port = _port(bindings)
        rejected = []
        accepted = []
        states = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        return port, rejected, accepted, states

    def test_preroll_null_ok_remove_ok_reject_only(self, qapp):
        # CASE 1: PAUSED FAIL + NULL OK + remove OK → solo rechazo, reusable
        bindings = FakeBindings()
        port, rejected, accepted, _states = self._port_with(
            bindings, True, False, False
        )
        port.load(Path("/m/b.flac"))
        for _ in range(5):
            QCoreApplication.processEvents()
        assert rejected == [
            (Path("/m/b.flac"), "GStreamer failed to enter PAUSED during preroll")
        ]
        assert accepted == []
        assert port._pipeline is None  # NULL OK → liberado
        assert port._bus_source is None
        # port reutilizable
        port.close()

    def test_preroll_null_ok_remove_fail_raises_bus_error(self, qapp):
        # CASE 2: PAUSED FAIL + NULL OK + remove FAIL → bus cleanup error
        bindings = FakeBindings()
        port, rejected, accepted, states = self._port_with(bindings, True, False, True)
        with pytest.raises(RuntimeError, match="bus watch"):
            port.load(Path("/m/b.flac"))
        for _ in range(5):
            QCoreApplication.processEvents()
        assert rejected == [
            (Path("/m/b.flac"), "GStreamer failed to enter PAUSED during preroll")
        ]
        assert accepted == []
        assert states == []
        # el pipeline ya llegó a NULL pero el ownership queda retenido como
        # evidencia de que el lifecycle cleanup no completó
        assert port._pipeline is not None
        assert port._bus_source is not None  # bookkeeping del watch retenido
        # limpieza para salir del test
        bus = port._bus
        bus.fail_remove_watch = False
        port._detach_pipeline_sources()
        port._pipeline = None

    def test_preroll_triple_failure_null_is_primary(self, qapp):
        # CASE 3 CRÍTICO: PAUSED FAIL + NULL FAIL + remove FAIL
        # → primario: NULL cleanup failure (NO "bus watch")
        bindings = FakeBindings()
        port, rejected, accepted, states = self._port_with(bindings, True, True, True)
        with pytest.raises(RuntimeError, match="NULL"):
            port.load(Path("/m/b.flac"))
        for _ in range(5):
            QCoreApplication.processEvents()
        assert rejected == [
            (Path("/m/b.flac"), "GStreamer failed to enter PAUSED during preroll")
        ]
        assert accepted == []
        assert states == []
        failed_pipeline = bindings.pipelines[-1]
        assert port._pipeline is failed_pipeline  # ownership retenido
        assert bindings.null_request_count == 1  # NULL intentado exactamente 1
        assert port._current_path is None
        assert port._pending_path is None
        # close() posterior con fallos removidos limpia todo
        bindings.failed_states.discard(_FakeState.NULL)
        bus = port._bus
        bus.fail_remove_watch = False
        port.close()
        assert port._pipeline is None


class TestCleanupExceptionBoundary:
    """M11.3C-R5.1: los boundaries de cleanup best-effort capturan CUALQUIER
    Exception normal (no solo RuntimeError) — el binding puede lanzar
    ValueError/TypeError/GLib.Error. BaseException nunca se captura."""

    def test_close_detach_exception_still_attempts_null(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = port._pipeline
        bus_a = port._bus
        bus_a.remove_watch_exception = ValueError("synthetic remove exception")
        with pytest.raises(ValueError, match="synthetic remove exception"):
            port.close()
        assert port._closed is True
        assert bindings.null_request_count == 1  # NULL intentado pese a todo
        assert pipeline.state == _FakeState.NULL
        assert port._pipeline is None  # NULL OK → liberado
        assert port._timer_source is None  # timer cleanup continuó
        assert port._pump is None  # pump cleanup continuó
        assert bus_a.remove_watch_count == 0  # la remoción no ocurrió (evidencia)

    def test_close_detach_typeerror_null_fails_retains_pipeline(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = port._pipeline
        bus_a = port._bus
        bus_a.remove_watch_exception = TypeError("synthetic remove exception")
        bindings.failed_states.add(_FakeState.NULL)
        with pytest.raises(TypeError, match="synthetic remove exception"):
            port.close()
        # TypeError es PRIMARIO (el detach ocurre primero en la cronología),
        # pero el NULL igual se intentó y el pipeline se retiene
        assert bindings.null_request_count == 1
        assert port._pipeline is pipeline  # NULL falló → retenido
        assert port._pump is None  # pump cleanup continuó
        assert port._closed is True

    def test_close_detach_exception_pump_timeout_keeps_first_error(self, qapp):
        bindings = FakeBindings()
        bindings.ignore_quit = True
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        bus_a = port._bus
        pump = port._pump
        bus_a.remove_watch_exception = ValueError("synthetic remove exception")
        with pytest.raises(ValueError, match="synthetic remove exception"):
            port.close()
        # ValueError primario; el timeout del pump es secundario
        assert port._pipeline is None  # NULL OK
        assert port._pump is pump  # worker vivo retenido (secundario)
        bindings.ignore_quit = False
        bindings.quit_loop(port._loop or "loop")
        pump.join(timeout=2.0)
        port._pump = None
        port._loop = None
        port._context = None

    def test_preroll_null_ok_detach_exception(self, qapp):
        bindings = FakeBindings()
        bindings.failed_states.add(_FakeState.PAUSED)
        bindings.remove_watch_exception = ValueError("synthetic detach exception")
        port = _port(bindings)
        rejected = []
        accepted = []
        states = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        with pytest.raises(ValueError, match="synthetic detach exception"):
            port.load(Path("/m/b.flac"))
        for _ in range(5):
            QCoreApplication.processEvents()
        assert rejected == [
            (Path("/m/b.flac"), "GStreamer failed to enter PAUSED during preroll")
        ]
        assert accepted == []
        assert states == []
        assert bindings.null_request_count == 1  # el NULL OK ocurrió
        assert port._pipeline is not None  # ownership retenido (evidencia)
        bus = port._bus
        bus.remove_watch_exception = None
        port._detach_pipeline_sources()
        port._pipeline = None

    def test_preroll_triple_detach_exception_null_is_primary(self, qapp):
        # CRÍTICO: PAUSED FAIL + NULL FAIL + detach ValueError
        # → primario: NULL cleanup RuntimeError (NO ValueError)
        bindings = FakeBindings()
        bindings.failed_states.update({_FakeState.PAUSED, _FakeState.NULL})
        bindings.remove_watch_exception = ValueError("synthetic detach exception")
        port = _port(bindings)
        rejected = []
        accepted = []
        states = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        with pytest.raises(RuntimeError, match="NULL"):
            port.load(Path("/m/b.flac"))
        for _ in range(5):
            QCoreApplication.processEvents()
        assert rejected == [
            (Path("/m/b.flac"), "GStreamer failed to enter PAUSED during preroll")
        ]
        assert accepted == []
        assert states == []
        failed_pipeline = bindings.pipelines[-1]
        assert port._pipeline is failed_pipeline  # retenido
        assert bindings.null_request_count == 1
        assert port._pending_path is None
        assert port._current_path is None
        # limpieza del test: close() con fallos removidos limpia todo
        bindings.failed_states.discard(_FakeState.NULL)
        bus = port._bus
        bus.remove_watch_exception = None
        port.close()
        assert port._pipeline is None


class TestAcceptedStopReplay:
    """M11.3C-R6 P1-01: stop sobre una fuente ACEPTADA detiene el transporte
    sin descargar la fuente — replay sin load, generación/bus intactos."""

    def _accepted_playing(self, bindings):
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline)
        _deliver(port, msg, gen)
        port.play()
        m2, g2 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        return port, pipeline

    def test_accepted_stop_retains_source_and_generation(self, qapp):
        bindings = FakeBindings()
        port, pipeline = self._accepted_playing(bindings)
        generation_before = port._generation
        bus_before = port._bus
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.stop()
        for _ in range(5):
            QCoreApplication.processEvents()
        assert states[-1] == PlaybackStatus.STOPPED
        assert port._current_path == Path("/m/a.flac")  # A retenida
        assert port._generation == generation_before  # generación intacta
        assert port._pipeline is pipeline  # mismo pipeline
        assert port._bus is bus_before  # mismo bus
        assert bus_before.watch_installed is True  # watch sigue instalado
        assert port._pending_play is False
        port.close()

    def test_stop_then_play_delivers_playing(self, qapp):
        bindings = FakeBindings()
        port, pipeline = self._accepted_playing(bindings)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.stop()
        port.play()
        m, g = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, m, g)
        assert states[-1] == PlaybackStatus.PLAYING  # generación N válida
        assert port._current_path == Path("/m/a.flac")
        port.close()

    def test_stop_then_resume_delivers_playing(self, qapp):
        bindings = FakeBindings()
        port, pipeline = self._accepted_playing(bindings)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.stop()
        port.resume()
        m, g = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, m, g)
        assert states[-1] == PlaybackStatus.PLAYING
        port.close()

    def test_position_polling_after_stop_play(self, qapp):
        bindings = FakeBindings()
        port, pipeline = self._accepted_playing(bindings)
        positions = []
        port.subscribe_position_changed(lambda ms: positions.append(ms))
        port.stop()
        port.play()
        m, g = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, m, g)
        port._poll_position()  # seam del timer: current_path retenido
        for _ in range(5):
            QCoreApplication.processEvents()
        assert len(positions) == 1  # posición entregada para A tras replay
        port.close()

    def test_stop_null_failure_keeps_identity_and_generation(self, qapp):
        bindings = FakeBindings()
        port, pipeline = self._accepted_playing(bindings)
        generation_before = port._generation
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        bindings.failed_states.add(_FakeState.NULL)
        port.stop()
        assert PlaybackStatus.STOPPED not in states  # sin claim falso
        assert port._current_path == Path("/m/a.flac")
        assert port._generation == generation_before
        assert port._pipeline is pipeline
        bindings.failed_states.discard(_FakeState.NULL)
        port.close()


class TestPendingStopCancellation:
    """M11.3C-R6 P1-01: stop sobre un candidato PENDIENTE = cancelación."""

    def test_stop_cancels_pending_candidate(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/b.flac"))  # preroll pendiente, sin ASYNC_DONE aún
        pipeline_b = bindings.pipelines[-1]
        bus_b = port._bus
        assert port._pending_path == Path("/m/b.flac")
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.stop()
        assert port._pending_path is None  # candidato cancelado
        assert port._current_path is None
        assert port._pipeline is None  # pipeline candidato liberado
        assert bus_b.watch_installed is False  # watch liberado
        # late ASYNC_DONE (generación vieja) → ignorado
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_b)
        _deliver(port, msg, gen)
        assert accepted == []
        assert port._current_path is None
        port.close()

    def test_play_after_cancelled_pending_does_not_resurrect(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/b.flac"))
        port.stop()
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.play()  # sin pipeline: no-op, no resucita B
        assert port._pipeline is None
        assert states == []
        assert port._current_path is None
        port.close()


class TestEosConvergence:
    """M11.3C-R6 P1-02: EOS converge a STOPPED, EOM una vez por ciclo,
    replay same-source definido; late EOS tras stop explícito ignorado."""

    def _playing_a(self, bindings):
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline)
        _deliver(port, msg, gen)
        port.play()
        m2, g2 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        return port, pipeline

    def test_eos_converges_stopped_and_emits_eom_once(self, qapp):
        bindings = FakeBindings()
        port, pipeline = self._playing_a(bindings)
        states = []
        eoms = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.subscribe_end_of_media(lambda: eoms.append(1))
        m, g = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m, g)
        assert states[-1] == PlaybackStatus.STOPPED  # convergencia
        assert eoms == [1]  # EOM exactamente una vez
        assert port._current_path == Path("/m/a.flac")  # fuente retenida
        # EOS duplicado del mismo ciclo → sin segundo EOM
        m2, g2 = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m2, g2)
        assert eoms == [1]
        port.close()

    def test_play_after_eos_replays_same_source(self, qapp):
        bindings = FakeBindings()
        port, pipeline = self._playing_a(bindings)
        states = []
        eoms = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.subscribe_end_of_media(lambda: eoms.append(1))
        m, g = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m, g)
        assert eoms == [1]
        # replay: play() reinicia NULL→PLAYING sin pipeline nuevo
        port.play()
        assert port._eos_emitted is False  # marcador reseteado tras éxito
        m2, g2 = msg_state(port, pipeline, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        assert states[-1] == PlaybackStatus.PLAYING
        assert len(bindings.pipelines) == 1  # mismo pipeline, sin reload
        # segundo EOS → segundo EOM (total 2)
        m3, g3 = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m3, g3)
        assert eoms == [1, 1]
        assert states[-1] == PlaybackStatus.STOPPED
        port.close()

    def test_eos_replay_null_failure_retryable(self, qapp):
        bindings = FakeBindings()
        port, pipeline = self._playing_a(bindings)
        eoms = []
        port.subscribe_end_of_media(lambda: eoms.append(1))
        m, g = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m, g)
        bindings.failed_states.add(_FakeState.NULL)
        port.play()
        assert port._eos_emitted is True  # retryable
        assert port._pending_play is False
        # retry con éxito
        bindings.failed_states.clear()
        port.play()
        assert port._eos_emitted is False
        port.close()

    def test_eos_replay_playing_failure_retryable(self, qapp):
        bindings = FakeBindings()
        port, pipeline = self._playing_a(bindings)
        eoms = []
        port.subscribe_end_of_media(lambda: eoms.append(1))
        m, g = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m, g)
        bindings.failed_states.add(_FakeState.PLAYING)
        port.play()  # NULL OK, PLAYING FAIL
        assert port._eos_emitted is True  # no reseteado: retryable
        assert port._pending_play is False
        bindings.failed_states.clear()
        port.play()
        assert port._eos_emitted is False
        port.close()

    def test_late_eos_after_explicit_stop_ignored(self, qapp):
        bindings = FakeBindings()
        port, pipeline = self._playing_a(bindings)
        eoms = []
        port.subscribe_end_of_media(lambda: eoms.append(1))
        # EOS encolado antes del stop explícito; el stop gana
        port.stop()
        m, g = _msg(port, _FakeMsgType.EOS, pipeline)
        _deliver(port, m, g)
        assert eoms == []  # sin EOM falso
        assert port._current_state == PlaybackStatus.STOPPED  # ya stop
        assert port._pending_play is False
        port.close()


class TestArmTransaction:
    """M11.3C-R6 P1-03 / R6.1: el ARM del pipeline nuevo es
    exception-atomic — la excepción de ARM ORIGINAL queda como __cause__ de
    AudioLoadError(previous_source_preserved=False) y el adapter coherente."""

    ARM_STAGES = [
        "make_playbin3",
        "set_volume",
        "set_muted",
        "get_bus",
        "set_uri",
        "ensure_pump",
        "create_bus_source",
        "create_timeout_source",
        "attach_source",
        "set_state_paused",
    ]

    @pytest.mark.parametrize("stage", ARM_STAGES)
    def test_arm_exception_leaves_adapter_coherent(self, qapp, stage):
        from michi.application.ports import AudioLoadError

        bindings = FakeBindings()
        bindings.arm_exception_stage = stage
        bindings.arm_exception = ValueError(f"synthetic arm failure: {stage}")
        port = _port(bindings)
        accepted = []
        states = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        with pytest.raises(AudioLoadError) as caught:
            port.load(Path("/m/b.flac"))
        # disposición destructiva (PHASE A ya cruzó el commit point) y la
        # causa de bajo nivel preservada como __cause__
        assert caught.value.previous_source_preserved is False
        assert caught.value.candidate_path == Path("/m/b.flac")
        assert isinstance(caught.value.__cause__, ValueError)
        assert f"arm failure: {stage}" in str(caught.value.__cause__)
        # sin candidato fantasma, sin media falsa
        assert port._pending_path is None
        assert port._current_path is None
        assert port._pending_play is False
        assert accepted == []
        assert states == []
        # el port puede cerrarse limpiamente
        port.close()

    def test_arm_failure_after_watch_attached_invalidates_generation(self, qapp):
        bindings = FakeBindings()
        bindings.arm_exception_stage = "attach_source"
        port = _port(bindings)
        from michi.application.ports import AudioLoadError

        with pytest.raises(AudioLoadError) as caught:
            port.load(Path("/m/b.flac"))
        assert caught.value.previous_source_preserved is False
        assert isinstance(caught.value.__cause__, ValueError)
        bus_b = bindings.pipelines[-1].get_bus()
        assert bus_b.watch_installed is False  # watch removido en rollback
        # late mensaje del candidato fallido (generación vieja) → ignorado
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
        _deliver(port, msg, gen)
        assert accepted == []
        assert port._current_path is None
        port.close()

    def test_arm_retry_after_failure(self, qapp):
        bindings = FakeBindings()
        bindings.arm_exception_stage = "set_uri"
        port = _port(bindings)
        from michi.application.ports import AudioLoadError

        with pytest.raises(AudioLoadError):
            port.load(Path("/m/b.flac"))
        # retry: el port sigue usable
        bindings.arm_exception_stage = None
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.load(Path("/m/c.flac"))
        pipeline_c = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_c)
        _deliver(port, msg, gen)
        assert accepted == [Path("/m/c.flac")]
        port.play()
        m2, g2 = msg_state(port, pipeline_c, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        port.close()

    def test_arm_failure_after_old_source_playing_converges_stopped(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        # A aceptada y PLAYING
        port.load(Path("/m/a.flac"))
        pipeline_a = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a)
        _deliver(port, msg, gen)
        port.play()
        m2, g2 = msg_state(port, pipeline_a, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        # B arma falla en set_uri (después del teardown de A)
        bindings.arm_exception_stage = "set_uri"
        from michi.application.ports import AudioLoadError

        with pytest.raises(AudioLoadError):
            port.load(Path("/m/b.flac"))
        for _ in range(5):
            QCoreApplication.processEvents()
        assert states[-1] == PlaybackStatus.STOPPED  # sin PLAYING falso
        assert port._current_path is None
        assert port._pending_path is None
        assert port._current_state == PlaybackStatus.STOPPED
        port.close()

    def test_arm_failure_timer_does_not_poison_next_load(self, qapp):
        bindings = FakeBindings()
        bindings.arm_exception_stage = "attach_source"  # timer creado y falla
        port = _port(bindings)
        from michi.application.ports import AudioLoadError

        with pytest.raises(AudioLoadError):
            port.load(Path("/m/b.flac"))
        # el timer creado por el arm fallido se destruyó
        assert port._timer_source is None
        # retry exitoso: el timer nuevo se attacha normalmente
        bindings.arm_exception_stage = None
        port.load(Path("/m/c.flac"))
        assert port._timer_source is not None
        assert port._timer_source.attached is True
        port.close()

    def test_arm_exception_null_cleanup_failure_keeps_primary(self, qapp):
        bindings = FakeBindings()
        bindings.arm_exception_stage = "set_uri"
        bindings.failed_states.add(_FakeState.NULL)  # cleanup NULL falla
        bindings.fail_remove_watch = True  # y el remove del watch falla
        port = _port(bindings)
        from michi.application.ports import AudioLoadError

        with pytest.raises(AudioLoadError) as caught:
            port.load(Path("/m/b.flac"))
        assert isinstance(caught.value.__cause__, ValueError)
        # la excepción ORIGINAL del arm sigue siendo primaria
        assert port._pending_path is None
        assert port._current_path is None
        # pipeline retenido (NULL cleanup falló) para diagnóstico/close
        assert port._pipeline is not None
        # close() posterior limpia el bookkeeping retenido
        bindings.failed_states.clear()
        bindings.fail_remove_watch = False
        port.close()
        assert port._pipeline is None


class TestGStreamerQueueIntegration:
    """M11.3C-R6: GStreamerAudioPort (FakeBindings) → PlaybackService →
    QueueService — auto-advance por EOS del adapter real."""

    def test_eos_advances_to_b_exactly_once(self, qapp):
        from michi.application.coordinator import PlaybackCoordinator
        from michi.application.playback_service import PlaybackService
        from michi.application.queue_service import QueueService

        bindings = FakeBindings()
        port = GStreamerAudioPort(bindings)
        svc = PlaybackService(port)
        q = QueueService(svc)
        q.add(Path("/m/a.flac"))
        q.add(Path("/m/b.flac"))
        q.play_index(0)
        coord = PlaybackCoordinator(port, q, svc)
        coord.start()
        # A aceptada vía el adapter real
        pipeline_a = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a)
        _deliver(port, msg, gen)
        assert q.state.current_index == 0
        port.play()
        m2, g2 = msg_state(port, pipeline_a, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        # EOS → STOPPED + EOM → Queue pide B exactamente una vez
        eos, eg = _msg(port, _FakeMsgType.EOS, pipeline_a)
        _deliver(port, eos, eg)
        assert q.state.current_index == 0  # B pending, no commiteado
        assert len(bindings.pipelines) == 2  # B armado exactamente una vez
        # B aceptada
        pipeline_b = bindings.pipelines[-1]
        m3, g3 = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_b)
        _deliver(port, m3, g3)
        assert q.state.current_index == 1
        port.close()

    def test_repeat_one_requests_a_exactly_once(self, qapp):
        from michi.application.coordinator import PlaybackCoordinator
        from michi.application.playback_service import PlaybackService
        from michi.application.queue_service import QueueService
        from michi.domain.queue import RepeatMode

        bindings = FakeBindings()
        port = GStreamerAudioPort(bindings)
        svc = PlaybackService(port)
        q = QueueService(svc)
        q.add(Path("/m/a.flac"))
        q.set_repeat_mode(RepeatMode.ONE)
        q.play_index(0)
        coord = PlaybackCoordinator(port, q, svc)
        coord.start()
        pipeline_a = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a)
        _deliver(port, msg, gen)
        port.play()
        m2, g2 = msg_state(port, pipeline_a, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        eos, eg = _msg(port, _FakeMsgType.EOS, pipeline_a)
        _deliver(port, eos, eg)
        assert len(bindings.pipelines) == 2  # A pedida exactamente una vez
        pipeline_a2 = bindings.pipelines[-1]
        m3, g3 = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a2)
        _deliver(port, m3, g3)
        assert q.state.current_index == 0
        assert svc.state.file_path == Path("/m/a.flac")
        port.close()


class TestFailedArmOwnership:
    """M11.3C-R6.1 P1-01: tras un ARM fallido con remoción del watch también
    fallida, el pipeline se retiene como ANCLA de limpieza retryable —
    nunca _pipeline=None con _bus_source!=None."""

    def _failed_arm_with_retained_watch(self):
        bindings = FakeBindings()
        bindings.arm_exception_stage = "attach_source"  # watch ya instalado
        bindings.fail_remove_watch = True  # y la remoción falla
        bindings.arm_exception = ValueError("synthetic attach failure")
        port = _port(bindings)
        accepted = []
        states = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        from michi.application.ports import AudioLoadError

        with pytest.raises(AudioLoadError) as caught:
            port.load(Path("/m/b.flac"))
        assert isinstance(caught.value.__cause__, ValueError)
        assert caught.value.previous_source_preserved is False
        return bindings, port, accepted, states

    def test_failed_arm_retains_pipeline_bus_and_watch(self, qapp):
        bindings, port, accepted, states = self._failed_arm_with_retained_watch()
        # NULL cleanup OK + detach FAIL → pipeline retenido como ancla
        assert port._pipeline is not None
        assert port._bus is not None
        assert port._bus_source is not None
        bus_b = port._bus
        assert bus_b.watch_installed is True  # watch sigue instalado
        assert bus_b.remove_watch_count == 0
        # identidad semántica limpia y generación invalidada
        assert port._pending_path is None
        assert port._current_path is None
        assert accepted == []
        assert states == []
        bus_b.fail_remove_watch = False  # liberar antes del close
        port.close()

    def test_close_retries_retained_watch(self, qapp):
        bindings, port, accepted, states = self._failed_arm_with_retained_watch()
        bus_b = port._bus
        # deshabilitar el fallo en el BUS retenido (el flag del bindings se
        # copió al bus en get_bus)
        bus_b.fail_remove_watch = False
        port.close()
        assert bus_b.watch_installed is False  # watch removido en el retry
        assert bus_b.remove_watch_count == 1
        assert port._bus_source is None
        assert port._bus is None
        assert port._pipeline is None
        assert port._pump is None  # pump terminó

    def test_next_load_recovers_retained_watch(self, qapp):
        bindings, port, accepted, states = self._failed_arm_with_retained_watch()
        bus_b = port._bus
        bus_b.fail_remove_watch = False
        bindings.fail_remove_watch = False  # los buses nuevos no heredan fallo
        bindings.arm_exception_stage = None  # desarmar el inyector
        # load(C): _try_stop_pipeline limpia el ownership retenido de B y
        # arma C exactamente una vez
        accepted.clear()
        port.load(Path("/m/c.flac"))
        assert bus_b.watch_installed is False  # B watch removido
        assert bus_b.remove_watch_count == 1
        pipeline_c = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_c)
        _deliver(port, msg, gen)
        assert accepted == [Path("/m/c.flac")]
        assert port._bus is not None
        assert port._bus.watch_installed is True  # un solo watch activo
        port.close()


class TestGStreamerPlaybackDisposition:
    """M11.3C-R6.1 P1-02: GStreamerAudioPort + PlaybackService — la verdad
    del backend y la de la app convergen tras fallos destructivos."""

    def test_destructive_arm_failure_converges_playback(self, qapp):
        from michi.application.playback_service import PlaybackService
        from michi.application.ports import AudioLoadError

        bindings = FakeBindings()
        port = GStreamerAudioPort(bindings)
        svc = PlaybackService(port)
        # A aceptada y PLAYING
        svc.load_and_play(Path("/m/a.flac"))
        pipeline_a = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a)
        _deliver(port, msg, gen)
        port.play()
        m2, g2 = msg_state(port, pipeline_a, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        assert svc._accepted is True
        # B ARM falla en set_uri (después del teardown destructivo de A)
        bindings.arm_exception_stage = "set_uri"
        bindings.arm_exception = ValueError("synthetic set_uri failure")
        with pytest.raises(AudioLoadError) as caught:
            svc.load_and_play(Path("/m/b.flac"))
        assert caught.value.previous_source_preserved is False
        assert isinstance(caught.value.__cause__, ValueError)
        assert "set_uri" in str(caught.value.__cause__)
        # GStreamer: sin fuente
        assert port._current_path is None
        assert port._pending_path is None
        # PlaybackService: identidad lógica A, sin aceptación backend
        assert svc.state.file_path == Path("/m/a.flac")
        assert svc._accepted is False
        assert svc._intent is False
        assert svc.state.status == PlaybackStatus.STOPPED
        port.close()

    def test_play_recovers_logical_track_after_destructive_failure(self, qapp):
        from michi.application.playback_service import PlaybackService
        from michi.application.ports import AudioLoadError

        bindings = FakeBindings()
        port = GStreamerAudioPort(bindings)
        svc = PlaybackService(port)
        svc.load_and_play(Path("/m/a.flac"))
        pipeline_a = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a)
        _deliver(port, msg, gen)
        bindings.arm_exception_stage = "set_uri"
        bindings.arm_exception = ValueError("synthetic set_uri failure")
        with pytest.raises(AudioLoadError):
            svc.load_and_play(Path("/m/b.flac"))
        # play() recarga A por el camino canónico
        bindings.arm_exception_stage = None
        svc.play()
        assert port._pending_path == Path("/m/a.flac")  # A pendiente de nuevo
        pipeline_a2 = bindings.pipelines[-1]
        m2, g2 = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a2)
        _deliver(port, m2, g2)
        assert svc._accepted is True
        port.play()
        m3, g3 = msg_state(port, pipeline_a2, _FakeState.PLAYING)
        _deliver(port, m3, g3)
        assert svc.state.status == PlaybackStatus.PLAYING  # sin no-op
        port.close()

    def test_controlled_rejection_then_play_recovers_a(self, qapp):
        from michi.application.playback_service import PlaybackService

        bindings = FakeBindings()
        port = GStreamerAudioPort(bindings)
        svc = PlaybackService(port)
        svc.load_and_play(Path("/m/a.flac"))
        pipeline_a = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a)
        _deliver(port, msg, gen)
        # B preroll controlado falla (PAUSED → False) → rejection
        bindings.failed_states.add(_FakeState.PAUSED)
        svc.load_and_play(Path("/m/b.flac"))
        for _ in range(5):
            QCoreApplication.processEvents()
        assert svc.state.file_path == Path("/m/a.flac")  # identidad lógica
        assert svc._accepted is False  # sin autoridad backend
        assert svc.state.status == PlaybackStatus.STOPPED
        # play() recarga A
        bindings.failed_states.clear()
        svc.play()
        assert port._pending_path == Path("/m/a.flac")
        pipeline_a2 = bindings.pipelines[-1]
        m2, g2 = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a2)
        _deliver(port, m2, g2)
        assert svc._accepted is True
        port.close()

    def test_play_phase_failure_converges_playback(self, qapp):
        """M11.3C-R6.2 P1-02 full-stack: load(B) OK + play(B) raise →
        sin aceptación falsa de A, sin late-commit de B, play() recarga A."""
        from michi.application.playback_service import PlaybackService

        bindings = FakeBindings()
        port = GStreamerAudioPort(bindings)
        svc = PlaybackService(port)
        # A aceptada y PLAYING
        svc.load_and_play(Path("/m/a.flac"))
        pipeline_a = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a)
        _deliver(port, msg, gen)
        port.play()
        m2, g2 = msg_state(port, pipeline_a, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        assert svc._accepted is True
        # B: load OK (armado, preroll OK) + request PLAYING RAISE
        bindings.arm_exception_stage = "set_state_playing"
        bindings.arm_exception = RuntimeError("synthetic play failure")
        with pytest.raises(RuntimeError, match="play failure"):
            svc.load_and_play(Path("/m/b.flac"))
        # PlaybackService: identidad lógica A, sin autoridad backend
        assert svc.state.file_path == Path("/m/a.flac")
        assert svc._accepted is False
        assert svc._intent is False
        assert svc.state.status == PlaybackStatus.STOPPED
        assert svc._pending_path is None
        # late media_accepted(B) → ignorado (B nunca committea)
        bindings.arm_exception_stage = None
        pipeline_b = bindings.pipelines[-1]
        m3, g3 = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_b)
        _deliver(port, m3, g3)
        assert svc.state.file_path == Path("/m/a.flac")
        assert svc._accepted is False
        # play() recarga A por el camino canónico → PLAYING
        svc.play()
        assert port._pending_path == Path("/m/a.flac")
        pipeline_a2 = bindings.pipelines[-1]
        m4, g4 = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a2)
        _deliver(port, m4, g4)
        assert svc._accepted is True
        assert svc.state.file_path == Path("/m/a.flac")
        port.close()


class TestPostPlayFailureOwnership:
    """M11.3C-R6.3 P1-01: tras un RAISE del request PLAYING sobre un
    candidato PENDING, el backend cancela B failure-atomic — la igualdad
    logical/AudioPort/backend queda sellada y los eventos tardíos de B
    mueren en el AudioPort."""

    def _a_accepted_and_pending_b(self, bindings):
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline_a = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a)
        _deliver(port, msg, gen)
        port.play()
        m2, g2 = msg_state(port, pipeline_a, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        # B: load OK (armado, preroll OK) sin aceptación aún
        port.load(Path("/m/b.flac"))
        return port, bindings

    def test_play_failure_cancels_pending_candidate(self, qapp):
        bindings = FakeBindings()
        port, _ = self._a_accepted_and_pending_b(bindings)
        pipeline_b = bindings.pipelines[-1]
        bus_b = port._bus
        generation_b = port._generation
        bindings.arm_exception_stage = "set_state_playing"
        bindings.arm_exception = RuntimeError("synthetic play failure")
        with pytest.raises(RuntimeError, match="play failure"):
            port.play()
        # B terminal en el backend (cleanup exitoso)
        assert port._pending_path is None
        assert port._current_path is None
        assert port._pending_play is False
        assert port._generation == generation_b + 1  # generación invalidada
        assert port._pipeline is None  # pipeline B liberado
        assert port._bus is None
        assert port._bus_source is None
        assert bus_b.watch_installed is False  # watch B removido
        assert pipeline_b.state == _FakeState.NULL
        port.close()

    def test_late_b_events_ignored_at_audioport(self, qapp):
        bindings = FakeBindings()
        port, _ = self._a_accepted_and_pending_b(bindings)
        pipeline_b = bindings.pipelines[-1]
        generation_b = port._generation
        bindings.arm_exception_stage = "set_state_playing"
        bindings.arm_exception = RuntimeError("synthetic play failure")
        with pytest.raises(RuntimeError):
            port.play()
        # drenar la cola: el STOPPED de la convergencia del load(B) quedó
        # encolado ANTES de suscribir — no debe contar como evento tardío
        for _ in range(5):
            QCoreApplication.processEvents()
        accepted = []
        states = []
        positions = []
        durations = []
        eoms = []
        rejected = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.subscribe_position_changed(lambda ms: positions.append(ms))
        port.subscribe_duration_changed(lambda ms: durations.append(ms))
        port.subscribe_end_of_media(lambda: eoms.append(1))
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        # eventos tardíos de B con la generación CAPTURADA por su bus
        # (generation_b = la del load(B), ya invalidada por la cancelación)
        for msg_type in (
            _FakeMsgType.ASYNC_DONE,
            _FakeMsgType.EOS,
            _FakeMsgType.DURATION_CHANGED,
            _FakeMsgType.ERROR,
        ):
            m = FakeMessage(msg_type, pipeline_b, error_text="late b error")
            _deliver(port, m, generation_b)
        m2 = FakeMessage(
            _FakeMsgType.STATE_CHANGED, pipeline_b, new_state=_FakeState.PLAYING
        )
        _deliver(port, m2, generation_b)
        m3 = FakeMessage(
            _FakeMsgType.STATE_CHANGED, pipeline_b, new_state=_FakeState.PAUSED
        )
        _deliver(port, m3, generation_b)
        assert accepted == []  # sin media_accepted(B)
        assert states == []  # sin state updates
        assert positions == []
        assert durations == []
        assert eoms == []  # sin EOM
        assert rejected == []  # sin rejection de A
        assert port._current_path is None
        assert port._generation == generation_b + 1  # B stale por generación
        port.close()

    def test_position_poll_after_play_failure_projects_nothing(self, qapp):
        bindings = FakeBindings()
        port, _ = self._a_accepted_and_pending_b(bindings)
        bindings.arm_exception_stage = "set_state_playing"
        bindings.arm_exception = RuntimeError("synthetic play failure")
        with pytest.raises(RuntimeError):
            port.play()
        positions = []
        port.subscribe_position_changed(lambda ms: positions.append(ms))
        port._poll_position()  # seam del timer
        for _ in range(5):
            QCoreApplication.processEvents()
        assert positions == []  # B nunca se proyecta
        port.close()

    def test_cleanup_failure_retains_retryable_ownership(self, qapp):
        bindings = FakeBindings()
        port, _ = self._a_accepted_and_pending_b(bindings)
        pipeline_b = bindings.pipelines[-1]
        bindings.arm_exception_stage = "set_state_playing"
        bindings.arm_exception = RuntimeError("synthetic play failure")
        bindings.failed_states.add(_FakeState.NULL)  # cleanup NULL falla
        with pytest.raises(RuntimeError, match="play failure"):
            port.play()
        # la excepción ORIGINAL del play sigue siendo primaria
        assert port._generation == 3  # B stale SIEMPRE (aunque cleanup falle)
        assert port._pending_path is None
        assert port._current_path is None
        # ownership residual retenido como ancla retryable (NO media válida)
        assert port._pipeline is pipeline_b
        assert port._bus is not None
        # close() posterior limpia el ancla
        bindings.failed_states.clear()
        port.close()
        assert port._pipeline is None
        assert port._bus_source is None

    def test_accepted_source_play_failure_does_not_cancel(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline_a = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a)
        _deliver(port, msg, gen)
        port.play()
        m2, g2 = msg_state(port, pipeline_a, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        # play() extra sobre la fuente aceptada con raise → NO cancela A
        bindings.arm_exception_stage = "set_state_playing"
        bindings.arm_exception = RuntimeError("synthetic play failure")
        with pytest.raises(RuntimeError, match="play failure"):
            port.play()
        assert port._current_path == Path("/m/a.flac")  # A retenida
        assert port._pipeline is pipeline_a
        assert port._generation == 1  # sin invalidación
        assert port._pending_play is True  # intención de A preservada (CASO B)
        bindings.arm_exception_stage = None
        port.close()


class TestGStreamerPostPlayFailureConvergence:
    """M11.3C-R6.3 full-stack: load(B) OK + play(B) raise → las tres capas
    convergen; late B events no contaminan; play() recupera A a PLAYING."""

    def test_full_stack_convergence_and_recovery(self, qapp):
        from michi.application.playback_service import PlaybackService

        bindings = FakeBindings()
        port = GStreamerAudioPort(bindings)
        svc = PlaybackService(port)
        # A committed y PLAYING
        svc.load_and_play(Path("/m/a.flac"))
        pipeline_a = bindings.pipelines[-1]
        msg, gen = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a)
        _deliver(port, msg, gen)
        port.play()
        m2, g2 = msg_state(port, pipeline_a, _FakeState.PLAYING)
        _deliver(port, m2, g2)
        assert svc._accepted is True
        # B: load OK + play RAISE
        bindings.arm_exception_stage = "set_state_playing"
        bindings.arm_exception = RuntimeError("synthetic play failure")
        with pytest.raises(RuntimeError, match="play failure"):
            svc.load_and_play(Path("/m/b.flac"))
        pipeline_b = bindings.pipelines[-1]
        # PlaybackService convergido
        assert svc.state.file_path == Path("/m/a.flac")
        assert svc._accepted is False
        assert svc._intent is False
        assert svc.state.status == PlaybackStatus.STOPPED
        assert svc._pending_path is None
        # backend convergido: B sin media ni pending ni generación vigente
        assert port._pending_path is None
        assert port._current_path is None
        assert port._pipeline is None
        assert port._generation == 3  # load(A)=1, load(B)=2, cancel=3 → B stale
        # late B events (con la generación capturada por B) → todo ignorado
        for _ in range(5):
            QCoreApplication.processEvents()  # drenar el STOPPED de la
            # convergencia del load(B) (encolado antes de suscribir)
        accepted = []
        states = []
        positions = []
        durations = []
        eoms = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.subscribe_position_changed(lambda ms: positions.append(ms))
        port.subscribe_duration_changed(lambda ms: durations.append(ms))
        port.subscribe_end_of_media(lambda: eoms.append(1))
        gen_b = 2  # generación capturada por el bus de B (stale desde el cancel)
        msg3 = FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline_b)
        _deliver(port, msg3, gen_b)
        m4 = FakeMessage(
            _FakeMsgType.STATE_CHANGED, pipeline_b, new_state=_FakeState.PLAYING
        )
        _deliver(port, m4, gen_b)
        m5 = FakeMessage(_FakeMsgType.EOS, pipeline_b)
        _deliver(port, m5, gen_b)
        m6 = FakeMessage(_FakeMsgType.DURATION_CHANGED, pipeline_b)
        _deliver(port, m6, gen_b)
        assert svc.state.file_path == Path("/m/a.flac")
        assert svc.state.status == PlaybackStatus.STOPPED
        assert accepted == []
        assert states == []
        assert positions == []
        assert durations == []
        assert eoms == []
        # recovery: play() recarga A canónicamente → PLAYING
        bindings.arm_exception_stage = None
        svc.play()
        assert port._pending_path == Path("/m/a.flac")
        pipeline_a2 = bindings.pipelines[-1]
        m7, g7 = _msg(port, _FakeMsgType.ASYNC_DONE, pipeline_a2)
        _deliver(port, m7, g7)
        assert svc._accepted is True
        assert svc.state.file_path == Path("/m/a.flac")
        port.play()
        m8, g8 = msg_state(port, pipeline_a2, _FakeState.PLAYING)
        _deliver(port, m8, g8)
        assert svc.state.status == PlaybackStatus.PLAYING
        assert svc._intent is True
        port.close()


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

    def test_real_stop_play_replay(self, qapp, tmp_path):
        """M11.3C-R6.2 P1-01: gate REAL de autoridad de estado — los
        callbacks PRODUCTIVOS del AudioPort deben entregar

            PLAYING → STOPPED → PLAYING

        (nunca solo pipeline.get_state(); get_state queda como diagnóstico)."""
        try:
            import gi  # noqa: PLC0415

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # noqa: PLC0415

            Gst.init(None)
        except (ImportError, ValueError):
            pytest.skip("GI/GStreamer runtime no disponible")

        import time

        from michi.domain.playback import PlaybackStatus
        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerAudioPort,
            GStreamerBindings,
            _probe_missing_runtime_dependencies,
        )

        class StopPlayBindings(GStreamerBindings):
            def make_playbin3(self):
                pipeline = super().make_playbin3()
                if pipeline is None:
                    pytest.skip("playbin3 no disponible")
                fakesink = self._gst.ElementFactory.make(
                    "fakesink", "michi_test_audio_sink"
                )
                fakesink.set_property("sync", True)  # reloj real, sin HW
                pipeline.set_property("audio-sink", fakesink)
                return pipeline

        bindings = StopPlayBindings()
        bindings.ensure_loaded()
        missing = _probe_missing_runtime_dependencies(bindings)
        if missing is not None:
            pytest.skip(f"dependency absent: {missing} element factory not available")
        # WAV de ~5 segundos: margen para el replay antes del EOS natural
        import struct
        import wave

        wav = tmp_path / "stop_play.wav"
        with wave.open(str(wav), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"".join(struct.pack("<h", 0) for _ in range(44100 * 5)))

        port = GStreamerAudioPort(bindings)
        accepted = []
        states = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.subscribe_playback_state_changed(lambda s: states.append(s))

        def wait_for(predicate, what):
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                QCoreApplication.processEvents()
                if predicate():
                    return True
                time.sleep(0.02)
            return False

        port.load(wav)
        assert wait_for(lambda: bool(accepted), "accept"), "no accept"
        pipeline = port._pipeline
        assert pipeline is not None
        assert len(accepted) == 1
        # primer play → callback PRODUCTIVO PLAYING (no solo get_state)
        port.play()
        assert wait_for(lambda: PlaybackStatus.PLAYING in states, "callback PLAYING"), (
            f"no productive PLAYING callback (states={states}, "
            f"pipeline={pipeline.get_state(0).state})"
        )
        # stop → callback/estado canónico STOPPED, fuente retenida
        generation_before = port._generation
        port.stop()
        assert wait_for(lambda: PlaybackStatus.STOPPED in states, "callback STOPPED"), (
            f"no canonical STOPPED (states={states}, "
            f"pipeline={pipeline.get_state(0).state})"
        )
        assert port._current_path == wav  # fuente retenida
        assert port._pipeline is pipeline  # mismo pipeline
        assert port._generation == generation_before  # generación intacta
        # segundo play → callback PRODUCTIVO PLAYING otra vez (replay)
        port.play()
        assert wait_for(
            lambda: states.count(PlaybackStatus.PLAYING) >= 2, "callback rePLAYING"
        ), (
            f"no second productive PLAYING (states={states}, "
            f"pipeline={pipeline.get_state(0).state})"
        )
        assert len(accepted) == 1  # sin segundo media_accepted
        # la secuencia productiva completa es PLAYING → STOPPED → PLAYING
        playing = [i for i, s in enumerate(states) if s == PlaybackStatus.PLAYING]
        stopped = [i for i, s in enumerate(states) if s == PlaybackStatus.STOPPED]
        assert len(playing) == 2 and len(stopped) == 1
        assert playing[0] < stopped[0] < playing[1]
        port.close()
        assert port._pipeline is None
        assert port._pump is None

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
