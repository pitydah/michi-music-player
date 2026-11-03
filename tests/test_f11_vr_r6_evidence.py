"""VR-R6 evidence: machine-checked captures and presentation contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/audio/phase2/F11_VR_R6_EVIDENCE.json"
QML = ROOT / "src/michi/presentation/qml"


def test_r6_captures_and_runtime_log_are_hash_pinned() -> None:
    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    captures = document["kwin"]["captures"]
    assert len(captures) == 8
    surfaces = {capture["surface"] for capture in captures}
    assert {
        "nowplaying_full",
        "quick_equalizer",
        "advanced_graphic",
        "signal_truth_live",
        "signal_truth_historical",
        "audio_engine",
        "audio_output",
    } <= surfaces
    for capture in captures:
        path = ROOT / capture["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == capture["sha256"], capture["file"]

    log = (ROOT / document["kwin"]["runtime_log"]).read_text(encoding="utf-8")
    for fingerprint in (
        "TypeError",
        "ReferenceError",
        "Unable to assign",
        "Cannot read property",
    ):
        assert fingerprint not in log
    assert "AtSpiAdaptor" in log


def test_signal_truth_uses_typed_badge_and_measured_overlay_geometry() -> None:
    source = (QML / "player/SignalTruthPopup.qml").read_text(encoding="utf-8")
    now_playing = (QML / "player/NowPlayingBar.qml").read_text(encoding="utf-8")
    badge = (QML / "components/MichiQualityDot.qml").read_text(encoding="utf-8")

    assert "SIGNAL TRUTH" in source
    assert "LAST PLAYBACK" in source
    assert "MichiQualityDot" in source
    assert "pathProofState" in source
    assert source.count("Historical") == 0
    assert "focusFirstStage" in source
    assert 'text: qsTr("Close")' not in source
    assert "parent: Overlay.overlay" in now_playing
    assert "function positionTruthPopup()" in now_playing
    assert "qualityBadge.mapToItem(Overlay.overlay, 0, 0)" in now_playing
    assert "sourceQualityClass" in now_playing
    assert "qualityClass" in badge
    assert "qualityClass === \"pcm_hires\"" in badge


def test_advanced_equalizer_exposes_the_premium_workspace_contract() -> None:
    source = (QML / "player/AdvancedEqualizerPopup.qml").read_text(encoding="utf-8")
    plot = (QML / "components/MichiEqResponsePlot.qml").read_text(encoding="utf-8")

    assert "Math.min(960" in source
    assert "Math.min(700" in source
    assert "Graphic 10" in source
    assert "PEAK 10" in source
    assert 'text: qsTr("Discard draft")' in source
    assert 'text: qsTr("Apply draft")' in source
    assert 'text: qsTr("Close")' not in source
    assert "padLeft = 40" in plot
    assert "padRight = 16" in plot
    assert "padTop = 16" in plot
    assert "padBottom = 26" in plot
    assert 'qsTr("Calculated response · draft")' in plot
    assert plot.count("Calculated response") == 1
