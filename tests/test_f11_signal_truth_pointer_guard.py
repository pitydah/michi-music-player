"""Signal Truth P0 pointer containment + icon semantics (AP2-F11 VR-R2).

This is a source contract only. A real QTest/KWin pointer E2E test is a
separate closure gate; no screenshot or source test proves event delivery.
"""

from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src/michi/presentation/qml"


def _qml(path: str) -> str:
    return (QML / path).read_text(encoding="utf-8")


def test_truth_popup_is_modal_without_dimming() -> None:
    popup = _qml("player/SignalTruthPopup.qml")
    assert "modal: true" in popup
    assert "dim: false" in popup
    assert "Popup.CloseOnPressOutside" in popup
    assert "signalPathBridge" in popup
    assert "playPauseRequested" not in popup
    assert "trackActivated" not in popup


def test_signal_node_has_exclusive_mouse_owner_and_one_semantic_icon() -> None:
    node = _qml("components/MichiSignalNode.qml")
    assert "TapHandler {" not in node
    assert node.count("MouseArea {") == 1
    assert "propagateComposedEvents: false" in node
    assert "preventStealing: true" in node
    assert "MichiSignalStageIcon" in node
    assert "roleName: root.iconName" in node
    assert "name: root.glyphName" in node  # independent evidence badge
    assert "height: Math.max(0, parent.height - 40)" in node
    assert "Keys.onSpacePressed" in node


def test_compact_dac_view_is_not_a_dead_navigation_surface() -> None:
    view = _qml("components/MichiSignalPathView.qml")
    assert "compact: root.compact" in view
    assert 'configAction: root.compact ? "NONE"' in view


def test_semantic_stage_icons_have_explicit_license() -> None:
    icon = _qml("components/MichiSignalStageIcon.qml")
    assert "Tabler Icons (MIT)" in icon
    assert "Permission is hereby granted" in icon
    for symbol in ("track", "audio-engine", "equalizer", "audio-output"):
        assert symbol in icon
    assert "Canvas" in icon
    assert "QtSvg" in icon  # documentation: no runtime QtSvg dependency


def test_read_only_advanced_tabs_never_apply_the_quick_eq_graph() -> None:
    advanced = _qml("player/AdvancedEqualizerPopup.qml")
    assert "Edits are drafts until Apply confirms host readback" in advanced
    assert "root.processingBridge.apply_draft_async()" in advanced
    assert "root.processingBridge.discard_draft()" in advanced


def test_unverified_dsp_is_not_labeled_proven_in_the_headline() -> None:
    bridge = (QML.parent / "signal_path_bridge.py").read_text(encoding="utf-8")
    assert 'verdict_state == "dsp" and processing_state == "unknown"' in bridge
    assert 'headline = "DSP detected · identity unverified"' in bridge


def test_nowplaying_capsule_uses_bar_integrated_material() -> None:
    bar = _qml("player/NowPlayingBar.qml")
    assert 'objectName: "trackCard"' in bar
    assert "materialOpacityOverride: 1.0" in bar
    assert "allowBackdropBlur: false" in bar
    assert "shadowed: false" in bar
    assert "tileSeed: 17" in bar
    assert "Layout.preferredWidth: 66" in bar
    assert "root.nowPlayingRequested()" in bar


def test_audio_route_popups_share_visual_grammar() -> None:
    engine = _qml("player/AudioEnginePopup.qml")
    output = _qml("player/AudioOutputPopup.qml")
    for popup in (engine, output):
        assert "modal: true" in popup and "dim: false" in popup
        assert "MichiAudioRouteIcon {" in popup
        assert "MichiRouteSelectionSkin {" in popup
        assert "roleName:" in popup
    assert 'routeIconName: "engine"' in engine
    assert 'routeIconName: "dac"' in output


def test_audio_route_action_contracts_are_preserved() -> None:
    engine = _qml("player/AudioEnginePopup.qml")
    output = _qml("player/AudioOutputPopup.qml")
    assert "root.engineSwitchRequested(row.modelData.id)" in engine
    assert "root.deviceSelectionRequested(row.modelData.stableDeviceId)" in output
    assert "root.sharedSelectionRequested()" in output
    assert "root.displayAudioExpanded = !root.displayAudioExpanded" in output
    assert "root.recoveryActionRequested(modelData.action)" in output
    assert "root.settingsRequested()" in output


def test_audio_icon_draws_without_html_canvas_roundrect() -> None:
    icons = _qml("components/MichiAudioRouteIcon.qml")
    surface = _qml("components/MichiRouteSelectionSkin.qml")
    header = _qml("components/MichiPopupHeader.qml")
    assert "ctx.roundRect" not in icons
    assert "ctx.quadraticCurveTo" in icons
    for role in ("engine", "gstreamer", "mpd", "system", "display", "usb", "internal"):
        assert role in icons
    assert "readonly property" not in surface or "active" in surface
    assert "routeIconName" in header
