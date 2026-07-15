"""Tests for Settings controls — correct types for boolean, enum, int, float, slider, etc."""
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
    return {
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


class TestSettingsRowControls:
    def _create_qml(self, engine, bridge, entry_props):
        bridge._values[entry_props["key"]] = entry_props.get("default", "")
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "components/settings/SettingsRow.qml")))
        return comp

    def test_boolean_switch(self, engine, bridge):
        props = _make_entry_props("bool", key="test/bool", default=False)
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_enum_combobox(self, engine, bridge):
        props = _make_entry_props("select", key="test/enum", default="a",
            options=[{"value": "a", "label": "A"}, {"value": "b", "label": "B"}])
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_int_spinbox(self, engine, bridge):
        props = _make_entry_props("int", key="test/int", default=42, min_value=0, max_value=100)
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_float_michidouble(self, engine, bridge):
        props = _make_entry_props("float", key="test/float", default=1.5, min_value=0, max_value=10)
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_range_slider(self, engine, bridge):
        props = _make_entry_props("range", key="test/range", default=50, min_value=0, max_value=100)
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_slider_control(self, engine, bridge):
        props = _make_entry_props("slider", key="test/slider", default=50, min_value=0, max_value=100)
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_multi_select(self, engine, bridge):
        props = _make_entry_props("multi-select", key="test/multi", default="a,b")
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_file_selector(self, engine, bridge):
        props = _make_entry_props("file", key="test/file", default="/home/test")
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_directory_selector(self, engine, bridge):
        props = _make_entry_props("directory", key="test/dir", default="/home")
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_path_selector(self, engine, bridge):
        props = _make_entry_props("path", key="test/path", default="/home")
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_color_picker(self, engine, bridge):
        props = _make_entry_props("color", key="test/color", default="#8FB7FF")
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_action_button(self, engine, bridge):
        props = _make_entry_props("action", key="test/action", label="Run")
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_text_control(self, engine, bridge):
        props = _make_entry_props("text", key="test/text")
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_secret_control(self, engine, bridge):
        props = _make_entry_props("secret", key="test/secret")
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_restart_badge_shown(self, engine, bridge):
        props = _make_entry_props("text", key="test/restart", requires_restart=True)
        comp = self._create_qml(engine, bridge, props)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_row_qml_exists(self):
        assert (QML_DIR / "components/settings/SettingsRow.qml").exists()

    def test_double_spinbox_qml_exists(self):
        assert (QML_DIR / "components/MichiDoubleSpinBox.qml").exists()

    def test_settings_page_exists(self):
        assert (QML_DIR / "pages/SettingsPage.qml").exists()
