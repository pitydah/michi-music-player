"""Contract tests for CapabilityBridge and navigation gating."""
from __future__ import annotations

from ui_qml_bridge.capability_bridge import CapabilityBridge


class FakeSearchService:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def has_fts5(self):
        return self.enabled


class FakeContainer:
    def __init__(self, services=None):
        self.services = services or {}

    def contains(self, name):
        return name in self.services and self.services[name] is not None

    def get(self, name):
        return self.services.get(name)


class FakeNavigation:
    def __init__(self):
        self.available = set()

    def set_capabilities(self, capabilities):
        self.available = set(capabilities)


class FakeFactory:
    def __init__(self, bridges=None, services=None, capabilities=None):
        self._bridges = bridges or {}
        self._container = FakeContainer(services)
        self._capabilities = capabilities or {}

    @property
    def capabilities(self):
        return dict(self._capabilities)


def test_without_factory_reports_unavailable_capabilities():
    bridge = CapabilityBridge()

    result = bridge.refresh()

    assert result["eq"] == "unavailable"
    assert bridge.has("eq") is False
    assert bridge.state("eq") == "unavailable"


def test_refresh_marks_created_bridges_available():
    navigation = FakeNavigation()
    factory = FakeFactory(
        bridges={
            "navigation": navigation,
            "eq": object(),
            "home_audio": object(),
            "michi_ai": object(),
            "devices": object(),
        }
    )
    bridge = CapabilityBridge(factory=factory)

    result = bridge.refresh()

    assert result["eq"] == "available"
    assert result["transmit"] == "available"
    assert result["ai"] == "available"
    assert result["devices"] == "available"
    assert bridge.has("eq") is True


def test_refresh_wires_available_capabilities_into_navigation():
    navigation = FakeNavigation()
    factory = FakeFactory(
        bridges={
            "navigation": navigation,
            "audio_lab": object(),
            "connections": object(),
            "output_profiles": object(),
        }
    )
    bridge = CapabilityBridge(factory=factory)

    bridge.refresh()

    assert "audio_lab" in navigation.available
    assert "connections" in navigation.available
    assert "output_profiles" in navigation.available
    assert "disc_lab" not in navigation.available


def test_service_capabilities_are_reported_from_container():
    navigation = FakeNavigation()
    factory = FakeFactory(
        bridges={"navigation": navigation},
        services={
            "global_search_service": FakeSearchService(enabled=True),
            "radio_service": object(),
            "device_sync_service": object(),
            "home_audio_service": object(),
        },
    )
    bridge = CapabilityBridge(factory=factory)

    result = bridge.refresh()

    assert result["has_fts5"] == "available"
    assert result["has_radio"] == "available"
    assert result["has_sync"] == "available"
    assert result["has_home_audio"] == "available"
    assert result["has_snapcast"] == "available"


def test_explicit_factory_capability_is_preserved():
    navigation = FakeNavigation()
    factory = FakeFactory(
        bridges={"navigation": navigation},
        capabilities={"disc_lab": "available"},
    )
    bridge = CapabilityBridge(factory=factory)

    bridge.refresh()

    assert bridge.has("disc_lab") is True
    assert "disc_lab" in navigation.available
