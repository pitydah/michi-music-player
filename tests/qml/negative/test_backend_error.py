"""Backend error handling — core tests, no QML."""
from __future__ import annotations

import pytest

from core.service_container import ServiceContainer, ServicePriority


class TestBackendError:
    def test_missing_required_service(self):
        c = ServiceContainer()
        with pytest.raises(KeyError):
            c.require("nonexistent_service_name")

    def test_registered_none_service(self):
        c = ServiceContainer()
        c.register("test", None, priority=ServicePriority.OPTIONAL)
        svc = c.get("test")
        assert svc is None

    def test_registered_real_service(self):
        c = ServiceContainer()
        c.register("test", "real_value", priority=ServicePriority.OPTIONAL)
        svc = c.get("test")
        assert svc == "real_value"
