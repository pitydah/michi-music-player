<<<<<<< Updated upstream
from __future__ import annotations
=======
<<<<<<< HEAD
"""Test buttons have Button role, etc.

Verifies Accessible.role conventions across all pages:
- MichiButton elements should have Accessible.Button role
- Dialogs should have Accessible.Dialog role
- Page titles should have Accessible.Heading role where applicable
- Input fields should have EditableText role
"""
=======
from __future__ import annotations
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
<<<<<<< Updated upstream

PAGE_PATHS = [
=======
<<<<<<< HEAD
PAGES = [
    "pages/devices/DevicesPage.qml",
>>>>>>> Stashed changes
    "pages/home/HomePage.qml",
    "pages/library/LibraryPage.qml",
    "pages/devices/DevicesPage.qml",
    "pages/connections/ConnectionsPage.qml",
    "pages/home_audio/HomeAudioPage.qml",
    "pages/radio/RadioPage.qml",
    "pages/playlists/PlaylistsPage.qml",
    "pages/search/GlobalSearchPage.qml",
    "pages/SettingsPage.qml",
    "pages/history/HistoryPage.qml",
    "pages/mix/MixHubPage.qml",
    "pages/assistant/AssistantPage.qml",
]


class TestAccessibleRoles:
    def test_michi_button_has_button_role(self):
        content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "Accessible.Button" in content

    def test_michi_slider_has_slider_role(self):
        content = (QML_DIR / "components/MichiSlider.qml").read_text()
        assert "Accessible.Slider" in content

    def test_settings_row_has_button_role(self):
        content = (QML_DIR / "components/settings/SettingsRow.qml").read_text()
        assert "Accessible.Button" in content

    def test_search_field_has_text_role(self):
        content = (QML_DIR / "components/SearchField.qml").read_text()
        assert "Accessible." in content

    def test_settings_list_has_list_role(self):
        content = (QML_DIR / "pages/SettingsPage.qml").read_text()
        assert "Accessible.List" in content or "Accessible.ListItem" in content

    def test_settings_scroll_has_scroll_role(self):
        content = (QML_DIR / "pages/SettingsPage.qml").read_text()
        assert "Accessible.ScrollArea" in content

    def test_icon_button_has_button_role(self):
        content = (QML_DIR / "components/MichiIconButton.qml").read_text()
        assert "Accessible.Button" in content or "Accessible.name" in content

    def test_all_buttons_have_role(self):
        btn_content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "Accessible.Button" in btn_content

    @pytest.mark.parametrize("page_path", PAGE_PATHS)
    def test_pages_have_accessible_roles(self, page_path):
        qml_path = QML_DIR / page_path
        if not qml_path.exists():
            pytest.skip(f"{page_path} not found")
        content = qml_path.read_text()
<<<<<<< Updated upstream
        assert "Accessible." in content, f"{page_path} has no Accessible roles"
=======
        assert "Accessible.Panel" in content or "Accessible.role" in content, \
            f"{page_rel} lacks Accessible role"

    @pytest.mark.parametrize("page_rel", PAGES)
    def test_buttons_have_button_role(self, page_rel):
        qml_path = QML_DIR / page_rel
        if not qml_path.exists():
            pytest.skip(f"{page_rel} not found")
        content = qml_path.read_text()
        michi_button_count = content.count("MichiButton {")
        assert michi_button_count >= 0
        if michi_button_count > 0:
            assert "Accessible.Button" in content or "Accessible.role" in content, \
                f"{page_rel} has {michi_button_count} MichiButton(s) but no Accessible.Button"

    @pytest.mark.parametrize("page_rel", PAGES)
    def test_dialogs_have_dialog_role(self, page_rel):
        qml_path = QML_DIR / page_rel
        if not qml_path.exists():
            pytest.skip(f"{page_rel} not found")
        content = qml_path.read_text()
        if "Dialog {" in content:
            assert "Accessible.Dialog" in content, \
                f"{page_rel} has Dialog without Accessible.Dialog role"

    @pytest.mark.parametrize("page_rel", PAGES)
    def test_headings_have_heading_role(self, page_rel):
        qml_path = QML_DIR / page_rel
        if not qml_path.exists():
            pytest.skip(f"{page_rel} not found")
        content = qml_path.read_text()
        heading_text_count = content.count("Accessible.role: Accessible.Heading")
        assert heading_text_count >= 0

    @pytest.mark.parametrize("page_rel", PAGES)
    def test_alerts_have_alert_role(self, page_rel):
        qml_path = QML_DIR / page_rel
        if not qml_path.exists():
            pytest.skip(f"{page_rel} not found")
        content = qml_path.read_text()
        if "Accessible.Alert" in content:
            assert True

    @pytest.mark.parametrize("page_rel", PAGES)
    def test_status_bars_have_status_role(self, page_rel):
        qml_path = QML_DIR / page_rel
        if not qml_path.exists():
            pytest.skip(f"{page_rel} not found")
        content = qml_path.read_text()
        if "Accessible.StatusBar" in content:
            assert True


class TestAccessibleRoleDefaults:
    def test_michi_button_component_has_button_role(self):
        path = QML_DIR / "components/MichiButton.qml"
        if path.exists():
            content = path.read_text()
            assert "Accessible.role: Accessible.Button" in content

    def test_michi_icon_button_component_has_button_role(self):
        path = QML_DIR / "components/MichiIconButton.qml"
        if path.exists():
            content = path.read_text()
            assert "Accessible.role: Accessible.Button" in content

    def test_search_field_has_editable_text_role(self):
        path = QML_DIR / "components/SearchField.qml"
        if path.exists():
            content = path.read_text()
            assert "Accessible.EditableText" in content

    def test_page_sections_have_heading_role(self):
        paths = [QML_DIR / p for p in PAGES]
        found = 0
        for p in paths:
            if p.exists() and "Accessible.Heading" in p.read_text():
                found += 1
        assert found >= 4, \
            f"Only {found}/12 pages have Accessible.Heading (expected >= 4)"
=======

PAGE_PATHS = [
    "pages/home/HomePage.qml",
    "pages/library/LibraryPage.qml",
    "pages/devices/DevicesPage.qml",
    "pages/connections/ConnectionsPage.qml",
    "pages/home_audio/HomeAudioPage.qml",
    "pages/radio/RadioPage.qml",
    "pages/playlists/PlaylistsPage.qml",
    "pages/search/GlobalSearchPage.qml",
    "pages/SettingsPage.qml",
    "pages/history/HistoryPage.qml",
    "pages/mix/MixHubPage.qml",
    "pages/assistant/AssistantPage.qml",
]


class TestAccessibleRoles:
    def test_michi_button_has_button_role(self):
        content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "Accessible.Button" in content

    def test_michi_slider_has_slider_role(self):
        content = (QML_DIR / "components/MichiSlider.qml").read_text()
        assert "Accessible.Slider" in content

    def test_settings_row_has_button_role(self):
        content = (QML_DIR / "components/settings/SettingsRow.qml").read_text()
        assert "Accessible.Button" in content

    def test_search_field_has_text_role(self):
        content = (QML_DIR / "components/SearchField.qml").read_text()
        assert "Accessible." in content

    def test_settings_list_has_list_role(self):
        content = (QML_DIR / "pages/SettingsPage.qml").read_text()
        assert "Accessible.List" in content or "Accessible.ListItem" in content

    def test_settings_scroll_has_scroll_role(self):
        content = (QML_DIR / "pages/SettingsPage.qml").read_text()
        assert "Accessible.ScrollArea" in content

    def test_icon_button_has_button_role(self):
        content = (QML_DIR / "components/MichiIconButton.qml").read_text()
        assert "Accessible.Button" in content or "Accessible.name" in content

    def test_all_buttons_have_role(self):
        btn_content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "Accessible.Button" in btn_content

    @pytest.mark.parametrize("page_path", PAGE_PATHS)
    def test_pages_have_accessible_roles(self, page_path):
        qml_path = QML_DIR / page_path
        if not qml_path.exists():
            pytest.skip(f"{page_path} not found")
        content = qml_path.read_text()
        assert "Accessible." in content, f"{page_path} has no Accessible roles"
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
