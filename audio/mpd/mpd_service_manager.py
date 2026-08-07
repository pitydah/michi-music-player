"""MPD Service Manager — manages a local MPD process.

Can start, stop, restart, and check status of a local MPD instance.
Uses a lifecycle-managed subprocess (``core.process_controller``) to launch
mpd with a custom config file — daemon spawning never happens through a bare
``subprocess`` call in this module.
Does NOT require root — runs as the current user with a data dir in
~/.local/share.

Lifecycle states: ``idle -> starting -> process_started -> service_connected``
(or ``port_busy`` / ``external_instance`` / ``failed``). ``PROCESS_STARTED``
means our daemon process is alive; ``SERVICE_CONNECTED`` means the MPD port
answers our ping. Port-busy detection distinguishes an external MPD instance
from our own managed daemon. The daemon port is pre-checked before spawn, and
``stop()`` ONLY terminates the process started by this instance — external
instances are never touched. All waits are bounded by an explicit timeout
(short polls, never unbounded ``time.sleep``).
"""

import logging
import os
import shutil
import time
from enum import Enum

from core.process_controller import ProcessController
from audio.mpd.mpd_client import MpdClient
from audio.mpd.mpd_errors import MpdConnectionError
from audio.mpd.mpd_config_builder import (
    write_mpd_conf,
    default_data_dir,
)

logger = logging.getLogger("michi.mpd.service")

POLL_INTERVAL_SECONDS = 0.2
DEFAULT_READY_TIMEOUT = 10.0


class MpdServiceState(str, Enum):
    """Service lifecycle states — distinct process vs connection states."""

    IDLE = "idle"
    STARTING = "starting"
    PROCESS_STARTED = "process_started"
    SERVICE_CONNECTED = "service_connected"
    PORT_BUSY = "port_busy"
    EXTERNAL_INSTANCE = "external_instance"
    FAILED = "failed"
    STOPPED = "stopped"


