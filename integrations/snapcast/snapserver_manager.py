"""Owned local Snapserver lifecycle with control-endpoint readiness checks."""

from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from core.paths import app_config_dir
from integrations.snapcast.json_rpc_client import SnapcastJsonRpcClient

SNAPSERVER_BIN = shutil.which("snapserver") or ""
logger = logging.getLogger("michi.snapserver")
_RECONNECT_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="michi-snapserver-reconnect",
)

# Canonical Snapserver lifecycle states.
# The lifecycle distinguishes three idle/terminal conditions so consumers can
# tell them apart instead of conflating them:
#   - STATE_OFFLINE      ("stopped")      not running by choice; can be started
#   - STATE_UNAVAILABLE  ("unavailable")  snapserver binary missing; cannot run
#   - STATE_FAILED       ("error")        run attempted but failed; reconnect scheduled
# STATE_STARTING/STATE_RUNNING are the transient/healthy active states.
STATE_OFFLINE = "stopped"
STATE_UNAVAILABLE = "unavailable"
STATE_FAILED = "error"
STATE_STARTING = "starting"
STATE_RUNNING = "running"

DEFAULT_CONFIG = """\
[server]
tcp_port = {tcp}
control_port = {ctrl}
http_port = {http}
stream = pipe://{fifo}?name=michi&codec=flac&sampleformat=44100:16:2
"""


