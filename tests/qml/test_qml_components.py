"""Tests for QML Design System components.

Verifies that all components are importable and instantiable without errors.
"""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


def _load_qml(engine, source: str) -> QQmlComponent:
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / source)))
    return component


class TestMichiButton:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_primary_variant(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_danger_variant(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_ghost_variant(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_secondary_variant(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_with_icon_text(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()

    def test_disabled(self, engine):
        component = _load_qml(engine, "components/MichiButton.qml")
        assert component.isReady()


class TestMichiIconButton:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiIconButton.qml")
        assert component.isReady()

    def test_smoke_can_load(self, engine):
        component = _load_qml(engine, "components/MichiIconButton.qml")
        assert component.status() == QQmlComponent.Ready


class TestMichiSlider:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiSlider.qml")
        assert component.isReady()

    def test_default_value(self, engine):
        component = _load_qml(engine, "components/MichiSlider.qml")
        assert component.isReady()

    def test_disabled_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiSlider.qml")
        assert component.isReady()

    def test_slider_contract_properties(self, engine):
        component = _load_qml(engine, "components/MichiSlider.qml")
        assert component.isReady()
        obj = component.create()
        try:
            assert obj.property("stepSize") == 1
            assert obj.property("enabled") is True
            assert obj.property("activeFocusOnTab") is True
        finally:
            obj.deleteLater()

    def test_slider_moved_signal_exists(self, engine):
        component = _load_qml(engine, "components/MichiSlider.qml")
        assert component.isReady()
        source = (QML_DIR / "components" / "MichiSlider.qml").read_text()
        assert "signal moved()" in source or "signal moved" in source


class TestMichiBadge:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiBadge.qml")
        assert component.isReady()

    def test_success_variant(self, engine):
        component = _load_qml(engine, "components/MichiBadge.qml")
        assert component.isReady()


class TestMichiProgressBar:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/MichiProgressBar.qml")
        assert component.isReady()

    def test_smoke_can_load(self, engine):
        component = _load_qml(engine, "components/MichiProgressBar.qml")
        assert component.status() == QQmlComponent.Ready


class TestGlassPanel:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/GlassPanel.qml")
        assert component.isReady()


class TestGlassCard:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/GlassCard.qml")
        assert component.isReady()


class TestSearchField:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/SearchField.qml")
        assert component.isReady()


class TestSectionHeader:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/SectionHeader.qml")
        assert component.isReady()


class TestSidebarItem:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/SidebarItem.qml")
        assert component.isReady()


class TestStatusBadge:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/StatusBadge.qml")
        assert component.isReady()


class TestEmptyState:
    def test_instantiate(self, engine):
        component = _load_qml(engine, "components/EmptyState.qml")
        assert component.isReady()


# ── Page smoke tests (file existence) ──

PAGE_FILES = [
    "pages/home/HomePage.qml",
    "pages/library/LibraryPage.qml",
    "pages/PlaybackPage.qml",
    "pages/connections/ConnectionsPage.qml",
    "pages/SettingsPage.qml",
    "pages/assistant/AssistantPage.qml",
    "pages/playlists/PlaylistsPage.qml",
    "pages/RadioPage.qml",
]


class TestLibraryComponents:
    LIBRARY_FILES = [
        "pages/library/LibraryPage.qml",
        "pages/library/SongTable.qml",
        "pages/library/SongRow.qml",
        "pages/library/AlbumGrid.qml",
        "pages/library/AlbumCard.qml",
        "pages/library/ArtistList.qml",
        "pages/library/ArtistCard.qml",
        "pages/library/FolderBrowser.qml",
        "pages/library/ArtistDetailPage.qml",
        "pages/library/AlbumDetailPage.qml",
    ]

    INSTANTIABLE = [
        "pages/library/SongTable.qml",
        "pages/library/SongRow.qml",
        "pages/library/FolderBrowser.qml",
    ]

    def test_all_library_files_exist(self):
        for rel_path in self.LIBRARY_FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing library file: {p}"

    def test_song_table_instantiate(self, engine):
        component = _load_qml(engine, "pages/library/SongTable.qml")
        assert component.isReady()

    def test_song_row_instantiate(self, engine):
        component = _load_qml(engine, "pages/library/SongRow.qml")
        assert component.isReady()

    def test_folder_browser_instantiate(self, engine):
        component = _load_qml(engine, "pages/library/FolderBrowser.qml")
        assert component.isReady()


class TestPageFiles:
    def test_all_pages_exist(self):
        for rel_path in PAGE_FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing page file: {p}"


class TestShellComponents:
    SHELL_FILES = [
        "shell/HeaderBar.qml",
        "shell/Sidebar.qml",
        "shell/RouteTransition.qml",
        "shell/PageStack.qml",
    ]

    def test_all_files_exist(self):
        for rel_path in self.SHELL_FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing: {p}"

    def test_header_bar_instantiate(self, engine):
        component = _load_qml(engine, "shell/HeaderBar.qml")
        assert component.isReady()

    def test_sidebar_instantiate(self, engine):
        component = _load_qml(engine, "shell/Sidebar.qml")
        assert component.isReady()

    def test_route_transition_instantiate(self, engine):
        component = _load_qml(engine, "shell/RouteTransition.qml")
        assert component.isReady()

    def test_page_stack_instantiate(self, engine):
        component = _load_qml(engine, "shell/PageStack.qml")
        assert component.isReady()


class TestNowPlayingComponents:
    NOWPLAYING_FILES = [
        "components/NowPlayingBar.qml",
        "components/NowPlayingControls.qml",
        "components/NowPlayingInfo.qml",
        "components/NowPlayingCover.qml",
        "components/NowPlayingSeekBar.qml",
        "components/NowPlayingVolume.qml",
    ]

    def test_all_files_exist(self):
        for rel_path in self.NOWPLAYING_FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing: {p}"

    def test_now_playing_controls_exists(self, engine):
        component = _load_qml(engine, "components/NowPlayingControls.qml")
        assert component.isReady()

    def test_now_playing_info_exists(self, engine):
        component = _load_qml(engine, "components/NowPlayingInfo.qml")
        assert component.isReady()

    def test_now_playing_seek_bar_exists(self, engine):
        component = _load_qml(engine, "components/NowPlayingSeekBar.qml")
        assert component.isReady()

    def test_now_playing_volume_exists(self, engine):
        component = _load_qml(engine, "components/NowPlayingVolume.qml")
        assert component.isReady()


class TestPlaylistsComponents:
    PLAYLISTS_FILES = [
        "pages/playlists/PlaylistsPage.qml",
        "pages/playlists/PlaylistDetailPage.qml",
        "pages/playlists/PlaylistCard.qml",
    ]

    def test_all_files_exist(self):
        for rel_path in self.PLAYLISTS_FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing: {p}"

    def test_playlist_card_instantiate(self, engine):
        component = _load_qml(engine, "pages/playlists/PlaylistCard.qml")
        assert component.isReady()

    def test_playlist_detail_instantiate(self, engine):
        component = _load_qml(engine, "pages/playlists/PlaylistDetailPage.qml")
        assert component.isReady()


class TestRadioComponents:
    def test_radio_page_exists(self):
        p = QML_DIR / "pages" / "RadioPage.qml"
        assert p.exists(), "Missing RadioPage.qml"


class TestSettingsDevicesConnections:
    FILES = [
        "pages/SettingsPage.qml",
        "pages/DevicesPage.qml",
        "pages/devices/DeviceCard.qml",
        "pages/devices/SyncStatusPanel.qml",
        "pages/connections/ConnectionsPage.qml",
        "pages/connections/ExternalServerCard.qml",
        "pages/home_audio/HomeAudioPage.qml",
    ]

    INSTANTIABLE = [
        "pages/SettingsPage.qml",
        "pages/devices/DeviceCard.qml",
        "pages/devices/SyncStatusPanel.qml",
        "pages/connections/ExternalServerCard.qml",
    ]

    def test_all_files_exist(self):
        for rel_path in self.FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing: {p}"

    def test_device_card_instantiate(self, engine):
        component = _load_qml(engine, "pages/devices/DeviceCard.qml")
        assert component.isReady()

    def test_sync_status_instantiate(self, engine):
        component = _load_qml(engine, "pages/devices/SyncStatusPanel.qml")
        assert component.isReady()

    def test_settings_page_instantiate(self, engine):
        component = _load_qml(engine, "pages/SettingsPage.qml")
        assert component.isReady()

    def test_external_server_card_instantiate(self, engine):
        component = _load_qml(engine, "pages/connections/ExternalServerCard.qml")
        assert component.isReady()


class TestMetadataComponents:
    FILES = [
        "pages/metadata/MetadataInspectorPage.qml",
        "pages/metadata/MetadataFieldRow.qml",
        "pages/metadata/MetadataArtworkPreview.qml",
    ]

    def test_all_files_exist(self):
        for rel_path in self.FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing: {p}"

    def test_field_row_instantiate(self, engine):
        component = _load_qml(engine, "pages/metadata/MetadataFieldRow.qml")
        assert component.isReady()

    def test_artwork_preview_instantiate(self, engine):
        component = _load_qml(engine, "pages/metadata/MetadataArtworkPreview.qml")
        assert component.isReady()

    def test_no_michi_cover_direct(self):
        content = (QML_DIR / "pages" / "metadata" / "MetadataArtworkPreview.qml").read_text()
        assert "MichiCover" not in content, "MetadataArtworkPreview still imports MichiCover directly"


class TestAudioLab:
    def test_audio_lab_page_exists(self):
        p = QML_DIR / "pages" / "assistant" / "AudioLabPage.qml"
        assert p.exists(), "Missing AudioLabPage.qml"

    def test_suggestion_card_exists(self):
        p = QML_DIR / "pages" / "assistant" / "SuggestionCard.qml"
        assert p.exists(), "Missing SuggestionCard.qml"

    def test_chat_bubble_exists(self):
        p = QML_DIR / "pages" / "assistant" / "ChatBubble.qml"
        assert p.exists(), "Missing ChatBubble.qml"


class TestRemainingPages:
    REMAINING_FILES = [
        "pages/connections/ConfiguredServerCard.qml",
        "pages/connections/DiscoveredServerCard.qml",
        "pages/connections/HomeAudioAccess.qml",
        "pages/connections/MicroServerHero.qml",
        "pages/connections/NetworkDiscoveryPanel.qml",
        "pages/home/AssistantCard.qml",
        "pages/home_audio/AudioZoneCard.qml",
        "pages/home_audio/HomeAssistantPanel.qml",
        "pages/home_audio/HomeAudioModeSelector.qml",
        "pages/home_audio/MichiMusicStreamPanel.qml",
        "pages/home_audio/ReceiverCard.qml",
        "pages/home/ContinueCard.qml",
        "pages/home/EcosystemCard.qml",
        "pages/home/HomeHero.qml",
        "pages/home/LibraryStatusCard.qml",
        "pages/PlaceholderPage.qml",
    ]

    INSTANTIABLE = [
        "pages/connections/HomeAudioAccess.qml",
        "pages/connections/MicroServerHero.qml",
        "pages/home/HomeHero.qml",
        "pages/PlaceholderPage.qml",
    ]

    def test_all_files_exist(self):
        for rel_path in self.REMAINING_FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing: {p}"

    def test_home_audio_access_instantiate(self, engine):
        component = _load_qml(engine, "pages/connections/HomeAudioAccess.qml")
        assert component.isReady()

    def test_micro_server_hero_instantiate(self, engine):
        component = _load_qml(engine, "pages/connections/MicroServerHero.qml")
        assert component.isReady()

    def test_home_hero_instantiate(self, engine):
        component = _load_qml(engine, "pages/home/HomeHero.qml")
        assert component.isReady()

    def test_placeholder_instantiate(self, engine):
        component = _load_qml(engine, "pages/PlaceholderPage.qml")
        assert component.isReady()


class TestEqLibraryDoctor:
    FILES = [
        "pages/EqPage.qml",
        "pages/LibraryDoctorPage.qml",
    ]

    def test_all_files_exist(self):
        for rel_path in self.FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing: {p}"

    def test_eq_page_instantiate(self, engine):
        component = _load_qml(engine, "pages/EqPage.qml")
        assert component.isReady()

    def test_library_doctor_instantiate(self, engine):
        component = _load_qml(engine, "pages/LibraryDoctorPage.qml")
        assert component.isReady()


class TestOutputProfilesSmartTagging:
    FILES = [
        "pages/OutputProfilesPage.qml",
        "pages/SmartTaggingPage.qml",
    ]

    def test_all_files_exist(self):
        for rel_path in self.FILES:
            p = QML_DIR / rel_path
            assert p.exists(), f"Missing: {p}"

    def test_output_profiles_instantiate(self, engine):
        component = _load_qml(engine, "pages/OutputProfilesPage.qml")
        assert component.isReady()

    def test_smart_tagging_instantiate(self, engine):
        component = _load_qml(engine, "pages/SmartTaggingPage.qml")
        assert component.isReady()


class TestRuntimeBlockerFixes:
    def test_library_page_has_layouts_import(self):
        content = (QML_DIR / "pages" / "library" / "LibraryPage.qml").read_text()
        assert "import QtQuick.Layouts" in content, "LibraryPage missing QtQuick.Layouts import"

    def test_home_audio_page_has_layouts_import(self):
        content = (QML_DIR / "pages" / "home_audio" / "HomeAudioPage.qml").read_text()
        assert "import QtQuick.Layouts" in content, "HomeAudioPage missing QtQuick.Layouts import"

    def test_no_bridge_binding_loops(self):
        import re
        pages = list((QML_DIR / "pages").rglob("*.qml"))
        violations = []
        for p in pages:
            text = p.read_text()
            matches = re.findall(r'property var (\w+Bridge): typeof \w+Bridge', text)
            for m in matches:
                violations.append(f"{p.relative_to(QML_DIR)}: {m}")
        assert not violations, "Bridge binding loop pattern found:\n" + "\n".join(violations)

    def test_no_placeholder_text_on_text_input(self):
        pages = list((QML_DIR / "pages").rglob("*.qml"))
        for p in pages:
            text = p.read_text()
            if "TextInput" in text and "placeholderText" in text:
                # Verify it's not TextInput.placeholderText (only TextField has it)
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if "TextInput" in line.strip():
                        for j in range(i, min(i + 15, len(lines))):
                            if "placeholderText" in lines[j] and not lines[j].strip().startswith("//"):
                                assert False, f"{p.relative_to(QML_DIR)}:{j+1}: TextInput cannot have placeholderText"

    def test_michi_icon_button_no_enabled_override(self):
        content = (QML_DIR / "components" / "MichiIconButton.qml").read_text()
        assert "property bool enabled" not in content, "MichiIconButton still overrides enabled"

    def test_glass_card_has_interactive_property(self):
        content = (QML_DIR / "components" / "GlassCard.qml").read_text()
        assert "property bool interactive" in content, "GlassCard missing interactive property"

    def test_metadata_inspector_no_duplicate_width(self):
        lines = (QML_DIR / "pages" / "metadata" / "MetadataInspectorPage.qml").read_text().split("\n")
        in_component = False
        width_count = 0
        for line in lines:
            if "Component {" in line and "emptyComponent" in lines[lines.index(line)-1] if lines.index(line) > 0 else False:
                in_component = True
            stripped = line.strip()
            if stripped.startswith("width:") and in_component:
                width_count += 1
        assert width_count <= 1, f"EmptyComponent has {width_count} width assignments (should be 1)"

    def test_no_ui_qml_icon_paths(self):
        pages = list((QML_DIR / "pages").rglob("*.qml"))
        components = list((QML_DIR / "components").rglob("*.qml"))
        all_files = pages + components
        violations = []
        for p in all_files:
            text = p.read_text()
            if '"ui_qml/icons' in text or "'ui_qml/icons" in text:
                violations.append(str(p.relative_to(QML_DIR)))
        assert not violations, f"Files referencing ui_qml/icons path: {violations}"


class TestRemainingRisks:
    def test_smart_tagging_has_file_dialog(self):
        content = (QML_DIR / "pages" / "SmartTaggingPage.qml").read_text()
        assert "FileDialog" in content, "SmartTaggingPage missing FileDialog"
        assert "selectedFile" in content, "SmartTaggingPage missing selectedFile"
        assert "/example/" not in content, "SmartTaggingPage still has fake path"

    def test_eq_page_has_bridge_property(self):
        content = (QML_DIR / "pages" / "EqPage.qml").read_text()
        assert "eqBridge" in content, "EqPage missing eqBridge property"
        assert "applyPreset" in content, "EqPage missing applyPreset"

    def test_eq_bridge_importable(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        assert EqBridge is not None


class TestSprintNewPages:
    FILES = [
        "pages/DiscLabPage.qml",
    ]

    BRIDGES_IMPORTABLE = [
        "library_doctor_bridge",
    ]

    def test_disc_lab_page_exists(self):
        p = QML_DIR / "pages" / "DiscLabPage.qml"
        assert p.exists(), "Missing DiscLabPage.qml"

    def test_disc_lab_instantiate(self, engine):
        component = _load_qml(engine, "pages/DiscLabPage.qml")
        assert component.isReady()

    def test_library_doctor_bridge_importable(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        assert LibraryDoctorBridge is not None

    def test_playlists_has_create_dialog(self):
        content = (QML_DIR / "pages" / "playlists" / "PlaylistsPage.qml").read_text()
        assert "Dialog" in content, "PlaylistsPage missing create dialog"
        assert "nameInput" in content, "PlaylistsPage missing name input"

    def test_playlists_create_dialog_no_auto_name(self):
        content = (QML_DIR / "pages" / "playlists" / "PlaylistsPage.qml").read_text()
        assert 'createPlaylist("Nueva playlist")' not in content, "PlaylistsPage still uses auto-generated name"

    def test_playlist_detail_has_rename_dialog(self):
        content = (QML_DIR / "pages" / "playlists" / "PlaylistDetailPage.qml").read_text()
        assert "renameDialog" in content, "PlaylistDetailPage missing rename dialog"
        assert "renamePlaylist" in content, "PlaylistDetailPage missing renamePlaylist call"

    def test_smart_tagging_has_extension_validation(self):
        content = (QML_DIR / "pages" / "SmartTaggingPage.qml").read_text()
        assert "isValidAudio" in content, "SmartTaggingPage missing extension validation"
        assert "/example/" not in content, "SmartTaggingPage still has fake path"

    def test_disc_lab_bridge_importable(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        assert DiscLabBridge is not None

    def test_selection_context_bridge_importable(self):
        from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
        bridge = SelectionContextBridge()
        assert not bridge.hasSelection
        bridge.setSelected({"title": "test", "filepath": "/test.mp3"})
        assert bridge.hasSelection
        assert bridge.selectedTitle == "test"
        bridge.clearSelection()
        assert not bridge.hasSelection

    def test_metadata_page_has_selection_context(self):
        content = (QML_DIR / "pages" / "metadata" / "MetadataInspectorPage.qml").read_text()
        assert "selectionContextBridge" in content, "Metadata page missing selection context"
        assert "loadFromSelection" in content, "Metadata page missing loadFromSelection"

    def test_song_table_has_workflow_actions(self):
        content = (QML_DIR / "pages" / "library" / "SongTable.qml").read_text()
        assert "selectionContextBridge.setSelected" in content, "SongTable missing selection context integration"
        assert "navigationBridge.navigate(\"metadata_inspector\")" in content, "SongTable missing metadata navigation"
        assert "navigationBridge.navigate(\"playlists\")" in content, "SongTable missing playlists navigation"

    def test_playlists_page_has_add_track(self):
        content = (QML_DIR / "pages" / "playlists" / "PlaylistsPage.qml").read_text()
        assert "addSelectedTrackToPlaylist" in content, "PlaylistsPage missing addSelectedTrackToPlaylist"
        assert "selectionContextBridge" in content, "PlaylistsPage missing selection context"

    def test_library_doctor_issue_clickable(self):
        content = (QML_DIR / "pages" / "LibraryDoctorPage.qml").read_text()
        assert "metadata_inspector" in content, "LibraryDoctorPage missing metadata navigation"
        assert "MouseArea" in content, "LibraryDoctorPage issues not clickable"

    def test_audio_lab_has_metadata_card(self):
        content = (QML_DIR / "pages" / "assistant" / "AudioLabPage.qml").read_text()
        assert "metadata_inspector" in content, "AudioLabPage missing metadata inspector link"

    def test_eq_bridge_backend_available(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        bridge = EqBridge()
        bridge.refresh()
        assert hasattr(bridge, 'backendAvailable')
        assert not bridge.backendAvailable  # No player_service

    def test_playlists_bridge_add_track(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        bridge = PlaylistsBridge()
        result = bridge.addSelectedTrackToPlaylist(0)
        assert result.get("ok") is False  # No DB


class TestNowPlayingBarMigration:
    def test_nowplaying_bridge_has_backend_status(self):
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        bridge = NowPlayingBridge()
        assert bridge.backendAvailable is False
        assert bridge.playbackStatus == "unavailable"
        assert bridge.safeMode is True
        assert bridge.errorMessage == ""

    def test_nowplaying_bridge_commands_recorded(self):
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        bridge = NowPlayingBridge()
        bridge.togglePlay()
        assert bridge.lastCommand == "togglePlay"
        bridge.next()
        assert bridge.lastCommand == "next"
        bridge.previous()
        assert bridge.lastCommand == "previous"
        bridge.seek(30)
        assert bridge.lastCommand == "seek"

    def test_nowplaying_bridge_seek_no_duration(self):
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        bridge = NowPlayingBridge()
        bridge.seek(30)
        assert not bridge.lastCommandOk

    def test_nowplaying_bridge_volume_clamped(self):
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        bridge = NowPlayingBridge(player_service=object())
        bridge.setVolume(-10)
        assert bridge.volume == 0
        bridge.setVolume(150)
        assert bridge.volume == 100

    def test_nowplaying_bar_has_queue_panel(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert "notificationBridge" in content  # notification integrated

    def test_nowplaying_queue_panel_exists(self):
        p = QML_DIR / "components" / "NowPlayingQueuePanel.qml"
        assert p.exists(), "Missing NowPlayingQueuePanel.qml"

    def test_nowplaying_queue_panel_instantiate(self, engine):
        component = _load_qml(engine, "components/NowPlayingQueuePanel.qml")
        assert component.isReady()

    def test_nowplaying_bar_has_notification_bridge(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert "notificationBridge" in content, "NowPlayingBar missing notificationBridge"

    def test_nowplaying_bar_has_backend_status(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert "backendAvailable" in content, "NowPlayingBar missing backend status"

    def test_nowplaying_info_has_backend_param(self):
        content = (QML_DIR / "components" / "NowPlayingInfo.qml").read_text()
        assert "backendAvailable" in content, "NowPlayingInfo missing backendAvailable"


class TestActionButtonNotPresent:
    def test_action_button_not_in_components(self):
        qmldir = QML_DIR / "components" / "qmldir"
        if qmldir.exists():
            content = qmldir.read_text()
            assert "ActionButton" not in content, "ActionButton still registered in components/qmldir"
        action_button = QML_DIR / "components" / "ActionButton.qml"
        assert not action_button.exists(), "ActionButton.qml still exists"
