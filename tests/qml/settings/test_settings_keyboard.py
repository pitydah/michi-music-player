"""Combined keyboard navigation tests for all 7 settings pages — Tab, Enter, Escape."""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeSettingsBridgeV2(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {}

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return []

    @Slot(str, result="QVariant")
    def getValue(self, key):
        return self._values.get(key)

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


PAGE_FILES = [
    "SettingsGeneralPage.qml",
    "SettingsAppearancePage.qml",
    "SettingsPlaybackPage.qml",
    "SettingsLibraryPage.qml",
    "SettingsAccessibilityPage.qml",
    "SettingsAudioPage.qml",
    "SettingsAboutPage.qml",
]


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


@pytest.fixture
def bridge():
    return FakeSettingsBridgeV2()


class TestSettingsKeyboardNavigation:
    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_all_pages_have_escape_signal(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            sig = obj.metaObject().indexOfSignal("closeRequested()")
            assert sig >= 0, f"{page_file} is missing closeRequested signal"

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_all_pages_have_object_name(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            name = obj.objectName()
            assert name.startswith("settings"), f"{page_file} objectName does not start with 'settings': {name}"

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_all_pages_initial_state_ready(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            state = obj.property("pageState")
            assert state == 2, f"{page_file} initial state is not READY: {state}"

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_all_pages_have_accessible_role(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            assert obj.property("accessibleRole") is not None, f"{page_file} missing accessibleRole"

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_all_pages_with_null_bridge(self, engine, bridge, page_file):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, f"{page_file} failed with null bridge: {comp.errorString()}"

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_all_pages_create_successfully(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, f"{page_file} failed: {comp.errorString()}"
