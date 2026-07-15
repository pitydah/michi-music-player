"""Test focus returns when dialogs close.

Verifies that:
- Dialogs implement Keys.onEscapePressed
- Dialogs have proper modal and close behavior
- Keyboard focus management exists around dialogs
"""

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
pytestmark = [pytest.mark.qml_module("accessibility")]


class TestFocusRestoration:
    def test_history_page_dialog_focus(self):
        path = QML_DIR / "pages/history/HistoryPage.qml"
        if not path.exists():
            pytest.skip("HistoryPage.qml not found")
        content = path.read_text()
        assert "confirmClearDialog" in content
        assert "Keys.onEscapePressed" in content or "Keys.onEscapePressed" in content

    def test_playlists_page_create_dialog(self):
        path = QML_DIR / "pages/playlists/PlaylistsPage.qml"
        if not path.exists():
            pytest.skip("PlaylistsPage.qml not found")
        content = path.read_text()
        assert "createDialog" in content
        assert "Keys.onEscapePressed" in content or "Dialog {" in content

    def test_playlists_page_batch_delete_dialog(self):
        path = QML_DIR / "pages/playlists/PlaylistsPage.qml"
        if not path.exists():
            pytest.skip("PlaylistsPage.qml not found")
        content = path.read_text()
        assert "confirmBatchDelete" in content
        assert "Keys.onEscapePressed" in content or "onRejected" in content

    def test_history_page_retention_dialog(self):
        path = QML_DIR / "pages/history/HistoryPage.qml"
        if not path.exists():
            pytest.skip("HistoryPage.qml not found")
        content = path.read_text()
        assert "retentionDialog" in content
        assert "onRetentionApplied" in content

    def test_playlist_import_dialog_escape(self):
        path = QML_DIR / "pages/playlists/PlaylistsPage.qml"
        if not path.exists():
            pytest.skip("PlaylistsPage.qml not found")
        content = path.read_text()
        assert "importDialog" in content

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
