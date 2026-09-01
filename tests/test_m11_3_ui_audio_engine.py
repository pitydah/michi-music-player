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

    def test_popup_live_bound_not_imperative(self):
        """M11.3-UI-R1 (P1-03): the popup is permanently bound to the
        parent projections — no imperative copies before opening."""
        npb = read("player/NowPlayingBar.qml")
        assert "enginePopup.engines =" not in npb
        assert "enginePopup.selectedEngineId =" not in npb
        assert "engines: root.audioEngines" in npb
        assert "selectedEngineId: root.selectedEngineId" in npb
        assert "activeEngineId: root.activeEngineId" in npb
        assert "switchingTo: root.audioEngineSwitchingTo" in npb

    def test_open_requests_controlled_refresh(self):
        npb = read("player/NowPlayingBar.qml")
        assert "audioEngineRefreshRequested()" in npb
        assert "enginePopup.open()" in npb
        assert npb.index("enginePopup.open()") < npb.index(
            "root.audioEngineRefreshRequested()"
        )

    def test_popup_and_settings_consume_application_plan_roles(self):
        popup = read("player/AudioEnginePopup.qml")
        settings = read("views/AudioEngineSettingsSection.qml")
        for source in (popup, settings):
            assert "modelData.selectionAllowed" in source
            assert "modelData.selectionAction" in source
            assert "modelData.selectionBlocker" in source

    def test_tooltip_uses_friendly_names_not_ids(self):
        """M11.3-UI-R1 (P2-02): tooltip never shows canonical engine IDs."""
        npb = read("player/NowPlayingBar.qml")
        tooltip_fn = npb.split("function audioEngineTooltip()")[1].split(
            "function formatTime"
        )[0]
        assert "audioEngineActiveName" in tooltip_fn
        assert "audioEngineSelectedName" in tooltip_fn
        # canonical IDs never appear in displayed text (they may appear in
        # comparison conditions, never in the .arg() output)
        assert ".arg(root.activeEngineId" not in tooltip_fn
        assert ".arg(root.selectedEngineId" not in tooltip_fn
        assert "qt_multimedia" not in tooltip_fn

    def test_tooltip_fallback_wording(self):
        npb = read("player/NowPlayingBar.qml")
        tooltip_fn = npb.split("function audioEngineTooltip()")[1].split(
            "function formatTime"
        )[0]
        assert "%1 in use · %2 preferred" in tooltip_fn

    def test_appshell_surfaces_switch_failure_toast(self):
        """M11.3-UI-R1 (P1-04): switch failures reach the existing
        ToastHost through AppShell — no new notification machinery."""
        shell = read("shell/AppShell.qml")
        assert "Connections {" in shell
        assert "target: audioEngine" in shell
        assert "onSwitchFailed" in shell
        assert "showToast(message" in shell
        assert "toastHost.show(text, tone)" in shell
        assert shell.count("ToastHost {") == 1  # reused, not duplicated

    def test_appshell_binds_friendly_engine_names(self):
        shell = read("shell/AppShell.qml")
        assert "audioEngineActiveName: audioEngine.activeEngineName" in shell
        assert "audioEngineSelectedName: audioEngine.selectedEngineName" in shell

    def test_popup_reduced_motion_gate(self):
        """M11.3-UI-R2 P2-01: enter/exit fades are gated on
        MichiAccessibility.reducedMotion — deterministic open/close."""
        popup = read("player/AudioEnginePopup.qml")
        assert popup.count("enabled: !MichiAccessibility.reducedMotion") == 2

    def test_popup_keyboard_navigation_skips_disabled(self):
        """M11.3-UI-R2 P2-02: Up/Down navigation resolves ENABLED rows."""
        popup = read("player/AudioEnginePopup.qml")
        assert "function _navigate(fromIndex, delta)" in popup
        assert "item.enabled" in popup
        assert "KeyNavigation.up: root._navigate(index, -1)" in popup
        assert "KeyNavigation.down: root._navigate(index, 1)" in popup

    def test_settings_cards_keyboard_navigation_skips_disabled(self):
        section = read("views/AudioEngineSettingsSection.qml")
        assert "function _navigate(fromIndex, delta)" in section
        assert "KeyNavigation.up: root._navigate(index, -1)" in section
        assert "KeyNavigation.down: root._navigate(index, 1)" in section


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
