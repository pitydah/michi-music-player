from unittest.mock import MagicMock

from core.service_container import ServiceContainer
from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.connections_bridge import ConnectionsBridge
from ui_qml_bridge.home_bridge import HomeBridge


class TestHomeBridge:
    def test_create(self):
        bridge = HomeBridge(db=MagicMock())
        assert bridge is not None

    def test_ecosystem_state_tracks_connections_bridge(self):
        connections = ConnectionsBridge()
        bridge = HomeBridge(connections_bridge=connections)
        changed = MagicMock()
        bridge.snapshotChanged.connect(changed)

        connections._set_state("connected")

        assert bridge.ecosystemState == "connected"
        changed.assert_called_once_with()

    def test_factory_injects_connections_bridge(self):
        factory = BridgeFactory(ServiceContainer())
        connections = ConnectionsBridge()
        factory._bridges["connections"] = connections

        factory.create_home_bridge()

        assert factory.get("home")._connections is connections

    def test_partial_service_failure_marks_snapshot_degraded(self):
        sources = MagicMock()
        sources.list.side_effect = RuntimeError("offline")
        bridge = HomeBridge(library_sources_service=sources)

        assert bridge.refresh() is True
        assert bridge.degraded is True
        assert "Fuentes" in bridge.degradedMessage
