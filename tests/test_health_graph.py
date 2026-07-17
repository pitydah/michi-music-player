from integrations.michi_ecosystem.health_graph import EcosystemHealthNode, EcosystemHealthEdge, EcosystemHealthGraph, build_health_graph


class TestHealthGraph:
    def test_node(self):
        node = EcosystemHealthNode(id="n1", label="Test", type="sync", status="ok")
        assert node.id == "n1"

    def test_build_graph(self):
        graph = build_health_graph({})
        assert graph is not None
