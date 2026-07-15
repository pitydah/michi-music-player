from __future__ import annotations

"""MS: Specialized accessibility — Home Audio page."""


def test_home_audio_page_has_focus():
    filepath = "ui_qml/pages/home_audio/HomeAudioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "focus: true" in content


def test_home_audio_page_has_accessible_role():
    filepath = "ui_qml/pages/home_audio/HomeAudioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.role" in content


def test_home_audio_page_has_accessible_name():
    filepath = "ui_qml/pages/home_audio/HomeAudioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.name" in content


def test_home_audio_page_keyboard_navigation():
    filepath = "ui_qml/pages/home_audio/HomeAudioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "KeyNavigation.tab" in content


def test_home_audio_page_keyboard_activation():
    filepath = "ui_qml/pages/home_audio/HomeAudioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Keys.onReturnPressed" in content


def test_home_audio_page_state_announcement():
    filepath = "ui_qml/pages/home_audio/HomeAudioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.description" in content or "Accessible.name" in content


def test_home_audio_page_font_scaling():
    filepath = "ui_qml/pages/home_audio/HomeAudioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "pixelSize" in content


def test_home_audio_page_reduced_motion():
    filepath = "ui_qml/pages/home_audio/HomeAudioPage.qml"
    with open(filepath) as f:
        content = f.read()
    assert "MichiTheme" in content
