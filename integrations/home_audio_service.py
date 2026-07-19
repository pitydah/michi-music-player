"""Network clients for Snapcast and Home Assistant audio devices."""

from __future__ import annotations

import json
import logging
import socket
import threading
from typing import Any

logger = logging.getLogger(__name__)


class HomeAudioError(Exception):
    """Raised when a home-audio transport cannot complete an operation."""

    def __init__(self, message: str, code: str = "SNAPCAST_RPC_FAILED"):
        super().__init__(message)
        self.code = code


class SnapcastJsonRpcClient:
    """Small synchronous client for the Snapserver JSON-RPC control API."""

    def __init__(self, host: str = "localhost", port: int = 1705, timeout: float = 5.0):
        self._host = host
        self._port = int(port)
        self._timeout = float(timeout)
        self._connected = False
        self._request_id = 0
        self._id_lock = threading.Lock()
        self._last_error = ""

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def endpoint(self) -> str:
        return f"{self._host}:{self._port}"

    @property
    def connection_state(self) -> str:
        return "active" if self._connected else "stopped"

    @property
    def last_error(self) -> str:
        return self._last_error

    def _rpc(self, method: str, params: Any = None) -> dict:
        with self._id_lock:
            self._request_id += 1
            request_id = self._request_id
        request = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": method,
                    "params": params or {},
                }
            )
            + "\r\n"
        )
        try:
            with socket.create_connection(
                (self._host, self._port),
                timeout=self._timeout,
            ) as sock:
                sock.settimeout(self._timeout)
                sock.sendall(request.encode("utf-8"))
                chunks: list[bytes] = []
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    if b"\n" in chunk:
                        break
            payload = b"".join(chunks).decode("utf-8", errors="replace").strip()
            if not payload:
                raise HomeAudioError("Snapcast returned an empty response", "EMPTY_RESPONSE")
            try:
                response = json.loads(payload.splitlines()[0])
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HomeAudioError("Snapcast returned invalid JSON", "INVALID_RESPONSE") from exc
            if not isinstance(response, dict):
                raise HomeAudioError("Snapcast returned a non-object response", "INVALID_RESPONSE")
            if response.get("id") != request_id:
                raise HomeAudioError("Snapcast response ID does not match request", "RESPONSE_ID_MISMATCH")
            if "error" in response:
                raise HomeAudioError(f"Snapcast RPC error: {response['error']}", "RPC_ERROR")
            result = response.get("result", {})
            if not isinstance(result, dict):
                raise HomeAudioError("Snapcast result is not an object", "INVALID_RESPONSE")
            self._connected = True
            self._last_error = ""
            return result
        except HomeAudioError as exc:
            self._connected = False
            self._last_error = str(exc)
            raise
        except socket.timeout as exc:
            self._connected = False
            self._last_error = str(exc)
            raise HomeAudioError(
                f"Snapcast timed out at {self.endpoint}", "TIMEOUT"
            ) from exc
        except ConnectionRefusedError as exc:
            self._connected = False
            self._last_error = str(exc)
            raise HomeAudioError(
                f"Snapcast refused the connection at {self.endpoint}", "CONNECTION_REFUSED"
            ) from exc
        except OSError as exc:
            self._connected = False
            self._last_error = str(exc)
            raise HomeAudioError(
                f"Cannot use Snapcast at {self.endpoint}: {exc}", "CONNECTION_FAILED"
            ) from exc

    def get_status(self) -> dict:
        return self._rpc("Server.GetStatus")

    def ping(self) -> bool:
        try:
            self.get_status()
            return True
        except HomeAudioError:
            return False

    @staticmethod
    def _server_from_status(status: dict) -> dict:
        return status.get("server", status) if isinstance(status, dict) else {}

    def get_groups(self) -> list[dict]:
        server = self._server_from_status(self.get_status())
        return list(server.get("groups", []) or [])

    def get_streams(self) -> list[dict]:
        server = self._server_from_status(self.get_status())
        return list(server.get("streams", []) or [])

    def get_client_list(self) -> list[dict]:
        clients = []
        for group in self.get_groups():
            group_id = group.get("id", "")
            group_name = group.get("name", "")
            stream_id = group.get("stream_id", group.get("streamId", ""))
            for client in group.get("clients", []) or []:
                config = client.get("config", {}) or {}
                volume = config.get("volume", {}) or {}
                host = client.get("host", {}) or {}
                clients.append(
                    {
                        "id": client.get("id", ""),
                        "name": config.get("name") or client.get("name", ""),
                        "connected": bool(client.get("connected", False)),
                        "volume": int(volume.get("percent", 100) or 0),
                        "muted": bool(volume.get("muted", False)),
                        "latency_ms": int(config.get("latency", 0) or 0),
                        "group": group_id,
                        "group_name": group_name,
                        "stream_id": stream_id,
                        "host": host.get("ip", ""),
                        "backend": "snapcast",
                    }
                )
        return clients

    def set_client_volume(
        self,
        client_id: str,
        volume: int,
        mute: bool = False,
    ) -> bool:
        volume = max(0, min(100, int(volume)))
        self._rpc(
            "Client.SetVolume",
            {
                "id": client_id,
                "volume": {"percent": volume, "muted": bool(mute)},
            },
        )
        return True

    def set_client_latency(self, client_id: str, latency_ms: int) -> bool:
        self._rpc(
            "Client.SetLatency",
            {"id": client_id, "latency": max(0, int(latency_ms))},
        )
        return True

    def set_client_name(self, client_id: str, name: str) -> bool:
        self._rpc("Client.SetName", {"id": client_id, "name": name})
        return True

    def set_group_stream(self, group_id: str, stream_id: str) -> bool:
        self._rpc(
            "Group.SetStream",
            {"id": group_id, "stream_id": stream_id},
        )
        return True

    def set_group_clients(self, group_id: str, client_ids: list[str]) -> bool:
        self._rpc(
            "Group.SetClients",
            {"id": group_id, "clients": list(client_ids)},
        )
        return True

    def set_group_name(self, group_id: str, name: str) -> bool:
        self._rpc("Group.SetName", {"id": group_id, "name": name})
        return True


