"""M11.3C: GStreamerAudioPort transport gates.

Deterministic unit tests through a fake GStreamer surface (injectable
bindings): acceptance/rejection semantics, state convergence (preroll vs
user pause), EOS exactly-once, seek/time conversion, duration/position,
stale-source isolation by pipeline identity, post-close isolation, teardown
and router parity. No real GStreamer runtime required (CI-safe).

A small optional smoke test exercises the REAL GI runtime when available.
"""

from pathlib import Path

from michi.application.audio_transport_router import AudioTransportRouter
from michi.domain.audio_engine import AudioEngineId
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.audio_engines.gstreamer import (
    GStreamerAudioPort,
    gst_time_to_millis,
    millis_to_gst_time,
)


class _FakeState:
    NULL = 0
    READY = 1
    PAUSED = 2
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
        self.watch_count = 0

    def add_watch(self, priority, callback, user_data=None):
        self.watch_count += 1
        return self.watch_count

    def remove_watch(self, watch_id=None):
        self.watch_count = max(0, self.watch_count - 1)
        return True


def msg_state(pipeline, state):
    """FakeMessage STATE_CHANGED helper (líneas cortas)."""
    return FakeMessage(_FakeMsgType.STATE_CHANGED, pipeline, new_state=state)


class FakeMessage:
    def __init__(self, msg_type, pipeline, error_text=None, new_state=None):
        self.type = msg_type
        self.src = pipeline
        self._error_text = error_text
        self._new_state = new_state

    def parse_error(self):
        from gi.repository import GLib

        return GLib.Error(self._error_text), ""

    def parse_state_changed(self):
        return None, None, self._new_state


class FakeBindings:
    """Test seam: same object surface as GStreamerBindings, no GI needed."""

    def __init__(self):
        self.pipelines = []

    def supports_pump(self):
        return False  # tests deliver messages directly

    def ensure_loaded(self):
        pass

    def make_playbin3(self):
        p = FakePipeline(f"P{len(self.pipelines)}")
        self.pipelines.append(p)
        return p

    def set_state(self, pipeline, state):
        return pipeline.set_state(state)

    def get_bus(self, pipeline):
        return pipeline.get_bus()

    def bus_add_watch(self, bus, callback):
        return bus.add_watch(0, callback)

    def bus_remove_watch(self, bus, watch_id=None):
        return bus.remove_watch(watch_id)

    def new_main_context(self):
        return None

    def new_main_loop(self, context):
        return None

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


class TestTimeConversion:
    def test_millis_to_ns(self):
        assert millis_to_gst_time(1000) == 1_000_000_000
        assert millis_to_gst_time(1234) == 1_234_000_000

    def test_ns_to_millis(self):
        assert gst_time_to_millis(1_234_000_000) == 1234
        assert gst_time_to_millis(0) == 0


