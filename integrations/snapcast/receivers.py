"""ReceiverWizard — dialog to configure Snapcast receivers (RPi, ESP32, Docker)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ReceiverWizard:
    """Guides the user through adding a Snapcast receiver.

    Supported receiver types:
      - rpi: Raspberry Pi running snapclient
      - esp32: ESP32 running ESP-Snapcast
      - docker: Docker container running snapclient
    """

    RECEIVER_TYPES = ("rpi", "esp32", "docker")

    def __init__(self, parent=None):
        self._parent = parent
        self._result: dict[str, Any] = {}

    def run(self, receiver_type: str) -> dict[str, Any]:
        """Run the wizard for a given receiver type.

        Returns a dict with:
          - ok: bool
          - receiver_type: str
          - host: str (user-provided or auto-detected)
          - port: int
          - config: dict (type-specific settings)
        """
        if receiver_type not in self.RECEIVER_TYPES:
            return {"ok": False, "error": f"Unknown receiver type: {receiver_type}"}

        result: dict[str, Any] = {
            "ok": True,
            "receiver_type": receiver_type,
        }

        if receiver_type == "rpi":
            result.update(self._configure_rpi())
        elif receiver_type == "esp32":
            result.update(self._configure_esp32())
        elif receiver_type == "docker":
            result.update(self._configure_docker())

        self._result = result
        return result

    def _configure_rpi(self) -> dict[str, Any]:
        return {
            "host": "raspberrypi.local",
            "port": 1704,
            "config": {
                "auto_start": True,
                "use_alsa": True,
                "audio_output": "headphone",
                "latency": 0,
            },
        }

    def _configure_esp32(self) -> dict[str, Any]:
        return {
            "host": "esp32-snapcast.local",
            "port": 1704,
            "config": {
                "wifi_ssid": "",
                "wifi_password": "",
                "i2s_pins": {"bclk": 26, "ws": 25, "dout": 22},
                "volume_control": True,
            },
        }

    def _configure_docker(self) -> dict[str, Any]:
        return {
            "host": "127.0.0.1",
            "port": 1704,
            "config": {
                "container_name": "snapclient",
                "image": "bocki/snapclient:latest",
                "network_mode": "host",
                "auto_restart": True,
            },
        }

    @property
    def result(self) -> dict[str, Any]:
        return dict(self._result)

    @property
    def is_complete(self) -> bool:
        return self._result.get("ok", False)
