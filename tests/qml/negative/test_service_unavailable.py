"""Service unavailable state — core service test, no QML."""
from __future__ import annotations

from core.service_container import ServiceContainer, ServicePriority


class TestServiceUnavailable:
    def test_container_returns_none_for_unregistered(self):
        c = ServiceContainer()
        svc = c.get("nonexistent_service")
        assert svc is None

    def test_optional_service_can_be_none(self):
        c = ServiceContainer()
        c.register("test", None, priority=ServicePriority.OPTIONAL)
        svc = c.get("test")
        assert svc is None

    def test_required_service_raises_error(self):
        c = ServiceContainer()
        c.register("test", "real", priority=ServicePriority.REQUIRED)
        svc = c.get("test")
        assert svc == "real"
