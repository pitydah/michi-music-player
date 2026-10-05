"""Real GStreamer host smoke: fresh process handshake + bounded shutdown.

Proves the child process initializes GStreamer itself (never inherited) and
reports primitive runtime facts; semantic authorities stay in the parent.
"""

from __future__ import annotations

import importlib.util

import pytest

from michi.infrastructure.audio_engines.gstreamer_host_client import (
    GRACEFUL,
    GStreamerHostSupervisor,
)

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="PyGObject/GStreamer not available on this host"
)


def test_real_host_handshake_reports_gstreamer_runtime() -> None:
    supervisor = GStreamerHostSupervisor(
        start_timeout_s=45.0,
        command_timeout_s=15.0,
        terminate_grace_s=5.0,
        term_grace_s=3.0,
        kill_grace_s=3.0,
    )
    try:
        hello = supervisor.start()
        assert isinstance(hello["gstreamer_version"], str)
        assert "GStreamer" in hello["gstreamer_version"]
        assert hello["playbin3_available"] is True
        assert hello["runtime_failure"] is None
        assert hello["pid"] != 0
        assert supervisor.ping()["pong"] is True
        assert supervisor.host_generation == 1
    finally:
        kind = supervisor.shutdown()
    assert kind == GRACEFUL
    assert not supervisor.pid_alive()


def test_real_host_restart_is_a_new_generation() -> None:
    supervisor = GStreamerHostSupervisor(
        start_timeout_s=45.0,
        command_timeout_s=15.0,
        terminate_grace_s=5.0,
        term_grace_s=3.0,
        kill_grace_s=3.0,
    )
    generations = []
    for _ in range(2):
        supervisor.start()
        generations.append(supervisor.host_generation)
        assert supervisor.shutdown() == GRACEFUL
    assert generations == [1, 2]


def test_real_hosted_port_opens_the_real_engine_inside_the_child() -> None:
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    supervisor = GStreamerHostSupervisor(
        start_timeout_s=45.0,
        command_timeout_s=30.0,
        terminate_grace_s=8.0,
        term_grace_s=5.0,
        kill_grace_s=5.0,
    )
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
    )
    try:
        port.activate()
        hello = port.host_hello
        assert hello is not None
        assert hello["playbin3_available"] is True
        assert "GStreamer" in hello["gstreamer_version"]
        assert supervisor.pid_alive()
    finally:
        port.close()
    assert port.termination_kind == GRACEFUL
    assert not supervisor.pid_alive()


def test_real_shared_playback_command_surface_on_the_hosted_port() -> None:
    """Full Shared command surface through the REAL host (silent, volume 0).

    Exercises load -> accepted -> play/pause/resume/seek -> stop -> close
    with real GStreamer sinks but zero gain, so no audible output is
    produced and no physical claim is made.
    """
    import time
    from pathlib import Path

    from michi.domain.playback import PlaybackStatus
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    fixture = (
        Path(__file__).resolve().parents[2]
        / "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run"
        / "fixtures/pcm16_44100.wav"
    )
    if not fixture.is_file():
        pytest.skip("PCM fixture unavailable")

    supervisor = GStreamerHostSupervisor(
        start_timeout_s=45.0,
        command_timeout_s=30.0,
        terminate_grace_s=8.0,
        term_grace_s=5.0,
        kill_grace_s=5.0,
    )
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
    )
    accepted: list[str] = []
    states: list[PlaybackStatus] = []
    port.subscribe_media_accepted(lambda path: accepted.append(str(path)))
    port.subscribe_playback_state_changed(states.append)
    try:
        port.activate()
        port.load(fixture)
        deadline = time.monotonic() + 30.0
        while not accepted and time.monotonic() < deadline:
            port.dispatch_pending()
            time.sleep(0.02)
        port.dispatch_pending()
        assert accepted, "hosted load never published media acceptance"

        port.set_volume(0)  # silent: no audible output, real pipeline only

        def wait_state(wanted: PlaybackStatus, timeout_s: float = 15.0) -> bool:
            deadline = time.monotonic() + timeout_s
            while wanted not in states and time.monotonic() < deadline:
                port.dispatch_pending()
                time.sleep(0.02)
            return wanted in states

        # A real caller waits for each transition: a newer command supersedes
        # older pending events by design (two-domain generation fence).
        port.play()
        assert wait_state(PlaybackStatus.PLAYING), states
        port.pause()
        assert wait_state(PlaybackStatus.PAUSED), states
        port.resume()
        assert wait_state(PlaybackStatus.PLAYING), states
        port.seek(0)
        port.stop()
        assert wait_state(PlaybackStatus.STOPPED), states
    finally:
        port.close()
    assert port.termination_kind == GRACEFUL
    assert not supervisor.pid_alive()
