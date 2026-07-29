"""Tests for the Home Audio QML meta-object contract."""

import json
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QUrl, Signal

from integrations.home_audio_service import HomeAssistantWebSocketClient
from ui_qml_bridge.home_audio_bridge import HomeAudioBridge


class FakeSignal:
    """Minimal Qt-compatible signal used by the fake WebSocket."""

    def __init__(self) -> None:
        self._callbacks: list[Callable[..., None]] = []

    def connect(self, callback: Callable[..., None]) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: Any) -> None:
        for callback in self._callbacks:
            callback(*args)


class FakeWebSocket:
    """Record WebSocket operations without opening a network connection."""

    def __init__(self) -> None:
        self.connected = FakeSignal()
        self.disconnected = FakeSignal()
        self.textMessageReceived = FakeSignal()
        self.errorOccurred = FakeSignal()
        self.opened_urls: list[str] = []
        self.sent_messages: list[dict] = []

    def open(self, url: QUrl) -> None:
        self.opened_urls.append(url.toString())

    def close(self) -> None:
        return None

    def sendTextMessage(self, message: str) -> None:
        self.sent_messages.append(json.loads(message))

    def errorString(self) -> str:
        return "fake error"


class FakeHomeAudioService(QObject):
    """Expose the state signal consumed by HomeAudioBridge."""

    state_changed = Signal(dict)
    websocket_connected = True


def test_home_audio_bridge_exposes_qml_signal_and_slot_names() -> None:
    bridge = HomeAudioBridge()
    meta_object = bridge.metaObject()
    method_names = {
        bytes(meta_object.method(index).name()).decode("utf-8")
        for index in range(meta_object.methodOffset(), meta_object.methodCount())
    }

    assert {
        "stateChanged",
        "operationFinished",
        "groupZones",
        "setZoneVolume",
    } <= method_names
    assert bridge.metaObject().indexOfProperty("haWebSocketConnected") >= 0


def test_home_assistant_websocket_authenticates_and_subscribes() -> None:
    socket = FakeWebSocket()
    client = HomeAssistantWebSocketClient(websocket=socket)

    client.configure("ha.local", "secret", 8123)
    socket.connected.emit()
    socket.textMessageReceived.emit(json.dumps({"type": "auth_required"}))
    socket.textMessageReceived.emit(json.dumps({"type": "auth_ok"}))

    assert socket.opened_urls == ["ws://ha.local:8123/api/websocket"]
    assert socket.sent_messages == [
        {"type": "auth", "access_token": "secret"},
        {
            "id": 1,
            "type": "subscribe_events",
            "event_type": "state_changed",
        },
    ]
    assert client.connected is True


def test_home_assistant_websocket_emits_only_media_player_states() -> None:
    socket = FakeWebSocket()
    client = HomeAssistantWebSocketClient(websocket=socket)
    states = []
    client.state_changed.connect(states.append)
    client.configure("ha.local", "secret")

    for entity_id in ("light.kitchen", "media_player.living_room"):
        socket.textMessageReceived.emit(
            json.dumps(
                {
                    "type": "event",
                    "event": {
                        "data": {
                            "entity_id": entity_id,
                            "new_state": {
                                "entity_id": entity_id,
                                "state": "playing",
                            },
                        }
                    },
                }
            )
        )

    assert states == [
        {"entity_id": "media_player.living_room", "state": "playing"}
    ]


def test_home_audio_bridge_applies_websocket_state_change() -> None:
    service = FakeHomeAudioService()
    bridge = HomeAudioBridge(home_audio_service=service)

    service.state_changed.emit(
        {
            "entity_id": "media_player.living_room",
            "state": "playing",
            "attributes": {
                "friendly_name": "Living room",
                "volume_level": 0.35,
            },
        }
    )

    assert bridge.haWebSocketConnected is True
    assert bridge.devices == [
        {
            "id": "media_player.living_room",
            "entity_id": "media_player.living_room",
            "name": "Living room",
            "state": "playing",
            "volume": 0.35,
            "muted": False,
            "backend": "home_assistant",
        }
    ]
