"""QueueBridge persistence tests for the canonical QueueService contract."""

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
from core.runtime_persistence import RuntimePersistence
from ui_qml_bridge.queue_bridge import QueueBridge


@pytest.fixture
def queue_stack(tmp_path):
    persistence = RuntimePersistence(base_dir=str(tmp_path))
    service = QueueService(runtime_persistence=persistence)
    bridge = QueueBridge(queue_service=service)
    return persistence, service, bridge


def test_save_and_load_state_delegate_to_queue_service(queue_stack):
    _persistence, service, bridge = queue_stack
    saved = {"ok": True, "count": 2}
    loaded = {"ok": True, "count": 2}
    service.save_state = MagicMock(return_value=saved)
    service.load_state = MagicMock(return_value=loaded)

    assert bridge.saveState() == saved
    assert bridge.loadState() == loaded
    service.save_state.assert_called_once_with()
    service.load_state.assert_called_once_with()


def test_bridge_round_trip_uses_canonical_queue_payload(queue_stack):
    persistence, service, bridge = queue_stack
    items = [
        {"track_uid": "uid1", "title": "Track 1", "filepath": "/1.flac"},
        {"track_uid": "uid2", "title": "Track 2", "filepath": "/2.flac"},
    ]
    service.replace(items, start_index=1)
    service.set_repeat("one")
    service.set_shuffle(True)

    save_result = bridge.saveState()
    assert save_result["ok"] is True
    assert save_result["count"] == 2
    payload = persistence.read("queue")
    assert payload["version"] == 3
    assert payload["source"] == "queue_service"
    assert payload["items"] == service.get_items()
    assert payload["current_index"] == service.current_index
    assert payload["shuffle"] is True
    assert payload["repeat"] == "one"

    restored_service = QueueService(runtime_persistence=persistence)
    restored_bridge = QueueBridge(queue_service=restored_service)
    assert restored_bridge.loadState() == {"ok": True, "count": 2}
    assert restored_service.get_items() == payload["items"]
    assert restored_service.shuffle is True
    assert restored_service.repeat == "one"
