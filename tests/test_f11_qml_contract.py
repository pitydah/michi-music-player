"""F11 presentation contract: real QML surfaces and the surgical slot map."""

# ruff: noqa: N802 - fake QML bridge properties intentionally use camelCase.

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

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


def test_quality_badge_is_a_real_signal_truth_button():
    source = NOW_PLAYING.read_text(encoding="utf-8")
    marker = source.index('objectName: "qualityBadge"')
    block = _block(source, "qualityBadge")
    prefix = source[max(0, marker - 240) : marker]
    assert "Button" in prefix
    assert "signalTruthPopup.open()" in block
    assert "Accessible.role: Accessible.Button" in block
    assert "MichiSignalIndicator" in block
    assert "indicatorState" in block
    assert "GradientStop" not in block


def test_signal_node_rail_uses_index_and_state_semantics():
    node = (QML_DIR / "components" / "MichiSignalNode.qml").read_text(encoding="utf-8")
    assert "root.y > 0" not in node
    assert "root.first" in node
    assert "root.last" in node
    assert "stageIndex" in node
    assert "stateText" in node
    assert "segmentColor" in node


def test_nowplaying_indicator_is_bound_to_the_signal_path_bridge():
    source = NOW_PLAYING.read_text(encoding="utf-8")
    block = _block(source, "qualityBadge")
    assert "signalPathBridge.indicatorState" in block
    assert "signalPathBridge.indicatorTooltip" in block
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
        assert "Overlay.overlay.height - height - MichiSpacing.sm" in now_playing
        assert "qualityBadge.mapToItem(Overlay.overlay, 0, 0).y" in now_playing
    finally:
        popup.deleteLater()
