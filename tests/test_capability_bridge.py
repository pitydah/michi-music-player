from ui_qml_bridge.capability_bridge import (
    BRIDGE_ALIASES,
    CapabilityBridge,
    _resolve_alias,
)


def test_resolve_alias_transforms_known_keys():
    assert _resolve_alias("transmit") == "home_audio"
    assert _resolve_alias("ai") == "michi_ai"
    assert _resolve_alias("library") == "library"
    assert _resolve_alias("unknown_key") == "unknown_key"


def test_state_uses_alias_resolution():
    bridge = CapabilityBridge()
    bridge.refresh()
    result = bridge.state("transmit")
    assert result == "unavailable"

    result = bridge.state("ai")
    assert result == "unavailable"


def test_refresh_returns_structured_dict():
    bridge = CapabilityBridge()
    result = bridge.refresh()

    assert result["ok"] is False
    assert result["error"] == "NO_FACTORY"


def test_refresh_with_factory_wires_capabilities():
    capabilities = {"library": "available", "home_audio": "available"}

    class FakeFactory:
        def __init__(self):
            self.bridges = {}

        def get(self, name):
            return self.bridges.get(name)

    factory = FakeFactory()
    factory.capabilities = dict(capabilities)
    bridge = CapabilityBridge(factory=factory)

    result = bridge.refresh()

    assert result["ok"] is True
    assert bridge.has("library") is True
    assert bridge.has("home_audio") is True
    assert bridge.state("transmit") == "available"


def test_label_preserves_compatibility():
    bridge = CapabilityBridge()

    assert bridge.label("home_audio") == "Home Audio"
    assert bridge.label("unknown") == "unknown"


def test_explicit_factory_capability_is_preserved():
    class FakeFactory:
        def __init__(self):
            self.bridges = {}
            self.capabilities = {"transmit": "deferred_physical"}

        def get(self, name):
            return self.bridges.get(name)

    bridge = CapabilityBridge(factory=FakeFactory())
    bridge.refresh()

    assert bridge.state("transmit") == "deferred_physical"
    assert bridge.has("transmit") is False


def test_bridge_aliases_map_correctly():
    assert "transmit" in BRIDGE_ALIASES
    assert BRIDGE_ALIASES["transmit"] == "home_audio"
    assert "ai" in BRIDGE_ALIASES
    assert BRIDGE_ALIASES["ai"] == "michi_ai"
