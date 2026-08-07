"""MPD owned-process lifecycle: start -> PROCESS_STARTED -> SERVICE_CONNECTED.

Uses a fake MPD binary (a minimal MPD-protocol TCP listener) so the test is
hermetic: no real MPD daemon is required. Verifies:
  - PROCESS_STARTED vs SERVICE_CONNECTED are distinct states
  - port-busy (external instance) detection before spawning
  - stop() only terminates the process WE spawned (external listener untouched)
  - PID cleanup after unexpected exit
"""
from __future__ import annotations

import os
import signal
import socket
import sys
import time
from pathlib import Path

import pytest

from audio.mpd.mpd_config_builder import MpdConfig
from audio.mpd.mpd_service_manager import (
    MpdServiceManager,
    MpdServiceState,
)
from core.process_controller import ProcessController

FAKE_MPD_SCRIPT = r"""#!/usr/bin/env python3
import os, re, signal, socket, sys, threading

if sys.argv[1] == "--no-daemon":
    conf = open(sys.argv[2]).read()
    port = int(re.search(r'port\s+"(\d+)"', conf).group(1))
else:
    port = int(sys.argv[1])
pid_file = sys.argv[-1]
stop = threading.Event()

def _term(*_):
    stop.set()

signal.signal(signal.SIGTERM, _term)
signal.signal(signal.SIGINT, _term)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("127.0.0.1", port))
sock.listen(4)
with open(pid_file, "w") as f:
    f.write(str(os.getpid()))

def handle(conn):
    try:
        conn.sendall(b"OK MPD 0.23.0 fake\n")
        while not stop.is_set():
            data = conn.recv(4096)
            if not data:
                break
            for _ in data.splitlines():
                conn.sendall(b"OK\n")
    except OSError:
        pass
    finally:
        try:
            conn.close()
        except OSError:
            pass

sock.settimeout(0.5)
while not stop.is_set():
    try:
        conn, _ = sock.accept()
    except socket.timeout:
        continue
    except OSError:
        break
    threading.Thread(target=handle, args=(conn,), daemon=True).start()
sock.close()
"""


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture()
def fake_binary(tmp_path) -> Path:
    script = tmp_path / "fake_mpd.py"
    script.write_text(FAKE_MPD_SCRIPT, encoding="utf-8")
    script.chmod(0o755)
    return script


def _spawn_fake_mpd(script: Path, port: int, pid_file: Path) -> int:
    proc = __import__("subprocess").Popen(
        [sys.executable, str(script), str(port), str(pid_file)],
        stdout=__import__("subprocess").DEVNULL,
        stderr=__import__("subprocess").DEVNULL,
    )
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if pid_file.exists() and pid_file.read_text().strip():
            return int(pid_file.read_text().strip())
        if proc.poll() is not None:
            raise RuntimeError("fake mpd exited early")
        time.sleep(0.05)
    raise RuntimeError("fake mpd did not write pid file")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


