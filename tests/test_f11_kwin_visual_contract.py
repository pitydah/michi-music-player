"""F11 KWin visual evidence contract.

The test checks the manifest and image hashes; it is not a pixel-diff golden.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_AUDIT = _ROOT / "docs/audio/phase2/F11_VISUAL_AUDIT.json"


def _audit() -> dict:
    return json.loads(_AUDIT.read_text(encoding="utf-8"))


def test_every_reviewed_capture_matches_the_recorded_hash() -> None:
    audit = _audit()
    captures = audit["captures"]
    assert len(captures) >= 12
    for capture in captures:
        assert capture["reviewed"] is True
        image = _ROOT / capture["file"]
        assert image.is_file(), capture["file"]
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        assert digest == capture["sha256"], capture["file"]


def test_visual_audit_covers_the_required_surfaces_and_viewports() -> None:
    audit = _audit()
    surfaces = {capture["surface"] for capture in audit["captures"]}
    assert {
        "NowPlayingBar",
        "EqualizerPopup",
        "SignalTruthPopup",
        "AdvancedEqualizerPopup",
        "AudioEnginePopup",
        "AudioOutputPopup",
    } <= surfaces
    viewports = {capture["viewport"] for capture in audit["captures"]}
    assert {"full", "compact", "narrow", "stress"} <= viewports
    assert audit["checks"]["nowplaying_height_154"] == "PASS"
    assert audit["checks"]["popup_mutual_exclusivity"] == "PASS"
    assert audit["checks"]["automated_pixel_golden_diff"] == "NOT_RUN"


def test_runtime_log_has_no_qml_warning_fingerprints() -> None:
    audit = _audit()
    runtime_log = audit["runtime_log"]
    path = _ROOT / runtime_log["file"]
    assert path.is_file()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == runtime_log["sha256"]
    text = path.read_text(encoding="utf-8")
    for fingerprint in (
        "TypeError",
        "ReferenceError",
        "Unable to assign",
        "Cannot read property",
        "QML",
    ):
        assert fingerprint not in text
    assert "AtSpiAdaptor" in text
