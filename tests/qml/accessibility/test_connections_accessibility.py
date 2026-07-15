from __future__ import annotations

"""MS: Specialized accessibility — Connections page."""


def test_connections_page_has_focus():
    filepath = "ui_qml/pages/connections/ConnectionsPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "focus: true" in content


def test_connections_page_has_accessible_role():
    filepath = "ui_qml/pages/connections/ConnectionsPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.role" in content


def test_connections_page_has_accessible_name():
    filepath = "ui_qml/pages/connections/ConnectionsPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.name" in content


def test_connections_page_keyboard_navigation():
    filepath = "ui_qml/pages/connections/ConnectionsPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "activeFocusOnTab" in content


def test_connections_page_keyboard_activation():
    filepath = "ui_qml/pages/connections/ConnectionsPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Keys.onReturnPressed" in content or "Keys.onSpacePressed" in content


def test_connections_page_reduced_motion():
    filepath = "ui_qml/pages/connections/ConnectionsPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "MichiTheme" in content
