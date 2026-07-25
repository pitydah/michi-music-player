"""Shutdown ownership tests for the canonical queue stack."""

import pytest

from core.queue_service import QueueService
from core.runtime_persistence import RuntimePersistence
from ui_qml_bridge.queue_bridge import QueueBridge

pytestmark = [pytest.mark.qml_module("queue")]


@pytest.fixture
def queue_stack(tmp_path):
    persistence = RuntimePersistence(base_dir=str(tmp_path))
    service = QueueService(runtime_persistence=persistence)
    bridge = QueueBridge(queue_service=service)
    return persistence, service, bridge


def test_queue_service_shutdown_persists_state(queue_stack):
    persistence, service, _bridge = queue_stack
    items = [{"track_uid": "uid1", "title": "Track 1", "filepath": "/1.flac"}]
    service.replace(items)
    service.set_repeat("all")

    service.shutdown(position=42.5)

    state = persistence.read("queue")
    assert state["items"] == items
    assert state["position"] == 42.5
    assert state["repeat"] == "all"


def test_queue_bridge_shutdown_only_unsubscribes(queue_stack):
    persistence, service, bridge = queue_stack
    service.replace([{"track_uid": "uid1", "filepath": "/1.flac"}])

    bridge.shutdown()
    bridge.shutdown()

    assert bridge._unsubscribe is None
    assert persistence.read("queue") is None
