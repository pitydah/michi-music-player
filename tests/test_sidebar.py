"""Tests for sidebar routing and UI structure."""
import unicodedata

import pytest


def _is_emoji(char: str) -> bool:
    """Return True if char is an emoji (So category) but not a known UI symbol."""
    # U+25BE ▾ and U+25B8 ▸ are geometric shapes used for chevrons, not emojis
    KNOWN_NON_EMOJI_SO = {"▾", "▸", "▪", "▫", "●", "○", "◆", "◇", "►", "◄"}
    if char in KNOWN_NON_EMOJI_SO:
        return False
    return unicodedata.category(char) == "So"


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
        from ui_qml_bridge.route_registry import get_sidebar_sections
        sections, fixed = get_sidebar_sections()
        all_routes = [s["route"] for s in sections]
        for s in sections:
            all_routes.extend(c["route"] for c in s.get("children", []))
        all_routes.extend(f["route"] for f in fixed)
        expected = [
            "home", "library", "mix", "streaming", "playlists",
            "connections", "audio_lab", "home_audio", "michi_ai", "sync",
            "settings",
        ]
        for route in expected:
            assert route in all_routes, f"Route {route} not found in sidebar sections"

    def test_sidebar_no_emoji(self):
        from pathlib import Path
        content = Path("ui_qml/shell/Sidebar.qml").read_text()
        for char in content:
            if _is_emoji(char):
                pytest.fail(f"Emoji found in Sidebar.qml: {char}")

    def test_sidebar_sections_correct(self):
        from ui_qml_bridge.route_registry import get_sidebar_sections
        sections, _fixed = get_sidebar_sections()
        titles = [s["title"] for s in sections]
        for expected_title in ("Inicio", "Biblioteca", "Streaming", "Audio Lab",
                               "Home Audio", "Conexiones", "Michi Sync Suite"):
            assert expected_title in titles, \
                f"Section '{expected_title}' not found in sidebar registry"


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
