"""SnapClientDiscovery — discovers Snapclients via avahi-browse and snapcast client."""

import json
import shutil
import subprocess
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.settings_manager import get_list, set_

AVAHI_BROWSE = shutil.which("avahi-browse") or ""
_MANUAL_CLIENTS_KEY = "home_audio/manual_snapcast_receivers_v1"


class SnapClientDiscovery(QObject):
    """Discover Snapcast receivers and persist manually configured endpoints."""

    clients_found = Signal(list)  # list[dict]
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None, *, settings: Any = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._clients = []
        self._manual_clients = self._load_manual_clients()

    def _load_manual_clients(self) -> list[dict]:
        if self._settings is None:
            clients = get_list(_MANUAL_CLIENTS_KEY)
            return [client for client in clients if isinstance(client, dict)]
        raw = self._settings.value(_MANUAL_CLIENTS_KEY, "[]")
        try:
            clients = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        return [client for client in (clients or []) if isinstance(client, dict)]

    def _save_manual_clients(self) -> None:
        if self._settings is None:
            set_(_MANUAL_CLIENTS_KEY, self._manual_clients)
            return
        self._settings.setValue(
            _MANUAL_CLIENTS_KEY,
            json.dumps(self._manual_clients, ensure_ascii=False),
        )
        sync = getattr(self._settings, "sync", None)
        if callable(sync):
            sync()

    def clients(self) -> list[dict]:
        return self._clients + self._manual_clients

    def add_manual(self, host: str, port: int = 1704, name: str = "") -> None:
        client = {
            "id": f"manual:{host}:{port}",
            "name": name or host,
            "host": host, "port": port,
            "type": "snapclient", "backend": "snapcast",
            "manual": True, "available": True,
        }
        self._manual_clients = [
            existing for existing in self._manual_clients if existing.get("id") != client["id"]
        ]
        self._manual_clients.append(client)
        self._save_manual_clients()

    def remove_manual(self, client_id: str) -> None:
        self._manual_clients = [
            c for c in self._manual_clients
            if c["id"] != client_id]
        self._save_manual_clients()

    def refresh(self) -> None:
        found = []
        if AVAHI_BROWSE:
            found = self._discover_avahi()
        if not found:
            found = self._discover_snapcast_lib()
        self._clients = found
        self.clients_found.emit(self.clients())

    def _discover_avahi(self) -> list[dict]:
        try:
            result = subprocess.run(
                [AVAHI_BROWSE, "--all", "--terminate", "--parsable"],
                capture_output=True, text=True, timeout=5)
            clients = []
            for line in result.stdout.splitlines():
                if "_snapcast" not in line.lower():
                    continue
                parts = line.split(";")
                if len(parts) > 7:
                    clients.append({
                        "id": f"avahi:{parts[6]}:{parts[7]}",
                        "name": parts[3] if len(parts) > 3 else "Snapclient",
                        "host": parts[6], "port": int(parts[7]) if parts[7].isdigit() else 1704,
                        "type": "snapclient", "backend": "snapcast",
                        "manual": False, "available": True,
                    })
            return clients
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return []

    def _discover_snapcast_lib(self) -> list[dict]:
        import importlib.util
        if importlib.util.find_spec("snapcast") is None:
            return []
        return []
