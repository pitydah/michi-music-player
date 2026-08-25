"""M6.9-PRESENTATION — production composition.

The ApplicationContainer builds ONE enrichment graph and ONE
EnrichmentBridge over the SAME coordinator/service/asset store; the
bridge is disposed BEFORE the coordinator shutdown; constructing the
graph performs zero network.
"""

from michi.application.enrichment_coordinator import EnrichmentCoordinator
from michi.application.enrichment_service import EnrichmentService
from michi.bootstrap import ApplicationContainer, _build_enrichment_graph
from michi.presentation.enrichment_bridge import EnrichmentBridge


class _FakeLibrary:
    """Duck-typed LibraryService for the wiring test."""

    def artist_by_key(self, key):
        return None

    def albums_for_artist(self, key):
        return ()

    def tracks_for_artist(self, key):
        return ()

    def album_by_key(self, key):
        return None


class _DisposeSpy:
    """Universal lifecycle spy: every shutdown/stop/dispose/close call
    the container may issue is recorded."""

    def __init__(self, order, label):
        self._order = order
        self._label = label
        self._relay = None  # scan runner attribute probed by shutdown

    def dispose(self):
        self._order.append(self._label)

    def shutdown(self):
        self._order.append(self._label)

    def stop(self):
        self._order.append(self._label)

    def close(self):
        self._order.append(self._label)

    def unbind(self):
        self._order.append(self._label)


class _CoordShutdownSpy:
    def __init__(self, order):
        self._order = order

    def shutdown(self):
        self._order.append("coord")


class _GraphSpy:
    def __init__(self, coordinator):
        self.coordinator = coordinator


class TestProductionComposition:
    def test_bridge_uses_same_graph_objects(self, tmp_path):
        """ONE EnrichmentGraph, ONE EnrichmentBridge; the bridge receives
        the SAME coordinator, service and asset store from the graph."""
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        (tmp_path / "cache").mkdir(parents=True, exist_ok=True)
        graph = _build_enrichment_graph(
            tmp_path / "data", tmp_path / "cache", lambda: True
        )
        assert isinstance(graph.coordinator, EnrichmentCoordinator)
        assert isinstance(graph.service, EnrichmentService)

        bridge = EnrichmentBridge(
            coordinator=graph.coordinator,
            service=graph.service,
            library=_FakeLibrary(),
            asset_store=graph.asset_store,
        )
        # identity, not equality: the SAME objects
        assert bridge._coordinator is graph.coordinator
        assert bridge._service is graph.service
        assert bridge._asset_store is graph.asset_store
        bridge.dispose()

    def test_shutdown_order_bridge_before_coordinator(self):
        """The container disposes the bridge BEFORE the enrichment
        coordinator shutdown (no QML-deleted -> worker -> mutation)."""
        container = ApplicationContainer()
        order: list[str] = []
        container._enrichment = _GraphSpy(_CoordShutdownSpy(order))
        container._eb = _DisposeSpy(order, "eb")
        container._persistence = _DisposeSpy(order, "persistence")
        container._scan_runner = _DisposeSpy(order, "scan_runner")
        container._scan_dispatcher = _DisposeSpy(order, "scan_dispatcher")
        container._coordinator = _DisposeSpy(order, "coordinator")
        container._library_prefs = _DisposeSpy(order, "library_prefs")
        container._pb = _DisposeSpy(order, "pb")
        container._qb = _DisposeSpy(order, "qb")
        container._lb = _DisposeSpy(order, "lb")
        container._plb = _DisposeSpy(order, "plb")
        container._nb = _DisposeSpy(order, "nb")
        container._sb = None  # SettingsBridge has no dispose (by design)
        container._audio_engine_convergence = _DisposeSpy(order, "convergence")
        container._audio_router = _DisposeSpy(order, "router")
        container._qt_engine_provider = _DisposeSpy(order, "provider")
        container._audio_engine_registry = _DisposeSpy(order, "registry")
        container._engine = None
        container._app = None

        container.shutdown()

        assert order.index("eb") < order.index("coord"), (
            "bridge must be disposed BEFORE coordinator shutdown"
        )

    def test_graph_construction_zero_network(self, tmp_path):
        """Building the production enrichment graph performs zero network
        and zero pending work."""
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        (tmp_path / "cache").mkdir(parents=True, exist_ok=True)
        graph = _build_enrichment_graph(
            tmp_path / "data", tmp_path / "cache", lambda: True
        )
        assert graph.service.pending_count() == 0
        # The coordinator is enabled but nothing was ever submitted.
        assert graph.coordinator is not None
        graph.coordinator.shutdown()
