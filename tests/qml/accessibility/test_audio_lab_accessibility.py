from __future__ import annotations

"""MS: Specialized accessibility — Audio Lab page."""


def test_audio_lab_page_has_focus():
    filepath = "ui_qml/pages/audio_lab/AudioLabOverviewPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "focus: true" in content or "focus" in content


def test_audio_lab_page_has_accessible_role():
    filepath = "ui_qml/pages/audio_lab/AudioLabOverviewPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.role" in content


def test_audio_lab_page_has_accessible_name():
    filepath = "ui_qml/pages/audio_lab/AudioLabOverviewPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.name" in content


def test_audio_lab_page_keyboard_navigation():
    filepath = "ui_qml/pages/audio_lab/AudioLabOverviewPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "activeFocusOnTab" in content


def test_audio_lab_page_loading_accessible():
    filepath = "ui_qml/pages/audio_lab/AudioLabOverviewPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Loading" in content or "loading" in content


def test_audio_lab_page_error_accessible():
    filepath = "ui_qml/pages/audio_lab/AudioLabOverviewPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Error" in content or "error" in content or "UnavailableState" in content
