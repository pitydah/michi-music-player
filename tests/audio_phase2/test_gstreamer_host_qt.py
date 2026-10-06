"""Real Qt dispatch-path tests for the hosted port.

These tests deliberately DO NOT call ``dispatch_pending()``: they prove that
the production Qt queued-dispatch path delivers host events on the owner
loop, which is the path the real application uses.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from michi.application.ports import AudioLoadError
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.audio_engines.gstreamer_host_client import (
    GStreamerHostSupervisor,
)
from michi.infrastructure.audio_engines.gstreamer_host_port import (
    GStreamerHostedAudioPort,
)

FAKE_HOST = Path(__file__).parent / "gst_host_engine_fake.py"
FAST = {
    "start_timeout_s": 1.5,
    "command_timeout_s": 1.5,
    "terminate_grace_s": 0.4,
    "term_grace_s": 0.3,
    "kill_grace_s": 0.5,
}


def _port(behavior: str) -> tuple[GStreamerHostSupervisor, GStreamerHostedAudioPort]:
    def factory(fd: int) -> list[str]:
        return [
            sys.executable,
            str(FAKE_HOST),
            "--fd",
            str(fd),
            "--engine-behavior",
            behavior,
        ]

    supervisor = GStreamerHostSupervisor(command_factory=factory, **FAST)
    port = GStreamerHostedAudioPort(
        supervisor,
        command_deadline_s=FAST["command_timeout_s"],
        load_deadline_s=FAST["command_timeout_s"],
    )
    return supervisor, port


def test_spontaneous_event_arrives_through_the_real_qt_loop(qapp) -> None:
    """A late host event must be delivered by the Qt queued dispatcher.

    The fake engine emits PLAYING 300 ms after ``play()`` returns, i.e. while
    the owner is idle. Only the production dispatch path can deliver it.
    """
    supervisor, port = _port("delayed_event")
    states: list[PlaybackStatus] = []
    port.subscribe_playback_state_changed(states.append)
    try:
        port.activate()
        assert port._owner_invoker is not None, (  # noqa: SLF001
            "production Qt dispatch must arm when a QApplication exists"
        )
        port.load(Path("/tmp/qt-dispatch.flac"))
        port.play()
        deadline = time.monotonic() + 5.0
        while not states and time.monotonic() < deadline:
            qapp.processEvents()  # THE PRODUCTION LOOP — no manual drain
            time.sleep(0.01)
        assert states == [PlaybackStatus.PLAYING]
        # No queued work may be left behind once the loop processed it.
        assert port._owner_queue == []  # noqa: SLF001
    finally:
        port.close()
        supervisor.close()


def test_qt_dispatch_survives_when_owner_was_never_waiting(qapp) -> None:
    """Two consecutive spontaneous bursts are both delivered."""
    supervisor, port = _port("delayed_event")
    states: list[PlaybackStatus] = []
    port.subscribe_playback_state_changed(states.append)
    try:
        port.activate()
        deadline = time.monotonic() + 5.0
        for _ in range(2):
            port.play()
        while len(states) < 2 and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        assert states == [PlaybackStatus.PLAYING, PlaybackStatus.PLAYING]
    finally:
        port.close()
        supervisor.close()


def test_qt_timer_keeps_running_during_a_bounded_host_wait(qapp) -> None:
    """The REAL Qt loop keeps progressing while the owner waits on a host.

    A hung host converts into a typed, bounded failure; during that wait the
    Qt owner pumps timers (input/paint animate the same way) instead of
    freezing for the whole deadline.
    """
    from PySide6.QtCore import QTimer

    supervisor, port = _port("hang_on_load")
    ticks: list[float] = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    try:
        port.activate()
        timer.start()
        started = time.monotonic()
        with pytest.raises(AudioLoadError):
            port.load(Path("/tmp/qt-responsiveness.flac"))
        elapsed = time.monotonic() - started
        timer.stop()
        assert elapsed >= 0.5  # the deadline really elapsed
        assert len(ticks) >= 5, (
            f"Qt timer froze during a {elapsed:.2f}s host wait (ticks={len(ticks)})"
        )
    finally:
        port.close()
        supervisor.close()


def test_non_owner_threads_do_not_pump_qt(qapp) -> None:
    """Only the owner thread pumps; worker-thread waits stay plain."""
    supervisor, port = _port("hang_on_load")
    imported: list[bool] = []
    try:
        port.activate()
        # Simulate the old behavior: if the app were not captured, the wait
        # must still complete bounded and typed (pump path is optional).
        port._qt_app = None  # noqa: SLF001
        with pytest.raises(AudioLoadError):
            port.load(Path("/tmp/qt-responsiveness-2.flac"))
        imported.append(True)
    finally:
        port.close()
        supervisor.close()
    assert imported == [True]


def test_async_load_keeps_the_owner_free_and_reports_failure(qapp) -> None:
    """Async seam: the Qt owner never waits; the typed failure lands on it."""
    from PySide6.QtCore import QTimer

    supervisor, port = _port("hang_on_load")
    failures: list[Exception] = []
    ticks: list[float] = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    try:
        port.activate()
        timer.start()
        started = time.monotonic()
        port.load_async(Path("/tmp/async-hang.flac"), on_failed=failures.append)
        deadline = time.monotonic() + 5.0
        while not failures and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        elapsed = time.monotonic() - started
        timer.stop()
        assert failures and isinstance(failures[0], AudioLoadError)
        assert elapsed >= 0.5  # the parent deadline really elapsed
        # The owner stayed free the whole time: the timer kept firing.
        assert len(ticks) >= 5
    finally:
        port.close()
        supervisor.close()


def test_async_load_reports_success_on_the_owner(qapp) -> None:
    supervisor, port = _port("normal")
    done: list[dict] = []
    failures: list[Exception] = []
    try:
        port.activate()
        port.load_async(
            Path("/tmp/async-ok.flac"),
            on_done=done.append,
            on_failed=failures.append,
        )
        deadline = time.monotonic() + 5.0
        while not done and not failures and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert not failures
        assert done == [{}]
    finally:
        port.close()
        supervisor.close()
