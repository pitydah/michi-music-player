"""Tests for GStreamerEngine — fully mocked, no GStreamer dependency."""
import pytest
from unittest.mock import MagicMock, patch


# Build mock Gst module once for all tests
class _MockGst:
    class State:
        NULL = 1
        READY = 2
        PAUSED = 3
        PLAYING = 4
        VOID_PENDING = 5
    class StateChangeReturn:
        FAILURE = 0
        SUCCESS = 1
        ASYNC = 2
    class Format:
        TIME = 0
    class SeekFlags:
        FLUSH = 1
        KEY_UNIT = 2
    class MessageType:
        EOS = 1
        ERROR = 2
        WARNING = 4
        BUFFERING = 32
        TAG = 16
        STATE_CHANGED = 64
        DURATION_CHANGED = 262144
    class FlowReturn:
        OK = 0
    class MapFlags:
        READ = 1
    MSECOND = 1000000
    SECOND = 1000000000
    CLOCK_TIME_NONE = 0
    class Element:
        new = staticmethod(MagicMock(return_value=MagicMock()))
    class Bin:
        new = staticmethod(MagicMock(return_value=MagicMock()))
    class Pad:
        pass
    class Sample:
        pass
    class Memory:
        pass
    class BufferPool:
        pass
    class Allocator:
        pass
    class AllocationParams:
        pass
    class MapInfo:
        pass
    class BufferFlags:
        pass
    class PadLinkReturn:
        pass
    class PadLinkInfo:
        pass
    class PadTemplate:
        pass
    class CapsFeatures:
        pass
    class CapsIntersectMode:
        pass
    class DebugLevel:
        pass
    class DebugCategory:
        pass
    class DebugMessage:
        pass
    class Toc:
        pass
    class TocEntry:
        pass
    class Value:
        pass
    class Structure:
        pass
    class TagList:
        pass
    class Event:
        pass
    class Query:
        pass
    class Iterator:
        pass
    class Clock:
        pass
    class Bus:
        pass
    class Message:
        pass
    Buffer = MagicMock()
    Caps = MagicMock()
    Pipeline = MagicMock()
    ElementFactory = MagicMock()
    init = MagicMock()
    ClockTime = MagicMock()


MOCK_GST = _MockGst()


def _patch_player_module():
    """Patch audio.player module-level Gst/GLib with mocks."""

    glib_mock = MagicMock()
    glib_mock.filename_to_uri.side_effect = lambda p, _: "file://" + p

    gi_mock = MagicMock()
    gi_mock.require_version = MagicMock()
    gi_repo_mock = MagicMock()
    gi_repo_mock.Gst = MOCK_GST
    gi_repo_mock.GLib = glib_mock
    gi_repo_mock.GstPbutils = MagicMock()
    gi_mock.repository = gi_repo_mock

    fake_modules = {
        "gi": gi_mock,
        "gi.repository": gi_repo_mock,
        "gi.repository.Gst": MOCK_GST,
        "gi.repository.GLib": glib_mock,
        "gi.repository.GstPbutils": gi_repo_mock.GstPbutils,
    }
    sys_modules_patch = patch.dict("sys.modules", fake_modules, clear=False)

    patches = [
        sys_modules_patch,
        patch("audio.player.Gst", MOCK_GST),
        patch("audio.player.GLib", glib_mock),
        patch("audio.player.gi", gi_mock),
        patch("audio.player.QObject", MagicMock()),
        patch("audio.player.QTimer", MagicMock()),
    ]
    for p in patches:
        p.start()
    return patches


