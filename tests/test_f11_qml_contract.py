"""F11 presentation contract: real QML surfaces and the surgical slot map."""

# ruff: noqa: N802 - fake QML bridge properties intentionally use camelCase.

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QMetaObject, QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest

QML_DIR = Path("src/michi/presentation/qml").resolve()
NOW_PLAYING = QML_DIR / "player" / "NowPlayingBar.qml"


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


def _instantiate(path: Path, width: int, height: int) -> QObject:
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine, str(path))
    errors = "; ".join(error.toString() for error in component.errors())
    assert component.status() == QQmlComponent.Ready, f"{path.name}: {errors}"
    obj = component.createWithInitialProperties({"width": width, "height": height})
    assert obj is not None, f"{path.name}: null root"
    # The engine/component own the QML context; keep them alive for the test.
    obj._f11_engine = engine
    obj._f11_component = component
    return obj


def _named(root: QObject, name: str) -> QObject:
    found = root.findChild(QObject, name)
    assert found is not None, f"{name} not found"
    return found


def _block(source: str, object_name: str) -> str:
    marker = source.index(f'objectName: "{object_name}"')
    start = source.rfind("{", 0, marker)
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated block for {object_name}")


def _offset_within(item: QObject, root: QObject) -> tuple[float, float]:
    x = 0.0
    y = 0.0
    current = item
    while current is not None and current is not root:
        x += float(current.property("x") or 0.0)
        y += float(current.property("y") or 0.0)
        current = current.parent()
    assert current is root, "item is not inside the measured root"
    return x, y


def _layout(block: str, key: str) -> int:
    match = re.search(rf"Layout\.{key}:\s*(\d+)", block)
    assert match is not None, f"Layout.{key} missing in {block[:120]}"
    return int(match.group(1))


@pytest.fixture(scope="module")
def now_playing(qapp):
    root = _instantiate(NOW_PLAYING, 1920, 154)
    yield root
    root.deleteLater()


def test_now_playing_keeps_the_certified_geometry_and_real_landmarks(now_playing):
    assert now_playing.property("height") == pytest.approx(154)
    for name in (
        "trackCard",
        "trackArtwork",
        "playbackZone",
        "timeline",
        "playPauseButton",
        "outputZone",
        "queueButton",
        "volumeSlider",
        "qualityBadge",
        "outputDeviceButton",
        "audioEngineButton",
        "settingsButton",
    ):
        _named(now_playing, name)
    assert now_playing.findChild(QObject, "audioEngineIndicator") is None


def test_output_zone_slot_map_is_exact():
    source = NOW_PLAYING.read_text(encoding="utf-8")
    expected = {
        "dacVolumeControl": (0, 0, 2),
        "settingsButton": (0, 2, 1),
        "queueButton": (0, 3, 1),
        "audioEngineButton": (1, 0, 1),
        "qualityBadge": (1, 1, 1),
        "outputDeviceButton": (1, 2, 1),
    }
    for name, (row, column, span) in expected.items():
        block = _block(source, name)
        assert _layout(block, "row") == row, name
        assert _layout(block, "column") == column, name
        if span != 1:
            assert _layout(block, "columnSpan") == span, name
    # No third action row: the fourth column in row 1 is deliberately empty.
    assert "Layout.row: 1\n                Layout.column: 3" in source
    assert "Layout.row: 2" in source


def test_quality_badge_is_a_typed_capsule_and_real_signal_truth_button():
    source = NOW_PLAYING.read_text(encoding="utf-8")
    marker = source.index('objectName: "qualityBadge"')
    block = _block(source, "qualityBadge")
    prefix = source[max(0, marker - 240) : marker]
    assert "Button" in prefix
    assert "signalTruthPopup.open()" in block
    assert "Accessible.role: Accessible.Button" in block
    assert "qualityAccessibleText" in block
    assert "sourceFormatLabel" in block
    assert "sourceRateDepthLabel" in block
    assert "MichiQualityDot" in block
    assert "sourceQualityClass" in block
    assert "MichiSignalIndicator" not in block
    assert "indicatorState" not in block
    assert "GradientStop" not in block


