from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.notification_service import Notification, NotificationService, NotificationType
pytestmark = [pytest.mark.qml_module("notification")]



@pytest.fixture
def service():
    return NotificationService()


class TestNotificationService:
    def test_create_and_retrieve(self, service):
        n = Notification(title="Test", message="Hello")
        result = service.notify(n)
        assert result.id == n.id
        assert service.get(n.id) is n

    def test_update_notification(self, service):
        n = Notification(title="Initial", type=NotificationType.INFO)
        service.notify(n)
        updated = service.update(n.id, title="Updated", progress=50.0)
        assert updated is not None
        assert updated.title == "Updated"
        assert updated.progress == 50.0

    def test_update_nonexistent(self, service):
        result = service.update("nonexistent", title="Nope")
        assert result is None

    def test_dismiss(self, service):
        n = Notification(title="Dismiss me")
        service.notify(n)
        assert service.dismiss(n.id) is True
        assert service.get(n.id) is None

    def test_dismiss_non_dismissible(self, service):
        n = Notification(title="Sticky", dismissible=False)
        service.notify(n)
        assert service.dismiss(n.id) is False
        assert service.get(n.id) is not None

    def test_list_all(self, service):
        n1 = Notification(title="A")
        n2 = Notification(title="B")
        service.notify(n1)
        service.notify(n2)
        assert len(service.list_all()) == 2

    def test_list_persistent(self, service):
        n1 = Notification(title="Persistent", persistent=True)
        n2 = Notification(title="Transient", persistent=False)
        service.notify(n1)
        service.notify(n2)
        persistent = service.list_persistent()
        assert len(persistent) == 1
        assert persistent[0].title == "Persistent"

    def test_persistent_survives_trim(self, service):
        service._max_size = 3
        for i in range(5):
            service.notify(Notification(title=f"T{i}"))
        persistent = service.notify(Notification(title="Save", persistent=True))
        assert service.get(persistent.id) is not None

    def test_list_by_source(self, service):
        service.notify(Notification(title="A", source="scan"))
        service.notify(Notification(title="B", source="sync"))
        service.notify(Notification(title="C", source="scan"))
        assert len(service.list_by_source("scan")) == 2
        assert len(service.list_by_source("sync")) == 1

    def test_clear(self, service):
        service.notify(Notification(title="A", persistent=True))
        service.notify(Notification(title="B"))
        service.clear()
        assert len(service.list_all()) == 0
        assert len(service.list_persistent()) == 0

    def test_listener_called(self, service):
        listener = MagicMock()
        service.on(listener)
        n = Notification(title="Hello")
        service.notify(n)
        listener.assert_called_once_with(n)

    def test_listener_off(self, service):
        listener = MagicMock()
        service.on(listener)
        service.off(listener)
        service.notify(Notification(title="Hello"))
        listener.assert_not_called()

    def test_to_dict(self):
        n = Notification(id="test-1", type=NotificationType.WARNING,
                         title="Warning", message="Something",
                         progress=42.0, persistent=True,
                         actions=["retry"], job_id="j1")
        d = n.to_dict()
        assert d["id"] == "test-1"
        assert d["type"] == "warning"
        assert d["progress"] == 42.0
        assert d["persistent"] is True
        assert d["actions"] == ["retry"]
        assert d["job_id"] == "j1"
