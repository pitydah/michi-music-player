"""Network clients for Snapcast and Home Assistant audio devices."""

from __future__ import annotations

import json
import logging
import socket
import threading
from typing import Any
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtWebSockets import QWebSocket

logger = logging.getLogger(__name__)


class HomeAudioError(Exception):
    """Raised when a home-audio transport cannot complete an operation."""

    def __init__(self, message: str, code: str = "SNAPCAST_RPC_FAILED") -> None:
        super().__init__(message)
        self.code = code


class SnapcastJsonRpcClient:
    """Small synchronous client for the Snapserver JSON-RPC control API."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1705,
        timeout: float = 5.0,
    ) -> None:
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


class HomeAssistantWebSocketClient(QObject):
    """Subscribe to Home Assistant state changes through Qt WebSockets."""

    state_changed = Signal(dict)
    connection_changed = Signal(bool)

    def __init__(
        self,
        host: str = "",
        token: str = "",
        port: int = 8123,
        parent: QObject | None = None,
        websocket: Any = None,
    ) -> None:
        super().__init__(parent)
        self._host = host
        self._token = token
        self._port = int(port or 8123)
        self._socket = websocket or QWebSocket(parent=self)
        self._connected = False
        self._stopped = True
        self._authentication_failed = False
        self._next_reconnect_ms = 1000
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self.connect_to_host)
        self._socket.connected.connect(self._on_transport_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.textMessageReceived.connect(self._on_text_message)
        error_signal = getattr(self._socket, "errorOccurred", None)
        if error_signal is not None:
            error_signal.connect(self._on_socket_error)

    @property
    def connected(self) -> bool:
        """Whether Home Assistant authenticated the WebSocket session."""
        return self._connected

    @property
    def endpoint(self) -> str:
        """Return the configured Home Assistant WebSocket endpoint."""
        raw_host = self._host.strip()
        if not raw_host:
            return ""
        parsed = urlsplit(raw_host if "://" in raw_host else f"http://{raw_host}")
        scheme = "wss" if parsed.scheme == "https" else "ws"
        hostname = parsed.hostname or ""
        port = parsed.port or self._port
        return f"{scheme}://{hostname}:{port}/api/websocket"

    def configure(self, host: str, token: str, port: int = 8123) -> None:
        """Replace credentials and immediately attempt a connection."""
        self.stop()
        self._host = host
        self._token = token
        self._port = int(port or 8123)
        self._authentication_failed = False
        self._next_reconnect_ms = 1000
        self.connect_to_host()

    def connect_to_host(self) -> None:
        """Open the configured WebSocket endpoint without blocking Qt."""
        if not self.endpoint or not self._token:
            return
        self._stopped = False
        self._socket.open(QUrl(self.endpoint))

    def stop(self) -> None:
        """Stop reconnecting and close the current socket."""
        self._stopped = True
        self._reconnect_timer.stop()
        self._set_connected(False)
        self._socket.close()

    def _set_connected(self, connected: bool) -> None:
        if self._connected == connected:
            return
        self._connected = connected
        self.connection_changed.emit(connected)

    def _send(self, payload: dict) -> None:
        self._socket.sendTextMessage(json.dumps(payload, separators=(",", ":")))

    def _on_transport_connected(self) -> None:
        logger.debug("Home Assistant WebSocket transport connected")

    def _on_text_message(self, message: str) -> None:
        try:
            payload = json.loads(message)
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.debug("Home Assistant WebSocket returned invalid JSON")
            return
        if not isinstance(payload, dict):
            return

        message_type = payload.get("type")
        if message_type == "auth_required":
            self._send({"type": "auth", "access_token": self._token})
        elif message_type == "auth_ok":
            self._authentication_failed = False
            self._next_reconnect_ms = 1000
            self._send(
                {
                    "id": 1,
                    "type": "subscribe_events",
                    "event_type": "state_changed",
                }
            )
            self._set_connected(True)
        elif message_type == "auth_invalid":
            self._authentication_failed = True
            self._set_connected(False)
            self._socket.close()
        elif message_type == "event":
            self._emit_media_player_state(payload)

    def _emit_media_player_state(self, payload: dict) -> None:
        event = payload.get("event", {})
        data = event.get("data", {}) if isinstance(event, dict) else {}
        entity_id = str(data.get("entity_id", "")) if isinstance(data, dict) else ""
        if not entity_id.startswith("media_player."):
            return
        state = data.get("new_state")
        if not isinstance(state, dict):
            return
        normalized_state = dict(state)
        normalized_state.setdefault("entity_id", entity_id)
        self.state_changed.emit(normalized_state)

    def _on_disconnected(self) -> None:
        self._set_connected(False)
        if self._stopped or self._authentication_failed or not self._token:
            return
        delay_ms = self._next_reconnect_ms
        self._next_reconnect_ms = min(delay_ms * 2, 30_000)
        self._reconnect_timer.start(delay_ms)

    def _on_socket_error(self, _error: Any) -> None:
        logger.debug(
            "Home Assistant WebSocket error: %s",
            self._socket.errorString(),
        )


class HomeAssistantService(QObject):
    """Home Assistant media-player client with WebSocket push and REST fallback."""

    state_changed = Signal(dict)
    websocket_connection_changed = Signal(bool)

    def __init__(
        self,
        host: str = "",
        token: str = "",
        timeout: float = 10.0,
        parent: QObject | None = None,
        websocket_client: HomeAssistantWebSocketClient | None = None,
        websocket_port: int = 8123,
    ) -> None:
        super().__init__(parent)
        self._host = host.rstrip("/")
        self._token = token
        self._timeout = float(timeout)
        self._connected = False
        self._poll_timer: QTimer | None = None
        self._poll_interval_ms = 5000
        self._last_state_hash = 0
        self._states: dict[str, dict] = {}
        self._websocket = websocket_client or HomeAssistantWebSocketClient(
            host,
            token,
            websocket_port,
            self,
        )
        self._websocket.state_changed.connect(self._on_websocket_state_changed)
        self._websocket.connection_changed.connect(self._on_websocket_connection_changed)

    @property
    def connected(self) -> bool:
        return self._connected or self.websocket_connected

    @property
    def websocket_connected(self) -> bool:
        """Whether the authenticated WebSocket subscription is active."""
        return self._websocket.connected

    @staticmethod
    def _normalise_rest_host(host: str) -> str:
        value = host.strip().rstrip("/")
        if value and "://" not in value:
            value = f"http://{value}"
        return value

    def configure(
        self,
        host: str,
        token: str,
        websocket_port: int = 8123,
    ) -> None:
        self._host = host.rstrip("/")
        self._token = token
        self._connected = False
        self._states.clear()
        if not host or not token:
            self.unsubscribe_events()
            return
        if self._poll_timer is not None:
            self._poll_timer.stop()
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self._poll_interval_ms)
        self._poll_timer.timeout.connect(self._poll_state)
        self._poll_timer.start()
        self._websocket.configure(host, token, websocket_port)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def get_states(self) -> list[dict]:
        if self.websocket_connected:
            return list(self._states.values())
        if not self._host or not self._token:
            return []
        import requests

        try:
            response = requests.get(
                f"{self._normalise_rest_host(self._host)}/api/states",
                headers=self._headers(),
                timeout=self._timeout,
            )
            response.raise_for_status()
            self._connected = True
            states = response.json()
            media_player_states = [
                state
                for state in states
                if state.get("entity_id", "").startswith("media_player.")
            ]
            self._states = {
                state["entity_id"]: state
                for state in media_player_states
                if state.get("entity_id")
            }
            return media_player_states
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
                f"{self._normalise_rest_host(self._host)}/api/services/media_player/{service}",
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

    def subscribe_events(self, interval_ms: int = 5000) -> None:
        self._poll_interval_ms = interval_ms
        if self._poll_timer is not None:
            self._poll_timer.stop()
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(interval_ms)
        self._poll_timer.timeout.connect(self._poll_state)
        self._poll_timer.start()
        if self._host and self._token and not self.websocket_connected:
            self._websocket.connect_to_host()

    def unsubscribe_events(self) -> None:
        if self._poll_timer is not None:
            self._poll_timer.stop()
            self._poll_timer = None
        self._websocket.stop()

    def disconnect_home_assistant(self) -> None:
        """Close transports and clear in-memory credentials and state."""
        self.unsubscribe_events()
        self._host = ""
        self._token = ""
        self._connected = False
        self._states.clear()

    def _poll_state(self) -> None:
        if self.websocket_connected:
            return
        states = self.get_states()
        state_hash = hash(json.dumps(states, sort_keys=True, default=str))
        if state_hash != self._last_state_hash:
            self._last_state_hash = state_hash
            if states:
                self.state_changed.emit({"source": "rest", "states": states})

    def _on_websocket_state_changed(self, state: dict) -> None:
        entity_id = str(state.get("entity_id", ""))
        if not entity_id:
            return
        self._states[entity_id] = state
        self.state_changed.emit(state)

    def _on_websocket_connection_changed(self, connected: bool) -> None:
        if connected:
            if self._poll_timer is not None:
                self._poll_timer.stop()
        elif self._host and self._token:
            if self._poll_timer is None:
                self._poll_timer = QTimer(self)
                self._poll_timer.timeout.connect(self._poll_state)
            self._poll_timer.setInterval(self._poll_interval_ms)
            self._poll_timer.start()
        self.websocket_connection_changed.emit(connected)
