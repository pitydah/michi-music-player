"""Bounded discovery: manual start/stop, session deadline and real states."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from michi.integration.ecosystem_host import DiscoveryControl
from michi_ecosystem.application.discovery_runner import DiscoveryRunner


class _Source:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.polls = 0
        self.threads: list[int] = []
        self.gate = threading.Event()
        self.block = False

    def poll(self) -> int:
        self.threads.append(threading.get_ident())
        self.polls += 1
        if self.block:
            self.gate.wait(1.0)
        if self.fail:
            raise OSError("network down")
        return 0

    def ui_state(self) -> str:
        return "idle"


def _wait_stopped(runner: DiscoveryRunner, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while runner.running and time.monotonic() < deadline:
        time.sleep(0.01)


def test_session_deadline_stops_the_worker_without_an_explicit_stop():
    source = _Source()
    runner = DiscoveryRunner(source, interval_seconds=0.02, max_session_seconds=0.12)
    assert runner.start() is True
    _wait_stopped(runner)
    health = runner.health()
    assert health["expired"] is True
    assert health["sessionState"] == "expired"
    assert health["running"] is False
    assert health["maxSessionSeconds"] == 0.12


def test_repeated_manual_start_and_stop_cycles():
    source = _Source()
    runner = DiscoveryRunner(source, interval_seconds=0.02, max_session_seconds=30)
    for _ in range(3):
        assert runner.start() is True
        assert runner.running is True
        assert runner.stop() is True
        assert runner.running is False
    assert runner.stop() is True


def test_slow_worker_reports_stop_timeout_and_can_be_released():
    source = _Source()
    source.block = True
    runner = DiscoveryRunner(source, interval_seconds=0.02, max_session_seconds=30)
    assert runner.start() is True
    deadline = time.monotonic() + 1.0
    while source.polls == 0 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runner.stop(timeout=0.01) is False
    assert runner.running is True
    source.gate.set()
    assert runner.stop(timeout=1.0) is True
    assert runner.running is False


def test_polling_never_runs_on_the_calling_thread():
    source = _Source()
    runner = DiscoveryRunner(source, interval_seconds=0.01, max_session_seconds=30)
    caller = threading.get_ident()
    assert runner.start() is True
    deadline = time.monotonic() + 1.0
    while not source.threads and time.monotonic() < deadline:
        time.sleep(0.01)
    runner.stop()
    assert source.threads
    assert all(thread != caller for thread in source.threads)


def test_network_failure_is_reported_as_error_state():
    source = _Source(fail=True)
    runner = DiscoveryRunner(source, interval_seconds=0.01, max_session_seconds=30)
    runner.start()
    deadline = time.monotonic() + 1.0
    while runner.health()["errors"] == 0 and time.monotonic() < deadline:
        time.sleep(0.01)
    runner.stop()
    health = runner.health()
    assert health["errors"] > 0
    assert health["sessionState"] == "error"
    assert health["lastError"] == "OSError"


class _Runtime:
    def __init__(self, health: dict) -> None:
        self._health = health
        self.discovery_runner = None

    def availability(self) -> dict:
        return {
            "discovery": {"available": True, "running": False, "health": self._health}
        }


def test_discovery_control_maps_real_session_states():
    assert DiscoveryControl(_Runtime({"sessionState": "expired"})).state == "expired"
    assert DiscoveryControl(_Runtime({"sessionState": "error"})).state == "error"
    assert DiscoveryControl(_Runtime({"sessionState": "stopped"})).state == "stopped"


def test_control_stop_does_not_block_the_calling_thread():
    source = _Source()
    source.block = True
    runner = DiscoveryRunner(source, interval_seconds=0.02, max_session_seconds=30)

    class _Runtime:
        discovery_runner = runner

        def availability(self):
            return {
                "discovery": {
                    "available": True,
                    "running": runner.running,
                    "health": runner.health(),
                }
            }

        def start(self):
            return runner.start()

    control = DiscoveryControl(_Runtime())
    assert control.start() is True
    deadline = time.monotonic() + 1.0
    while source.polls == 0 and time.monotonic() < deadline:
        time.sleep(0.01)
    started = time.monotonic()
    control.stop()
    assert time.monotonic() - started < 0.6
    source.gate.set()
    _wait_stopped(runner)


def test_factory_package_has_no_discovery_timer():
    source = Path("src/michi/integration/ecosystem_host.py").read_text()
    page = Path(
        "src/michi/presentation/qml/ecosystem/discovery/DiscoveryPage.qml"
    ).read_text()
    assert "QTimer" not in source
    assert "QTimer" not in page
