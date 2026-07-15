"""Tests for CapabilityAwarePage template."""


def test_capability_aware_page_loads():
    import os
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    assert os.path.exists(filepath)
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityAwarePage" in content or "Item" in content


def test_capability_aware_page_has_required_capabilities():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "requiredCapabilities" in content


def test_capability_aware_page_has_check_function():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "checkCapabilities" in content


def test_capability_aware_page_has_all_capabilities_flag():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "allCapabilitiesAvailable" in content


def test_capability_aware_page_has_checking_flag():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "checkingCapabilities" in content


def test_capability_aware_page_shows_loading_while_checking():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "LoadingState" in content or "checkingHost" in content


def test_capability_aware_page_shows_content_when_available():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "contentHost" in content
    assert "allCapabilitiesAvailable" in content


def test_capability_aware_page_shows_unavailable_when_missing():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "UnavailableState" in content
    assert "unavailableHost" in content


def test_capability_aware_page_has_retry():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "retry" in content


def test_capability_aware_page_has_accessible():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.role" in content
    assert "Accessible.name" in content
    assert "Accessible.description" in content


def test_capability_aware_page_has_object_name():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "objectName:" in content


def test_capability_aware_page_has_capability_bridge_property():
    filepath = "ui_qml/components/CapabilityAwarePage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "capabilityBridge" in content
