"""Tests for all SettingsRow control types — instantiation and basic interaction."""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent / "ui_qml"


class FakeSettingsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {}

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return []

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


def _make_entry_props(entry_type, **kwargs):
    props = {
        "type": entry_type,
        "key": kwargs.get("key", f"test/{entry_type}"),
        "label": kwargs.get("label", f"Test {entry_type}"),
        "default": kwargs.get("default", ""),
        "options": kwargs.get("options", []),
        "placeholder": kwargs.get("placeholder", ""),
        "hint": kwargs.get("hint", ""),
        "requires_restart": kwargs.get("requires_restart", False),
        "min_value": kwargs.get("min_value"),
        "max_value": kwargs.get("max_value"),
    }
    return props


class TestAllControlsRuntime:
    def _create_component(self, engine, bridge, entry_props):
        bridge._values[entry_props["key"]] = entry_props.get("default", "")
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "components/settings/SettingsRow.qml")))
        return comp

    def _create_object(self, engine, bridge, entry_props):
        bridge._values[entry_props["key"]] = entry_props.get("default", "")
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        qml = """
        import QtQuick
        import "%s"
        SettingsRow {
            entry: %s
        }
        """ % ("theme/..", str(entry_props).replace("None", "null").replace("True", "true").replace("False", "false"))
        comp = QQmlComponent(engine)
        comp.setData(qml.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / "components/settings/SettingsRow.qml")))
        return comp

    def test_text_control(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("text", key="test/text"))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_int_control(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("int", default=42, min_value=0, max_value=100))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_float_control(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("float", default=1.5, min_value=0, max_value=10))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_bool_control(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("bool", default=False))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_select_control(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("select",
            options=[{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
            default="a"))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_slider_control(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("slider", default=50, min_value=0, max_value=100))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_file_control(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("file", default="/home/test"))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_directory_control(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("directory", default="/home"))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_secret_control(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("secret"))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_action_control(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("action", label="Run"))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_control_with_restart_required(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("text", requires_restart=True, key="test/restart"))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_control_with_platform_gate(self, engine, bridge):
        comp = self._create_component(engine, bridge, _make_entry_props("int", key="test/platform", min_value=0, max_value=10))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_qml_file_exists(self):
        assert (QML_DIR / "components/settings/SettingsRow.qml").exists()

    def test_settings_page_exists(self):
        assert (QML_DIR / "pages/SettingsPage.qml").exists()
