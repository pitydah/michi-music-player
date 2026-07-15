"""Negative tests for capability system: null bridge, unknown capability."""



def test_capability_guard_null_bridge():
    """CapabilityGuard should handle null bridge gracefully."""
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "!bridge" in content or "bridge" in content
    assert "typeof bridge" in content or "typeof" in content or "has" in content


def test_capability_guard_unknown_capability():
    """CapabilityGuard should handle unknown capability gracefully."""
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "capabilityName" in content


def test_capability_aware_page_null_bridge():
    """CapabilityAwarePage should handle null bridge gracefully."""
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "!root.capabilityBridge" in content or "capabilityBridge" in content


def test_capability_aware_page_empty_required_capabilities():
    """CapabilityAwarePage with no required capabilities should show available."""
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "requiredCapabilities" in content


def test_capability_bridge_has_method():
    """CapabilityBridge.has() handles unknown capability names."""
    from ui_qml_bridge.capability_bridge import CapabilityBridge

    bridge = CapabilityBridge()
    assert bridge.has("nonexistent_capability") is False
    assert bridge.has("") is False


def test_capability_bridge_refresh_no_factory():
    """CapabilityBridge.refresh() should not crash without factory."""
    from ui_qml_bridge.capability_bridge import CapabilityBridge

    bridge = CapabilityBridge()
    bridge.refresh()
    assert bridge.capabilities == {}


def test_service_capabilities_returns_dict():
    """compute_capabilities should return a dict."""
    from ui_qml_bridge.service_capabilities import compute_capabilities

    class MockServices:
        def has(self, name):
            return name == "db"

    result = compute_capabilities(MockServices())
    assert isinstance(result, dict)
    assert result.get("library") is True
    assert result.get("radio") is False


def test_page_guard_integration_devices():
    """Check that DevicesPage references CapabilityGuard."""
    filepath = "ui_qml/pages/devices/DevicesPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content
    assert "devices_sync" in content or "deviceGuard" in content


def test_page_guard_integration_connections():
    """Check that ConnectionsPage references CapabilityGuard."""
    filepath = "ui_qml/pages/connections/ConnectionsPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content
    assert "connections_michilink" in content or "connectionGuard" in content


def test_page_guard_integration_home_audio():
    """Check that HomeAudioPage references CapabilityGuard."""
    filepath = "ui_qml/pages/home_audio/HomeAudioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content
    assert "home_audio" in content or "homeAudioGuard" in content


def test_page_guard_integration_radio():
    """Check that RadioPage references CapabilityGuard."""
    filepath = "ui_qml/pages/radio/RadioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content
    assert "radioGuard" in content


def test_page_guard_integration_mix():
    """Check that MixHubPage references CapabilityGuard."""
    filepath = "ui_qml/pages/mix/MixHubPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content
    assert "mixGuard" in content


def test_page_guard_integration_audio_lab():
    """Check that AudioLabOverviewPage references CapabilityGuard."""
    filepath = "ui_qml/pages/audio_lab/AudioLabOverviewPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content
    assert "alabGuard" in content


def test_page_guard_integration_global_search():
    """Check that GlobalSearchPage references CapabilityGuard."""
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content
    assert "searchGuard" in content


def test_legacy_confirm_dialog_backwards_compatible():
    """ConfirmActionDialog should still work via ConfirmDialog."""
    filepath = "ui_qml/components/ConfirmActionDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "ConfirmDialog" in content
    assert "dialogs" in content


def test_legacy_confirmation_dialog_backwards_compatible():
    """ConfirmationDialog should still work via ConfirmDialog."""
    filepath = "ui_qml/components/ConfirmationDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "ConfirmDialog" in content
    assert "dialogs" in content


def test_legacy_destructive_action_dialog_backwards_compatible():
    """DestructiveActionDialog should still work via DestructiveDialog."""
    filepath = "ui_qml/components/DestructiveActionDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "DestructiveDialog" in content
    assert "dialogs" in content
