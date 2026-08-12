"""SettingsView geometry smoke and ownership verification."""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Property, QObject, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path("src/michi/presentation/qml").resolve()


class FakePlayback(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._volume = 50
        self._muted = False

    def _get_volume(self):
        return self._volume

    def _get_muted(self):
        return self._muted

    @Slot(int)
    def set_volume(self, v):
        self._volume = v

    @Slot(bool)
    def set_muted(self, m):
        self._muted = m

    volume = Property(int, _get_volume)
    muted = Property(bool, _get_muted)


class FakeLibrary(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dir = "/music"

    def _get_dir(self):
        return self._dir

    currentDir = Property(str, _get_dir)


class FakeNav(QObject):
    @Slot(str)
    def navigate(self, route):
        pass


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestSettingsViewGeometry:
    def test_panels_have_positive_size(self, qapp):
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))

        playback = FakePlayback()
        library = FakeLibrary()
        nav = FakeNav()

        ctx = engine.rootContext()
        ctx.setContextProperty("playback", playback)
        ctx.setContextProperty("library", library)
        ctx.setContextProperty("navigation", nav)

        component = QQmlComponent(engine, str(QML_DIR / "views" / "SettingsView.qml"))
        assert component.status() == QQmlComponent.Ready

        obj = component.create()
        assert obj is not None

        # Give geometry time to resolve
        obj.setProperty("width", 1000)
        obj.setProperty("height", 700)

        playback_panel = obj.findChild(QObject, "playbackSettingsPanel")
        library_panel = obj.findChild(QObject, "librarySettingsPanel")

        assert playback_panel is not None, "playbackSettingsPanel not found"
        assert library_panel is not None, "librarySettingsPanel not found"

        assert playback_panel.property("width") > 0
        assert playback_panel.property("height") > 0
        assert library_panel.property("width") > 0
        assert library_panel.property("height") > 0

        obj.deleteLater()
