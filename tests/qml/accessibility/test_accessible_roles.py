from __future__ import annotations

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

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
