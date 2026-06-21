"""SnapClientDiscovery — discovers Snapclients via avahi-browse and snapcast client."""
import shutil
import subprocess

from PySide6.QtCore import QObject, Signal

AVAHi_BROWSE = shutil.which("avahi-browse") or ""


class SnapClientDiscovery(QObject):
    clients_found = Signal(list)  # list[dict]
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clients = []
        self._manual_clients = []

    def clients(self) -> list[dict]:
        return self._clients + self._manual_clients

    def add_manual(self, host: str, port: int = 1704, name: str = ""):
        self._manual_clients.append({
            "id": f"manual:{host}:{port}",
            "name": name or host,
            "host": host, "port": port,
            "type": "snapclient", "backend": "snapcast",
            "manual": True, "available": True,
        })

    def remove_manual(self, client_id: str):
        self._manual_clients = [
            c for c in self._manual_clients
            if c["id"] != client_id]

    def refresh(self):
        found = []
        if AVAHi_BROWSE:
            found = self._discover_avahi()
        if not found:
            found = self._discover_snapcast_lib()
        self._clients = found
        self.clients_found.emit(self.clients())

    def _discover_avahi(self) -> list[dict]:
        try:
            result = subprocess.run(
                [AVAHi_BROWSE, "--all", "--terminate", "--parsable"],
                capture_output=True, text=True, timeout=5)
            clients = []
            for line in result.stdout.splitlines():
                if "_snapcast" not in line.lower():
                    continue
                parts = line.split(";")
                if len(parts) >= 7:
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
