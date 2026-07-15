<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Combined keyboard navigation tests for all 7 settings pages — Tab, Enter, Escape."""
from pathlib import Path
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
from __future__ import annotations

from unittest.mock import MagicMock
>>>>>>> Stashed changes

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

<<<<<<< Updated upstream
=======
pytestmark = [pytest.mark.qml_module("settings")]
=======
"""Combined keyboard navigation tests for all 7 settings pages — Tab, Enter, Escape."""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes


@pytest.fixture
def engine(qapp):
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    return QQmlEngine(qapp)
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    engine = QQmlEngine(qapp)
    engine.addImportPath(str(QML_DIR))
    return engine
>>>>>>> Stashed changes


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

<<<<<<< Updated upstream
=======
    def test_audio_escape_requests_close(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.audio"
        finally:
            obj.deleteLater()

    def test_about_escape_requests_close(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "settings.about"
        finally:
            obj.deleteLater()


class TestSettingsKeyboardTabOrder:
    def test_general_keyboard_tab_chain(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            lang = obj.findChild(object, "settings.general.language")
            if lang:
                tab = lang.property("KeyNavigation")["tab"]
                assert tab is not None
        finally:
            obj.deleteLater()

    def test_appearance_keyboard_tab_chain(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            sw = obj.findChild(object, "settings.appearance.reduceMotion")
            if sw:
                tab = sw.property("KeyNavigation")["tab"]
                assert tab is not None
        finally:
            obj.deleteLater()

    def test_audio_diagnostics_tab_chain(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "settings.audio.diagnostics")
            if btn:
                tab = btn.property("KeyNavigation")["tab"]
                assert tab is not None
        finally:
            obj.deleteLater()
=======
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

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_all_pages_create_successfully(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, f"{page_file} failed: {comp.errorString()}"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