def test_signal_node_rail_uses_index_and_state_semantics():
    node = (QML_DIR / "components" / "MichiSignalNode.qml").read_text(encoding="utf-8")
    assert "root.y > 0" not in node
    assert "root.first" in node
    assert "root.last" in node
    assert "stageIndex" in node
    assert "stateText" in node
    assert "segmentColor" in node


def test_quality_badge_and_proof_are_bound_to_typed_bridge_facts():
    source = NOW_PLAYING.read_text(encoding="utf-8")
    block = _block(source, "qualityBadge")
    assert "signalPathBridge.qualityAccessibleText" in block
    assert "signalPathBridge.sourceFormatLabel" in block
    assert "signalPathBridge.sourceRateDepthLabel" in block
    assert "MichiQualityDot" in block
    assert "signalPathBridge.sourceQualityClass" in source
    assert "signalPathBridge.pathProofState" in source
    assert "hasTrack" not in block


def test_audio_popups_are_mutually_exclusive():
    source = NOW_PLAYING.read_text(encoding="utf-8")
    assert "function closeOtherAudioPopups(exceptId)" in source
    for popup_id in ("equalizer", "engine", "output", "truth"):
        assert f'closeOtherAudioPopups("{popup_id}")' in source
    assert "equalizerPopup.closeAllSurfaces()" in source


def test_equalizer_popup_compiles_and_is_honest_about_its_contract(qapp):
    popup = _instantiate(QML_DIR / "player" / "EqualizerPopup.qml", 440, 470)
    try:
        assert popup.objectName() == "EqualizerPopup"
        source = (QML_DIR / "player" / "EqualizerPopup.qml").read_text(encoding="utf-8")
        assert "set_draft_band" in source
        assert "set_draft_preamp" in source
        assert "AdvancedEqualizerPopup" in source
    finally:
        popup.deleteLater()


def test_equalizer_controls_commit_through_the_bridge(qapp):
    source = (QML_DIR / "player" / "EqualizerPopup.qml").read_text(encoding="utf-8")
    assert "function commitDraft()" in source
    assert "processingBridge.apply_draft_async()" in source
    assert source.count("root.commitDraft()") >= 5
    assert "enabled: root.controlsEnabled" in source
    slider = (QML_DIR / "components" / "MichiEqSlider.qml").read_text(encoding="utf-8")
    assert "root.gainCommitted(root.gainDb)" in slider
    assert "keyboardCommit.restart()" in slider


def test_response_plot_expands_its_scale_for_large_gain(qapp):
    plot = _instantiate(QML_DIR / "components" / "MichiEqResponsePlot.qml", 440, 220)
    try:
        plot.setProperty("points", [{"hz": 20, "db": 0.0}, {"hz": 1000, "db": 30.0}])
        assert plot.property("rangeDb") == 36.0
        plot.setProperty("points", [{"hz": 20, "db": -20.0}, {"hz": 1000, "db": 0.0}])
        assert plot.property("rangeDb") == 24.0
        plot.setProperty("points", [{"hz": 20, "db": -12.0}, {"hz": 1000, "db": 0.0}])
        assert plot.property("rangeDb") == 18.0
    finally:
        plot.deleteLater()


