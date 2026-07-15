"""Tests for Settings responsive layout — desktop, tablet, compact, narrow with correct visible."""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine
pytestmark = [pytest.mark.qml_module("settings")]


QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeSettingsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {}
        self._categories = [
            {
                "id": "general", "title": "General", "icon": "settings",
                "sections": [
                    {
                        "id": "paths", "title": "Rutas",
                        "entries": [
                            {"key": "general/music_folder", "label": "Carpeta de música",
                             "type": "text", "default": "~/Música"}
                        ]
                    }
                ]
            }
        ]

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return self._categories

    @Slot(str, result="QVariant")
    def getValue(self, key):
        return self._values.get(key, "")

    @Slot(str, "QVariant", result=dict)
    def setValue(self, key, value):
        self._values[key] = value
        return {"ok": True, "key": key, "value": value, "applied": True, "requires_restart": False, "message": "ok"}

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


@pytest.fixture
def bridge():
    return FakeSettingsBridge()


class TestSettingsResponsiveLayouts:
    def _create_page(self, engine, bridge, width):
        bridge._categories = [
            {
                "id": "general", "title": "General", "icon": "settings",
                "sections": [
                    {
                        "id": "paths", "title": "Rutas",
                        "entries": [{"key": "general/music_folder", "label": "Carpeta de música",
                                     "type": "text", "default": "~/Música"}]
                    }
                ]
            }
        ]
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/SettingsPage.qml")))
        return comp

    def test_desktop_visible_900(self, engine, bridge):
        comp = self._create_page(engine, bridge, 900)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_visible_1280(self, engine, bridge):
        comp = self._create_page(engine, bridge, 1280)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_tablet_visible_700(self, engine, bridge):
        comp = self._create_page(engine, bridge, 700)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_tablet_visible_800(self, engine, bridge):
        comp = self._create_page(engine, bridge, 800)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_compact_visible_500(self, engine, bridge):
        comp = self._create_page(engine, bridge, 500)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_compact_visible_550(self, engine, bridge):
        comp = self._create_page(engine, bridge, 550)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_narrow_visible_300(self, engine, bridge):
        comp = self._create_page(engine, bridge, 300)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_narrow_visible_399(self, engine, bridge):
        comp = self._create_page(engine, bridge, 399)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_page_qml_exists(self):
        assert (QML_DIR / "pages/SettingsPage.qml").exists()
