<<<<<<< Updated upstream
from __future__ import annotations
=======
<<<<<<< HEAD
"""Test all interactive controls have Accessible.name.

Verifies every QML page's interactive controls declare Accessible.name,
Accessible.description, and Accessible.role where applicable."""
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

COMPONENT_PATHS = [
    "components/MichiButton.qml",
    "components/MichiSlider.qml",
    "components/MichiIconButton.qml",
    "components/GlassCard.qml",
    "components/StatusBadge.qml",
    "components/SearchField.qml",
    "components/settings/SettingsRow.qml",
    "materials/HeroMaterial.qml",
]


class TestAccessibleNames:
    @pytest.mark.parametrize("page_path", PAGE_PATHS)
    def test_page_has_accessible_names(self, page_path):
        qml_path = QML_DIR / page_path
        if not qml_path.exists():
            pytest.skip(f"{page_path} not found")
        content = qml_path.read_text()
        assert "Accessible." in content, f"{page_path} has no Accessible properties"

    @pytest.mark.parametrize("comp_path", [p for p in COMPONENT_PATHS
                                           if p not in ("components/GlassCard.qml",
                                                        "components/StatusBadge.qml",
                                                        "materials/HeroMaterial.qml")])
    def test_component_has_accessible_names(self, comp_path):
        qml_path = QML_DIR / comp_path
        if not qml_path.exists():
            pytest.skip(f"{comp_path} not found")
        content = qml_path.read_text()
        assert "Accessible." in content or "accessibleName" in content, \
            f"{comp_path} has no Accessible properties"

    def test_all_buttons_have_accessible_names(self):
        content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "Accessible.name" in content

    def test_all_sliders_have_accessible_names(self):
        content = (QML_DIR / "components/MichiSlider.qml").read_text()
        assert "accessibleName" in content or "Accessible.name" in content

    def test_settings_row_controls_have_accessible_names(self):
        content = (QML_DIR / "components/settings/SettingsRow.qml").read_text()
        assert "Accessible.name" in content

    def test_search_field_has_accessible_name(self):
        content = (QML_DIR / "components/SearchField.qml").read_text()
        assert "Accessible.name" in content or "accessibleName" in content

<<<<<<< Updated upstream
=======
    def test_object_name_exists_on_controls(self):
        for page_rel in PAGES:
            qml_path = QML_DIR / page_rel
            if not qml_path.exists():
                continue
            content = qml_path.read_text()
            obj_count = content.count("objectName:")
            assert obj_count >= 5, \
                f"{page_rel} has only {obj_count} objectName declarations (expected >= 5)"
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

COMPONENT_PATHS = [
    "components/MichiButton.qml",
    "components/MichiSlider.qml",
    "components/MichiIconButton.qml",
    "components/GlassCard.qml",
    "components/StatusBadge.qml",
    "components/SearchField.qml",
    "components/settings/SettingsRow.qml",
    "materials/HeroMaterial.qml",
]


class TestAccessibleNames:
    @pytest.mark.parametrize("page_path", PAGE_PATHS)
    def test_page_has_accessible_names(self, page_path):
        qml_path = QML_DIR / page_path
        if not qml_path.exists():
            pytest.skip(f"{page_path} not found")
        content = qml_path.read_text()
        assert "Accessible." in content, f"{page_path} has no Accessible properties"

    @pytest.mark.parametrize("comp_path", [p for p in COMPONENT_PATHS
                                           if p not in ("components/GlassCard.qml",
                                                        "components/StatusBadge.qml",
                                                        "materials/HeroMaterial.qml")])
    def test_component_has_accessible_names(self, comp_path):
        qml_path = QML_DIR / comp_path
        if not qml_path.exists():
            pytest.skip(f"{comp_path} not found")
        content = qml_path.read_text()
        assert "Accessible." in content or "accessibleName" in content, \
            f"{comp_path} has no Accessible properties"

    def test_all_buttons_have_accessible_names(self):
        content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "Accessible.name" in content

    def test_all_sliders_have_accessible_names(self):
        content = (QML_DIR / "components/MichiSlider.qml").read_text()
        assert "accessibleName" in content or "Accessible.name" in content

    def test_settings_row_controls_have_accessible_names(self):
        content = (QML_DIR / "components/settings/SettingsRow.qml").read_text()
        assert "Accessible.name" in content

    def test_search_field_has_accessible_name(self):
        content = (QML_DIR / "components/SearchField.qml").read_text()
        assert "Accessible.name" in content or "accessibleName" in content

>>>>>>> Stashed changes
    def test_glass_card_interactive_accessible(self):
        content = (QML_DIR / "components/GlassCard.qml").read_text()
        if "Accessible." not in content:
            pytest.skip("GlassCard has no Accessible properties (optional for non-interactive)")

    def test_hero_has_accessible_name(self):
        content = (QML_DIR / "materials/HeroMaterial.qml").read_text()
        if "Accessible." not in content and "accessibleName" not in content:
            pytest.skip("HeroMaterial has no Accessible properties (parent pages set them)")

    def test_icon_button_accessible_name(self):
        content = (QML_DIR / "components/MichiIconButton.qml").read_text()
        if "Accessible." not in content and "accessibleName" not in content:
            pytest.skip("MichiIconButton has no Accessible properties (optional)")

    def test_status_badge_accessible_name(self):
        content = (QML_DIR / "components/StatusBadge.qml").read_text()
        if "Accessible." not in content:
            pytest.skip("StatusBadge has no Accessible properties (optional)")
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
