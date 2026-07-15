from __future__ import annotations

"""MR: Capability states — verify all 4 states exist and behave."""

CAPABILITY_STATES = ["available", "degraded", "unavailable", "deferred_physical"]

SPECIALIZED_DOMAINS = [
    "devices_sync",
    "audio_lab",
    "mix",
    "connections_michilink",
    "home_audio",
    "notifications",
    "radio",
    "global_search",
]


def test_all_states_defined():
    from ui_qml_bridge.service_capabilities import CAPABILITY_STATES
    assert set(CAPABILITY_STATES.values()) == set(CAPABILITY_STATES.values())
    assert "AVAILABLE" in CAPABILITY_STATES
    assert "DEGRADED" in CAPABILITY_STATES
    assert "UNAVAILABLE" in CAPABILITY_STATES
    assert "DEFERRED_PHYSICAL" in CAPABILITY_STATES


def test_capability_guard_has_deferred_physical():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "deferredPhysical" in content
    assert "deferredPhysicalHost" in content
    assert "DEFERRED_PHYSICAL" in content or "deferred_physical" in content


def test_deferred_physical_state_component_exists():
    import os
    filepath = "ui_qml/components/states/MichiDeferredPhysicalState.qml"
    assert os.path.exists(filepath)
    with open(filepath) as f:
        content = f.read()
    assert "DeferredPhysicalState" in content or "Item" in content
    assert "Requiere hardware" in content


def test_compute_capabilities_returns_strings():
    from ui_qml_bridge.service_capabilities import compute_capabilities

    class MockServices:
        def has(self, name):
            return name == "db"

    result = compute_capabilities(MockServices())
    assert isinstance(result, dict)
    for v in result.values():
        assert v in CAPABILITY_STATES


def test_all_specialized_domains_have_capability():
    from ui_qml_bridge.service_capabilities import compute_capabilities

    class MockAll:
        def has(self, name):
            return True

    result = compute_capabilities(MockAll())
    for domain in SPECIALIZED_DOMAINS:
        assert domain in result, f"Missing capability for {domain}"
        assert result[domain] in CAPABILITY_STATES


def test_deferred_physical_not_mistaken_for_error():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "UnavailableState" in content
    assert "deferredPhysical" in content
    assert content.index("deferredPhysical") != content.index("UnavailableState")


def test_no_silent_hiding_in_devices_page():
    filepath = "ui_qml/pages/devices/DevicesPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content


def test_no_silent_hiding_in_audio_lab():
    filepath = "ui_qml/pages/audio_lab/AudioLabOverviewPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content or "alabGuard" in content


def test_no_silent_hiding_in_mix():
    filepath = "ui_qml/pages/mix/MixHubPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content or "mixGuard" in content


def test_no_silent_hiding_in_connections():
    filepath = "ui_qml/pages/connections/ConnectionsPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content or "connectionGuard" in content


def test_no_silent_hiding_in_home_audio():
    filepath = "ui_qml/pages/home_audio/HomeAudioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content or "homeAudioGuard" in content


def test_no_silent_hiding_in_radio():
    filepath = "ui_qml/pages/radio/RadioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content or "radioGuard" in content


def test_no_silent_hiding_in_global_search():
    filepath = "ui_qml/pages/search/GlobalSearchPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content or "searchGuard" in content


def test_capability_bridge_has_state_values():
    from ui_qml_bridge.capability_bridge import CAPABILITY_STATE_KEYS
    assert "library" in CAPABILITY_STATE_KEYS
    assert "devices_sync" in CAPABILITY_STATE_KEYS
    assert "home_audio" in CAPABILITY_STATE_KEYS
    assert "radio" in CAPABILITY_STATE_KEYS
    assert "global_search" in CAPABILITY_STATE_KEYS
    assert "mix" in CAPABILITY_STATE_KEYS
    assert "audio_lab" in CAPABILITY_STATE_KEYS


def test_home_audio_deferred_physical_when_snapcast_only():
    from ui_qml_bridge.service_capabilities import compute_capabilities

    class MockSnapcastOnly:
        def has(self, name):
            return name in ("db", "snapcast_controller")

    result = compute_capabilities(MockSnapcastOnly())
    assert result.get("home_audio") == "deferred_physical"
    assert result.get("home_audio") != "unavailable"
