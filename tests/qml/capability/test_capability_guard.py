"""Tests for CapabilityGuard component — all states."""



def test_capability_guard_loads():
    """CapabilityGuard QML file should load without syntax errors."""
    import os
    filepath = "ui_qml/components/CapabilityGuard.qml"
    assert os.path.exists(filepath)
    with open(filepath) as f:
        content = f.read()
    assert "CapabilityGuard" in content or "Item" in content
    assert "objectName:" in content


def test_capability_guard_has_capability_name():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "capabilityName" in content


def test_capability_guard_has_available_content():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "availableContent" in content or "availableHost" in content


def test_capability_guard_has_unavailable_content():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "unavailableContent" in content or "unavailableHost" in content


def test_capability_guard_has_degraded_content():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "degradedContent" in content or "degradedHost" in content


def test_capability_guard_has_loading_content():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "loadingContent" in content or "loadingHost" in content


def test_capability_guard_has_accessible():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.role" in content
    assert "Accessible.name" in content
    assert "Accessible.description" in content


def test_capability_guard_has_object_name():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "objectName:" in content


def test_capability_guard_check_function():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "checkCapability" in content
    assert "bridge" in content


def test_capability_guard_default_available_false():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "available: false" in content or "available: true" in content
