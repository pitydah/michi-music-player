"""MPD Service Manager — manages a local MPD process.

Can start, stop, restart, and check status of a local MPD instance.
Uses subprocess to launch mpd with a custom config file.
Does NOT require root — runs as the current user with a data dir in ~/.local/share.
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
    build_mpd_config,
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
            logger.error("MPD binary not found")
            return False

        config_path = self._config_path
        if hasattr(config, "audio_outputs"):
            config_path = write_mpd_conf(config, self._config_path)
        elif isinstance(config, str):
            config_path = config
        else:
            logger.error("Invalid config argument")
            return False

        try:
            self._process = subprocess.Popen(
                [self._mpd_binary, config_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.5)
            if self._process.poll() is not None:
                logger.error("MPD exited immediately (check %s)", config_path)
                return False
            logger.info("MPD started (pid %d)", self._process.pid)
            return True
        except OSError as e:
            logger.error("Failed to start MPD: %s", e)
            return False

    def stop(self):
        """Stop the local MPD instance."""
        if self._process:
            try:
                self._process.send_signal(signal.SIGTERM)
                self._process.wait(timeout=5.0)
                logger.info("MPD stopped")
            except subprocess.TimeoutExpired:
                logger.warning("MPD did not stop gracefully, killing")
                self._process.kill()
                self._process.wait(timeout=2.0)
            finally:
                self._process = None
        else:
            self._stop_all_mpd_instances()

    @staticmethod
    def _stop_all_mpd_instances():
        """Kill all mpd processes owned by this user (fallback)."""
        try:
            subprocess.run(
                ["pkill", "-u", os.environ.get("USER", ""), "mpd"],
                capture_output=True, timeout=3.0)
        except (subprocess.TimeoutExpired, OSError):
            pass

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
            return False, str(e)

    def get_status(self) -> dict:
        """Return dict with service status info."""
        return {
            "installed": self.is_installed(),
            "running": self.running,
            "binary": self._mpd_binary,
            "data_dir": self._data_dir,
            "config_path": self._config_path,
        }
