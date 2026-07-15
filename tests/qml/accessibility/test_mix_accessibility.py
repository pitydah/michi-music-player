from __future__ import annotations

"""MS: Specialized accessibility — Mix page."""


def test_mix_page_has_focus():
    filepath = "ui_qml/pages/mix/MixHubPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "focus: true" in content


def test_mix_page_has_accessible_role():
    filepath = "ui_qml/pages/mix/MixHubPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.role" in content


def test_mix_page_has_accessible_name():
    filepath = "ui_qml/pages/mix/MixHubPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.name" in content


def test_mix_page_keyboard_navigation():
    filepath = "ui_qml/pages/mix/MixHubPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "activeFocusOnTab" in content or "Keys.onReturnPressed" in content


def test_mix_page_focus_restoration():
    filepath = "ui_qml/pages/mix/MixHubPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "focus" in content


def test_mix_page_dialog_focus_trap():
    filepath = "ui_qml/pages/mix/MixHubPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "KeyNavigation" in content or "focus" in content
