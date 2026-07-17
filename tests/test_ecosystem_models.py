from integrations.michi_ecosystem.ecosystem_models import EcosystemService, EcosystemNode, EcosystemEdge


class TestEcosystemModels:
    def test_service(self):
        svc = EcosystemService(id="test", name="Test", type="sync")
        assert svc.id == "test"

    def test_node(self):
        node = EcosystemNode(id="n1", type="sync", label="Sync", status="ok")
        assert node.status == "ok"
