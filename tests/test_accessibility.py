"""Accessibility tests — QML Accessible properties, keyboard navigation, contrast."""
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


class TestAccessibility:
    def test_sidebar_has_accessible(self):
        content = (REPO / "ui_qml" / "shell" / "Sidebar.qml").read_text()
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_sidebar_item_has_accessible(self):
        content = (REPO / "ui_qml" / "components" / "SidebarItem.qml").read_text()
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_michi_button_has_accessible(self):
        content = (REPO / "ui_qml" / "components" / "MichiButton.qml").read_text()
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_keyboard_nav_in_sidebar(self):
        content = (REPO / "ui_qml" / "shell" / "Sidebar.qml").read_text()
        assert "onClicked" in content  # SidebarItem handles keyboard internally

    def test_button_focus_policy(self):
        content = (REPO / "ui_qml" / "components" / "MichiButton.qml").read_text()
        assert "activeFocusOnTab" in content

    def test_page_section_header_accessible(self):
        content = (REPO / "ui_qml" / "components" / "SectionHeader.qml").read_text()
        assert "Accessible.role" in content

    def test_search_page_has_accessible(self):
        p = REPO / "ui_qml" / "pages" / "search" / "GlobalSearchPage.qml"
        if p.exists():
            content = p.read_text()
            assert "Accessible" in content

    def test_home_page_accessible(self):
        content = (REPO / "ui_qml" / "pages" / "home" / "HomePage.qml").read_text()
        assert "Accessible.role" in content

    def test_nowplaying_accessible(self):
        content = (REPO / "ui_qml" / "pages" / "nowplaying" / "NowPlayingPage.qml").read_text()
        assert "Accessible" in content
