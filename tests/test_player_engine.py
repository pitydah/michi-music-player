"""Tests for GStreamerEngine — transport delegation pattern, no GStreamer dep."""
import sys
import pytest
from unittest.mock import MagicMock, patch


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


@pytest.fixture(scope="module")
def _fake_gst_module():
    """Inject fake gi/Gst into sys.modules and pre-import dependents.

    Only touches the 5 gi-related keys; saves and restores them at teardown
    instead of wiping the entire sys.modules dict. Pre-imports
    audio.backends.pipeline_transport and audio.player so that all
    module-level gi/Gst imports resolve to fakes.
    """
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

    saved = {k: sys.modules.get(k) for k in fake_modules}
    sys.modules.update(fake_modules)

    import audio.backends.pipeline_transport  # noqa: F811
    import audio.player  # noqa: F811, F401

    yield

    for mod_key in ["audio.backends.pipeline_transport", "audio.player"]:
        sys.modules.pop(mod_key, None)
    for k, v in saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v


class FakeTransport:
    """Fake transport that records calls for assertion.

    Implements every method GStreamerEngine calls on self._transport
    per the origin/main contract.
    """

    def __init__(self):
        self.set_callbacks = MagicMock()
        self.get_pipeline = MagicMock(return_value=None)
        self.adopt_pipeline = MagicMock()
        self.pause = MagicMock()
        self.resume = MagicMock()
        self.stop = MagicMock()
        self.seek = MagicMock()
        self.set_volume = MagicMock()
        self.get_position = MagicMock(return_value=0.0)
        self.get_duration = MagicMock(return_value=0.0)
        self.setup_bus = MagicMock()
        self.shutdown = MagicMock()
        self.enqueue = MagicMock()
        self.enqueue_next = MagicMock()
        self.play_next = MagicMock(return_value=False)
        self.play_prev = MagicMock(return_value=False)


