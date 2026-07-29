import logging

from integrations.snapcast.snapserver_manager import SnapServerManager


class FakeProcess:
    pid = 4321

    def __init__(self):
        self.terminated = False
        self.killed = False
        self.exit_code = None

    def poll(self):
        if self.terminated or self.killed:
            return 0
        return self.exit_code

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        return 0


def test_missing_binary_is_unavailable():
    manager = SnapServerManager(binary="")
    assert manager.state == "unavailable"
    assert manager.start()["error"] == "SNAPSERVER_BINARY_UNAVAILABLE"


def test_start_requires_control_readback_and_stop_owns_process(tmp_path, monkeypatch):
    probes = iter([False, True, False])
    process = FakeProcess()
    manager = SnapServerManager(
        binary="/bin/true",
        process_factory=lambda *_args, **_kwargs: process,
        readiness_probe=lambda *_args: next(probes),
        startup_timeout=0.2,
    )
    monkeypatch.setattr(manager, "_config_path", str(tmp_path / "snapserver.conf"))
    monkeypatch.setattr(manager, "_port_in_use", lambda *_args: False)

    started = manager.start()
    assert started == {"ok": True, "state": "running", "pid": 4321}
    assert manager.is_running is True

    stopped = manager.stop()
    assert stopped["ok"] is True
    assert process.terminated is True
    assert manager.state == "stopped"


def test_stop_does_not_terminate_foreign_server():
    manager = SnapServerManager(binary="/bin/true", readiness_probe=lambda *_args: True)
    result = manager.stop()
    assert result["error"] == "FOREIGN_SNAPSERVER_NOT_OWNED"


def test_start_rejects_occupied_port_without_launching(monkeypatch):
    launched = []
    manager = SnapServerManager(
        binary="/bin/true",
        process_factory=lambda *_args, **_kwargs: launched.append(True),
    )
    monkeypatch.setattr(manager, "_port_in_use", lambda *_args: True)

    result = manager.start()

    assert result["error"] == "SNAPSERVER_PORT_IN_USE"
    assert launched == []


def test_start_timeout_terminates_owned_process(tmp_path, monkeypatch):
    process = FakeProcess()
    manager = SnapServerManager(
        binary="/bin/true",
        process_factory=lambda *_args, **_kwargs: process,
        readiness_probe=lambda *_args: False,
        startup_timeout=0.1,
    )
    monkeypatch.setattr(manager, "_config_path", str(tmp_path / "snapserver.conf"))
    monkeypatch.setattr(manager, "_port_in_use", lambda *_args: False)

    result = manager.start()

    assert result["error"] == "SNAPSERVER_START_TIMEOUT"
    assert process.terminated is True


def test_restarts_after_owned_server_exits(qtbot, tmp_path, monkeypatch, caplog):
    first_process = FakeProcess()
    replacement_process = FakeProcess()
    processes = iter([first_process, replacement_process])
    manager = SnapServerManager(
        binary="/bin/true",
        process_factory=lambda *_args, **_kwargs: next(processes),
        readiness_probe=lambda *_args: True,
        startup_timeout=0.1,
    )
    monkeypatch.setattr(manager, "_config_path", str(tmp_path / "snapserver.conf"))
    monkeypatch.setattr(manager, "_port_in_use", lambda *_args: False)
    reconnected = []
    manager.reconnected.connect(lambda: reconnected.append(True))

    assert manager.start()["ok"] is True
    first_process.exit_code = 7
    with caplog.at_level(logging.INFO, logger="michi.snapserver"):
        manager._monitor_process()
        assert manager._reconnect_timer.interval() == 1_000
        manager._reconnect_timer.stop()
        manager._attempt_reconnect()

        qtbot.waitUntil(lambda: manager.is_running and bool(reconnected), timeout=1_000)

    assert manager.is_running is True
    assert reconnected == [True]
    assert "Snapserver reconnection attempt" in caplog.text


def test_reconnect_backoff_is_exponential_and_capped(qtbot):
    manager = SnapServerManager(binary="/bin/true")
    manager._should_run = True
    delays = []

    for _ in range(7):
        manager._schedule_reconnect()
        delays.append(manager._reconnect_timer.interval())
        manager._reconnect_timer.stop()

    assert delays == [1_000, 2_000, 4_000, 8_000, 16_000, 30_000, 30_000]
