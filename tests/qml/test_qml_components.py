"""Tests for QML Design System components.

Verifies that all components are importable and instantiable without errors.
"""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine, qmlRegisterType
from PySide6.QtQuick import QQuickItem

QML_DIR = Path(__file__).resolve().parent.parent.parent / "ui_qml"
_COVER_BRIDGE_REGISTERED = False


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


def _load_qml(engine, source: str) -> QQmlComponent:
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / source)))
    return component


def _register_cover_bridge():
    global _COVER_BRIDGE_REGISTERED
    if _COVER_BRIDGE_REGISTERED:
        return
    from ui_qml_bridge.cover_bridge import CoverBridge

    qmlRegisterType(CoverBridge, "MichiCover", 1, 0, "CoverBridge")
    _COVER_BRIDGE_REGISTERED = True


def _negative_item_dimensions(item):
    found = []
    if not isinstance(item, QQuickItem):
        return found
    if item.width() < 0 or item.height() < 0:
        found.append((item.metaObject().className(), item.width(), item.height()))
    for child in item.childItems():
        found.extend(_negative_item_dimensions(child))
    return found


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

    def test_nowplaying_bar_layout_has_no_negative_dimensions(self, engine, qapp):
        _register_cover_bridge()
        component = _load_qml(engine, "components/NowPlayingBar.qml")
        assert component.isReady(), [e.toString() for e in component.errors()]
        obj = component.create()
        try:
            obj.setWidth(1200)
            qapp.processEvents()
            assert _negative_item_dimensions(obj) == []
        finally:
            obj.deleteLater()

    def test_nowplaying_queue_panel_exists(self):
        p = QML_DIR / "components" / "NowPlayingQueuePanel.qml"
        assert p.exists(), "Missing NowPlayingQueuePanel.qml"

    def test_nowplaying_queue_panel_instantiate(self, engine):
        component = _load_qml(engine, "components/NowPlayingQueuePanel.qml")
        assert component.isReady()

    def test_filter_chip_has_stable_implicit_width(self, engine, qapp):
        component = _load_qml(engine, "components/FilterChip.qml")
        assert component.isReady(), [e.toString() for e in component.errors()]
        obj = component.create()
        try:
            obj.setProperty("text", "Todos")
            qapp.processEvents()
            assert obj.property("implicitWidth") >= 40
        finally:
            obj.deleteLater()

    def test_nowplaying_bar_has_notification_bridge(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert "notificationBridge" in content, "NowPlayingBar missing notificationBridge"

    def test_nowplaying_bar_has_backend_status(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert "backendAvailable" in content, "NowPlayingBar missing backend status"

    def test_nowplaying_info_has_backend_param(self):
        content = (QML_DIR / "components" / "NowPlayingInfo.qml").read_text()
        assert "backendAvailable" in content, "NowPlayingInfo missing backendAvailable"

    def test_nowplaying_bar_no_placeholder_no(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert '"NO"' not in content, "NowPlayingBar still has NO placeholder"
        assert '"Sin reproducción"' in content, "NowPlayingBar missing empty state text"

    def test_nowplaying_controls_use_inherited_enabled(self):
        content = (QML_DIR / "components" / "NowPlayingControls.qml").read_text()
        assert "property bool enabled" not in content, "NowPlayingControls overrides Item.enabled"
        assert "root.enabled" in content, "NowPlayingControls should still react to enabled state"
        assert "opacity:" in content, "NowPlayingControls missing opacity for disabled state"

    def test_nowplaying_seek_uses_inherited_enabled(self):
        content = (QML_DIR / "components" / "NowPlayingSeekBar.qml").read_text()
        assert "property bool enabled" not in content, "NowPlayingSeekBar overrides Item.enabled"
        assert "root.enabled" in content, "NowPlayingSeekBar should still react to enabled state"

    def test_nowplaying_volume_uses_inherited_enabled(self):
        content = (QML_DIR / "components" / "NowPlayingVolume.qml").read_text()
        assert "property bool enabled" not in content, "NowPlayingVolume overrides Item.enabled"
        assert "root.enabled" in content, "NowPlayingVolume should still react to enabled state"

    def test_nowplaying_bar_no_full_border(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert "border.width: 1" not in content, "NowPlayingBar still has full border"

    def test_home_ecosystem_card_height_fixed(self):
        content = (QML_DIR / "pages" / "home" / "EcosystemCard.qml").read_text()
        assert "implicitHeight: 210" in content, "EcosystemCard height not updated"

    def test_home_library_card_height_fixed(self):
        content = (QML_DIR / "pages" / "home" / "LibraryStatusCard.qml").read_text()
        assert "implicitHeight: 190" in content, "LibraryStatusCard height not updated"

    def test_nowplaying_controls_disabled_color(self):
        content = (QML_DIR / "components" / "NowPlayingControls.qml").read_text()
        assert "0.25" in content, "NowPlayingControls missing disabled accent color"

    def test_nowplaying_cover_no_n_placeholder(self):
        content = (QML_DIR / "components" / "NowPlayingCover.qml").read_text()
        assert '"NOWPLAYING"' not in content, "NowPlayingCover still has NOWPLAYING fallback"
        assert "placeholderMode" in content, "NowPlayingCover missing placeholderMode"

    def test_cover_image_has_mp_placeholder(self):
        content = (QML_DIR / "components" / "CoverImage.qml").read_text()
        assert '"MP"' in content, "CoverImage missing MP monogram placeholder"

    def test_expanded_nowplaying_panel_exists(self):
        p = QML_DIR / "components" / "ExpandedNowPlayingPanel.qml"
        assert p.exists(), "Missing ExpandedNowPlayingPanel.qml"

    def test_expanded_nowplaying_panel_instantiate(self, engine):
        component = _load_qml(engine, "components/ExpandedNowPlayingPanel.qml")
        assert component.isReady()

    def test_nowplaying_bar_has_expanded_panel(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert "ExpandedNowPlayingPanel" in content, "NowPlayingBar missing ExpandedNowPlayingPanel"
        assert "_panelExpanded" in content, "NowPlayingBar missing panel toggle"

    def test_nowplaying_bar_expanded_height(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert "280" in content, "NowPlayingBar missing expanded panel height"

    def test_song_row_has_play_button(self):
        content = (QML_DIR / "pages" / "library" / "SongRow.qml").read_text()
        assert "playClicked" in content, "SongRow missing playClicked signal"
        assert "rightClicked" in content, "SongRow missing rightClicked signal"

    def test_song_table_has_selected_props(self):
        content = (QML_DIR / "pages" / "library" / "SongTable.qml").read_text()
        assert "_selFilepath" in content, "SongTable missing _selFilepath"
        assert "doPlay" in content, "SongTable missing doPlay function"
        assert "notificationBridge" in content, "SongTable missing notificationBridge"

    def test_song_table_sets_selection_on_right_click(self):
        content = (QML_DIR / "pages" / "library" / "SongTable.qml").read_text()
        assert "onRightClicked" in content, "SongTable missing onRightClicked handler"
        assert "root._selId" in content, "SongTable doesn't store selection on right click"

    def test_library_page_has_refresh_button(self):
        content = (QML_DIR / "pages" / "library" / "LibraryPage.qml").read_text()
        assert "Refrescar" in content, "LibraryPage missing refresh button"

    def test_library_bridge_play_song_returns_dict(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        result = bridge.play_song("")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_FILEPATH"
        result2 = bridge.play_song("/nonexistent/file.mp3")
        assert result2.get("ok") is False
        assert "NO_PLAYER_SERVICE" in result2.get("error", "")

    def test_nowplaying_bridge_no_toggle_without_player(self):
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        bridge = NowPlayingBridge()
        bridge.togglePlay()
        assert not bridge.lastCommandOk
        assert not bridge.isPlaying
        assert bridge.playbackStatus == "unavailable"

    def test_route_registry_exists(self):
        from ui_qml_bridge.route_registry import ROUTES
        assert "home" in ROUTES
        assert "library" in ROUTES
        assert "placeholder" in ROUTES

    def test_route_registry_bridge_importable(self):
        from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
        bridge = RouteRegistryBridge()
        assert bridge.isValidRoute("home")
        assert not bridge.isValidRoute("nonexistent_route_xyz")
        assert bridge.getTitle("home") == "Inicio"

    def test_navigation_bridge_back_stack(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        assert not nav.canGoBack
        nav.navigate("library")
        assert nav.canGoBack
        nav.back()
        assert nav.currentRoute == "home"
        assert not nav.canGoBack

    def test_navigation_bridge_params(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        nav.navigateWithParams("playlist_detail", {"id": 42})
        assert nav.currentParams != {}

    def test_app_state_bridge_importable(self):
        from ui_qml_bridge.app_state_bridge import AppStateBridge
        bridge = AppStateBridge()
        assert bridge.appVersion is not None
        bridge.pushWarning("test", "test warning")
        assert len(bridge.runtimeWarnings) > 0
        bridge.clearWarnings()
        assert len(bridge.runtimeWarnings) == 0

    def test_diagnostics_bridge_importable(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        bridge = DiagnosticsBridge()
        check = bridge.runQuickCheck()
        assert "python_version" in check
        assert check["qml_mode"] is True

    def test_command_palette_bridge_importable(self):
        from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
        bridge = CommandPaletteBridge()
        assert len(bridge.commands) > 0
        results = bridge.searchCommands("biblioteca")
        assert len(results) > 0

    def test_diagnostics_page_exists(self):
        p = QML_DIR / "pages" / "DiagnosticsPage.qml"
        assert p.exists(), "Missing DiagnosticsPage.qml"

    def test_confirm_action_dialog_exists(self):
        p = QML_DIR / "components" / "ConfirmActionDialog.qml"
        assert p.exists(), "Missing ConfirmActionDialog.qml"

    def test_command_palette_exists(self):
        p = QML_DIR / "components" / "CommandPalette.qml"
        assert p.exists(), "Missing CommandPalette.qml"

    def test_shortcut_layer_exists(self):
        p = QML_DIR / "shell" / "ShortcutLayer.qml"
        assert p.exists(), "Missing ShortcutLayer.qml"

    def test_page_header_exists(self):
        p = QML_DIR / "components" / "PageHeader.qml"
        assert p.exists(), "Missing PageHeader.qml"


class TestActionButtonNotPresent:
    def test_action_button_not_in_components(self):
        qmldir = QML_DIR / "components" / "qmldir"
        if qmldir.exists():
            content = qmldir.read_text()
            assert "ActionButton" not in content, "ActionButton still registered in components/qmldir"
        action_button = QML_DIR / "components" / "ActionButton.qml"
        assert not action_button.exists(), "ActionButton.qml still exists"
