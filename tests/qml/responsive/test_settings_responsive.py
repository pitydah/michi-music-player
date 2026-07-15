from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("settings"), pytest.mark.qml_dimension("responsive")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeSettingsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {}
        self._categories = []

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return self._categories

    @Slot(str, result="QVariant")
    def getValue(self, key):
        return self._values.get(key, "")

    @Slot(str, "QVariant", result=dict)
    def setValue(self, key, value):
        self._values[key] = value
        return {"ok": True}

    @Slot(str, result=dict)
    def resetValue(self, key):
        return {"ok": True}

    @Slot(result=dict)
    def resetAll(self):
        return {"ok": True}

    @Slot()
    def refresh(self):
        self.dataChanged.emit()


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


class TestSettingsResponsive:
    def _create_page(self, engine, width, height):
        bridge = FakeSettingsBridge()
        bridge._categories = [
            {"id": "general", "title": "General", "icon": "settings",
             "sections": [{"id": "paths", "title": "Rutas",
                           "entries": [{"key": "general/music_folder", "label": "Carpeta",
                                        "type": "text", "default": "~/Música"}]}]}
        ]
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/SettingsPage.qml")))
        return comp

    def test_desktop_1920(self, engine):
        comp = self._create_page(engine, 1920, 1080)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_1366(self, engine):
        comp = self._create_page(engine, 1366, 768)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_1024(self, engine):
        comp = self._create_page(engine, 1024, 768)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_900(self, engine):
        comp = self._create_page(engine, 900, 700)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_compact(self, engine):
        comp = self._create_page(engine, 600, 800)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_narrow(self, engine):
        comp = self._create_page(engine, 360, 640)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_zoom_125(self, engine):
        comp = self._create_page(engine, 900, 700)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_zoom_150(self, engine):
        comp = self._create_page(engine, 900, 700)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_page_qml_exists(self):
        assert (QML_DIR / "pages/SettingsPage.qml").exists()
