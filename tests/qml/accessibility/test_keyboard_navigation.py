<<<<<<< Updated upstream
from __future__ import annotations
=======
<<<<<<< HEAD
"""Test Tab navigation through major pages.

Verifies KeyNavigation.tab chains, activeFocusOnTab, FocusScope, and
Keys.onReturnPressed/SpacePressed/EscapePressed patterns on all major pages."""
=======
from __future__ import annotations
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

from pathlib import Path

import pytest
<<<<<<< Updated upstream
from PySide6.QtQml import QQmlEngine
=======
<<<<<<< HEAD
>>>>>>> Stashed changes

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

KEY_NAV_PATTERNS = [
    "KeyNavigation.tab",
    "KeyNavigation.backtab",
    "Keys.onReturnPressed",
    "Keys.onSpacePressed",
    "Keys.onEscapePressed",
    "activeFocusOnTab",
    "focus",
    "focusPolicy",
]


@pytest.fixture
def engine(qapp):
    e = QQmlEngine(qapp)
    e.addImportPath(str(QML_DIR))
    return e


def _list_focusable_items(content: str):
    return [line for line in content.splitlines()
            if "activeFocusOnTab" in line or "focus" in line
            or "Keys.on" in line]


class TestKeyboardNavigationAllPages:
    def _check_page(self, filename: str):
        qml_path = QML_DIR / filename
        if not qml_path.exists():
            pytest.skip(f"{filename} not found")
        content = qml_path.read_text()
        assert "activeFocusOnTab" in content or "KeyNavigation" in content, \
            f"{filename} lacks keyboard navigation support"
        has_tab = "KeyNavigation.tab" in content or "activeFocusOnTab" in content
        has_keys = any(k in content for k in ("Keys.onReturnPressed", "Keys.onSpacePressed"))
        assert has_tab and has_keys, \
            f"{filename} missing tab navigation or key handlers"

    def test_home_page_keyboard(self, engine):
        self._check_page("pages/home/HomePage.qml")

    def test_library_page_keyboard(self, engine):
        self._check_page("pages/library/LibraryPage.qml")

    def test_devices_page_keyboard(self, engine):
        self._check_page("pages/devices/DevicesPage.qml")

    def test_connections_page_keyboard(self, engine):
        self._check_page("pages/connections/ConnectionsPage.qml")

    def test_home_audio_page_keyboard(self, engine):
        self._check_page("pages/home_audio/HomeAudioPage.qml")

    def test_radio_page_keyboard(self, engine):
        self._check_page("pages/radio/RadioPage.qml")

    def test_playlists_page_keyboard(self, engine):
        self._check_page("pages/playlists/PlaylistsPage.qml")

    def test_search_page_keyboard(self, engine):
        self._check_page("pages/search/GlobalSearchPage.qml")

    def test_settings_page_keyboard(self, engine):
        self._check_page("pages/SettingsPage.qml")

    def test_history_page_keyboard(self, engine):
        self._check_page("pages/history/HistoryPage.qml")

    def test_mix_hub_page_keyboard(self, engine):
        self._check_page("pages/mix/MixHubPage.qml")

    def test_assistant_page_keyboard(self, engine):
        self._check_page("pages/assistant/AssistantPage.qml")


class TestKeyboardEscapeClosesDialogs:
    def test_playlists_dialog_escape(self, engine):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "onRejected" in content or "Keys.onEscapePressed" in content or "standardButtons" in content

    def test_history_dialog_escape(self, engine):
        content = (QML_DIR / "pages/history/HistoryPage.qml").read_text()
        assert "onRejected" in content or "Keys.onEscapePressed" in content or "standardButtons" in content


class TestKeyboardEnterSpaceOnButtons:
    @pytest.mark.parametrize("page_path", PAGE_PATHS)
    def test_pages_have_button_key_handlers(self, page_path):
        qml_path = QML_DIR / page_path
        if not qml_path.exists():
            pytest.skip(f"{page_path} not found")
        qml_path.read_text()
        mia_btn_path = QML_DIR / "components/MichiButton.qml"
        if mia_btn_path.exists():
            btn_content = mia_btn_path.read_text()
            assert "Accessible.Button" in btn_content or "focusPolicy" in btn_content, \
                "MichiButton should be accessible and focusable"


class TestTabOrderAcrossControls:
    @pytest.mark.parametrize("page_path", PAGE_PATHS)
    def test_tab_forward_navigation(self, page_path):
        qml_path = QML_DIR / page_path
        if not qml_path.exists():
            pytest.skip(f"{page_path} not found")