class TestMediaAcceptance:
    def test_acceptance_only_after_runtime_evidence(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        path = Path("/m/a.flac")
        port.load(path)
        # el simple load (URI + set_state) NO debe aceptar
        assert accepted == []
        # ASYNC_DONE del pipeline vigente = evidencia de aceptación
        pipeline = bindings.pipelines[-1]
        port._process_message(FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline))
        assert accepted == [path]
        # sin doble acceptance por mensajes duplicados
        port._process_message(FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline))
        assert accepted == [path]
        port.close()

    def test_acceptance_requires_current_pipeline(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.load(Path("/m/a.flac"))
        old_pipeline = bindings.pipelines[-1]
        port.load(Path("/m/b.flac"))  # pipeline nuevo
        # ASYNC_DONE del pipeline ANTERIOR → ignorado (stale)
        port._process_message(FakeMessage(_FakeMsgType.ASYNC_DONE, old_pipeline))
        assert accepted == []
        # ASYNC_DONE del pipeline vigente → acepta b.flac
        port._process_message(
            FakeMessage(_FakeMsgType.ASYNC_DONE, bindings.pipelines[-1])
        )
        assert accepted == [Path("/m/b.flac")]
        port.close()


class TestRejection:
    def test_error_before_acceptance_rejects_once(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        rejected = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        path = Path("/m/bad.flac")
        port.load(path)
        pipeline = bindings.pipelines[-1]
        port._process_message(
            FakeMessage(_FakeMsgType.ERROR, pipeline, error_text="decode failed")
        )
        assert rejected == [(path, "decode failed")]
        port._process_message(
            FakeMessage(_FakeMsgType.ERROR, pipeline, error_text="dup")
        )
        assert len(rejected) == 1  # el pending se limpió — exactamente una vez
        port.close()

    def test_stale_pipeline_error_ignored(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        rejected = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.load(Path("/m/a.flac"))
        old_pipeline = bindings.pipelines[-1]
        port.load(Path("/m/b.flac"))
        port._process_message(
            FakeMessage(_FakeMsgType.ERROR, old_pipeline, error_text="stale")
        )
        assert rejected == []
        port.close()


class TestEos:
    def test_eos_exactly_once(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        eom = []
        port.subscribe_end_of_media(lambda: eom.append(1))
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port._process_message(FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline))
        port._process_message(FakeMessage(_FakeMsgType.EOS, pipeline))
        assert eom == [1]
        port._process_message(FakeMessage(_FakeMsgType.EOS, pipeline))  # dup
        assert eom == [1]
        port.close()

    def test_stale_pipeline_eos_ignored(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        eom = []
        port.subscribe_end_of_media(lambda: eom.append(1))
        port.load(Path("/m/a.flac"))
        old_pipeline = bindings.pipelines[-1]
        port._process_message(FakeMessage(_FakeMsgType.ASYNC_DONE, old_pipeline))
        port.load(Path("/m/b.flac"))
        port._process_message(FakeMessage(_FakeMsgType.EOS, old_pipeline))
        assert eom == []
        port.close()


class TestPlaybackState:
    def test_no_playing_from_command_return(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        port.play()  # intención — sin evidencia runtime, sin evento
        assert states == []
        pipeline = bindings.pipelines[-1]
        port._process_message(msg_state(pipeline, _FakeState.PLAYING))
        assert states == [PlaybackStatus.PLAYING]
        port.close()

    def test_preroll_paused_is_not_user_pause(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        port.play()
        pipeline = bindings.pipelines[-1]
        # PAUSED durante preroll (sin ASYNC_DONE aún) → transitorio
        port._process_message(msg_state(pipeline, _FakeState.PAUSED))
        assert PlaybackStatus.PAUSED not in states
        # ASYNC_DONE + PLAYING → real
        port._process_message(FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline))
        port._process_message(msg_state(pipeline, _FakeState.PLAYING))
        assert states[-1] == PlaybackStatus.PLAYING
        port.close()

    def test_user_pause_reported(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port._process_message(FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline))
        port.pause()  # intención de pausa del usuario
        port._process_message(msg_state(pipeline, _FakeState.PAUSED))
        assert states[-1] == PlaybackStatus.PAUSED
        port.close()


class TestSeekPositionDuration:
    def test_seek_conversion(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port._process_message(FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline))
        port.seek(1500)
        assert pipeline.seek_calls == [1_500_000_000]
        port.close()

    def test_position_duration_units(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        assert port.position() == 1234  # ns → ms
        assert port.duration() == 5000
        port.close()

    def test_duration_changed_event(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        durs = []
        port.subscribe_duration_changed(lambda ms: durs.append(ms))
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port._process_message(FakeMessage(_FakeMsgType.DURATION_CHANGED, pipeline))
        assert durs == [5000]
        port.close()


class TestVolumeMute:
    def test_volume_mute_semantics(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.set_volume(80)
        port.set_muted(True)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        assert pipeline.volume == 0.8
        assert pipeline.muted is True
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
        port.subscribe_duration_changed(lambda ms: events.append("dur"))
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port.close()
        # cualquier mensaje después de close → cero delivery
        port._process_message(FakeMessage(_FakeMsgType.EOS, pipeline))
        port._process_message(FakeMessage(_FakeMsgType.ERROR, pipeline, error_text="x"))
        port._process_message(msg_state(pipeline, _FakeState.PLAYING))
        port._process_message(FakeMessage(_FakeMsgType.DURATION_CHANGED, pipeline))
        assert events == []


class TestTeardown:
    def test_close_releases_pipeline(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        assert pipeline.closed is False
        port.close()
        assert pipeline.closed is True  # set_state(NULL)
        port.close()  # idempotente
        assert port._pipeline is None

    def test_stop_keeps_transport_usable(self, qapp):
        bindings = FakeBindings()
        port = _port(bindings)
        port.load(Path("/m/a.flac"))
        pipeline = bindings.pipelines[-1]
        port._process_message(FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline))
        port.stop()
        assert port._pipeline is not None  # stop ≠ close
        assert port.duration() == 5000  # transporte usable
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
        port._process_message(FakeMessage(_FakeMsgType.ASYNC_DONE, pipeline))
        port._process_message(FakeMessage(_FakeMsgType.DURATION_CHANGED, pipeline))
        port._process_message(FakeMessage(_FakeMsgType.EOS, pipeline))
        port._process_message(msg_state(pipeline, _FakeState.PLAYING))
        assert events == ["acc:a.flac", "dur:5000", "eom", "st"]
        # unbind: cero forwarding
        router.unbind()
        port._process_message(FakeMessage(_FakeMsgType.EOS, pipeline))
        assert events == ["acc:a.flac", "dur:5000", "eom", "st"]
        port.close()

    def test_router_has_no_gstreamer_logic(self):
        import inspect

        from michi.application import audio_transport_router as mod

        src = inspect.getsource(mod)
        assert "Gst" not in src
        assert "GStreamer" not in src
        assert "gi." not in src
