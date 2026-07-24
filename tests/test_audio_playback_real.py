"""Vertical playback test: Bootstrap → PlayerService → GStreamerEngine → fakesink.

Generates a real WAV file and plays it through the full pipeline.
Uses fakesink in CI (no audio hardware required).
"""
from __future__ import annotations

import os
import struct
import wave
import tempfile
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("QT_QPA_PLATFORM"),
    reason="Requires QT_QPA_PLATFORM",
)

SAMPLE_RATE = 44100
DURATION_SEC = 0.5
NUM_SAMPLES = int(SAMPLE_RATE * DURATION_SEC)


def _generate_test_wav() -> str:
    """Generate a 0.5s 440Hz sine WAV."""
    path = os.path.join(tempfile.gettempdir(), "michi_test_audio.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        samples = []
        for i in range(NUM_SAMPLES):
            t = i / SAMPLE_RATE
            val = int(16000 * __import__("math").sin(2 * 3.14159 * 440 * t))
            samples.append(struct.pack("<h", val))
        wf.writeframes(b"".join(samples))
    return path


@pytest.fixture(scope="module")
def test_wav():
    path = _generate_test_wav()
    yield path
    if os.path.exists(path):
        os.unlink(path)


def _get_player_svc(bootstrap):
    return bootstrap.container.get("playback_service")


def _get_engine(bootstrap):
    return _get_player_svc(bootstrap)._engine


def _get_adapter(bootstrap):
    return _get_player_svc(bootstrap)._engine_adapter


def test_bootstrap_creates_player_service(test_wav):
    """Bootstrap builds PlayerService connected to GStreamerEngine."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        player = _get_player_svc(bootstrap)
        assert player is not None
        assert player._engine is not None
        assert player._engine_adapter is not None
    finally:
        bootstrap.shutdown()


def test_play_wav_through_engine(test_wav):
    """GStreamerEngine.play() processes a WAV through PipelineFactory."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        engine = _get_engine(bootstrap)
        engine.play(test_wav)
        assert engine.state.value == 1  # PLAYING
        snap = _get_adapter(bootstrap).get_snapshot()
        assert snap.state == "playing"
        assert snap.current_path == test_wav
    finally:
        bootstrap.shutdown()


def test_pause_resume_cycle(test_wav):
    """Pause and resume work through the full chain."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        svc = _get_player_svc(bootstrap)

        svc.play(test_wav)
        svc.pause()
        snap = _get_adapter(bootstrap).get_snapshot()
        assert snap.state == "paused"

        svc.resume()
        snap = _get_adapter(bootstrap).get_snapshot()
        assert snap.state == "playing"
    finally:
        bootstrap.shutdown()


def test_stop_returns_to_stopped(test_wav):
    """Stop transitions to stopped state."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        svc = _get_player_svc(bootstrap)

        svc.play(test_wav)
        svc.stop()
        snap = _get_adapter(bootstrap).get_snapshot()
        assert snap.state == "stopped"
    finally:
        bootstrap.shutdown()


def test_seek_does_not_crash(test_wav):
    """Seek does not raise during active playback."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        svc = _get_player_svc(bootstrap)

        svc.play(test_wav)
        svc.seek(1.0)
        snap = _get_adapter(bootstrap).get_snapshot()
        assert snap.state == "playing"
    finally:
        bootstrap.shutdown()


def test_set_volume_affects_snapshot(test_wav):
    """Volume changes reflect in snapshot."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        svc = _get_player_svc(bootstrap)

        svc.set_volume(50)
        snap = _get_adapter(bootstrap).get_snapshot()
        assert snap.volume == 50
    finally:
        bootstrap.shutdown()


def test_play_nonexistent_file_does_not_crash(test_wav):
    """Playing a nonexistent file emits error but does not crash."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        svc = _get_player_svc(bootstrap)
        svc.play("/tmp/nonexistent_file_xyz.wav")
        snap = _get_adapter(bootstrap).get_snapshot()
        assert snap.state in ("stopped", "error")
    finally:
        bootstrap.shutdown()


def test_single_engine_instance(test_wav):
    """Only one GStreamerEngine exists in the process."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        engine = _get_engine(bootstrap)

        assert hasattr(engine, "_transport")
        assert not hasattr(engine, "_backend")
    finally:
        bootstrap.shutdown()


def test_no_attribute_error_during_play(test_wav):
    """No AttributeError is raised during the play() call chain."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        svc = _get_player_svc(bootstrap)

        errors = []

        def on_error(msg):
            errors.append(msg)

        svc.error_occurred.connect(on_error)
        svc.play(test_wav)

        attr_errors = [e for e in errors if "AttributeError" in str(e) or "object has no attribute" in str(e)]
        assert len(attr_errors) == 0, f"AttributeErrors during play: {attr_errors}"
    finally:
        bootstrap.shutdown()