class MpdServiceManager:
    """Controls a local MPD instance for Michi Music Player."""

    def __init__(self, data_dir: str = "", mpd_binary: str = "",
                 process_controller: ProcessController | None = None,
                 host: str = "127.0.0.1", port: int = 6600):
        self._data_dir = data_dir or default_data_dir()
        self._mpd_binary = mpd_binary or self._find_mpd()
        self._controller = process_controller or ProcessController()
        self._config_path = os.path.join(self._data_dir, "mpd.conf")
        self._pid_file = os.path.join(self._data_dir, "mpd.pid")
        self._pid: int = 0
        self._last_error: str = ""
        self._log_file: str = os.path.join(self._data_dir, "mpd.log")
        self._state: MpdServiceState = MpdServiceState.IDLE
        self._host = host
        self._port = int(port)

    @property
    def running(self) -> bool:
        """True while our tracked daemon process is alive."""
        if self._pid and self._controller.is_alive(self._pid):
            return True
        if self._pid:
            # Unexpected exit: clean up the tracked PID and state.
            self._controller.cleanup_sync(self._pid)
            self._pid = 0
            self._remove_pid_file()
            if self._state in (MpdServiceState.PROCESS_STARTED,
                               MpdServiceState.SERVICE_CONNECTED,
                               MpdServiceState.STARTING):
                self._state = MpdServiceState.STOPPED
        return False

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def config_path(self) -> str:
        return self._config_path

    @property
    def pid(self) -> int:
        return self._pid

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def log_file(self) -> str:
        return self._log_file

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @staticmethod
    def is_installed() -> bool:
        return shutil.which("mpd") is not None

    def _binary_available(self) -> bool:
        """True when the configured binary exists or is resolvable on PATH."""
        if self._mpd_binary and os.path.exists(self._mpd_binary):
            return True
        if self._mpd_binary and shutil.which(self._mpd_binary):
            return True
        return shutil.which("mpd") is not None

    @staticmethod
    def _find_mpd() -> str:
        return shutil.which("mpd") or "/usr/bin/mpd"

    # ── Port pre-check: detect an external instance before spawning ─────

    def probe_port(self, timeout: float = 1.0) -> tuple[bool, str]:
        """Try to reach an MPD on the configured port.

        Returns ``(True, ...)`` when an MPD service already answers — that is
        an EXTERNAL instance (or a stale managed one) that must not be
        confused with the daemon we spawn.
        """
        client = MpdClient(host=self._host, port=self._port, timeout=timeout)
        try:
            client.connect()
            client.ping()
            client.disconnect()
            return True, "MPD externo respondiendo en el puerto configurado"
        except MpdConnectionError as e:
            return False, str(e)

    # ── Lifecycle ───────────────────────────────────────────────────────

    def start(self, config, timeout: float = DEFAULT_READY_TIMEOUT) -> bool:
        """Start a local MPD instance with the given config.

        Flow: pre-check port -> spawn via ProcessController (PROCESS_STARTED)
        -> bounded readiness polling (SERVICE_CONNECTED). Returns True only
        when the service is connected and answering ping.
        """
        if self.running:
            logger.warning("MPD already running (pid %d)", self._pid)
            return True

        if not self._binary_available():
            self._set_error("MPD binary not found")
            self._state = MpdServiceState.FAILED
            return False

        config_path = self._config_path
        if hasattr(config, "audio_outputs"):
            config_path = write_mpd_conf(config, self._config_path)
        elif isinstance(config, str):
            config_path = config
        else:
            self._set_error("Invalid config argument")
            self._state = MpdServiceState.FAILED
            return False

        # Port pre-check: an external MPD on the port means we must NOT spawn
        # a second daemon (port-busy detection, before any process exists).
        port_ok, port_msg = self.probe_port()
        if port_ok:
            self._set_error(f"Puerto {self._port} ocupado por MPD externo")
            self._state = MpdServiceState.EXTERNAL_INSTANCE
            return False

        self._state = MpdServiceState.STARTING
        self._last_error = ""
        log_handle = self._open_log_handle()
        try:
            managed = self._controller.spawn_sync(
                self._mpd_binary,
                args=["--no-daemon", config_path],
                stdout=log_handle,
                stderr=log_handle,
            )
        except OSError as e:
            self._set_error(f"Failed to start MPD: {e}")
            self._state = MpdServiceState.FAILED
            return False
        if managed is None or managed.pid <= 0:
            self._set_error(f"Failed to spawn MPD ({self._mpd_binary})")
            self._state = MpdServiceState.FAILED
            return False

        self._pid = managed.pid
        self._write_pid_file(self._pid)
        # PROCESS_STARTED: our daemon process is alive (checked via poll).
        if not self._wait_process_started(managed, timeout):
            self._state = MpdServiceState.FAILED
            self._last_error = self._last_error or (
                f"MPD exited immediately (check {config_path})")
            self._read_log_tail()
            self._cleanup_after_dead_process()
            return False
        self._state = MpdServiceState.PROCESS_STARTED
        logger.info("MPD process started (pid %d)", self._pid)

        # SERVICE_CONNECTED: bounded readiness polling of the TCP port.
        if self._wait_service_ready(managed, timeout):
            self._state = MpdServiceState.SERVICE_CONNECTED
            self._last_error = ""
            logger.info("MPD service connected (pid %d)", self._pid)
            return True

        if managed.poll() is not None:
            # Our process died; check whether something else now owns the port.
            self._read_log_tail()
            port_ok, _ = self.probe_port()
            self._state = (
                MpdServiceState.EXTERNAL_INSTANCE
                if port_ok else MpdServiceState.FAILED
            )
            self._last_error = self._last_error or (
                f"MPD no respondió en {timeout}s (pid {self._pid})")
            self._cleanup_after_dead_process()
        else:
            self._last_error = (
                f"MPD proceso vivo pero sin servicio en el puerto "
                f"{self._port} tras {timeout}s")
        return False

    def _wait_process_started(self, managed, timeout: float) -> bool:
        """Bounded poll until the process is alive or it exits."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            code = managed.poll()
            if code is None:
                return True
            self._last_error = f"MPD exited with code {code}"
            return False
        return managed.poll() is None

    def _wait_service_ready(self, managed, timeout: float) -> bool:
        """Bounded ping polling; short waits only, never unbounded sleep."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if managed.poll() is not None:
                return False
            ok, _ = self.test_connection(timeout=1.0)
            if ok:
                return True
            time.sleep(POLL_INTERVAL_SECONDS)
        return False

    def stop(self) -> bool:
        """Stop the local MPD instance.

        ONLY terminates the process started by this instance (tracked PID).
        External MPD instances are never touched; no pkill/killall.
        """
        if self._pid:
            if self._controller.is_alive(self._pid):
                if self._controller.terminate_sync(self._pid, timeout=5.0):
                    logger.info("MPD stopped (pid %d)", self._pid)
                else:
                    logger.warning("MPD pid %d did not stop; killing", self._pid)
                # Drop tracking (kills only when still alive — own process).
                self._controller.cleanup_sync(self._pid)
            else:
                # Tracked PID already gone — clean bookkeeping only; external
                # daemons on the port are never touched.
                self._controller.cleanup_sync(self._pid)
            self._pid = 0
            self._remove_pid_file()
            self._state = MpdServiceState.STOPPED
            return True
        self._state = MpdServiceState.STOPPED
        logger.debug("No MPD process to stop")
        return True

    def restart(self, config=None, timeout: float = DEFAULT_READY_TIMEOUT) -> bool:
        """Restart MPD with optional new config (bounded waits only)."""
        self.stop()
        return self.start(config or self._config_path, timeout=timeout)

    def test_connection(self, host: str = "",
                        port: int = 0, timeout: float = 3.0) -> tuple[bool, str]:
        """Test connection to the MPD instance (used for readiness polling)."""
        client = MpdClient(host=host or self._host,
                           port=port or self._port, timeout=timeout)
        try:
            client.connect()
            client.ping()
            client.disconnect()
            return True, "Connected successfully"
        except MpdConnectionError as e:
            self._last_error = str(e)
            return False, str(e)

    def get_status(self) -> dict:
        """Return dict with service status info (honest, derived from state)."""
        return {
            "installed": self.is_installed(),
            "running": self.running,
            "state": self.state,
            "process_started": self._pid != 0 and self._controller.is_alive(self._pid),
            "service_connected": self._state == MpdServiceState.SERVICE_CONNECTED
            and self.running,
            "binary": self._mpd_binary,
            "data_dir": self._data_dir,
            "config_path": self._config_path,
            "pid": self._pid,
            "host": self._host,
            "port": self._port,
            "last_error": self._last_error,
            "log_file": self._log_file,
        }

    def health(self) -> dict:
        status = self.get_status()
        return {
            "available": bool(status["installed"]),
            "running": status["running"],
            "state": status["state"],
            "reasons": (
                [] if status["running"]
                else [status["last_error"] or "mpd_not_running"]
            ),
        }

    def _read_port(self) -> int:
        """Read port from config file (legacy helper, kept for tests)."""
        try:
            with open(self._config_path) as f:
                for line in f:
                    if "port" in line and '"' in line:
                        return int(line.split('"')[1])
        except (OSError, ValueError, IndexError):
            pass
        return self._port

    def _write_pid_file(self, pid: int) -> None:
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            with open(self._pid_file, "w") as f:
                f.write(str(pid))
        except OSError as e:
            logger.debug("pid file write failed: %s", e)

    def _remove_pid_file(self) -> None:
        try:
            if os.path.exists(self._pid_file):
                os.unlink(self._pid_file)
        except OSError as e:
            logger.debug("pid file remove failed: %s", e)

    def _open_log_handle(self):
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            return open(self._log_file, "a", encoding="utf-8")
        except OSError:
            return None

    def _cleanup_after_dead_process(self) -> None:
        self._controller.cleanup_sync(self._pid)
        self._pid = 0
        self._remove_pid_file()

    def _set_error(self, message: str) -> None:
        self._last_error = message
        logger.error(message)

    def _read_log_tail(self):
        """Read last lines of MPD log for diagnostics."""
        try:
            if os.path.exists(self._log_file):
                with open(self._log_file) as f:
                    lines = f.readlines()
                tail = "".join(lines[-10:])
                if tail.strip():
                    logger.warning("MPD log tail:\n%s", tail)
        except OSError:
            pass
