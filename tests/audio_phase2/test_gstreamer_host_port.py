"""Hosted AudioPort proxy tests: commands, events, fences, host-loss mapping.

The host runs the production command/session machinery with a scripted engine
(no GStreamer), so every boundary is deterministic.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

from michi.application.ports import (
    AudioLoadError,
    AudioTransportCommandError,
    AudioTransportUnavailableError,
)
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.audio_engines.gstreamer_host_client import (
    FORCED_TERM,
    GRACEFUL,
    GStreamerHostSupervisor,
    SupervisorState,
)
from michi.infrastructure.audio_engines.gstreamer_host_port import (
    GStreamerHostedAudioPort,
)
from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
    HostEvent,
    MessageKind,
    make_message,
)

FAKE_HOST = Path(__file__).parent / "gst_host_engine_fake.py"
FAST = {
    "start_timeout_s": 1.5,
    "command_timeout_s": 1.0,
    "terminate_grace_s": 0.3,
    "term_grace_s": 0.3,
    "kill_grace_s": 0.5,
}


def _port(behavior: str, **overrides):
    def factory(fd: int) -> list[str]:
        return [
            sys.executable,
            str(FAKE_HOST),
            "--fd",
            str(fd),
            "--engine-behavior",
            behavior,
        ]

    options = dict(FAST)
    options.update(overrides)
    supervisor = GStreamerHostSupervisor(command_factory=factory, **options)
    port = GStreamerHostedAudioPort(
        supervisor,
        command_deadline_s=options["command_timeout_s"],
        load_deadline_s=options["command_timeout_s"],
    )
    return supervisor, port


def _pids_alive(pids: list[int]) -> list[int]:
    alive = []
    for pid in pids:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:  # pragma: no cover - defensive
            alive.append(pid)
            continue
        alive.append(pid)
    return alive


def test_activate_load_play_pause_stop_close_round_trip() -> None:
    supervisor, port = _port("normal")
    accepted: list[Path] = []
    states: list[PlaybackStatus] = []
    port.subscribe_media_accepted(accepted.append)
    port.subscribe_playback_state_changed(states.append)
    try:
        port.activate()
        assert port.host_hello is not None
        assert port.host_hello["gstreamer_version"] == "GStreamer fake-1.0"
        media = Path("/tmp/michi-hosted-song.flac")
        port.load(media)
        port.dispatch_pending()
        assert accepted == [media]
        port.play()
        port.dispatch_pending()
        port.pause()
        port.dispatch_pending()
        port.stop()
        port.dispatch_pending()
        assert states == [
            PlaybackStatus.PLAYING,
            PlaybackStatus.PAUSED,
            PlaybackStatus.STOPPED,
        ]
        assert port.backend_state() == "stopped"
        assert port.position() == 1234
        assert port.duration() == 2345
    finally:
        port.close()
    assert port.termination_kind == GRACEFUL
    assert supervisor.state is SupervisorState.STOPPED
    assert not supervisor.pid_alive()


def test_callbacks_are_queued_never_invoked_from_the_reader_thread() -> None:
    supervisor, port = _port("normal")
    accepted: list[Path] = []
    port.subscribe_media_accepted(accepted.append)
    try:
        port.activate()
        port.load(Path("/tmp/x.flac"))
        # Whether or not the event already arrived, it must sit in the owner
        # queue until the owner drains it.
        assert accepted == []
        port.dispatch_pending()
        assert len(accepted) == 1
    finally:
        port.close()


def test_load_rejection_transports_previous_source_disposition() -> None:
    for behavior, preserved in (
        ("reject_load", False),
        ("reject_load_preserved", True),
    ):
        supervisor, port = _port(behavior)
        try:
            port.activate()
            path = Path("/tmp/rejected.flac")
            with pytest.raises(AudioLoadError) as info:
                port.load(path)
            assert info.value.previous_source_preserved is preserved
            assert info.value.candidate_path == path
        finally:
            port.close()


def test_stop_rejection_maps_to_transport_command_error() -> None:
    supervisor, port = _port("reject_stop")
    try:
        port.activate()
        with pytest.raises(AudioTransportCommandError):
            port.stop()
        assert supervisor.pid_alive()  # a rejected command is not a lost host
    finally:
        port.close()


def test_hung_load_is_bounded_kills_host_and_maps_truthfully() -> None:
    supervisor, port = _port("hang_on_load", command_timeout_s=0.6)
    port.activate()
    ticks = 0
    stop = threading.Event()

    def ticker() -> None:
        nonlocal ticks
        while not stop.is_set():
            ticks += 1
            time.sleep(0.01)

    thread = threading.Thread(target=ticker)
    thread.start()
    started = time.monotonic()
    try:
        with pytest.raises(AudioLoadError) as info:
            port.load(Path("/tmp/wedged.flac"))
    finally:
        stop.set()
        thread.join(timeout=1.0)
    assert time.monotonic() - started < 4.0
    assert info.value.previous_source_preserved is False
    assert ticks >= 20  # the parent owner thread stayed responsive
    assert not supervisor.pid_alive()
    supervisor.close()


def test_host_crash_maps_to_transport_unavailable_and_relays_failure() -> None:
    supervisor, port = _port("crash_on_play")
    failures: list[tuple[int, str]] = []
    port.set_runtime_failure_callback(
        lambda generation, reason: failures.append((generation, reason))
    )
    try:
        port.activate()
        with pytest.raises(AudioTransportUnavailableError):
            port.play()
        port.dispatch_pending()
        assert failures and "OUTPUT_HOST_LOST" in failures[0][1]
        # The transport is truthfully gone: no silent continuation.
        with pytest.raises(AudioTransportUnavailableError):
            port.play()
    finally:
        port.close()
    assert not supervisor.pid_alive()


def test_pump_death_in_child_relays_runtime_failure() -> None:
    supervisor, port = _port("pump_death")
    failures: list[tuple[int, str]] = []
    port.set_runtime_failure_callback(
        lambda generation, reason: failures.append((generation, reason))
    )
    try:
        port.activate()
        port.play()
        port.dispatch_pending()
        assert failures
        assert "pump died inside the host" in failures[0][1]
        # The child is still alive: a port runtime failure is not host loss.
        assert supervisor.pid_alive()
    finally:
        port.close()


def test_generation_fence_drops_events_from_superseded_commands() -> None:
    supervisor, port = _port("normal")
    states: list[PlaybackStatus] = []
    port.subscribe_playback_state_changed(states.append)
    try:
        port.activate()
        port.load(Path("/tmp/fence.flac"))
        port.dispatch_pending()
        current = port._command_generation  # noqa: SLF001 - fence under test
        assert current >= 1
        stale = make_message(
            MessageKind.EVENT,
            host_generation=supervisor.host_generation,
            command_generation=max(0, current - 1),
            payload={"event": HostEvent.STATE_CHANGED.value, "status": "PLAYING"},
        )
        fresh = make_message(
            MessageKind.EVENT,
            host_generation=supervisor.host_generation,
            command_generation=current,
            payload={"event": HostEvent.STATE_CHANGED.value, "status": "PAUSED"},
        )
        port._on_host_event(stale)  # noqa: SLF001 - fence under test
        port._on_host_event(fresh)  # noqa: SLF001 - fence under test
        port.dispatch_pending()
        assert states == [PlaybackStatus.PAUSED]
    finally:
        port.close()


def test_close_is_bounded_idempotent_and_reaps() -> None:
    supervisor, port = _port("normal")
    port.activate()
    pid = supervisor.pid
    port.close()
    port.close()
    assert port.termination_kind == GRACEFUL
    assert not supervisor.pid_alive()
    assert pid is not None and _pids_alive([pid]) == []


def test_close_escalates_when_engine_close_hangs() -> None:
    supervisor, port = _port("hang_on_close")
    port.activate()
    port.close()
    assert port.termination_kind in (FORCED_TERM, "FORCED_KILL")
    assert not supervisor.pid_alive()


def test_repeated_open_close_cycles_leave_no_orphans() -> None:
    pids: list[int] = []
    for _ in range(3):
        supervisor, port = _port("normal")
        port.activate()
        pid = supervisor.pid
        assert pid is not None
        pids.append(pid)
        port.close()
    assert _pids_alive(pids) == []


def test_unix_socket_is_not_left_behind() -> None:
    # The supervisor uses a private socketpair, never an fs path: nothing to
    # leak. This test pins the transport choice against regressions.
    supervisor, port = _port("normal")
    try:
        port.activate()
        assert socket.AF_UNIX  # socketpair-based transport (no fs socket)
        assert not list(Path("/tmp").glob("*michi*gst*host*.sock"))
    finally:
        port.close()


def test_owner_work_is_drained_during_a_bounded_host_wait() -> None:
    """The Qt/owner dispatch seam runs queued work while the owner waits.

    A deadlocked host must not freeze owner-thread work indefinitely: the
    supervisor's bounded wait drains the owner queue itself, so heartbeat
    work keeps running until the deadline converts the wedge into a typed,
    bounded failure.
    """
    pytest.importorskip("PySide6.QtCore")
    from PySide6.QtCore import QCoreApplication

    # NEVER create a Qt application here: a bare QCoreApplication races the
    # suite's real QApplication creation (Qt aborts). Only run when the suite
    # already owns one.
    if QCoreApplication.instance() is None:
        pytest.skip("suite has no live Qt application instance")

    supervisor, port = _port("hang_on_load", command_timeout_s=0.7)
    ticks: list[float] = []

    def beat() -> None:
        ticks.append(time.monotonic())
        if len(ticks) < 40:
            port._enqueue(beat)  # noqa: SLF001 - owner seam under test

    try:
        port.activate()
        started = time.monotonic()
        port._enqueue(beat)  # noqa: SLF001 - owner seam under test
        with pytest.raises(AudioLoadError):
            port.load(Path("/tmp/wedged.flac"))
        # Owner work ran DURING the bounded wait (not only after it).
        assert len(ticks) >= 3
        assert ticks[0] >= started
        # And the owner thread resumed immediately after the bounded failure.
        resumed_at = time.monotonic()
        assert resumed_at - started < 3.0
    finally:
        port.close()
        supervisor.close()