class TestGStreamerEngine:
    """Test GStreamerEngine — every assertion verifies transport delegation."""

    @pytest.fixture(autouse=True)
    def _patch_transport(self, _fake_gst_module):
        """Replace GStreamerPipelineTransport with FakeTransport.

        Patches audio.backends.pipeline_transport.GStreamerPipelineTransport
        so that GStreamerEngine.__init__ receives a FakeTransport.
        The __init__ import is ``from audio.backends.pipeline_transport
        import GStreamerPipelineTransport``, so we patch the source module.
        """
        import audio.backends.pipeline_transport

        self._transport = FakeTransport()
        audio.backends.pipeline_transport.GStreamerPipelineTransport = MagicMock(
            return_value=self._transport
        )
        yield

    @pytest.fixture
    def engine(self):
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
        result.queue_progressed = MagicMock()
        return result

    # ── Initialisation ──

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

    def test_warns_when_distribution_conflicts_with_bitperfect(self, engine, caplog):
        engine._audio_profile = "bitperfect_pcm"
        engine._snapcast_fifo_enabled = True

        with caplog.at_level("WARNING", logger="michi.player"):
            distribution_requires_pcm = engine._check_distribution_vs_bitperfect()

        assert distribution_requires_pcm is True
        assert "distribution requires PCM output" in caplog.text

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

    def test_play_adopts_pipeline_and_starts(self, engine):
        pipeline = MagicMock()
        pipeline.set_state.return_value = MOCK_GST.StateChangeReturn.SUCCESS
        pipeline.get_bus.return_value = MagicMock()

        with (
            patch("audio.format_probe.probe_format") as mock_probe,
            patch("audio.output_profiles.get_profile") as mock_get_profile,
            patch("audio.output_device_manager.get_device") as mock_get_device,
            patch("audio.pipeline_factory.PipelineFactory") as mock_pf_class,
            patch("audio.dsp_state.DspState") as mock_dsp_class,
            patch("audio.dac_manager.DacManager") as mock_dm_class,
        ):
            mock_probe.return_value = MagicMock(
                codec="flac",
                sample_rate=44100,
                bit_depth=16,
                channels=2,
                is_dsd=False,
            )
            mock_get_profile.return_value = MagicMock(
                key="standard",
                allows_replaygain=False,
                allows_transmit=True,
                bitperfect=False,
            )
            mock_get_device.return_value = MagicMock(
                display_name="dev", device_string="hw:0", backend="alsa"
            )
            mock_pf = MagicMock()
            mock_pf.build_for_uri.return_value = pipeline
            mock_pf_class.return_value = mock_pf
            mock_dsp_class.return_value = MagicMock()
            mock_dm = MagicMock()
            mock_dm.refresh_devices = MagicMock()
            mock_dm.select_output_route.return_value = MagicMock()
            mock_dm_class.return_value = mock_dm

            engine._setup_bus = MagicMock()
            engine._setup_timer = MagicMock()
            engine.set_library_db = MagicMock()

            engine.play("/tmp/test.flac")

        self._transport.adopt_pipeline.assert_called_with(pipeline)
        pipeline.set_state.assert_called_with(MOCK_GST.State.PLAYING)
        from audio.player import PlaybackState

        signals = [c[0][0] for c in engine.state_changed.emit.call_args_list]
        assert any(s == PlaybackState.PLAYING for s in signals)

    def test_play_pipeline_failure(self, engine):
        mock_pf = MagicMock()
        mock_pf.build_for_uri.return_value = None

        with (
            patch("audio.format_probe.probe_format") as mock_probe,
            patch("audio.output_profiles.get_profile") as mock_get_profile,
            patch("audio.output_device_manager.get_device") as mock_get_device,
            patch("audio.pipeline_factory.PipelineFactory") as mock_pf_class,
            patch("audio.dsp_state.DspState"),
            patch("audio.dac_manager.DacManager") as mock_dm_class,
        ):
            mock_probe.return_value = MagicMock(
                codec="flac", sample_rate=44100, bit_depth=16, channels=2, is_dsd=False
            )
            mock_get_profile.return_value = MagicMock(
                key="standard",
                allows_replaygain=False,
                allows_transmit=True,
                bitperfect=False,
            )
            mock_get_device.return_value = MagicMock(
                display_name="dev", device_string="hw:0", backend="alsa"
            )
            mock_pf_class.return_value = mock_pf
            mock_dm = MagicMock()
            mock_dm.refresh_devices = MagicMock()
            mock_dm.select_output_route.return_value = MagicMock()
            mock_dm_class.return_value = mock_dm

            engine._setup_bus = MagicMock()
            engine._setup_timer = MagicMock()
            engine.set_library_db = MagicMock()

            engine.play("/tmp/test.flac")

        engine.error_occurred.emit.assert_called_with("Failed to create pipeline")

    def test_play_set_state_failure(self, engine):
        pipeline = MagicMock()
        pipeline.set_state.return_value = MOCK_GST.StateChangeReturn.FAILURE
        pipeline.get_bus.return_value = MagicMock()

        with (
            patch("audio.format_probe.probe_format") as mock_probe,
            patch("audio.output_profiles.get_profile") as mock_get_profile,
            patch("audio.output_device_manager.get_device") as mock_get_device,
            patch("audio.pipeline_factory.PipelineFactory") as mock_pf_class,
            patch("audio.dsp_state.DspState"),
            patch("audio.dac_manager.DacManager") as mock_dm_class,
        ):
            mock_probe.return_value = MagicMock(
                codec="flac",
                sample_rate=44100,
                bit_depth=16,
                channels=2,
                is_dsd=False,
            )
            mock_get_profile.return_value = MagicMock(
                key="standard",
                allows_replaygain=False,
                allows_transmit=True,
                bitperfect=False,
            )
            mock_get_device.return_value = MagicMock(
                display_name="dev", device_string="hw:0", backend="alsa"
            )
            mock_pf = MagicMock()
            mock_pf.build_for_uri.return_value = pipeline
            mock_pf_class.return_value = mock_pf
            mock_dm = MagicMock()
            mock_dm.refresh_devices = MagicMock()
            mock_dm.select_output_route.return_value = MagicMock()
            mock_dm_class.return_value = mock_dm

            engine._setup_bus = MagicMock()
            engine._setup_timer = MagicMock()
            engine.set_library_db = MagicMock()

            engine.play("/tmp/test.flac")

        engine.error_occurred.emit.assert_called_with("Failed to start playback")

    # ── pause / resume / toggle / stop ──

    def test_pause_delegates_to_transport(self, engine):
        """DRIFT: origin/main pause() has no state guard — always delegates."""
        engine.pause()

        self._transport.pause.assert_called_once()
        from audio.player import PlaybackState

        signals = [c[0][0] for c in engine.state_changed.emit.call_args_list]
        assert any(s == PlaybackState.PAUSED for s in signals)

    def test_resume_delegates_to_transport(self, engine):
        """DRIFT: origin/main resume() has no state guard — always delegates."""
        engine.resume()

        self._transport.resume.assert_called_once()
        from audio.player import PlaybackState

        signals = [c[0][0] for c in engine.state_changed.emit.call_args_list]
        assert any(s == PlaybackState.PLAYING for s in signals)

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

    def test_stop_cleans_up_pipeline_and_transport(self, engine):
        """DRIFT: origin/main stop() uses transport.get_pipeline(),
        transport.adopt_pipeline(None), then transport.stop()."""
        pipeline = MagicMock()
        pipeline.get_state.return_value = (
            MOCK_GST.StateChangeReturn.SUCCESS,
            MOCK_GST.State.NULL,
        )
        self._transport.get_pipeline.return_value = pipeline
        timer = MagicMock()
        engine._timer = timer
        from audio.player import PlaybackState

        engine.stop()

        self._transport.get_pipeline.assert_called()
        self._transport.adopt_pipeline.assert_called_with(None)
        pipeline.set_state.assert_called_with(MOCK_GST.State.NULL)
        timer.stop.assert_called_once()
        assert engine._timer is None
        self._transport.stop.assert_called_once()
        signals = [c[0][0] for c in engine.state_changed.emit.call_args_list]
        assert any(s == PlaybackState.STOPPED for s in signals)

    def test_stop_without_timer(self, engine):
        engine._timer = None
        from audio.player import PlaybackState

        engine.stop()

        self._transport.stop.assert_called_once()
        signals = [c[0][0] for c in engine.state_changed.emit.call_args_list]
        assert any(s == PlaybackState.STOPPED for s in signals)

    # ── seek ──

    def test_seek_delegates_to_transport(self, engine):
        """DRIFT: origin/main seek() delegates to transport.seek()."""
        engine.seek(42.5)
        self._transport.seek.assert_called_once_with(42.5)

    def test_seek_negative(self, engine):
        engine.seek(-10)
        # DRIFT: transport receives raw value; clamping happens in transport
        self._transport.seek.assert_called_once_with(-10)

    # ── set_volume ──

    def test_set_volume_stores_int_delegates_float(self, engine):
        """DRIFT: origin/main stores int 0-100, sends 0.0-1.0 to transport."""
        engine.set_volume(75)
        assert engine._volume == 75
        self._transport.set_volume.assert_called_with(0.75)

    def test_set_volume_clamps_top(self, engine):
        engine.set_volume(200)
        assert engine._volume == 100

    def test_set_volume_clamps_bottom(self, engine):
        engine.set_volume(-50)
        assert engine._volume == 0

    def test_set_volume_rounds_float(self, engine):
        """int(vol) cast truncates; origin/main accepts int."""
        engine.set_volume(75.9)
        assert engine._volume == 75

    # ── Queue operations ──

    def test_enqueue_delegates_to_transport(self, engine):
        """DRIFT: origin/main enqueue() delegates to transport.enqueue()."""
        engine.enqueue(["/tmp/a.flac", "/tmp/b.flac"])
        self._transport.enqueue.assert_called_once_with(
            ["/tmp/a.flac", "/tmp/b.flac"], True
        )
        engine.queue_changed.emit.assert_called_once()

    def test_enqueue_play_now_false(self, engine):
        engine.enqueue(["/tmp/c.flac"], play_now=False)
        self._transport.enqueue.assert_called_once_with(
            ["/tmp/c.flac"], False
        )

    def test_enqueue_next_delegates(self, engine):
        engine.enqueue_next(["/tmp/d.flac"])
        self._transport.enqueue_next.assert_called_once_with(["/tmp/d.flac"])
        engine.queue_changed.emit.assert_called_once()

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

    def test_get_queue_returns_filepath_only(self, engine):
        """DRIFT: origin/main get_queue() returns [{'filepath': fp}] only."""
        engine._queue = ["/tmp/a.flac", "/tmp/b.flac"]

        items = engine.get_queue()

        assert len(items) == 2
        assert items[0]["filepath"] == "/tmp/a.flac"
        assert "title" not in items[0]
        assert "is_current" not in items[0]

    def test_get_queue_empty(self, engine):
        assert engine.get_queue() == []

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

    def test_play_next_delegates(self, engine):
        """DRIFT: origin/main play_next() delegates to transport.play_next()."""
        self._transport.play_next.return_value = True
        result = engine.play_next()
        assert result is True
        self._transport.play_next.assert_called_once()
        engine.queue_changed.emit.assert_called_once()

    def test_play_next_at_end(self, engine):
        self._transport.play_next.return_value = False
        result = engine.play_next()
        assert result is False
        self._transport.play_next.assert_called_once()

    def test_play_prev_delegates(self, engine):
        """DRIFT: origin/main play_prev() delegates to transport.play_prev()."""
        self._transport.play_prev.return_value = True
        result = engine.play_prev()
        assert result is True
        self._transport.play_prev.assert_called_once()
        engine.queue_changed.emit.assert_called_once()

    def test_play_prev_at_start(self, engine):
        self._transport.play_prev.return_value = False
        result = engine.play_prev()
        assert result is False
        self._transport.play_prev.assert_called_once()

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

    def test_set_shuffle_preserves_canonical_queue_order(self, engine):
        engine._queue = ["a.flac", "b.flac", "c.flac"]

        assert engine.set_shuffle(True) is True
        assert engine._shuffle is True
        assert engine._queue == ["a.flac", "b.flac", "c.flac"]

    def test_set_repeat_accepts_canonical_modes(self, engine):
        for mode in ("none", "all", "one"):
            assert engine.set_repeat(mode) == mode
            assert engine._repeat == mode

    def test_set_repeat_rejects_invalid_mode(self, engine):
        with pytest.raises(ValueError, match="Invalid repeat mode"):
            engine.set_repeat("track")

    def test_toggle_repeat_cycles(self, engine):
        engine._repeat = "none"
        assert engine.toggle_repeat() == "all"
        assert engine.toggle_repeat() == "one"
        assert engine.toggle_repeat() == "none"
        assert engine.toggle_repeat() == "all"

    def test_set_shuffle_preserves_canonical_queue_order(self, engine):
        engine._queue = ["a.flac", "b.flac", "c.flac"]

        assert engine.set_shuffle(True) is True
        assert engine._shuffle is True
        assert engine._queue == ["a.flac", "b.flac", "c.flac"]

    def test_set_repeat_accepts_canonical_modes(self, engine):
        for mode in ("none", "all", "one"):
            assert engine.set_repeat(mode) == mode
            assert engine._repeat == mode

    def test_set_repeat_rejects_invalid_mode(self, engine):
        with pytest.raises(ValueError, match="Invalid repeat mode"):
            engine.set_repeat("track")

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
        pipeline.get_state.return_value = (
            MOCK_GST.StateChangeReturn.SUCCESS,
            MOCK_GST.State.NULL,
        )
        self._transport.get_pipeline.return_value = pipeline
        engine._timer = MagicMock()

        engine._on_bus_message(bus, message)

        engine.error_occurred.emit.assert_called()
        self._transport.adopt_pipeline.assert_called_with(None)
        pipeline.set_state.assert_called_with(MOCK_GST.State.NULL)
        engine._timer.stop.assert_called_once()

    def test_bus_message_warning_does_not_emit_error(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.WARNING
        message.parse_warning.return_value = ("warn", "detail")

        engine._on_bus_message(bus, message)

        engine.error_occurred.emit.assert_not_called()

    def test_bus_message_buffering_pauses_pipeline(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.BUFFERING
        message.parse_buffering.return_value = 50
        pipeline = MagicMock()
        pipeline.set_state.return_value = MOCK_GST.StateChangeReturn.SUCCESS
        self._transport.get_pipeline.return_value = pipeline
        from audio.player import PlaybackState

        engine._state = PlaybackState.PLAYING

        engine._on_bus_message(bus, message)

        pipeline.set_state.assert_called_with(MOCK_GST.State.PAUSED)

    def test_bus_message_buffering_complete_resumes(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.BUFFERING
        message.parse_buffering.return_value = 100
        pipeline = MagicMock()
        pipeline.set_state.return_value = MOCK_GST.StateChangeReturn.SUCCESS
        self._transport.get_pipeline.return_value = pipeline
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
        self._transport.get_pipeline.return_value = pipeline

        engine._on_bus_message(bus, message)

        assert engine._duration == 123.456789
        engine.duration_changed.emit.assert_called_with(123.456789)

    def test_bus_message_state_changed_non_pipeline_src(self, engine):
        bus = MagicMock()
        message = MagicMock()
        message.type = MOCK_GST.MessageType.STATE_CHANGED
        message.src = "not_pipeline"
        engine._pipeline = MagicMock()
        # no crash expected

        engine._on_bus_message(bus, message)

    # ── _to_uri ──

    def test_to_uri_preserves_http(self, engine):
        assert (
            engine._to_uri("http://example.com/stream")
            == "http://example.com/stream"
        )

    def test_to_uri_preserves_https(self, engine):
        assert (
            engine._to_uri("https://example.com/stream")
            == "https://example.com/stream"
        )

    def test_to_uri_preserves_icy(self, engine):
        assert (
            engine._to_uri("icy://example.com/stream")
            == "icy://example.com/stream"
        )

    def test_to_uri_preserves_file_protocol(self, engine):
        assert (
            engine._to_uri("file:///home/test.flac")
            == "file:///home/test.flac"
        )

    def test_to_uri_converts_filepath(self, engine):
        result = engine._to_uri("/home/test.flac")
        assert result == "file:///home/test.flac"

    # ── _on_media_finished / _on_media_finished_eos ──

    def test_on_media_finished_delegates_to_play_next(self, engine):
        """DRIFT: origin/main _on_media_finished uses play_next() for
        transport delegation."""
        self._transport.play_next.return_value = True

        engine._on_media_finished()

        self._transport.play_next.assert_called_once()
        engine.finished.emit.assert_not_called()

    def test_on_media_finished_at_end_stops(self, engine):
        pipeline = MagicMock()
        pipeline.get_state.return_value = (
            MOCK_GST.StateChangeReturn.SUCCESS,
            MOCK_GST.State.NULL,
        )
        self._transport.get_pipeline.return_value = pipeline
        self._transport.play_next.return_value = False
        from audio.player import PlaybackState

        engine._on_media_finished()

        self._transport.play_next.assert_called_once()
        pipeline.set_state.assert_called_with(MOCK_GST.State.NULL)
        signals = [c[0][0] for c in engine.state_changed.emit.call_args_list]
        assert any(s == PlaybackState.STOPPED for s in signals)
        engine.finished.emit.assert_called_once()

    def test_on_media_finished_eos_gapless_clears_flag_and_emits(self, engine):
        """EOS with more items clears gapless flag and emits queue_progressed.
        Queue index advance is delegated to queue_service via the signal."""
        engine._gapless_active = True
        engine._queue = ["a.flac", "b.flac"]
        engine._queue_index = 0

        engine._on_media_finished_eos()

        assert engine._gapless_active is False
        engine.queue_progressed.emit.assert_called_with(
            0, "a.flac", "eos", engine._queue_revision
        )

    def test_on_media_finished_eos_no_gapless_falls_through(self, engine):
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
        self._transport.get_pipeline.return_value = pipeline

        assert engine.get_position_ns() == 5000000000

    def test_get_position_ns_no_pipeline(self, engine):
        """DRIFT: origin/main reads pipeline from transport.get_pipeline()."""
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
