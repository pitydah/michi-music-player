"""Signal Truth P0 pointer containment + icon semantics (AP2-F11 VR-R2).

This is a source contract only. A real QTest/KWin pointer E2E test is a
separate closure gate; no screenshot or source test proves event delivery.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "src/michi/presentation/qml"


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
    # Evidence is an independent microdot, never a second semantic glyph.
    assert "width: 6" in node
    assert "color: root.stateColor" in node
    assert "height: Math.max(0, parent.height - 42)" in node
    assert "width: 32" in node
    assert "height: 32" in node
    assert "Keys.onSpacePressed" in node


def test_compact_dac_view_is_not_a_dead_navigation_surface() -> None:
    view = _qml("components/MichiSignalPathView.qml")
    assert "compact: root.compact" in view
    assert "configurationEnabled" in view
    assert "configAction: root.configurationEnabled" in view
    assert '(modelData.configAction || "NONE") : "NONE"' in view


def test_semantic_stage_icons_have_explicit_license() -> None:
    icon = _qml("components/MichiSignalStageIcon.qml")
    assert "Tabler Icons geometry (MIT)" in icon
    assert "MIT License" in icon
    for symbol in (
        "file-music",
        "cpu",
        "adjustments-horizontal",
        "arrows-exchange",
        "wave-sine",
        "circuit-diode",
    ):
        assert symbol in icon
    assert "PathSvg" in icon
    assert "Canvas" not in icon
    assert "QtSvg" not in icon


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
    assert "Layout.preferredHeight: 96" in bar
    assert "Layout.preferredWidth: 72" in bar
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


def test_audio_icons_use_official_tabler_svg() -> None:
    icons = _qml("components/MichiAudioRouteIcon.qml")
    stage_icon = _qml("components/MichiSignalStageIcon.qml")
    surface = _qml("components/MichiRouteSelectionSkin.qml")
    header = _qml("components/MichiPopupHeader.qml")
    assert "Canvas {" not in icons
    assert "MichiSignalStageIcon" in icons
    assert "PathSvg" in stage_icon
    assert "preferredRendererType: Shape.CurveRenderer" in stage_icon
    for role in ("engine", "gstreamer", "mpd", "system", "display", "usb", "internal"):
        assert role in stage_icon
    assert "readonly property" not in surface or "active" in surface
    assert "routeIconName" in header


def test_route_icons_cover_every_bridge_icon_type() -> None:
    stage_icon = _qml("components/MichiSignalStageIcon.qml")
    bridge_sources = (
        (ROOT / "src/michi/presentation/audio_engine_bridge.py").read_text(
            encoding="utf-8"
        ),
        (ROOT / "src/michi/presentation/audio_output_bridge.py").read_text(
            encoding="utf-8"
        ),
    )
    # The bridges are the authority for iconType; QML must never sniff names.
    emitted = set()
    for source in bridge_sources:
        emitted.update(re.findall(r'"((?:engine-[a-z-]+|audio-engine))"', source))
        emitted.update(
            re.findall(r'"((?:display-audio|audio-jack|audio-output|dac))"', source)
        )
    assert emitted == {
        "engine-qt",
        "engine-gstreamer",
        "engine-mpd",
        "audio-engine",
        "display-audio",
        "dac",
        "audio-jack",
        "audio-output",
    }
    for role in sorted(emitted) + ["system", "generic", "internal", "display"]:
        assert f'"{role}":' in stage_icon, f"missing route icon alias: {role}"
