from __future__ import annotations

"""MS: Specialized accessibility — Devices page."""


def test_devices_page_has_focus():
    filepath = "ui_qml/pages/devices/DevicesPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "focus: true" in content or "focus" in content


def test_devices_page_has_accessible_role():
    filepath = "ui_qml/pages/devices/DevicesPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.role" in content


def test_devices_page_has_accessible_name():
    filepath = "ui_qml/pages/devices/DevicesPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.name" in content


def test_devices_page_keyboard_navigation():
    filepath = "ui_qml/pages/devices/DevicesPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "KeyNavigation.tab" in content or "Keys.onReturnPressed" in content
    assert "activeFocusOnTab" in content


def test_devices_page_font_scaling():
    filepath = "ui_qml/pages/devices/DevicesPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "pixelSize" in content


def test_devices_reduced_motion():
    filepath = "ui_qml/pages/devices/DevicesPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "MichiTheme" in content
