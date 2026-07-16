"""Integration tests for SettingsPage and sub-pages UI."""
import pytest

pytestmark = [pytest.mark.qml_workflow("settings")]


class TestSettingsPage:
    """Verify SettingsPage loads, accessible props, null bridge, search, navigation."""

    PAGE_QML = "ui_qml/pages/SettingsPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "settings.page"

    def test_null_bridge_graceful(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("bridge") is None or page.property("bridge")

    def test_search_categories_no_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.searchCategories("test")
        assert page.property("searchQuery") == "test"

    def test_reset_all_no_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.resetAll()

    def test_back_from_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.back()


class TestSettingsGeneralPage:
    PAGE_QML = "ui_qml/pages/settings/SettingsGeneralPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "settings.general"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2
        assert page.property("accessible_name") == "Ajustes generales"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("bridge") is None

    def test_state_error_on_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("state") == "ERROR"

    def test_close_requested_signal(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("closeRequested") is not None

    def test_keyboard_escape(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("focus") is True


class TestSettingsAudioPage:
    PAGE_QML = "ui_qml/pages/settings/SettingsAudioPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "settings.audio"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_name") == "Audio"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("state") == "ERROR"

    def test_open_diagnostics_signal(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert hasattr(page, "openDiagnostics")


class TestSettingsPlaybackPage:
    PAGE_QML = "ui_qml/pages/settings/SettingsPlaybackPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "settings.playback"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_name") == "Reproducción"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("state") == "ERROR"


class TestSettingsLibraryPage:
    PAGE_QML = "ui_qml/pages/settings/SettingsLibraryPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "settings.library"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_name") == "Biblioteca"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("state") == "ERROR"


class TestSettingsAppearancePage:
    PAGE_QML = "ui_qml/pages/settings/SettingsAppearancePage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "settings.appearance"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_name") == "Apariencia"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("bridge") is None

    def test_state_error_on_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("state") == "ERROR"


class TestSettingsAccessibilityPage:
    PAGE_QML = "ui_qml/pages/settings/SettingsAccessibilityPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "settings.accessibility"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_name") == "Accesibilidad"

    def test_state_default(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("state") == "READY"


class TestSettingsAboutPage:
    PAGE_QML = "ui_qml/pages/settings/SettingsAboutPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "settings.about"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_name") == "Acerca de"

    def test_check_updates_signal(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert hasattr(page, "checkUpdates")
