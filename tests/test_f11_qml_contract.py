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
    assert "sourceQualityClass" not in block
    assert "MichiSignalIndicator" not in block
    assert "indicatorState" not in block
    assert "Layout.preferredWidth: 8" in block
    assert "Layout.preferredHeight: 8" in block
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
    assert "qualityDotColor()" in block
    assert "function qualityDotColor()" in source
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


def test_advanced_equalizer_has_the_five_named_tabs(qapp):
    popup = _instantiate(QML_DIR / "player" / "AdvancedEqualizerPopup.qml", 760, 640)
    try:
        assert popup.objectName() == "AdvancedEqualizerPopup"
        source = (QML_DIR / "player" / "AdvancedEqualizerPopup.qml").read_text(
            encoding="utf-8"
        )
        for tab in (
            "Graphic",
            "Parametric",
            "Convolution / FIR",
            "Signal / Resampling",
            "Profiles",
        ):
            assert tab in source
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
            NowPlayingBar {
                objectName: "barUnderTest"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 154
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
        assert 420.0 <= popup_height <= 520.0
        assert badge_height == pytest.approx(34.0)
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
        assert "signalTruthStagesScroll" in source
        assert "Overlay.overlay.height : 584" in source
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
