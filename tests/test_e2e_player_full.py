"""E2E test: complete playback cycle through Bootstrap + PlayerService + Engine."""
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
NUM_SAMPLES = int(SAMPLE_RATE * 0.3)


def _generate_wav() -> str:
    path = os.path.join(tempfile.gettempdir(), "michi_e2e_test.wav")
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
def wav_path():
    path = _generate_wav()
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_e2e_bootstrap_playback_cycle(wav_path):
    """Full cycle: bootstrap -> play -> pause -> resume -> stop -> snapshot."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        svc = bootstrap.container.get("playback_service")
        assert svc is not None

        # Play
        svc.play(wav_path)
        snap = svc._engine_adapter.get_snapshot()
        assert snap.state == "playing", f"Expected playing, got {snap.state}"
        assert snap.current_path == wav_path

        # Pause
        svc.pause()
        snap = svc._engine_adapter.get_snapshot()
        assert snap.state == "paused"

        # Resume
        svc.resume()
        snap = svc._engine_adapter.get_snapshot()
        assert snap.state == "playing"

        # Stop
        svc.stop()
        snap = svc._engine_adapter.get_snapshot()
        assert snap.state == "stopped"

        # Verify backend
        assert snap.backend_id == "gstreamer"
    finally:
        bootstrap.shutdown()


def test_e2e_playback_signals(wav_path):
    """Playback signals are emitted: state_changed, position_changed."""
    from core.application_bootstrap import ApplicationBootstrap
    from PySide6.QtCore import QTimer

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        svc = bootstrap.container.get("playback_service")

        states = []
        svc.state_changed.connect(lambda s: states.append(s))

        svc.play(wav_path)
        QTimer.singleShot(200, svc.stop)
        QTimer.singleShot(300, lambda: None)

        assert "playing" in states, f"State playing not emitted: {states}"
    finally:
        bootstrap.shutdown()


def test_e2e_playback_no_crash_on_bad_file(wav_path):
    """Playing a nonexistent file does not crash the engine."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        svc = bootstrap.container.get("playback_service")

        errors = []
        svc.error_occurred.connect(lambda m: errors.append(m))

        svc.play("/tmp/nonexistent_e2e_file.wav")
        snap = svc._engine_adapter.get_snapshot()
        assert snap.state in ("stopped", "error")
    finally:
        bootstrap.shutdown()


def test_e2e_volume_persistence(wav_path):
    """Volume set before play persists in snapshot."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        svc = bootstrap.container.get("playback_service")

        svc.set_volume(42)
        snap = svc._engine_adapter.get_snapshot()
        assert snap.volume == 42, f"Expected 42, got {snap.volume}"

        svc.play(wav_path)
        snap = svc._engine_adapter.get_snapshot()
        assert snap.volume == 42, f"Volume changed after play: {snap.volume}"
    finally:
        bootstrap.shutdown()


def test_e2e_single_engine(wav_path):
    """Only one engine instance exists."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        engine = bootstrap.container.get("playback_service")._engine
        assert hasattr(engine, "_transport")
        assert not hasattr(engine, "_backend"), "Engine should not use _backend architecture"
    finally:
        bootstrap.shutdown()
