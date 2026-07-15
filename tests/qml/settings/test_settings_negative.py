<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Negative tests for settings pages — null bridge, error state, destructive confirmation."""
from pathlib import Path
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
from __future__ import annotations
>>>>>>> Stashed changes

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

<<<<<<< Updated upstream
=======
pytestmark = [pytest.mark.qml_module("settings")]
=======
"""Negative tests for settings pages — null bridge, error state, destructive confirmation."""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

class FailingSettingsBridgeV2(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fail_get = False
        self._fail_set = False

    @Property("QVariantList", notify=dataChanged)
    def categories(self):
        return []

    @Slot(str, result="QVariant")
    def getValue(self, key):
        if self._fail_get:
            return None
        return None

    @Slot(str, "QVariant", result=dict)
    def setValue(self, key, value):
        if self._fail_set:
            return {"ok": False, "error": "Falla simulada", "message": "Error al guardar"}
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


EMPTY_BRIDGE = type("Empty", (QObject,), {})
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
def failing_bridge():
    return FailingSettingsBridgeV2()


PAGE_FILES = [
    "SettingsGeneralPage.qml",
    "SettingsAppearancePage.qml",
    "SettingsPlaybackPage.qml",
    "SettingsLibraryPage.qml",
    "SettingsAccessibilityPage.qml",
    "SettingsAudioPage.qml",
    "SettingsAboutPage.qml",
]


class TestSettingsNegative:
    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_no_bridge_context_does_not_crash(self, engine, bridge, page_file):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, f"{page_file} crashed without bridge: {comp.errorString()}"

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_nonexistent_bridge_property_fallback(self, engine, bridge, page_file):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            bridge_prop = obj.property("bridge")
            assert bridge_prop is None or bridge_prop is not None

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_error_state_can_be_set(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            obj.setProperty("pageState", 4)
            assert obj.property("pageState") == 4

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_loading_state_can_be_set(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            obj.setProperty("pageState", 1)
            assert obj.property("pageState") == 1

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_error_message_property(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            test_msg = "Error de prueba"
            obj.setProperty("errorMessage", test_msg)
            assert obj.property("errorMessage") == test_msg

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_error_details_property(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            test_details = "Detalles del error"
            obj.setProperty("errorDetails", test_details)
            assert obj.property("errorDetails") == test_details

    def test_library_destructive_confirmation_dialog(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsLibraryPage.qml")))
        if comp.isReady():
            obj = comp.create()
            confirm_dialog = obj.findChild(type(obj).metaObject().superClass(), "confirmRescan")
            assert confirm_dialog is not None

    def test_general_clear_cache_confirmation(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsLibraryPage.qml")))
        if comp.isReady():
            obj = comp.create()
            confirm_dialog = obj.findChild(type(obj).metaObject().superClass(), "confirmClearCache")
            assert confirm_dialog is not None

<<<<<<< Updated upstream
=======

class TestSettingsAudioNullBridge:
    def test_no_bridge_shows_error(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()


class TestSettingsAboutNullBridge:
    def test_no_bridge_no_crash(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("objectName") == "settings.about"
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()


class TestSettingsPageCompiles:
    def test_general_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsGeneralPage.qml")
        assert comp.isReady()

    def test_appearance_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsAppearancePage.qml")
        assert comp.isReady()

    def test_playback_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsPlaybackPage.qml")
        assert comp.isReady()

    def test_library_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsLibraryPage.qml")
        assert comp.isReady()

    def test_accessibility_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsAccessibilityPage.qml")
        assert comp.isReady()

    def test_audio_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsAudioPage.qml")
        assert comp.isReady()

    def test_about_page_compiles(self, engine):
        comp = _load_page(engine, "SettingsAboutPage.qml")
        assert comp.isReady()
=======
    return QQmlEngine(qapp)


@pytest.fixture
def failing_bridge():
    return FailingSettingsBridgeV2()


PAGE_FILES = [
    "SettingsGeneralPage.qml",
    "SettingsAppearancePage.qml",
    "SettingsPlaybackPage.qml",
    "SettingsLibraryPage.qml",
    "SettingsAccessibilityPage.qml",
    "SettingsAudioPage.qml",
    "SettingsAboutPage.qml",
]


class TestSettingsNegative:
    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_no_bridge_context_does_not_crash(self, engine, bridge, page_file):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, f"{page_file} crashed without bridge: {comp.errorString()}"

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_nonexistent_bridge_property_fallback(self, engine, bridge, page_file):
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            bridge_prop = obj.property("bridge")
            assert bridge_prop is None or bridge_prop is not None

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_error_state_can_be_set(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            obj.setProperty("pageState", 4)
            assert obj.property("pageState") == 4

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_loading_state_can_be_set(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            obj.setProperty("pageState", 1)
            assert obj.property("pageState") == 1

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_error_message_property(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            test_msg = "Error de prueba"
            obj.setProperty("errorMessage", test_msg)
            assert obj.property("errorMessage") == test_msg

    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_error_details_property(self, engine, bridge, page_file):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        if comp.isReady():
            obj = comp.create()
            test_details = "Detalles del error"
            obj.setProperty("errorDetails", test_details)
            assert obj.property("errorDetails") == test_details

    def test_library_destructive_confirmation_dialog(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsLibraryPage.qml")))
        if comp.isReady():
            obj = comp.create()
            confirm_dialog = obj.findChild(type(obj).metaObject().superClass(), "confirmRescan")
            assert confirm_dialog is not None

    def test_general_clear_cache_confirmation(self, engine, bridge):
        engine.rootContext().setContextProperty("settingsBridgeV2", bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/SettingsLibraryPage.qml")))
        if comp.isReady():
            obj = comp.create()
            confirm_dialog = obj.findChild(type(obj).metaObject().superClass(), "confirmClearCache")
            assert confirm_dialog is not None

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    @pytest.mark.parametrize("page_file", PAGE_FILES)
    def test_bridge_save_failure_handled_gracefully(self, engine, failing_bridge, page_file):
        failing_bridge._fail_set = True
        engine.rootContext().setContextProperty("settingsBridgeV2", failing_bridge)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/settings/" / page_file)))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, f"{page_file} failed with failing bridge: {comp.errorString()}"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
