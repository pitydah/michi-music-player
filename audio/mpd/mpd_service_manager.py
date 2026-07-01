"""MPD Service Manager — manages a local MPD process.

Can start, stop, restart, and check status of a local MPD instance.
Uses subprocess to launch mpd with a custom config file.
Does NOT require root — runs as the current user with a data dir in ~/.local/share.

SAFETY: stop() ONLY terminates the process started by this instance.
It does NOT use pkill/killall to avoid killing external MPD instances.
"""

import logging
import os
import shutil
import signal
import subprocess
import time

from audio.mpd.mpd_client import MpdClient
from audio.mpd.mpd_errors import MpdConnectionError
from audio.mpd.mpd_config_builder import (
    write_mpd_conf,
    default_data_dir,
)

logger = logging.getLogger("michi.mpd.service")


class MpdServiceManager:
    """Controls a local MPD instance for Michi Music Player."""

    def __init__(self, data_dir: str = "", mpd_binary: str = ""):
        self._data_dir = data_dir or default_data_dir()
        self._mpd_binary = mpd_binary or self._find_mpd()
        self._process: subprocess.Popen | None = None
        self._config_path = os.path.join(self._data_dir, "mpd.conf")
        self._pid: int = 0
        self._last_error: str = ""
        self._log_file: str = os.path.join(self._data_dir, "mpd.log")

    @property
    def running(self) -> bool:
        if self._process:
            ret = self._process.poll()
            if ret is None:
                return True
            self._process = None
        return False

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

    @staticmethod
    def is_installed() -> bool:
        return shutil.which("mpd") is not None

    @staticmethod
    def _find_mpd() -> str:
        return shutil.which("mpd") or "/usr/bin/mpd"

    def start(self, config) -> bool:
        """Start a local MPD instance with the given config.

        Args:
            config: MpdConfig instance or a path to an existing mpd.conf.

        Returns:
            True if started successfully, False otherwise.
        """
        if self.running:
            logger.warning("MPD already running")
            return True

        if not self.is_installed():
            self._last_error = "MPD binary not found"
            logger.error(self._last_error)
            return False

        config_path = self._config_path
        if hasattr(config, "audio_outputs"):
            config_path = write_mpd_conf(config, self._config_path)
        elif isinstance(config, str):
            config_path = config
        else:
            self._last_error = "Invalid config argument"
            logger.error(self._last_error)
            return False

        try:
            self._process = subprocess.Popen(
                [self._mpd_binary, "--no-daemon", config_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._pid = self._process.pid or 0
            time.sleep(0.5)
            if self._process.poll() is not None:
                self._last_error = f"MPD exited immediately (check {config_path})"
                logger.error(self._last_error)
                self._read_log_tail()
                return False
            logger.info("MPD started (pid %d)", self._process.pid)
            return True
        except OSError as e:
            self._last_error = f"Failed to start MPD: {e}"
            logger.error(self._last_error)
            return False

    def stop(self):
        """Stop the local MPD instance.

        ONLY terminates the process started by this instance.
        Does NOT use pkill/killall.
        """
        if self._process:
            try:
                self._process.send_signal(signal.SIGTERM)
                self._process.wait(timeout=5.0)
                logger.info("MPD stopped (pid %d)", self._pid)
            except subprocess.TimeoutExpired:
                logger.warning("MPD pid %d did not stop gracefully, killing", self._pid)
                self._process.kill()
                self._process.wait(timeout=2.0)
            finally:
                self._process = None
                self._pid = 0
        else:
            logger.debug("No MPD process to stop")

    def restart(self, config=None) -> bool:
        """Restart MPD with optional new config."""
        self.stop()
        time.sleep(0.5)
        return self.start(config or self._config_path)

    def test_connection(self, host: str = "127.0.0.1",
                        port: int = 6600, timeout: float = 3.0) -> tuple[bool, str]:
        """Test connection to the MPD instance."""
        client = MpdClient(host=host, port=port, timeout=timeout)
        try:
            client.connect()
            client.ping()
            client.disconnect()
            return True, "Connected successfully"
        except MpdConnectionError as e:
            self._last_error = str(e)
            return False, str(e)

    def get_status(self) -> dict:
        """Return dict with service status info."""
        return {
            "installed": self.is_installed(),
            "running": self.running,
            "binary": self._mpd_binary,
            "data_dir": self._data_dir,
            "config_path": self._config_path,
            "pid": self._pid,
            "port": self._read_port(),
            "last_error": self._last_error,
            "log_file": self._log_file,
        }

    def _read_port(self) -> int:
        """Read port from config file."""
        try:
            with open(self._config_path) as f:
                for line in f:
                    if "port" in line and '"' in line:
                        return int(line.split('"')[1])
        except (OSError, ValueError, IndexError):
            pass
        return 6600

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
