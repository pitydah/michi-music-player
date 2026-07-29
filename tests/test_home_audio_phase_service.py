"""Service tests for Home Audio roadmap phases 3 through 7."""

from copy import deepcopy
from typing import Any
from unittest.mock import MagicMock

from core.home_audio_service import HomeAudioService


class MemorySettings:
    """Minimal settings store for HomeAudioService tests."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    def value(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def setValue(self, key: str, value: Any) -> None:
        self.values[key] = value

    def sync(self) -> None:
        return None


class SnapcastControl:
    """In-memory Snapcast control with readback behavior."""

    def __init__(self) -> None:
        self.connected = True
        self.groups = [
            {
                "id": "group-1",
                "name": "Living room",
                "stream_id": "stream-old",
                "clients": [
                    {"id": "receiver-1", "connected": True},
                    {"id": "receiver-2", "connected": True},
                ],
            }
        ]
        self.streams = [{"id": "stream-new", "status": "idle"}]

    def get_groups(self) -> list[dict]:
        return deepcopy(self.groups)

    def get_streams(self) -> list[dict]:
        return deepcopy(self.streams)

    def set_group_stream(self, group_id: str, stream_id: str) -> bool:
        self.groups[0]["stream_id"] = stream_id
        return True

    def set_group_clients(self, group_id: str, receiver_ids: list[str]) -> bool:
        clients = {client["id"]: client for client in self.groups[0]["clients"]}
        self.groups[0]["clients"] = [clients[receiver_id] for receiver_id in receiver_ids]
        return True

    def set_group_name(self, group_id: str, name: str) -> bool:
        self.groups[0]["name"] = name
        return True


def test_assign_source_to_zone_sets_and_verifies_snapcast_stream() -> None:
    control = SnapcastControl()
    service = HomeAudioService(snapcast_control=control, settings=MemorySettings())

    result = service.assign_source_to_zone("group-1", "stream-new")

    assert result == {"ok": True, "stream_id": "stream-new", "verified": True}


def test_assign_source_to_zone_rejects_unknown_source() -> None:
    service = HomeAudioService(
        snapcast_control=SnapcastControl(), settings=MemorySettings()
    )

    result = service.assign_source_to_zone("group-1", "missing")

    assert result["ok"] is False
    assert result["error"] == "UNKNOWN_SOURCE"


def test_update_group_replaces_members_and_verifies_name() -> None:
    control = SnapcastControl()
    service = HomeAudioService(snapcast_control=control, settings=MemorySettings())

    result = service.update_group("group-1", "Studio", ["receiver-2"])

    assert result == {"ok": True, "errors": []}
    assert control.groups[0]["name"] == "Studio"
    assert [client["id"] for client in control.groups[0]["clients"]] == ["receiver-2"]


def test_disconnect_closes_home_assistant_client() -> None:
    client = MagicMock()
    client.disconnect_home_assistant.return_value = None
    service = HomeAudioService(ha_client=client, settings=MemorySettings())

    result = service.disconnect_home_assistant()

    client.disconnect_home_assistant.assert_called_once_with()
    assert result == {"ok": True, "disconnected": True}
