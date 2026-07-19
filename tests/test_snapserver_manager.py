from integrations.snapcast.snapserver_manager import SnapServerManager


class FakeProcess:
    pid = 4321

    def __init__(self):
        self.terminated = False
        self.killed = False

    def poll(self):
        return 0 if self.terminated or self.killed else None

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
