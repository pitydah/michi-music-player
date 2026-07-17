"""Productive audio tests with synthetic WAV and fakesink."""
import os
import wave
import struct
import math
import tempfile
import time

import pytest
from unittest.mock import MagicMock

try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    HAVE_GSTREAMER = True
except (ImportError, ValueError):
    HAVE_GSTREAMER = False


def _create_sine_wav(path, freq=440, duration=1.0, sample_rate=44100):
    num_samples = int(sample_rate * duration)
    max_val = int(0.5 * 32767)
    with wave.open(path, 'w') as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for i in range(num_samples):
            t = i / sample_rate
            val = int(max_val * math.sin(2 * math.pi * freq * t))
            packed = struct.pack('<h', val)
            wav.writeframes(packed)
            wav.writeframes(packed)


skip_no_gst = pytest.mark.skipif(not HAVE_GSTREAMER, reason="GStreamer not available")


@skip_no_gst
class TestAudioProductive:
    """Productive tests using real GStreamer with fakesink pipeline."""

    @pytest.fixture(autouse=True)
    def _ensure_qapp(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield

    def _make_fakesink_pipeline(self, wav_path):
        uri = Gst.filename_to_uri(os.path.abspath(wav_path))
        pipeline = Gst.parse_launch(
            f'uridecodebin uri={uri} ! audioconvert ! fakesink sync=true'
        )
        return pipeline

    def _setup_bus_safe(self, engine):
        pipeline = engine._backend.get_pipeline()
        if not pipeline:
            return
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", engine._on_bus_message)
        engine._gapless_active = False

    def test_synthetic_wav_plays_with_fakesink(self):
        from audio.player import GStreamerEngine

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            _create_sine_wav(f.name)
            engine = GStreamerEngine()
            db_mock = MagicMock()
            db_mock.load_queue.return_value = ([], -1)
            db_mock.load_settings.return_value = None
            engine.set_library_db(db_mock)

            pipeline = self._make_fakesink_pipeline(f.name)
            engine._backend.adopt_pipeline(pipeline)
            engine._current = f.name
            self._setup_bus_safe(engine)
            engine._setup_timer()

            ret = pipeline.set_state(Gst.State.PLAYING)
            assert ret != Gst.StateChangeReturn.FAILURE, "Pipeline failed to start"

            time.sleep(0.5)

            state = engine.state
            assert state is not None

            engine.stop()
            os.unlink(f.name)

    def test_play_pause_stop(self):
        from audio.player import GStreamerEngine

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            _create_sine_wav(f.name)
            engine = GStreamerEngine()

            pipeline = self._make_fakesink_pipeline(f.name)
            engine._backend.adopt_pipeline(pipeline)
            engine._current = f.name
            self._setup_bus_safe(engine)

            ret = pipeline.set_state(Gst.State.PLAYING)
            assert ret != Gst.StateChangeReturn.FAILURE
            time.sleep(0.3)

            engine.pause()
            time.sleep(0.1)

            engine.resume()
            time.sleep(0.1)

            engine.stop()
            os.unlink(f.name)

    def test_single_backend_instance(self):
        from audio.player import GStreamerEngine
        from audio.backends.gstreamer_backend import GStreamerAudioBackend

        engine = GStreamerEngine()
        assert hasattr(engine, '_backend')
        assert isinstance(engine._backend, GStreamerAudioBackend)
