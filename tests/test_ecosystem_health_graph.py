from integrations.michi_ecosystem.ecosystem_health_graph import EcosystemHealthGraphBuilder


class TestEcosystemHealthGraph:
    def test_build_empty(self):
        builder = EcosystemHealthGraphBuilder()
        graph = builder.build({})
        assert len(graph.nodes) == 0

    def test_build_with_data(self):
        builder = EcosystemHealthGraphBuilder()
        graph = builder.build({"mobile_sync": {"status": "ok", "service": "sync"}})
        assert len(graph.nodes) == 1