class TestMpdOwnedProcessLifecycle:
    def test_start_reaches_service_connected(self, fake_binary, tmp_path):
        port = _free_port()
        pid_file = tmp_path / "fake.pid"
        mgr = MpdServiceManager(
            data_dir=str(tmp_path),
            mpd_binary=str(fake_binary),
            process_controller=ProcessController(),
            port=port,
        )
        assert mgr.state == MpdServiceState.IDLE.value
        assert mgr.start(MpdConfig(audio_outputs=[], port=port), timeout=8.0) is True
        assert mgr.state == MpdServiceState.SERVICE_CONNECTED.value
        assert mgr.pid > 0
        assert mgr.running
        status = mgr.get_status()
        assert status["process_started"] is True
        assert status["service_connected"] is True
        mgr.stop()
        assert mgr.state == MpdServiceState.STOPPED.value
        assert not mgr.running

    def test_start_sets_process_started_before_service_connected(
            self, fake_binary, tmp_path):
        port = _free_port()
        mgr = MpdServiceManager(
            data_dir=str(tmp_path),
            mpd_binary=str(fake_binary),
            process_controller=ProcessController(),
            port=port,
        )
        assert mgr.start(MpdConfig(audio_outputs=[], port=port), timeout=8.0) is True
        # Both distinct states were observable during the flow.
        assert mgr.state == MpdServiceState.SERVICE_CONNECTED.value
        assert mgr.get_status()["process_started"] is True
        mgr.stop()

    def test_external_instance_port_busy_detected(self, fake_binary, tmp_path):
        port = _free_port()
        ext_pid_file = tmp_path / "external.pid"
        external_pid = _spawn_fake_mpd(fake_binary, port, ext_pid_file)
        try:
            mgr = MpdServiceManager(
                data_dir=str(tmp_path),
                mpd_binary=str(fake_binary),
                process_controller=ProcessController(),
                port=port,
            )
            assert mgr.start(MpdConfig(audio_outputs=[], port=port), timeout=5.0) is False
            assert mgr.state == MpdServiceState.EXTERNAL_INSTANCE.value
            assert mgr.pid == 0
            assert _pid_alive(external_pid), "external instance must be untouched"
        finally:
            os.kill(external_pid, signal.SIGTERM)

    def test_stop_only_terminates_own_process(self, fake_binary, tmp_path):
        port = _free_port()
        mgr = MpdServiceManager(
            data_dir=str(tmp_path),
            mpd_binary=str(fake_binary),
            process_controller=ProcessController(),
            port=port,
        )
        assert mgr.start(MpdConfig(audio_outputs=[], port=port), timeout=8.0) is True
        own_pid = mgr.pid
        assert own_pid > 0 and _pid_alive(own_pid)

        # Spawn an unrelated external listener on ANOTHER port; stop() must
        # never touch it (it is not our tracked process).
        other_port = _free_port()
        other_pid_file = tmp_path / "other.pid"
        other_pid = _spawn_fake_mpd(fake_binary, other_port, other_pid_file)
        try:
            mgr.stop()
            assert not _pid_alive(own_pid), "own process must be stopped"
            assert _pid_alive(other_pid), "external process must survive stop()"
            assert mgr.pid == 0
        finally:
            os.kill(other_pid, signal.SIGTERM)

    def test_pid_cleanup_after_unexpected_exit(self, fake_binary, tmp_path):
        port = _free_port()
        mgr = MpdServiceManager(
            data_dir=str(tmp_path),
            mpd_binary=str(fake_binary),
            process_controller=ProcessController(),
            port=port,
        )
        assert mgr.start(MpdConfig(audio_outputs=[], port=port), timeout=8.0) is True
        own_pid = mgr.pid
        assert own_pid > 0
        # Kill the daemon out from under the manager (simulated crash).
        os.kill(own_pid, signal.SIGKILL)
        deadline = time.monotonic() + 5.0
        while _pid_alive(own_pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not mgr.running, "unexpected exit must be detected"
        assert mgr.pid == 0, "PID bookkeeping must be cleaned up"
        assert not Path(tmp_path / "mpd.pid").exists(), "pid file must be removed"

    def test_start_after_stop_restarts(self, fake_binary, tmp_path):
        port = _free_port()
        mgr = MpdServiceManager(
            data_dir=str(tmp_path),
            mpd_binary=str(fake_binary),
            process_controller=ProcessController(),
            port=port,
        )
        assert mgr.start(MpdConfig(audio_outputs=[], port=port), timeout=8.0) is True
        first_pid = mgr.pid
        mgr.stop()
        assert mgr.start(MpdConfig(audio_outputs=[], port=port), timeout=8.0) is True
        assert mgr.state == MpdServiceState.SERVICE_CONNECTED.value
        assert mgr.pid > 0
        assert mgr.pid != first_pid
        mgr.stop()
