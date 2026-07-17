"""Home Audio service - manages Snapcast and Home Assistant audio devices."""
import logging
import json
import socket

logger = logging.getLogger(__name__)


class HomeAudioError(Exception):
    pass


class SnapcastService:
    """Client for Snapcast JSON-RPC API."""

    def __init__(self, host: str = "localhost", port: int = 1780):
        self._host = host
        self._port = port
        self._connected = False

    def _rpc(self, method: str, params: list | None = None) -> dict:
        """Send JSON-RPC call to Snapserver."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self._host, self._port))
            request = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params or []
            }) + "\n"
            sock.send(request.encode())
            response = sock.recv(65536).decode()
            sock.close()
            result = json.loads(response)
            if "error" in result:
                raise HomeAudioError(f"Snapcast RPC error: {result['error']}")
            return result.get("result", {})
        except (socket.timeout, ConnectionRefusedError) as e:
            self._connected = False
            raise HomeAudioError(f"Cannot connect to Snapcast at {self._host}:{self._port}: {e}") from e

    def get_client_list(self) -> list[dict]:
        """Get list of connected Snapcast clients."""
        result = self._rpc("Server.GetStatus")
        groups = result.get("server", {}).get("groups", [])
        clients = []
        for group in groups:
            for client in group.get("clients", []):
                clients.append({
                    "id": client.get("id", ""),
                    "name": client.get("name", ""),
                    "connected": client.get("connected", False),
                    "volume": client.get("config", {}).get("volume", {}).get("percent", 100),
                    "muted": client.get("config", {}).get("volume", {}).get("muted", False),
                    "group": group.get("id", ""),
                    "group_name": group.get("name", ""),
                })
        return clients

    def set_client_volume(self, client_id: str, volume: int, mute: bool = False) -> bool:
        """Set volume for a Snapcast client (0-100)."""
        volume = max(0, min(100, volume))
        try:
            self._rpc("Client.SetVolume", {
                "id": client_id,
                "volume": {"percent": volume, "muted": mute}
            })
            return True
        except HomeAudioError:
            return False


class HomeAssistantService:
    """Client for Home Assistant REST API."""

    def __init__(self, host: str = "", token: str = ""):
        self._host = host.rstrip('/')
        self._token = token
        self._connected = False

    def get_states(self) -> list[dict]:
        """Get all media_player states from Home Assistant."""
        import requests
        try:
            resp = requests.get(
                f"{self._host}/api/states",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                timeout=10
            )
            if resp.status_code == 200:
                states = resp.json()
                return [s for s in states if s.get("entity_id", "").startswith("media_player.")]
            return []
        except requests.RequestException:
            return []
