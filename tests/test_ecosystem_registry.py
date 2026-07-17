from unittest.mock import MagicMock
from integrations.michi_ecosystem.ecosystem_registry import EcosystemRegistry
from integrations.michi_ecosystem.ecosystem_models import EcosystemService


class TestEcosystemRegistry:
    def test_create(self):
        reg = EcosystemRegistry()
        assert reg is not None

    def test_register_and_list(self):
        reg = EcosystemRegistry()
        svc = EcosystemService(id="s1", name="Service 1", type="sync")
        reg.register_service(svc)
        services = reg.list_services()
        assert any(s.id == "s1" for s in services)
