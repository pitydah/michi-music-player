from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge


class TestRouteRegistryBridge:
    def test_create(self):
        bridge = RouteRegistryBridge()
        assert bridge is not None