<<<<<<< Updated upstream
        content = qml_path.read_text()
        tab_count = content.count("activeFocusOnTab")
        assert tab_count > 0, f"{page_path} should have at least 1 focusable element"
=======
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
=======
from PySide6.QtQml import QQmlEngine

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

KEY_NAV_PATTERNS = [
    "KeyNavigation.tab",
    "KeyNavigation.backtab",
    "Keys.onReturnPressed",
    "Keys.onSpacePressed",
    "Keys.onEscapePressed",
    "activeFocusOnTab",
    "focus",
    "focusPolicy",
]


@pytest.fixture
def engine(qapp):
    e = QQmlEngine(qapp)
    e.addImportPath(str(QML_DIR))
    return e


def _list_focusable_items(content: str):
    return [line for line in content.splitlines()
            if "activeFocusOnTab" in line or "focus" in line
            or "Keys.on" in line]


class TestKeyboardNavigationAllPages:
    def _check_page(self, filename: str):
        qml_path = QML_DIR / filename
        if not qml_path.exists():
            pytest.skip(f"{filename} not found")
        content = qml_path.read_text()
        assert "activeFocusOnTab" in content or "KeyNavigation" in content, \
            f"{filename} lacks keyboard navigation support"
        has_tab = "KeyNavigation.tab" in content or "activeFocusOnTab" in content
        has_keys = any(k in content for k in ("Keys.onReturnPressed", "Keys.onSpacePressed"))
        assert has_tab and has_keys, \
            f"{filename} missing tab navigation or key handlers"

    def test_home_page_keyboard(self, engine):
        self._check_page("pages/home/HomePage.qml")

    def test_library_page_keyboard(self, engine):
        self._check_page("pages/library/LibraryPage.qml")

    def test_devices_page_keyboard(self, engine):
        self._check_page("pages/devices/DevicesPage.qml")

    def test_connections_page_keyboard(self, engine):
        self._check_page("pages/connections/ConnectionsPage.qml")

    def test_home_audio_page_keyboard(self, engine):
        self._check_page("pages/home_audio/HomeAudioPage.qml")

    def test_radio_page_keyboard(self, engine):
        self._check_page("pages/radio/RadioPage.qml")

    def test_playlists_page_keyboard(self, engine):
        self._check_page("pages/playlists/PlaylistsPage.qml")

    def test_search_page_keyboard(self, engine):
        self._check_page("pages/search/GlobalSearchPage.qml")

    def test_settings_page_keyboard(self, engine):
        self._check_page("pages/SettingsPage.qml")

    def test_history_page_keyboard(self, engine):
        self._check_page("pages/history/HistoryPage.qml")

    def test_mix_hub_page_keyboard(self, engine):
        self._check_page("pages/mix/MixHubPage.qml")

    def test_assistant_page_keyboard(self, engine):
        self._check_page("pages/assistant/AssistantPage.qml")


class TestKeyboardEscapeClosesDialogs:
    def test_playlists_dialog_escape(self, engine):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "onRejected" in content or "Keys.onEscapePressed" in content or "standardButtons" in content

    def test_history_dialog_escape(self, engine):
        content = (QML_DIR / "pages/history/HistoryPage.qml").read_text()
        assert "onRejected" in content or "Keys.onEscapePressed" in content or "standardButtons" in content


class TestKeyboardEnterSpaceOnButtons:
    @pytest.mark.parametrize("page_path", PAGE_PATHS)
    def test_pages_have_button_key_handlers(self, page_path):
        qml_path = QML_DIR / page_path
        if not qml_path.exists():
            pytest.skip(f"{page_path} not found")
        qml_path.read_text()
        mia_btn_path = QML_DIR / "components/MichiButton.qml"
        if mia_btn_path.exists():
            btn_content = mia_btn_path.read_text()
            assert "Accessible.Button" in btn_content or "focusPolicy" in btn_content, \
                "MichiButton should be accessible and focusable"


class TestTabOrderAcrossControls:
    @pytest.mark.parametrize("page_path", PAGE_PATHS)
    def test_tab_forward_navigation(self, page_path):
        qml_path = QML_DIR / page_path
        if not qml_path.exists():
            pytest.skip(f"{page_path} not found")
        content = qml_path.read_text()
        tab_count = content.count("activeFocusOnTab")
        assert tab_count > 0, f"{page_path} should have at least 1 focusable element"
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