class SnapServerManager(QObject):
    """Start and stop only the Snapserver process owned by Michi."""

    started = Signal()
    stopped = Signal()
    state_changed = Signal(str)
    error_occurred = Signal(str)
    server_ready = Signal(int, int)
    reconnected = Signal()
    _reconnect_attempt_finished = Signal(object)

    def __init__(
        self,
        parent=None,
        *,
        binary: str | None = None,
        process_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
        readiness_probe: Callable[[str, int, float], bool] | None = None,
        startup_timeout: float = 5.0,
    ):
        super().__init__(parent)
        self._binary = binary if binary is not None else (shutil.which("snapserver") or "")
        self._process_factory = process_factory
        self._readiness_probe = readiness_probe or self._probe_control
        self._startup_timeout = max(0.1, float(startup_timeout))
        self._process: subprocess.Popen | None = None
        self._state = STATE_OFFLINE if self._binary else STATE_UNAVAILABLE
        self._tcp_port = 1704
        self._control_port = 1705
        self._http_port = 1780
        self._config_path = str(Path(app_config_dir()) / "snapserver.conf")
        self._last_error = ""
        self._lock = threading.RLock()
        self._should_run = False
        self._next_reconnect_ms = 1_000
        self._reconnect_future: Future | None = None
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._attempt_reconnect)
        self._reconnect_attempt_finished.connect(self._on_reconnect_attempt_finished)
        self._monitor_timer = QTimer(self)
        self._monitor_timer.setInterval(1_000)
        self._monitor_timer.timeout.connect(self._monitor_process)
        self._monitor_timer.start()

    @property
    def state(self) -> str:
        self._reconcile_process()
        return self._state

    @property
    def is_running(self) -> bool:
        self._reconcile_process()
        return self._state == STATE_RUNNING and self._process is not None

    @property
    def pid(self) -> int:
        return int(self._process.pid) if self._process is not None else 0

    @property
    def tcp_port(self) -> int:
        return self._tcp_port

    @property
    def control_port(self) -> int:
        return self._control_port

    @property
    def http_port(self) -> int:
        return self._http_port

    @property
    def last_error(self) -> str:
        return self._last_error

    def is_binary_available(self) -> bool:
        return bool(self._binary and os.access(self._binary, os.X_OK))

    def configure(self, tcp: int = 1704, ctrl: int = 1705, http: int = 1780) -> dict:
        if any(int(port) <= 0 or int(port) > 65535 for port in (tcp, ctrl, http)):
            return {"ok": False, "error": "INVALID_PORT"}
        if self._process is not None:
            return {"ok": False, "error": "SERVER_RUNNING"}
        self._tcp_port = int(tcp)
        self._control_port = int(ctrl)
        self._http_port = int(http)
        return {"ok": True}

    def _set_state(self, state: str, error: str = "") -> None:
        self._state = state
        self._last_error = error
        self.state_changed.emit(state)
        if error:
            self.error_occurred.emit(error)

    def _reconcile_process(self) -> None:
        process = self._process
        if process is None or self._state not in {STATE_STARTING, STATE_RUNNING}:
            return
        exit_code = process.poll()
        if exit_code is not None:
            self._process = None
            self._set_state(STATE_FAILED, f"SNAPSERVER_EXITED: {exit_code}")
            self._schedule_reconnect()

    def _monitor_process(self) -> None:
        """Detect an unexpected exit of the owned Snapserver process."""
        self._reconcile_process()

    def _schedule_reconnect(self) -> None:
        if not self._should_run or self._reconnect_timer.isActive():
            return
        delay_ms = self._next_reconnect_ms
        self._next_reconnect_ms = min(delay_ms * 2, 30_000)
        logger.warning(
            "Snapserver unavailable; scheduling reconnection in %.1fs",
            delay_ms / 1_000,
        )
        self._reconnect_timer.start(delay_ms)

    def _attempt_reconnect(self) -> None:
        if not self._should_run:
            return
        if self._reconnect_future is not None and not self._reconnect_future.done():
            return
        logger.info("Snapserver reconnection attempt")
        self._reconnect_future = _RECONNECT_EXECUTOR.submit(self.start)
        self._reconnect_future.add_done_callback(
            self._reconnect_attempt_finished.emit
        )

    def _on_reconnect_attempt_finished(self, future: Future) -> None:
        try:
            result = future.result()
        except Exception:
            logger.exception("Snapserver reconnection attempt failed")
            result = {"ok": False}
        if result.get("ok"):
            logger.info("Snapserver reconnected")
            self.reconnected.emit()
            return
        self._schedule_reconnect()

    @staticmethod
    def _probe_control(host: str, port: int, timeout: float) -> bool:
        return SnapcastJsonRpcClient(host, port, timeout=timeout).ping()

    @staticmethod
    def _port_in_use(host: str, port: int, timeout: float = 0.2) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def _write_config(self) -> str:
        path = Path(self._config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        from integrations.snapcast.fifo_manager import ensure_fifo, fifo_path
        ensure_fifo()
        path.write_text(
            DEFAULT_CONFIG.format(
                tcp=self._tcp_port,
                ctrl=self._control_port,
                http=self._http_port,
                fifo=fifo_path(),
            ),
            encoding="utf-8",
        )
        return str(path)

    def start(self) -> dict:
        """Start the owned process and wait for verified JSON-RPC readiness.

        This method blocks during readiness polling and must be dispatched through
        WorkerManager by UI callers.
        """
        with self._lock:
            if self.is_running:
                self._should_run = True
                return {"ok": True, "state": STATE_RUNNING, "pid": self.pid, "already_running": True}
            if not self.is_binary_available():
                self._set_state(STATE_UNAVAILABLE, "SNAPSERVER_BINARY_UNAVAILABLE")
                return {"ok": False, "error": "SNAPSERVER_BINARY_UNAVAILABLE", "state": self._state}
            if self._port_in_use("127.0.0.1", self._control_port):
                self._set_state(STATE_FAILED, "SNAPSERVER_PORT_IN_USE")
                return {"ok": False, "error": "SNAPSERVER_PORT_IN_USE", "state": self._state}
            try:
                config_path = self._write_config()
                self._process = self._process_factory(
                    [self._binary, "-c", config_path],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except (OSError, ValueError) as exc:
                self._process = None
                self._set_state(STATE_FAILED, f"SNAPSERVER_START_FAILED: {exc}")
                return {"ok": False, "error": "SNAPSERVER_START_FAILED", "message": str(exc)}
            self._set_state(STATE_STARTING)

        deadline = time.monotonic() + self._startup_timeout
        while time.monotonic() < deadline:
            process = self._process
            if process is None:
                break
            exit_code = process.poll()
            if exit_code is not None:
                self._process = None
                self._set_state(STATE_FAILED, f"SNAPSERVER_EXITED: {exit_code}")
                return {"ok": False, "error": "SNAPSERVER_EXITED", "exit_code": exit_code}
            if self._readiness_probe("127.0.0.1", self._control_port, 0.25):
                self._set_state(STATE_RUNNING)
                self._should_run = True
                self._next_reconnect_ms = 1_000
                self.started.emit()
                self.server_ready.emit(self._tcp_port, self._control_port)
                return {"ok": True, "state": STATE_RUNNING, "pid": self.pid}
            threading.Event().wait(0.1)

        self._terminate_owned()
        self._set_state(STATE_FAILED, "SNAPSERVER_START_TIMEOUT")
        return {"ok": False, "error": "SNAPSERVER_START_TIMEOUT", "state": self._state}

    def _terminate_owned(self, timeout: float = 2.0) -> None:
        process = self._process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=timeout)
        self._process = None

    def stop(self) -> dict:
        """Stop only the process created by this manager."""
        with self._lock:
            self._should_run = False
            self._reconnect_timer.stop()
            if self._process is None:
                if self._readiness_probe("127.0.0.1", self._control_port, 0.2):
                    return {"ok": False, "error": "FOREIGN_SNAPSERVER_NOT_OWNED", "state": self._state}
                # Distinguish offline from unavailable: a binary-less manager
                # cannot run, so it must stay unavailable instead of being
                # downgraded to offline ("stopped").
                if not self.is_binary_available():
                    self._set_state(STATE_UNAVAILABLE, "SNAPSERVER_BINARY_UNAVAILABLE")
                else:
                    self._set_state(STATE_OFFLINE)
                return {"ok": True, "state": self._state, "already_stopped": True}
            try:
                self._terminate_owned()
            except (OSError, subprocess.SubprocessError) as exc:
                self._set_state(STATE_FAILED, f"SNAPSERVER_STOP_FAILED: {exc}")
                return {"ok": False, "error": "SNAPSERVER_STOP_FAILED", "message": str(exc)}
            self._set_state(STATE_OFFLINE)
            self.stopped.emit()
            return {"ok": True, "state": STATE_OFFLINE}
