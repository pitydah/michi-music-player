"""Verify NowPlayingBar and its popups compile and instantiate."""
import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine


@pytest.fixture(scope="module")
def engine():
    app = QGuiApplication.instance() or QGuiApplication([])
    e = QQmlEngine()
    e.addImportPath("ui_qml")
    return e


def test_nowplaying_bar_compiles(engine):
    """NowPlayingBar loads without errors."""
    c = QQmlComponent(engine)
    c.loadUrl("file://" + os.path.abspath("ui_qml/components/NowPlayingBar.qml"))
    assert c.status() != QQmlComponent.Error, f"Compile errors: {c.errors()}"


def test_audio_output_menu_compiles(engine):
    """AudioOutputMenu loads without errors."""
    c = QQmlComponent(engine)
    c.loadUrl("file://" + os.path.abspath("ui_qml/components/AudioOutputMenu.qml"))
    assert c.status() != QQmlComponent.Error, f"Compile errors: {c.errors()}"


def test_output_profile_menu_compiles(engine):
    """OutputProfileMenu loads without errors."""
    c = QQmlComponent(engine)
    c.loadUrl("file://" + os.path.abspath("ui_qml/components/OutputProfileMenu.qml"))
    assert c.status() != QQmlComponent.Error, f"Compile errors: {c.errors()}"


def test_no_show_profiles_property():
    """OutputProfileMenu does NOT have a 'showProfiles' property."""
    with open("ui_qml/components/OutputProfileMenu.qml") as f:
        content = f.read()
    assert "showProfiles" not in content, "showProfiles found in OutputProfileMenu.qml"


def test_output_and_profile_are_different_types():
    """The two popups in NowPlayingBar are different component types."""
    with open("ui_qml/components/NowPlayingBar.qml") as f:
        content = f.read()
    # Check both component types are referenced
    assert "AudioOutputMenu" in content, "AudioOutputMenu not found in NowPlayingBar"
    assert "OutputProfileMenu" in content, "OutputProfileMenu not found in NowPlayingBar"
    # Check showProfiles is NOT referenced
    assert "showProfiles" not in content, "showProfiles should not appear anywhere"
