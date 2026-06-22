"""TransmitManager — wireless audio transmission to remote devices."""

import os
import json
from dataclasses import dataclass, asdict

from PySide6.QtCore import QObject, Signal

CONFIG_DIR = os.path.expanduser("~/.local/share/michi-music-player")
DEVICES_PATH = os.path.join(CONFIG_DIR, "transmit_devices.json")


@dataclass
class TransmitDevice:
    name: str
    stype: str = "http"      # "http" | "snapcast"
    address: str = ""
    port: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TransmitDevice":
        return cls(
            name=d.get("name", ""),
            stype=d.get("stype", "http"),
            address=d.get("address", ""),
            port=d.get("port", 0),
        )


class TransmitManager(QObject):
    device_changed = Signal()        # list modified
    active_changed = Signal()        # active device toggled

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices: list[TransmitDevice] = []
        self._active: TransmitDevice | None = None
        self.load()

    def load(self):
        if os.path.exists(DEVICES_PATH):
            try:
                with open(DEVICES_PATH) as f:
                    data = json.load(f)
                self._devices = [TransmitDevice.from_dict(d) for d in data]
            except Exception:
                import logging
                logging.getLogger("michi").debug("Failed to load transmit devices config")
                self._devices = []

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(DEVICES_PATH, "w") as f:
            json.dump([d.to_dict() for d in self._devices], f, indent=2)

    def add_device(self, name: str, stype: str, address: str, port: int = 0):
        dev = TransmitDevice(name=name, stype=stype, address=address, port=port)
        self._devices.append(dev)
        self.save()
        self.device_changed.emit()
        return dev

    def remove_device(self, name: str):
        self._devices = [d for d in self._devices if d.name != name]
        if self._active and self._active.name == name:
            self._active = None
            self.active_changed.emit()
        self.save()
        self.device_changed.emit()

    def update_device(self, old_name: str, name: str, stype: str,
                      address: str, port: int = 0):
        for d in self._devices:
            if d.name == old_name:
                d.name = name
                d.stype = stype
                d.address = address
                d.port = port
                break
        self.save()
        self.device_changed.emit()

    def get_devices(self) -> list[TransmitDevice]:
        return list(self._devices)

    def set_active(self, device: TransmitDevice | None):
        self._active = device
        self.active_changed.emit()

    def get_active(self) -> TransmitDevice | None:
        return self._active