def test_advanced_equalizer_has_the_five_named_tabs(qapp):
    popup = _instantiate(QML_DIR / "player" / "AdvancedEqualizerPopup.qml", 760, 640)
    try:
        assert popup.objectName() == "AdvancedEqualizerPopup"
        source = (QML_DIR / "player" / "AdvancedEqualizerPopup.qml").read_text(
            encoding="utf-8"
        )
        for tab in (
            "Graphic 10",
            "PEAK 10",
            "FIR status",
            "Signal status",
            "Presets",
        ):
            assert tab in source
        assert "Math.min(960" in source
        assert "Math.min(700" in source
        assert "Layout.preferredHeight: Math.min(240" in source
        assert 'text: qsTr("Discard draft")' in source
        assert 'text: qsTr("Validate")' in source
        assert 'text: qsTr("Apply draft")' in source
        assert 'text: qsTr("Close")' not in source
        plot = (QML_DIR / "components" / "MichiEqResponsePlot.qml").read_text(
            encoding="utf-8"
        )
        assert "padLeft = 40" in plot
        assert "padRight = 16" in plot
        assert "padTop = 16" in plot
        assert "padBottom = 26" in plot
        assert 'qsTr("Calculated response · draft")' in plot
        assert plot.count("Calculated response") == 1
        assert "readonly property real rangeDb" in plot
        assert "var levels = [root.rangeDb, 0, -root.rangeDb]" in plot
        assert "legendText: root.responseLegend()" in source
        assert "Layout.maximumWidth: 56" in source
        assert 'objectName: "graphicRailsHost"' in source
        assert "anchors.horizontalCenter: parent.horizontalCenter" in source
    finally:
        popup.deleteLater()


@pytest.mark.parametrize(
    ("width", "height"),
    [(1920, 1036), (1920, 1080), (1366, 768), (900, 600)],
)
def test_signal_truth_popup_is_measured_against_the_quality_badge(qapp, width, height):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine)
    component.setData(
        b"""
        import QtQuick
        import QtQuick.Controls
        import "player"
        ApplicationWindow {
            visible: true
            QtObject {
                id: fakeSignalPath
                property var stages: [
                    { id: "source", title: "Source", summary: "WAVE",
                      detail: "PCM - 16-bit - 44.1 kHz", detailRows: [],
                      configAction: "NONE", state: "observed" },
                    { id: "decode", title: "Decode",
                      summary: "S16LE - 16-bit - 44.1 kHz",
                      detail: "Runtime decoder evidence", detailRows: [],
                      configAction: "OPEN_ENGINE", state: "observed" },
                    { id: "processing", title: "Processing", summary: "Bypassed",
                      detail: "No processing graph installed", detailRows: [],
                      configAction: "OPEN_PROCESSING", state: "bypassed" },
                    { id: "output", title: "Output", summary: "S32_LE - 44.1 kHz",
                      detail: "Container adapted", detailRows: [],
                      configAction: "OPEN_OUTPUT", state: "observed" },
                    { id: "device", title: "DAC / Device", summary: "SMSL USB AUDIO",
                      detail: "usb:152a:85dd", detailRows: [],
                      configAction: "OPEN_DEVICE_SETUP", state: "observed" }
                ]
                property string headline: "Direct path"
                property string proofLevel: "Source - host - transport"
                property string statusLabel: "Active"
                property string status: "ACTIVE"
                property string pathProofState: "partially_verified"
                property string pathProofLabel: "Partially verified"
                property string sourceFormatLabel: "WAVE"
                property string sourceRateDepthLabel: "16-bit - 44.1 kHz"
                property string sourceQualityClass: "pcm_standard"
                property string indicatorState: "observed"
                property string indicatorTooltip: "Signal Truth: path observed"
                property int generation: 7
                function request_configuration(action) {}
            }
            NowPlayingBar {
                objectName: "barUnderTest"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 154
                signalPathBridge: fakeSignalPath
            }
        }
        """,
        QUrl.fromLocalFile(str(QML_DIR / "f11_measure_harness.qml")),
    )
    assert component.status() == QQmlComponent.Ready, "; ".join(
        error.toString() for error in component.errors()
    )
    window = component.createWithInitialProperties({"width": width, "height": height})
    assert window is not None
    QTest.qWait(150)
    try:
        bar = _named(window, "barUnderTest")
        badge = _named(bar, "qualityBadge")
        popup = _named(bar, "SignalTruthPopup")
        emitted: list[str] = []
        bar.seekRequested.connect(lambda *_: emitted.append("seek"))
        bar.playPauseRequested.connect(lambda *_: emitted.append("play"))
        bar.audioEngineSwitchRequested.connect(lambda *_: emitted.append("engine"))
        bar.audioOutputDeviceSelectionRequested.connect(
            lambda *_: emitted.append("device")
        )
        QMetaObject.invokeMethod(bar, "positionTruthPopup")
        QMetaObject.invokeMethod(popup, "open")
        QTest.qWait(120)
        assert popup.property("visible") is True
        viewport = _named(popup, "signalTruthStagesViewport")
        popup_width = float(popup.property("width"))
        popup_height = float(popup.property("height"))
        popup_x = float(popup.property("x"))
        popup_y = float(popup.property("y"))
        badge_x, badge_y = _offset_within(badge, bar)
        badge_x += float(bar.property("x") or 0.0)
        badge_y += float(bar.property("y") or 0.0)
        badge_width = float(badge.property("width"))
        badge_height = float(badge.property("height"))
        assert abs((popup_x + popup_width) - (badge_x + badge_width)) <= 1.0
        assert popup_x >= 8.0
        assert popup_x + popup_width <= width - 8.0
        assert popup_y >= 8.0
        assert popup_y + popup_height <= height - 8.0
        gap = badge_y - (popup_y + popup_height)
        assert 8.0 <= gap <= 12.0
        assert 420.0 <= popup_width <= 520.0
        if height >= 768:
            assert 560.0 <= popup_height <= 680.0
        else:
            assert 420.0 <= popup_height <= 560.0
        assert badge_height == pytest.approx(34.0)
        content_height = float(viewport.property("contentHeight"))
        viewport_height = float(viewport.property("height"))
        assert viewport.property("interactive") is (
            content_height > viewport_height + 1
        )
        if height >= 768:
            assert viewport.property("interactive") is False
        QMetaObject.invokeMethod(popup, "close")
        QTest.qWait(300)
        assert popup.property("visible") is False
        assert badge.property("activeFocus") is True
        assert emitted == []
    finally:
        window.close()
        window.deleteLater()
        component.deleteLater()
        engine.deleteLater()


