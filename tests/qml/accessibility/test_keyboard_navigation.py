"""Test Tab navigation through major pages.

Verifies KeyNavigation.tab chains, activeFocusOnTab, FocusScope, and
Keys.onReturnPressed/SpacePressed/EscapePressed patterns on all major pages."""

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
PAGES = [
    "devices/DevicesPage.qml",
    "home/HomePage.qml",
    "home_audio/HomeAudioPage.qml",
    "connections/ConnectionsPage.qml",
    "library/LibraryPage.qml",
    "history/HistoryPage.qml",
    "playlists/PlaylistsPage.qml",
    "search/GlobalSearchPage.qml",
    "radio/RadioPage.qml",
    "mix/MixHubPage.qml",
    "assistant/AssistantPage.qml",
    "audio_lab/AudioLabOverviewPage.qml",
]
pytestmark = [pytest.mark.qml_module("accessibility")]


@pytest.fixture(params=PAGES)
def page_path(request):
    p = QML_DIR / "pages" / request.param
    return p


class TestKeyboardTabNavigation:
    def test_page_has_focus_scope(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "FocusScope" in content, f"{page_path.name} lacks FocusScope"

    def test_page_has_active_focus_on_tab(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "activeFocusOnTab" in content, f"{page_path.name} lacks activeFocusOnTab"

    def test_page_has_key_navigation(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "KeyNavigation.tab" in content or "KeyNavigation.backtab" in content, \
            f"{page_path.name} lacks KeyNavigation chains"

    def test_page_has_on_return_pressed(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "Keys.onReturnPressed" in content, f"{page_path.name} lacks Keys.onReturnPressed"

    def test_page_has_on_space_pressed(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "Keys.onSpacePressed" in content or "Keys.onReturnPressed" in content, \
            f"{page_path.name} lacks keyboard activation keys"

    def test_page_has_on_escape_pressed(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "Keys.onEscapePressed" in content, f"{page_path.name} lacks Keys.onEscapePressed"

    def test_page_has_object_names(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "objectName:" in content, f"{page_path.name} lacks objectName on controls"
        count = content.count("objectName:")
        assert count >= 3, f"{page_path.name} has too few objectName declarations ({count})"


class TestKeyboardFocusAcrossPages:
    def test_radiopage_dialog_escape(self):
        p = QML_DIR / "pages/radio/RadioPage.qml"
        if not p.exists():
            pytest.skip("RadioPage.qml not found")
        content = p.read_text()
        assert "_showAddStation" not in content or "Keys.onEscapePressed" in content

    def test_playlist_escape_dismisses_dialogs(self):
        p = QML_DIR / "pages/playlists/PlaylistsPage.qml"
        if not p.exists():
            pytest.skip("PlaylistsPage.qml not found")
        content = p.read_text()
        assert "Keys.onEscapePressed" in content
        assert "createDialog.close()" in content or "createDialog.opened" in content

    def test_history_escape_dismisses_dialogs(self):
        p = QML_DIR / "pages/history/HistoryPage.qml"
        if not p.exists():
            pytest.skip("HistoryPage.qml not found")
        content = p.read_text()
        assert "Keys.onEscapePressed" in content
        assert "confirmClearDialog.close" in content or "confirmClearDialog.opened" in content

    def test_search_focus_management(self):
        p = QML_DIR / "pages/search/GlobalSearchPage.qml"
        if not p.exists():
            pytest.skip("GlobalSearchPage.qml not found")
        content = p.read_text()
        assert "Keys.onEscapePressed" in content

    def test_assistant_chat_input_focusable(self):
        p = QML_DIR / "pages/assistant/AssistantPage.qml"
        if not p.exists():
            pytest.skip("AssistantPage.qml not found")
        content = p.read_text()
        assert "activeFocusOnTab" in content
        assert "chatInput.activeFocus" in content or "onActiveFocusChanged" in content
