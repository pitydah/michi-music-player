"""Tests for sidebar routing and UI structure."""
import pytest


class TestSidebarRoutes:
    def test_sidebar_qml_exists(self):
        from pathlib import Path
        sidebar = Path("ui_qml/shell/Sidebar.qml")
        assert sidebar.exists(), "Sidebar.qml not found"

    def test_sidebar_item_component_exists(self):
        from pathlib import Path
        item = Path("ui_qml/components/SidebarItem.qml")
        assert item.exists(), "SidebarItem.qml not found"

    def test_sidebar_section_component_exists(self):
        from pathlib import Path
        section = Path("ui_qml/components/SidebarSection.qml")
        assert section.exists(), "SidebarSection.qml not found"

    def test_sidebar_routes_defined(self):
        from pathlib import Path
        content = Path("ui_qml/shell/Sidebar.qml").read_text()
        expected_routes = [
            "home", "library", "mix", "playlists", "radio",
            "connections", "devices", "home_audio",
            "audio_lab", "metadata.inspector", "library_doctor",
            "equalizer", "outputs",
            "search", "assistant", "queue", "history", "settings",
        ]
        for route in expected_routes:
            assert route in content, f"Route {route} not found in Sidebar.qml"

    def test_sidebar_no_emoji(self):
        from pathlib import Path
        content = Path("ui_qml/shell/Sidebar.qml").read_text()
        import unicodedata
        for char in content:
            if unicodedata.category(char) == 'So':  # Symbol, Other = emoji
                pytest.fail(f"Emoji found in Sidebar.qml: {char}")

    def test_sidebar_sections_correct(self):
        from pathlib import Path
        content = Path("ui_qml/shell/Sidebar.qml").read_text()
        assert "ESCUCHAR" in content
        assert "ECOSISTEMA" in content
        assert "HERRAMIENTAS" in content
        assert "ACCESOS" in content


class TestSkeleton:
    def test_skeleton_component_exists(self):
        from pathlib import Path
        s = Path("ui_qml/components/Skeleton.qml")
        assert s.exists(), "Skeleton.qml not found"

    def test_skeleton_card_exists(self):
        from pathlib import Path
        sc = Path("ui_qml/components/SkeletonCard.qml")
        assert sc.exists(), "SkeletonCard.qml not found"


class TestAccessibility:
    def test_sidebar_accessible(self):
        from pathlib import Path
        content = Path("ui_qml/shell/Sidebar.qml").read_text()
        assert "Accessible" in content

    def test_sidebar_item_accessible(self):
        from pathlib import Path
        content = Path("ui_qml/components/SidebarItem.qml").read_text()
        assert "Accessible.role" in content
        assert "Accessible.name" in content
