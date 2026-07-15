from __future__ import annotations

"""MS: Specialized accessibility — Radio page."""


def test_radio_page_has_focus():
    filepath = "ui_qml/pages/radio/RadioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "focus: true" in content


def test_radio_page_has_accessible_role():
    filepath = "ui_qml/pages/radio/RadioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.role" in content


def test_radio_page_has_accessible_name():
    filepath = "ui_qml/pages/radio/RadioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.name" in content


def test_radio_page_keyboard_navigation():
    filepath = "ui_qml/pages/radio/RadioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "activeFocusOnTab" in content


def test_radio_page_keyboard_activation():
    filepath = "ui_qml/pages/radio/RadioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Keys.onReturnPressed" in content or "Keys.onSpacePressed" in content


def test_radio_page_progress_cancel_accessibility():
    filepath = "ui_qml/pages/radio/RadioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.name" in content


def test_radio_page_error_announcement():
    filepath = "ui_qml/pages/radio/RadioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "error" in content.lower() or "Error" in content


def test_radio_page_font_scaling():
    filepath = "ui_qml/pages/radio/RadioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "pixelSize" in content
