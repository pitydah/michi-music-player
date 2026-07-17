"""Micro Server service - communicates with the Rust Michi Micro Server."""
import logging
import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
RECONNECT_BACKOFF = [1, 2, 4, 8, 15]


class MicroServerError(Exception):
    def __init__(self, message: str, status_code: int = 0, recoverable: bool = True):
        self.message = message
        self.status_code = status_code
        self.recoverable = recoverable
        super().__init__(message)


class MicroServerService:
    """Client for Michi Micro Server (Rust)."""

    def __init__(self, host: str = "localhost", port: int = 53318, token: str = ""):
        self._host = host
        self._port = port
        self._token = token
        self._session = requests.Session()
        self._session.timeout = DEFAULT_TIMEOUT
        self._connected = False
        self._version = ""

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def discover(self, timeout: float = 2.0) -> list[dict]:
        """Discover Micro Servers on the local network via mDNS."""
        servers = []
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            msg = b"\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x05_michi\x04_tcp\x05local\x00\x00\x0c\x00\x01"
            sock.sendto(msg, ("224.0.0.251", 5353))
            try:
                data, addr = sock.recvfrom(1024)
                servers.append({"host": addr[0], "port": 53318, "name": f"Michi Micro Server ({addr[0]})"})
            except socket.timeout:
                pass
            sock.close()
        except Exception as e:
            logger.debug(f"mDNS discovery failed: {e}")
        servers.append({"host": "localhost", "port": 53318, "name": "Michi Micro Server (localhost)"})
        return servers

    def health(self) -> dict:
        """Check server health."""
        try:
            resp = self._session.get(f"{self.base_url}/health", timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 200:
                self._connected = True
                return resp.json()
            else:
                self._connected = False
                return {"ok": False, "status": resp.status_code}
        except requests.RequestException as e:
            self._connected = False
            return {"ok": False, "error": str(e), "recoverable": True}

    def get_status(self) -> dict:
        """Get full server status."""
        try:
            resp = self._session.get(f"{self.base_url}/status", headers=self._headers(), timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            return {"ok": False, "status": resp.status_code}
        except requests.RequestException as e:
            return {"ok": False, "error": str(e), "recoverable": True}

    def import_tracks(self, paths: list[str]) -> dict:
        """Import tracks to Micro Server. Must contact server."""
        if not paths:
            return {"ok": False, "error": "No paths provided", "error_code": "NO_PATHS"}
        try:
            resp = self._session.post(
                f"{self.base_url}/tracks/import",
                headers=self._headers(),
                json={"paths": paths},
                timeout=120
            )
            if resp.status_code == 200:
                result = resp.json()
                return {"ok": True, "imported": result.get("count", 0), "errors": result.get("errors", [])}
            return {"ok": False, "status": resp.status_code, "error": resp.text}
        except requests.RequestException as e:
            return {"ok": False, "error": str(e), "recoverable": True}

    def shutdown(self):
        self._session.close()
