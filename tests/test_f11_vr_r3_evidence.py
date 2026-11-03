"""F11 VR-R3 evidence stays machine-checkable and honest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/audio/phase2/F11_VR_R3_EVIDENCE.json"


def _document() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_r3_captures_exist_and_match_their_hashes() -> None:
    document = _document()
    captures = document["captures"]
    assert len(captures) >= 8
    names = {capture["name"] for capture in captures}
    assert {
        "signal_active_stress_900x600",
        "signal_pcm_direct_active",
        "signal_dsp_active",
        "signal_dsp_active_readback",
        "native_active_truth_pending",
        "high_contrast_active",
        "reduced_motion_active",
    } <= names
    for capture in captures:
        path = ROOT / capture["file"]
        assert path.is_file(), path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == capture["sha256"], capture["file"]


def test_r3_claims_do_not_hide_failed_or_unverified_paths() -> None:
    document = _document()
    matrix = document["pointer_keyboard_matrix"]
    assert matrix["outside_click_over_library_row"].startswith("PASS")
    assert matrix["keyboard_escape"].startswith("PASS")
    assert matrix["scroll_inside_popup"].startswith("PASS")
    assert "DOP_QUALIFICATION_FAILED" in document["not_run"]["dop_active_signal"]
    assert "DSD_PCM_TARGET_UNQUALIFIED" in document["not_run"]["dsd_pcm_active_signal"]
    assert "Pending/Unknown" in document["limitations"][0]
    assert document["tests"]["full_suite"] == "PENDING"
    assert document["tests"]["ci"] == "PENDING"
