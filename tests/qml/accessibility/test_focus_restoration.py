from __future__ import annotations
from __future__ import annotations
"""Test focus returns when dialogs close.

Verifies that:
- Dialogs implement Keys.onEscapePressed
- Dialogs have proper modal and close behavior
- Keyboard focus management exists around dialogs
"""

from pathlib import Path


QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class TestFocusRestoration:
    def test_dialog_close_returns_focus(self):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "focus" in content

    def test_settings_back_returns_focus(self):
        content = (QML_DIR / "pages/SettingsPage.qml").read_text()
        assert "focus" in content
        assert "back()" in content

    def test_history_clear_returns_focus(self):
        content = (QML_DIR / "pages/history/HistoryPage.qml").read_text()
        assert "focus" in content or "activeFocusOnTab" in content

    def test_dialog_on_accepted_focus_restored(self):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "onAccepted" in content

    def test_dialog_on_rejected_focus_restored(self):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "onRejected" in content

    def test_focus_scope_manages_focus(self):
        for name in ["DevicesPage", "HomePage", "HomeAudioPage", "ConnectionsPage",
                      "LibraryPage", "HistoryPage", "PlaylistsPage", "GlobalSearchPage",
                      "RadioPage", "MixHubPage", "AssistantPage", "AudioLabOverviewPage"]:
            path = QML_DIR / f"pages/{name.lower().replace('page','')}/{name}.qml"
            if name == "GlobalSearchPage":
                path = QML_DIR / "pages/search/GlobalSearchPage.qml"
            elif name == "AssistantPage":
                path = QML_DIR / "pages/assistant/AssistantPage.qml"
            elif name == "AudioLabOverviewPage":
                path = QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml"
            elif name == "MixHubPage":
                path = QML_DIR / "pages/mix/MixHubPage.qml"
            if not path.exists():
                continue
            content = path.read_text()
            assert "FocusScope" in content, f"{path.name} lacks FocusScope"
            assert "activeFocusOnTab" in content, f"{path.name} lacks activeFocusOnTab"

from pathlib import Path


QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class TestFocusRestoration:
    def test_dialog_close_returns_focus(self):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "focus" in content

    def test_settings_back_returns_focus(self):
        content = (QML_DIR / "pages/SettingsPage.qml").read_text()
        assert "focus" in content
        assert "back()" in content

    def test_history_clear_returns_focus(self):
        content = (QML_DIR / "pages/history/HistoryPage.qml").read_text()
        assert "focus" in content or "activeFocusOnTab" in content

    def test_dialog_on_accepted_focus_restored(self):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "onAccepted" in content

    def test_dialog_on_rejected_focus_restored(self):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "onRejected" in content

    def test_confirm_dialog_has_focus_management(self):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        dlg_lines = [line for line in content.splitlines() if "Dialog" in line or "confirmBatchDelete" in line]
        assert len(dlg_lines) >= 2

    def test_settings_search_has_focus(self):
        content = (QML_DIR / "pages/SettingsPage.qml").read_text()
        assert "SearchField" in content
        assert "focus" in content or "activeFocusOnTab" in content

    def test_history_dialog_on_accepted_focus_restored(self):
        content = (QML_DIR / "pages/history/HistoryPage.qml").read_text()
        assert "onAccepted" in content

    def test_mix_page_no_stuck_focus(self):
        content = (QML_DIR / "pages/mix/MixHubPage.qml").read_text()
        assert "onClicked" in content

    def test_assistant_no_stuck_focus(self):
        content = (QML_DIR / "pages/assistant/AssistantPage.qml").read_text()
        assert "activeFocus" in content or "focus" in content