def test_signal_truth_popup_never_claims_unproven_truth(qapp):
    popup = _instantiate(QML_DIR / "player" / "SignalTruthPopup.qml", 440, 620)
    try:
        assert popup.objectName() == "SignalTruthPopup"
        source = (QML_DIR / "player" / "SignalTruthPopup.qml").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "Bit-perfect playback",
            "Exclusive verified",
            "Native DSD preserved",
            "DoP verified end-to-end",
        ):
            assert forbidden not in source
        assert "MichiSignalPathView" in source
        assert "stages: root.stages" in source
        assert "expandedStageId" in source
        assert "signalTruthStagesViewport" in source
        assert "desiredHeight" in source
        assert "interactive: contentHeight > height + 1" in source
        assert "MichiQualityDot" in source
        assert "sourceLine" in source
        assert "proofLabel" in source
        assert "focusFirstStage" in source
        assert "SIGNAL TRUTH" in source
        assert "LAST PLAYBACK" in source
        assert 'text: qsTr("Close")' not in source
        assert "Overlay.overlay.height : 768" in source
        now_playing = (QML_DIR / "player" / "NowPlayingBar.qml").read_text(
            encoding="utf-8"
        )
        assert "parent: Overlay.overlay" in now_playing
        assert "function positionTruthPopup()" in now_playing
        assert (
            "Overlay.overlay.height - signalTruthPopup.height - MichiSpacing.sm"
            in now_playing
        )
        assert "qualityBadge.mapToItem(Overlay.overlay, 0, 0)" in now_playing
        assert "opener.y - signalTruthPopup.height" in now_playing
    finally:
        popup.deleteLater()
