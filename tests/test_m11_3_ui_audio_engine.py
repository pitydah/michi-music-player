"""M11.3-UI — Audio Engine presentation & settings tests.

Structural + behavioral gates: NowPlayingBar quick selector, popup,
Settings Audio Engine section, selected != active truth, fallback UX,
availability/error UX, DAC separation. No new skips.
"""

from pathlib import Path

QML_DIR = Path("src/michi/presentation/qml").resolve()


def read(rel):
    return Path(QML_DIR, rel).read_text(encoding="utf-8")


def read_all(rel):
    return Path("src/michi", rel).read_text(encoding="utf-8")


class TestNowPlayingBar:
    def test_audio_engine_button_replaces_indicator(self):
        npb = read("player/NowPlayingBar.qml")
        assert npb.count('objectName: "audioEngineButton"') == 1
        assert 'objectName: "audioEngineIndicator"' not in npb

    def test_output_device_button_preserved_disabled(self):
        npb = read("player/NowPlayingBar.qml")
        assert npb.count('objectName: "outputDeviceButton"') == 1
        assert "enabled: false" in npb
        assert 'accessibleName: qsTr("Output selection unavailable")' in npb

    def test_popup_exists_and_has_engine_rows(self):
        popup = read("player/AudioEnginePopup.qml")
        assert "engines" in popup
        assert "displayName" in popup
        assert "Active" in popup
        assert "Not available" in popup
        assert "Switching" in popup
        assert "Preferred" in popup
        assert "engineSwitchRequested" in popup

    def test_popup_no_technical_clutter(self):
        """The popup exposes no technical UI strings (comments excluded)."""
        popup = read("player/AudioEnginePopup.qml")
        for line in popup.splitlines():
            stripped = line.strip()
            if stripped.startswith("//"):
                continue  # comments are developer text, not UI
            for forbidden in (
                "DAC",
                "DSD",
                "sample rate",
                "buffer",
                "socket",
                "pipeline",
            ):
                assert forbidden not in stripped, (forbidden, line)

    def test_nowplaying_bar_no_advanced_settings(self):
        npb = read("player/NowPlayingBar.qml")
        for forbidden in ("buffer", "latency", "resampl", "sample rate", "DSD", "DoP"):
            assert forbidden not in npb, forbidden

    def test_nowplaying_shell_wiring(self):
        shell = read("shell/AppShell.qml")
        assert "audioEngine.engines" in shell
        assert "audioEngine.switch_engine" in shell
        assert "audioEngine.refresh_engines" in shell


class TestSettingsAudioEngine:
    def test_settings_has_audio_engine_section(self):
        settings = read("views/SettingsView.qml")
        assert "AudioEngineSettingsSection" in settings
        assert "audioEngineSettingsSection" in settings

    def test_settings_explanation_and_separation(self):
        section = read("views/AudioEngineSettingsSection.qml")
        assert "This is separate from the audio device or DAC" in section
        assert "Preferred" in section
        assert "In use" in section

    def test_engine_cards_render_from_bridge_data(self):
        """Cards are data-driven: the bridge supplies the canonical engine
        display names; the section renders displayName + shortIdentity."""
        section = read("views/AudioEngineSettingsSection.qml")
        assert "modelData.displayName" in section
        assert "modelData.shortIdentity" in section
        assert "modelData.description" in section
        assert "modelData.canActivate" in section
        bridge = Path("src/michi/presentation/audio_engine_bridge.py").read_text()
        assert "Qt Multimedia" in bridge
        assert "GStreamer" in bridge
        assert "MPD" in bridge

    def test_advanced_details_progressive(self):
        section = read("views/AudioEngineSettingsSection.qml")
        assert "Advanced engine details" in section
        assert "Technical reason" in section
        assert "Engine ID" in section
        assert "Transport capabilities" in section

    def test_settings_no_fake_audiophile_controls(self):
        section = read("views/AudioEngineSettingsSection.qml")
        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            for forbidden in (
                "bit-perfect",
                "DSD",
                "DoP",
                "exclusive",
                "Audiophile Mode",
            ):
                assert forbidden not in stripped, (forbidden, line)
        # "DAC" appears only in the explanatory separation sentence
        assert "separate from the audio device or DAC" in section

    def test_settings_managed_note(self):
        section = read("views/AudioEngineSettingsSection.qml")
        assert "managed automatically by Michi" in section

    def test_settings_engine_switch_wiring(self):
        settings = read("views/SettingsView.qml")
        assert "audioEngine.switch_engine" in settings


class TestBridgeIntegration:
    def test_bridge_context_property_registered(self):
        bootstrap = Path("src/michi/bootstrap/__init__.py").read_text()
        assert 'setContextProperty("audioEngine"' in bootstrap
        assert "AudioEngineBridge(" in bootstrap

    def test_bridge_uses_same_runtime_services(self):
        bootstrap = Path("src/michi/bootstrap/__init__.py").read_text()
        assert "graph.audio_engine_service" in bootstrap
        assert "graph.audio_engine_registry" in bootstrap
        assert "self._engine_selection_coordinator" in bootstrap

    def test_bridge_dispose_in_shutdown(self):
        bootstrap = Path("src/michi/bootstrap/__init__.py").read_text()
        assert "self._aeb" in bootstrap

    def test_bridge_no_infrastructure_imports(self):
        bridge = Path("src/michi/presentation/audio_engine_bridge.py").read_text()
        for forbidden in ("GStreamerAudioPort", "MPDAudioPort", "QtMultimediaBackend"):
            assert forbidden not in bridge, forbidden

    def test_bridge_engine_descriptions_plain(self):
        bridge = Path("src/michi/presentation/audio_engine_bridge.py").read_text()
        assert "Compatibility" in bridge
        assert "Precision" in bridge
        assert "Dedicated" in bridge
        for overclaim in ("bit-perfect", "exclusive", "DSD"):
            assert overclaim not in bridge, overclaim
