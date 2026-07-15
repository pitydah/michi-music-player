"""Test all interactive controls have Accessible.name.

Verifies every QML page's interactive controls declare Accessible.name,
Accessible.description, and Accessible.role where applicable."""

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
PAGES = [
    "pages/devices/DevicesPage.qml",
    "pages/home/HomePage.qml",
    "pages/home_audio/HomeAudioPage.qml",
    "pages/connections/ConnectionsPage.qml",
    "pages/library/LibraryPage.qml",
    "pages/history/HistoryPage.qml",
    "pages/playlists/PlaylistsPage.qml",
    "pages/search/GlobalSearchPage.qml",
    "pages/radio/RadioPage.qml",
    "pages/mix/MixHubPage.qml",
    "pages/assistant/AssistantPage.qml",
    "pages/audio_lab/AudioLabOverviewPage.qml",
]
pytestmark = [pytest.mark.qml_module("accessibility")]


class TestAccessibleNames:
    @pytest.mark.parametrize("page_rel", PAGES)
    def test_page_has_accessible_names(self, page_rel):
        qml_path = QML_DIR / page_rel
        if not qml_path.exists():
            pytest.skip(f"{page_rel} not found")
        content = qml_path.read_text()
        assert "Accessible.name" in content, f"{page_rel} lacks Accessible.name"

    @pytest.mark.parametrize("page_rel", PAGES)
    def test_page_has_accessible_description(self, page_rel):
        qml_path = QML_DIR / page_rel
        if not qml_path.exists():
            pytest.skip(f"{page_rel} not found")
        content = qml_path.read_text()
        assert "Accessible.description" in content, f"{page_rel} lacks Accessible.description"

    @pytest.mark.parametrize("page_rel", PAGES)
    def test_page_has_accessible_role(self, page_rel):
        qml_path = QML_DIR / page_rel
        if not qml_path.exists():
            pytest.skip(f"{page_rel} not found")
        content = qml_path.read_text()
        assert "Accessible.role" in content, f"{page_rel} lacks Accessible.role"

    @pytest.mark.parametrize("page_rel", PAGES)
    def test_page_has_accessible_name_on_buttons(self, page_rel):
        qml_path = QML_DIR / page_rel
        if not qml_path.exists():
            pytest.skip(f"{page_rel} not found")
        content = qml_path.read_text()
        lines = content.split("\n")
        button_accessible = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("MichiButton") or stripped.startswith("Button {"):
                accessible_found = False
                for j in range(i, min(i + 15, len(lines))):
                    if "Accessible.name" in lines[j] or "accessibleName" in lines[j]:
                        accessible_found = True
                        break
                    if "}" in lines[j] and j > i + 1:
                        break
                if not accessible_found:
                    button_accessible += 1
        assert button_accessible == 0, \
            f"{page_rel} has {button_accessible} buttons without Accessible.name"

    @pytest.mark.parametrize("page_rel", PAGES)
    def test_accessible_name_not_empty(self, page_rel):
        qml_path = QML_DIR / page_rel
        if not qml_path.exists():
            pytest.skip(f"{page_rel} not found")
        content = qml_path.read_text()
        name_assignments = [
            line.split("Accessible.name:")[1].strip()
            for line in content.split("\n")
            if "Accessible.name:" in line
        ]
        for assignment in name_assignments:
            val = assignment.strip()
            assert val != "", f"{page_rel} has empty Accessible.name"
            assert val != '""', f"{page_rel} has empty string Accessible.name"

    def test_all_pages_have_accessible_names_on_michi_buttons(self):
        for page_rel in PAGES:
            qml_path = QML_DIR / page_rel
            if not qml_path.exists():
                continue
            content = qml_path.read_text()
            btn_count = content.count("MichiButton {")
            accessible_count = content.count("Accessible.name")
            assert accessible_count >= btn_count, \
                f"{page_rel}: {btn_count} MichiButton(s) but only {accessible_count} Accessible.name"

    def test_object_name_exists_on_controls(self):
        for page_rel in PAGES:
            qml_path = QML_DIR / page_rel
            if not qml_path.exists():
                continue
            content = qml_path.read_text()
            obj_count = content.count("objectName:")
            assert obj_count >= 5, \
                f"{page_rel} has only {obj_count} objectName declarations (expected >= 5)"