class TestGStreamerEngine:
    """Test every public method on GStreamerEngine with mocked GStreamer."""

    @pytest.fixture(autouse=True)
    def _patch_gst(self):
        """Patch audio.player Gst/GLib before each test."""
        patches = _patch_player_module()
        yield
        for p in patches:
            p.stop()

    # ── engine factory ──

    @pytest.fixture
    def engine(self):
        """Create GStreamerEngine instance with mocked dependencies."""
        import audio.player
        import importlib
        importlib.reload(audio.player)
        from audio.player import GStreamerEngine

        result = GStreamerEngine()
        result.position_changed = MagicMock()
        result.duration_changed = MagicMock()
        result.state_changed = MagicMock()
        result.finished = MagicMock()
        result.error_occurred = MagicMock()
        result.spectrum_data = MagicMock()
        result.queue_changed = MagicMock()
        result.audio_route_changed = MagicMock()
        result.eq_bitperfect_warning = MagicMock()
        return result

    # ── Initialization ──

    def test_init_defaults(self, engine):
        assert engine._state.value == 0
        assert engine._duration == 0.0
        assert engine._current is None
        assert engine._queue == []
        assert engine._queue_index == -1
        assert engine._shuffle is False
        assert engine._repeat == "none"
        assert engine._volume == 0.70

    def test_init_sets_default_eq_state(self, engine):
        eq = engine._eq
        assert eq.mode == "graphic"
        assert eq.bands_31 == [0.0] * 31
        assert eq.bands_parametric == []
        assert eq.preamp_db == 0.0

    def test_player_engine_alias(self, engine):
        import audio.player
        assert audio.player.PlayerEngine is audio.player.GStreamerEngine

    # ── Properties ──

    def test_state_property(self, engine):
        from audio.player import PlaybackState
        engine._state = PlaybackState.PLAYING
        assert engine.state == PlaybackState.PLAYING

    def test_current_property(self, engine):
        engine._current = "/tmp/song.mp3"
        assert engine.current == "/tmp/song.mp3"

    def test_current_returns_none_by_default(self, engine):
        assert engine.current is None

    # ── play() ──

    def _mock_play_internals(self):
        """Patch all imports that play() uses internally.

        Since play() does `from X import Y` inside the function body,
        we use patch.dict('sys.modules') to inject fake modules so
        those imports return our mocks instead of loading real modules.
        """

        pf_instance = MagicMock()
        pf_instance.build_for_uri.return_value = None  # caller sets this
        pf_module = MagicMock()
        pf_module.PipelineFactory = MagicMock(return_value=pf_instance)

        probe_mock = MagicMock(return_value=MagicMock(
            codec="flac", sample_rate=44100, bit_depth=16, channels=2, is_dsd=False))

        get_profile_mock = MagicMock(return_value=MagicMock(
            key="standard", allows_replaygain=False, allows_transmit=True,
            bitperfect=False))

        dev = MagicMock(display_name="dev", device_string="hw:0", backend="alsa")
        get_device_mock = MagicMock(return_value=dev)

        dm_instance = MagicMock()
        dm_instance.select_output_route.return_value = MagicMock()
        dm_mock = MagicMock(return_value=dm_instance)

        fake_modules = {
            "audio.pipeline_factory": pf_module,
            "audio.format_probe": MagicMock(probe_format=probe_mock),
            "audio.output_profiles": MagicMock(get_profile=get_profile_mock),
            "audio.output_device_manager": MagicMock(get_device=get_device_mock),
            "audio.dac_manager": MagicMock(DacManager=dm_mock),
            "audio.audio_diagnostics": MagicMock(AudioRouteDiagnostics=MagicMock()),
            "audio.dsp_state": MagicMock(DspState=MagicMock()),
        }
        return patch.dict("sys.modules", fake_modules, clear=False), pf_instance

    def test_play_sets_state_playing(self, engine):
        module_patch, pf_instance = self._mock_play_internals()
        pipeline = MagicMock()
        pipeline.set_state.return_value = MOCK_GST.StateChangeReturn.SUCCESS
        pipeline.get_bus.return_value = MagicMock()
        pf_instance.build_for_uri.return_value = pipeline
        engine._setup_bus = MagicMock()
        engine._setup_timer = MagicMock()
        engine.set_library_db = MagicMock()

        with module_patch:
            engine.play("/tmp/test.flac")

        pipeline.set_state.assert_called_with(MOCK_GST.State.PLAYING)
        from audio.player import PlaybackState
        signals = [c[0][0] for c in engine.state_changed.emit.call_args_list]
        assert any(s == PlaybackState.PLAYING for s in signals)

    def test_play_pipeline_failure(self, engine):
        module_patch, pf_instance = self._mock_play_internals()
        pf_instance.build_for_uri.return_value = None
        engine._setup_bus = MagicMock()
        engine._setup_timer = MagicMock()
        engine.set_library_db = MagicMock()

        with module_patch:
            engine.play("/tmp/test.flac")

        engine.error_occurred.emit.assert_called_with("Failed to create pipeline")

    def test_play_set_state_failure(self, engine):
        module_patch, pf_instance = self._mock_play_internals()
        pipeline = MagicMock()
        pipeline.set_state.return_value = MOCK_GST.StateChangeReturn.FAILURE
        pf_instance.build_for_uri.return_value = pipeline
        engine._setup_bus = MagicMock()
        engine._setup_timer = MagicMock()
        engine.set_library_db = MagicMock()

        with module_patch:
            engine.play("/tmp/test.flac")

        engine.error_occurred.emit.assert_called_with("Failed to start playback")

    # ── pause / resume / toggle / stop ──

    def test_pause(self, engine):
        pipeline = MagicMock()
        pipeline.set_state.return_value = MOCK_GST.StateChangeReturn.SUCCESS
        engine._pipeline = pipeline
        from audio.player import PlaybackState
        engine._state = PlaybackState.PLAYING

        engine.pause()

        pipeline.set_state.assert_called_with(MOCK_GST.State.PAUSED)
        engine.state_changed.emit.assert_called()

    def test_pause_when_not_playing_does_nothing(self, engine):
        pipeline = MagicMock()
        engine._pipeline = pipeline
        from audio.player import PlaybackState
        engine._state = PlaybackState.STOPPED
        engine.state_changed = MagicMock()

        engine.pause()

        pipeline.set_state.assert_not_called()
        engine.state_changed.emit.assert_not_called()

    def test_resume(self, engine):
        pipeline = MagicMock()
        pipeline.set_state.return_value = MOCK_GST.StateChangeReturn.SUCCESS
        engine._pipeline = pipeline
        from audio.player import PlaybackState
        engine._state = PlaybackState.PAUSED

        engine.resume()

        pipeline.set_state.assert_called_with(MOCK_GST.State.PLAYING)
        engine.state_changed.emit.assert_called()

    def test_resume_when_not_paused_does_nothing(self, engine):
        pipeline = MagicMock()
        engine._pipeline = pipeline
        from audio.player import PlaybackState
        engine._state = PlaybackState.STOPPED

        engine.resume()

        pipeline.set_state.assert_not_called()

    def test_toggle_playing_pauses(self, engine):
        from audio.player import PlaybackState
        engine._state = PlaybackState.PLAYING
        engine.pause = MagicMock()
        engine.resume = MagicMock()

        engine.toggle()

        engine.pause.assert_called_once()
        engine.resume.assert_not_called()

    def test_toggle_paused_resumes(self, engine):
        from audio.player import PlaybackState
        engine._state = PlaybackState.PAUSED
        engine.pause = MagicMock()
        engine.resume = MagicMock()

        engine.toggle()

        engine.resume.assert_called_once()
        engine.pause.assert_not_called()

    def test_toggle_stopped_plays_current(self, engine):
        from audio.player import PlaybackState
        engine._state = PlaybackState.STOPPED
        engine._current = "/tmp/song.mp3"
        engine.play = MagicMock()

        engine.toggle()

        engine.play.assert_called_once_with("/tmp/song.mp3")

    def test_stop(self, engine):
        pipeline = MagicMock()
        bus = MagicMock()
        pipeline.get_bus.return_value = bus
        pipeline.get_state.return_value = (MOCK_GST.StateChangeReturn.SUCCESS,
                                            MOCK_GST.State.NULL)
        engine._pipeline = pipeline
        engine._bus_id = 123
        engine._timer = MagicMock()
        from audio.player import PlaybackState

        engine.stop()

        pipeline.set_state.assert_called_with(MOCK_GST.State.NULL)
        bus.disconnect.assert_called_with(123)
        bus.remove_signal_watch.assert_called()
        assert engine._pipeline is None
        signals = [c[0][0] for c in engine.state_changed.emit.call_args_list]
        assert any(s == PlaybackState.STOPPED for s in signals)

    # ── seek ──

    def test_seek(self, engine):
        pipeline = MagicMock()
        engine._pipeline = pipeline

        engine.seek(42.5)

        pipeline.seek_simple.assert_called_once()
        args = pipeline.seek_simple.call_args[0]
        assert args[0] == MOCK_GST.Format.TIME
        assert args[2] == int(42.5 * 1e9)

    def test_seek_no_pipeline(self, engine):
        engine._pipeline = None
        engine.seek(10)

    # ── set_volume ──

    def test_set_volume(self, engine):
        pipeline = MagicMock()
        vol_elem = MagicMock()
        pipeline.get_by_name.return_value = vol_elem
        engine._pipeline = pipeline

        engine.set_volume(75)

        assert engine._volume == 0.75
        vol_elem.set_property.assert_called_with("volume", 0.75)

    def test_set_volume_clamps(self, engine):
        engine.set_volume(200)
        assert engine._volume == 1.0
        engine.set_volume(-50)
        assert engine._volume == 0.0

    def test_set_volume_no_pipeline(self, engine):
        engine._pipeline = None
        engine.set_volume(50)
        assert engine._volume == 0.5

    # ── Queue operations ──

    def test_enqueue_play_now(self, engine):
        engine.play = MagicMock()
        engine._db = None

        engine.enqueue(["/tmp/a.flac", "/tmp/b.flac"], play_now=True)

        assert engine._queue == ["/tmp/a.flac", "/tmp/b.flac"]
        assert engine._queue_index == 0
        engine.play.assert_called_once_with("/tmp/a.flac")
        engine.queue_changed.emit.assert_called_with(engine._queue)

    def test_enqueue_no_play_now(self, engine):
        engine.play = MagicMock()
        engine._queue = ["existing.flac"]
        engine._queue_index = 0
        engine._db = None

        engine.enqueue(["/tmp/c.flac"], play_now=False)

        assert engine._queue == ["existing.flac", "/tmp/c.flac"]
        engine.play.assert_not_called()

    def test_enqueue_no_play_now_empty_queue_plays(self, engine):
        engine.play = MagicMock()
        engine._queue = []
        engine._queue_index = -1
        engine._db = None

        engine.enqueue(["/tmp/a.flac"], play_now=False)

        assert engine._queue == ["/tmp/a.flac"]
        assert engine._queue_index == 0
        engine.play.assert_called_once_with("/tmp/a.flac")

    def test_clear_queue(self, engine):
        engine._queue = ["a.flac", "b.flac"]
        engine._queue_index = 1
        engine._db = None

        engine.clear_queue()

        assert engine._queue == []
        assert engine._queue_index == -1
        engine.queue_changed.emit.assert_called_with([])

    def test_clear_queue_calls_db(self, engine):
        engine._db = MagicMock()
        engine.clear_queue()
        engine._db.clear_queue_state.assert_called_once()

    def test_get_queue(self, engine):
        engine._queue = ["/tmp/a.flac", "/tmp/b.flac"]
        engine._queue_index = 0

        items = engine.get_queue()

        assert len(items) == 2
        assert items[0]["filepath"] == "/tmp/a.flac"
        assert items[0]["title"] == "a.flac"
        assert items[0]["is_current"] is True
        assert items[1]["is_current"] is False

    def test_get_queue_index(self, engine):
        assert engine.get_queue_index() == -1
        engine._queue_index = 2
        assert engine.get_queue_index() == 2

    def test_reorder_queue_preserves_current(self, engine):
        engine._queue = ["a.flac", "b.flac", "c.flac"]
        engine._queue_index = 1
        engine._db = None

        engine.reorder_queue(["c.flac", "b.flac", "a.flac"])

        assert engine._queue == ["c.flac", "b.flac", "a.flac"]
        assert engine._queue_index == 1

    def test_reorder_queue_current_not_found(self, engine):
        engine._queue = ["a.flac", "b.flac"]
        engine._queue_index = 0
        engine._db = None

        engine.reorder_queue(["x.flac", "y.flac"])

        assert engine._queue_index == 0

    # ── play_next / play_prev ──

    def test_play_next_simple(self, engine):
        engine._queue = ["a.flac", "b.flac", "c.flac"]
        engine._queue_index = 0
        engine.play = MagicMock()
        engine._db = None

        result = engine.play_next()

        assert result is True
        assert engine._queue_index == 1
        engine.play.assert_called_once_with("b.flac")

    def test_play_next_at_end(self, engine):
        engine._queue = ["a.flac", "b.flac"]
        engine._queue_index = 1
        engine.play = MagicMock()

        result = engine.play_next()

        assert result is False

    def test_play_next_repeat_one(self, engine):
        engine._queue = ["a.flac"]
        engine._queue_index = 0
        engine._repeat = "one"
        engine.play = MagicMock()
        engine._db = None

        result = engine.play_next()

        assert result is True
        engine.play.assert_called_once_with("a.flac")

    def test_play_next_repeat_all(self, engine):
        engine._queue = ["a.flac", "b.flac"]
        engine._queue_index = 1
        engine._repeat = "all"
        engine.play = MagicMock()
        engine._db = None

        result = engine.play_next()

        assert result is True
        assert engine._queue_index == 0
        engine.play.assert_called_once_with("a.flac")

    def test_play_prev(self, engine):
        engine._queue = ["a.flac", "b.flac", "c.flac"]
        engine._queue_index = 2
        engine.play = MagicMock()
        engine._db = None

        result = engine.play_prev()

        assert result is True
        assert engine._queue_index == 1
        engine.play.assert_called_once_with("b.flac")

    def test_play_prev_at_start(self, engine):
        engine._queue = ["a.flac", "b.flac"]
        engine._queue_index = 0
        engine.play = MagicMock()

        result = engine.play_prev()

        assert result is False
        engine.play.assert_not_called()

    # ── shuffle / repeat ──

    def test_toggle_shuffle_enables(self, engine):
        engine._queue = ["a.flac", "b.flac", "c.flac"]
        engine._queue_index = 0
        engine._db = None

        result = engine.toggle_shuffle()

        assert result is True
        assert engine._shuffle is True
        assert engine._queue[0] == "a.flac"

    def test_toggle_shuffle_disables(self, engine):
        engine._db = None
        engine._shuffle = True
        result = engine.toggle_shuffle()
        assert result is False
        assert engine._shuffle is False

    def test_toggle_repeat_cycles(self, engine):
        engine._repeat = "none"
        assert engine.toggle_repeat() == "all"
        assert engine.toggle_repeat() == "one"
        assert engine.toggle_repeat() == "none"
        assert engine.toggle_repeat() == "all"

    # ── play_url ──

    def test_play_url_stops_and_plays(self, engine):
        engine.stop = MagicMock()
        engine.play = MagicMock()

        engine.play_url("http://stream.example.com/radio")

        engine.stop.assert_called_once()
        engine.play.assert_called_once_with("http://stream.example.com/radio")

    # ── EQ state ──

    def test_get_eq_state_defaults(self, engine):
        state = engine.get_eq_state()
        assert state["mode"] == "graphic"
        assert state["bands_31"] == [0.0] * 31
        assert state["bands_parametric"] == []
        assert state["preamp_db"] == 0.0

    def test_set_eq_graphic(self, engine):
        bands = [float(i) for i in range(31)]
        engine.set_eq_graphic(bands)
        assert engine._eq.mode == "graphic"
        assert engine._eq.bands_31 == bands

    def test_set_eq_parametric(self, engine):
        bands = [{"type": "peaking", "frequency": 1000, "q": 0.7, "gain": 3.0}]
        engine.set_eq_parametric(bands)
        assert engine._eq.mode == "parametric"
        assert engine._eq.bands_parametric == bands

    def test_set_eq_bypass(self, engine):
        engine._eq.mode = "graphic"
        engine.set_eq_bypass(True)
        assert engine._eq.mode == "bypass"
        engine.set_eq_bypass(False)
        assert engine._eq.mode == "graphic"

    def test_set_eq_bypass_parametric(self, engine):
        engine._eq.mode = "bypass"
        engine._eq.bands_parametric = [{"type": "peaking", "frequency": 1000}]
        engine.set_eq_bypass(False)
        assert engine._eq.mode == "parametric"

    def test_set_eq_preamp(self, engine):
        engine.set_eq_preamp(-3.5)
        assert engine._eq.preamp_db == -3.5

    def test_eq_bitperfect_warning(self, engine):
        with patch("audio.output_profiles.get_profile") as mock_get:
            mock_profile = MagicMock()
            mock_profile.bitperfect = True
            mock_get.return_value = mock_profile
            engine._eq.mode = "bypass"
            engine._restart_if_playing = MagicMock()

            engine.set_eq_graphic([0.0] * 31)

            engine.eq_bitperfect_warning.emit.assert_called_once()

    # ── Bus message handling ──

    def test_bus_message_eos(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.EOS
        engine._on_media_finished_eos = MagicMock()

        engine._on_bus_message(bus, message)

        engine._on_media_finished_eos.assert_called_once()

    def test_bus_message_error(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.ERROR
        message.parse_error.return_value = ("some error", "debug info")
        pipeline = MagicMock()
        pipeline.get_state.return_value = (MOCK_GST.StateChangeReturn.SUCCESS,
                                            MOCK_GST.State.NULL)
        engine._pipeline = pipeline
        engine._bus_id = 123
        engine._timer = MagicMock()

        engine._on_bus_message(bus, message)

        engine.error_occurred.emit.assert_called()
        pipeline.set_state.assert_called_with(MOCK_GST.State.NULL)

    def test_bus_message_warning_does_not_emit_error(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.WARNING
        message.parse_warning.return_value = ("warn", "detail")

        engine._on_bus_message(bus, message)

        engine.error_occurred.emit.assert_not_called()

    def test_bus_message_buffering(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.BUFFERING
        message.parse_buffering.return_value = 50
        pipeline = MagicMock()
        pipeline.set_state.return_value = MOCK_GST.StateChangeReturn.SUCCESS
        engine._pipeline = pipeline
        from audio.player import PlaybackState
        engine._state = PlaybackState.PLAYING

        engine._on_bus_message(bus, message)

        pipeline.set_state.assert_called_with(MOCK_GST.State.PAUSED)

    def test_bus_message_buffering_complete(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.BUFFERING
        message.parse_buffering.return_value = 100
        pipeline = MagicMock()
        pipeline.set_state.return_value = MOCK_GST.StateChangeReturn.SUCCESS
        engine._pipeline = pipeline
        from audio.player import PlaybackState
        engine._state = PlaybackState.PLAYING

        engine._on_bus_message(bus, message)

        pipeline.set_state.assert_called_with(MOCK_GST.State.PLAYING)

    def test_bus_message_duration_changed(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.DURATION_CHANGED
        pipeline = MagicMock()
        pipeline.query_duration.return_value = (True, 123456789000)
        engine._pipeline = pipeline

        engine._on_bus_message(bus, message)

        assert engine._duration == 123.456789
        engine.duration_changed.emit.assert_called_with(123.456789)

    def test_bus_message_state_changed(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.STATE_CHANGED
        message.src = "not_pipeline"
        engine._pipeline = MagicMock()
        engine._on_bus_message(bus, message)

    # ── _to_uri ──

    def test_to_uri_preserves_http(self, engine):
        assert engine._to_uri("http://example.com/stream") == "http://example.com/stream"

    def test_to_uri_preserves_https(self, engine):
        assert engine._to_uri("https://example.com/stream") == "https://example.com/stream"

    def test_to_uri_preserves_icy(self, engine):
        assert engine._to_uri("icy://example.com/stream") == "icy://example.com/stream"

    def test_to_uri_preserves_file_protocol(self, engine):
        assert engine._to_uri("file:///home/test.flac") == "file:///home/test.flac"

    def test_to_uri_converts_filepath(self, engine):
        result = engine._to_uri("/home/test.flac")
        assert result == "file:///home/test.flac"

    # ── _on_media_finished / _on_media_finished_eos ──

    def test_on_media_finished_plays_next(self, engine):
        engine._queue = ["a.flac", "b.flac"]
        engine._queue_index = 0
        engine.play = MagicMock()
        engine._db = None

        engine._on_media_finished()

        engine.play.assert_called_once_with("b.flac")

    def test_on_media_finished_at_end(self, engine):
        pipeline = MagicMock()
        pipeline.get_state.return_value = (MOCK_GST.StateChangeReturn.SUCCESS,
                                            MOCK_GST.State.NULL)
        engine._pipeline = pipeline
        engine._queue = ["a.flac"]
        engine._queue_index = 0
        engine.play = MagicMock()
        engine._db = None

        engine._on_media_finished()

        engine.finished.emit.assert_called_once()

    def test_on_media_finished_eos_gapless(self, engine):
        engine._gapless_active = True
        engine._queue = ["a.flac", "b.flac"]
        engine._queue_index = 0

        engine._on_media_finished_eos()

        assert engine._gapless_active is False
        assert engine._queue_index == 1

    def test_on_media_finished_eos_no_gapless(self, engine):
        engine._gapless_active = False
        engine._on_media_finished = MagicMock()

        engine._on_media_finished_eos()

        engine._on_media_finished.assert_called_once()

    # ── Spectrum ──

    def test_set_spectrum_enabled(self, engine):
        engine.set_spectrum_enabled(True)
        assert engine._spectrum_enabled is True
        engine.set_spectrum_enabled(False)
        assert engine._spectrum_enabled is False

    # ── set_library_db ──

    def test_set_library_db_loads_queue(self, engine):
        db = MagicMock()
        db.load_queue.return_value = (["a.flac", "b.flac"], 1)

        engine.set_library_db(db)

        assert engine._queue == ["a.flac", "b.flac"]
        assert engine._queue_index == 1

    # ── set_output_device_id / get_output_device_id ──

    def test_set_output_device_id(self, engine):
        with patch("audio.output_device_manager.get_device") as mock_get_device:
            dev = MagicMock()
            dev.device_string = "hw:2,0"
            mock_get_device.return_value = dev
            engine._restart_if_playing = MagicMock()

            engine.set_output_device_id("some_id")

            assert engine._dac.device == "hw:2,0"
            engine._restart_if_playing.assert_called_once()

    def test_get_output_device_id(self, engine):
        engine._dac.device = "hw:1,0"
        assert engine.get_output_device_id() == "hw:1,0"

    # ── set_audio_profile / set_dsd_mode / gapless / replaygain ──

    def test_set_audio_profile(self, engine):
        engine._restart_if_playing = MagicMock()
        engine.set_audio_profile("hifi")
        assert engine._audio_profile == "hifi"

    def test_set_dsd_mode(self, engine):
        engine.set_dsd_mode("dop")
        assert engine._dac.dsd_mode == "dop"

    def test_set_gapless_enabled(self, engine):
        engine.set_gapless_enabled(False)
        assert engine._gapless_enabled is False
        engine.set_gapless_enabled(True)
        assert engine._gapless_enabled is True

    def test_set_replaygain_mode(self, engine):
        engine.set_replaygain_mode("track")
        assert engine._replaygain is True
        engine.set_replaygain_mode("off")
        assert engine._replaygain is False

    # ── get_position_ns ──

    def test_get_position_ns(self, engine):
        pipeline = MagicMock()
        pipeline.query_position.return_value = (True, 5000000000)
        engine._pipeline = pipeline
        assert engine.get_position_ns() == 5000000000

    def test_get_position_ns_no_pipeline(self, engine):
        engine._pipeline = None
        assert engine.get_position_ns() == 0

    # ── transmit ──

    def test_set_transmit_device(self, engine):
        device = MagicMock()
        engine._restart_if_playing = MagicMock()
        engine.set_transmit_device(device)
        assert engine._transmit_device is device

    def test_get_transmit_device(self, engine):
        assert engine.get_transmit_device() is None
        d = MagicMock()
        engine._transmit_device = d
        assert engine.get_transmit_device() is d

    # ── set_queue ──

    def test_set_queue(self, engine):
        engine.play = MagicMock()
        engine._db = None

        engine.set_queue(["a.flac", "b.flac", "c.flac"], start_index=1)

        assert engine._queue == ["a.flac", "b.flac", "c.flac"]
        assert engine._queue_index == 1