# Public legacy name used by composition and older consumers.
SnapcastService = SnapcastJsonRpcClient


class HomeAssistantService:
    """Client for the Home Assistant REST API, limited to media players."""

    def __init__(self, host: str = "", token: str = "", timeout: float = 10.0):
        self._host = host.rstrip("/")
        self._token = token
        self._timeout = float(timeout)
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def configure(self, host: str, token: str):
        self._host = host.rstrip("/")
        self._token = token
        self._connected = False

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def get_states(self) -> list[dict]:
        if not self._host or not self._token:
            return []
        import requests

        try:
            response = requests.get(
                f"{self._host}/api/states",
                headers=self._headers(),
                timeout=self._timeout,
            )
            response.raise_for_status()
            self._connected = True
            states = response.json()
            return [
                state
                for state in states
                if state.get("entity_id", "").startswith("media_player.")
            ]
        except requests.RequestException as exc:
            self._connected = False
            logger.debug("Home Assistant state request failed: %s", exc)
            return []

    def call_service(self, service: str, payload: dict) -> dict:
        if not self._host or not self._token:
            return {"ok": False, "error": "NOT_CONFIGURED"}
        import requests

        try:
            response = requests.post(
                f"{self._host}/api/services/media_player/{service}",
                headers=self._headers(),
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            self._connected = True
            return {"ok": True, "result": response.json() if response.content else []}
        except requests.RequestException as exc:
            self._connected = False
            return {"ok": False, "error": str(exc)}

    def set_volume(self, entity_id: str, volume: float) -> dict:
        return self.call_service(
            "volume_set",
            {"entity_id": entity_id, "volume_level": max(0.0, min(1.0, volume))},
        )

    def mute(self, entity_id: str, muted: bool) -> dict:
        return self.call_service(
            "volume_mute",
            {"entity_id": entity_id, "is_volume_muted": bool(muted)},
        )
