"""DeviceDiscoveryService — discover MTP, UMS, and network devices."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("michi.device_discovery")


class DeviceDiscoveryService:
    def __init__(self):
        self._discovered: list[dict] = []

    def discover_mtp(self) -> list[dict]:
        try:
            import subprocess
            out = subprocess.run(["simple-mtpfs", "--list-devices"],
                                 capture_output=True, text=True, timeout=5)
            devices = []
            for line in out.stdout.strip().split("\n"):
                if line.strip():
                    devices.append({"protocol": "mtp", "name": line.strip(), "id": str(hash(line))})
            return devices
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    def discover_ums(self) -> list[dict]:
        devices = []
        for base in ["/media", "/run/media", "/mnt"]:
            if os.path.isdir(base):
                for entry in os.listdir(base):
                    fp = os.path.join(base, entry)
                    if os.path.ismount(fp):
                        devices.append({"protocol": "ums", "mount_point": fp, "label": entry})
        return devices

    def discover_network(self) -> list[dict]:
        return [{"protocol": "network", "message": "DEFERRED_PHYSICAL"}]

    def health(self) -> dict:
        return {"available": True}

    def shutdown(self):
        self._discovered.clear()
