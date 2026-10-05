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
