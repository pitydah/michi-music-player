"""Supervisor tests: bounded start, deadlines, kill/reap, generation fences.

Every test uses the deterministic fake host (scripted faults) so the
parent-side containment is proven independently of real GStreamer.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

import pytest

from michi.infrastructure.audio_engines.gstreamer_host_client import (
    FORCED_KILL,
    FORCED_TERM,
    GRACEFUL,
    GStreamerHostSupervisor,
    OutputHostLostError,
    OutputHostStartError,
    OutputHostTimeoutError,
    SupervisorState,
)
from michi.infrastructure.audio_engines.gstreamer_host_protocol import HostOperation

FAKE_HOST = Path(__file__).parent / "gst_host_fake.py"
FAST = {
    "start_timeout_s": 1.5,
    "command_timeout_s": 0.8,
    "terminate_grace_s": 0.3,
    "term_grace_s": 0.3,
    "kill_grace_s": 0.5,
}


def _supervisor(behavior: str, **overrides) -> GStreamerHostSupervisor:
    def factory(fd: int) -> list[str]:
        return [
            sys.executable,
            str(FAKE_HOST),
            "--fd",
            str(fd),
            "--behavior",
            behavior,
        ]

    options = dict(FAST)
    options.update(overrides)
    return GStreamerHostSupervisor(command_factory=factory, **options)


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


def test_start_handshake_reports_host_identity() -> None:
    supervisor = _supervisor("normal")
    try:
        hello = supervisor.start()
        assert supervisor.state is SupervisorState.READY
        assert hello["protocol_version"] == 1
        assert hello["gstreamer_version"] == "GStreamer fake-1.0"
        assert hello["playbin3_available"] is True
        assert supervisor.host_generation == 1
        assert supervisor.pid_alive()
        assert supervisor.ping()["pong"] is True
    finally:
        kind = supervisor.shutdown()
    assert kind == GRACEFUL
    assert supervisor.state is SupervisorState.STOPPED
    assert not supervisor.pid_alive()


def test_start_failure_crash_is_typed_and_reaped() -> None:
    supervisor = _supervisor("crash")
    with pytest.raises(OutputHostStartError) as info:
        supervisor.start()
    assert info.value.code == "OUTPUT_HOST_START_FAILED"
    assert not supervisor.pid_alive()
    assert supervisor.state is SupervisorState.FAILED


def test_start_failure_no_hello_times_out_and_kills() -> None:
    supervisor = _supervisor("no_hello")
    started = time.monotonic()
    with pytest.raises(OutputHostStartError):
        supervisor.start()
    assert time.monotonic() - started < 4.0
    assert not supervisor.pid_alive()
    assert supervisor.termination_kind in (FORCED_TERM, FORCED_KILL, GRACEFUL)


def test_start_failure_garbage_and_oversized_and_version() -> None:
    for behavior in ("garbage", "oversized", "wrong_version"):
        supervisor = _supervisor(behavior)
        with pytest.raises(OutputHostStartError):
            supervisor.start()
        assert not supervisor.pid_alive(), behavior
        supervisor.close()


def test_shutdown_hang_escalates_to_term() -> None:
    supervisor = _supervisor("hang_on:shutdown")
    supervisor.start()
    kind = supervisor.shutdown()
    assert kind == FORCED_TERM
    assert not supervisor.pid_alive()


def test_shutdown_sigterm_ignored_escalates_to_kill() -> None:
    supervisor = _supervisor("hang_on_shutdown_ignore_term")
    supervisor.start()
    kind = supervisor.shutdown()
    assert kind == FORCED_KILL
    assert not supervisor.pid_alive()


def test_command_deadline_kills_and_reaps_wedged_host() -> None:
    lost: list[tuple[int, str, str]] = []
    supervisor = _supervisor(
        "hang_on:ping",
        on_lost=lambda generation, code, detail: lost.append(
            (generation, code, detail)
        ),
    )
    supervisor.start()
    started = time.monotonic()
    with pytest.raises(OutputHostTimeoutError) as info:
        supervisor.ping()
    assert info.value.code == "OUTPUT_HOST_TIMEOUT"
    assert time.monotonic() - started < 3.0
    assert not supervisor.pid_alive()
    assert supervisor.state is SupervisorState.FAILED
    assert lost and lost[0][0] == 1 and lost[0][1] == "OUTPUT_HOST_TIMEOUT"


def test_host_crash_during_command_reports_lost() -> None:
    lost: list[tuple[int, str, str]] = []
    supervisor = _supervisor(
        "crash_after_ack",
        on_lost=lambda generation, code, detail: lost.append(
            (generation, code, detail)
        ),
    )
    supervisor.start()
    with pytest.raises(OutputHostLostError):
        supervisor.ping()
    assert lost and lost[0][1] == "OUTPUT_HOST_LOST"
    assert not supervisor.pid_alive()


def test_background_request_gets_typed_error_when_host_is_shut_down() -> None:
    supervisor = _supervisor("hang_on:ping")
    supervisor.start()
    errors: list[Exception] = []

    def worker() -> None:
        try:
            supervisor.ping()
        except Exception as exc:  # noqa: BLE001 - captured for assertion
            errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    time.sleep(0.15)
    supervisor.shutdown()
    thread.join(timeout=4.0)
    assert not thread.is_alive()
    assert errors and isinstance(errors[0], OutputHostLostError)
    assert not supervisor.pid_alive()


def test_wrong_response_generation_cannot_commit() -> None:
    supervisor = _supervisor("wrong_response_generation")
    supervisor.start()
    # The fake answers non-ping commands with host_generation+1; the
    # supervisor drops the frame, so the command can never succeed through a
    # stale generation.
    with pytest.raises(OutputHostTimeoutError):
        supervisor.submit(HostOperation.LOAD, {"path": "/tmp/x"})
    assert not supervisor.pid_alive()


def test_stale_events_are_dropped_and_counted() -> None:
    events: list[dict] = []
    supervisor = _supervisor("wrong_event_generation", on_event=events.append)
    supervisor.start()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        ticks = [
            event["payload"].get("tick")
            for event in events
            if event["payload"].get("event") == "host_heartbeat"
        ]
        if ticks and supervisor.diagnostics()["stale_events"] >= 1:
            break
        time.sleep(0.02)
    ticks = [
        event["payload"].get("tick")
        for event in events
        if event["payload"].get("event") == "host_heartbeat"
    ]
    assert ticks == [2]  # only the frame from the CURRENT generation arrives
    assert supervisor.diagnostics()["stale_events"] >= 1
    assert supervisor.shutdown() == GRACEFUL


def test_owner_threads_stay_responsive_while_host_hangs() -> None:
    supervisor = _supervisor("hang_on:ping", command_timeout_s=0.6)
    supervisor.start()
    ticks = 0
    stop = threading.Event()

    def ticker() -> None:
        nonlocal ticks
        while not stop.is_set():
            ticks += 1
            time.sleep(0.01)

    thread = threading.Thread(target=ticker)
    thread.start()
    try:
        with pytest.raises(OutputHostTimeoutError):
            supervisor.ping()
    finally:
        stop.set()
        thread.join(timeout=1.0)
    # The parent's other threads kept running during the whole host wedge.
    assert ticks >= 20
    assert not supervisor.pid_alive()


def test_repeated_spawn_cycles_leave_no_orphans_or_fd_growth() -> None:
    def fd_count() -> int:
        return len(os.listdir("/proc/self/fd"))

    before = fd_count()
    pids: list[int] = []
    for _ in range(4):
        supervisor = _supervisor("normal")
        supervisor.start()
        pid = supervisor.pid
        assert pid is not None
        pids.append(pid)
        supervisor.ping()
        assert supervisor.shutdown() == GRACEFUL
    assert _pids_alive(pids) == []
    assert fd_count() - before <= 4


def test_close_is_idempotent() -> None:
    supervisor = _supervisor("normal")
    supervisor.start()
    supervisor.close()
    supervisor.close()
    assert supervisor.state is SupervisorState.STOPPED
    assert not supervisor.pid_alive()


def test_runtime_protocol_violation_is_a_lost_host() -> None:
    lost: list[str] = []
    supervisor = _supervisor(
        "malformed_response",
        on_lost=lambda generation, code, detail: lost.append(code),
    )
    supervisor.start()
    with pytest.raises(OutputHostLostError):
        supervisor.ping()
    assert "OUTPUT_HOST_PROTOCOL_ERROR" in lost
    assert not supervisor.pid_alive()


def test_generation_increments_across_restarts() -> None:
    supervisor = _supervisor("normal")
    generations = []
    for _ in range(3):
        supervisor.start()
        generations.append(supervisor.host_generation)
        assert supervisor.shutdown() == GRACEFUL
    assert generations == [1, 2, 3]
