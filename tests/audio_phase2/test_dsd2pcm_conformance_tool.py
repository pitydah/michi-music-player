from __future__ import annotations

import importlib.util

import pytest

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="GStreamer Python bindings unavailable"
)


def test_conformance_harness_captures_real_f32le_and_releases():
    from tools.audio_phase2.dsd2pcm_conformance import run

    result = run(fixture=None, target_rate=88_200, profile="FAST")
    assert result["status"] == "PARTIAL"
    assert result["sample_count"] > 0
    assert result["metrics"]["nan_inf"] == 0
    assert result["cleanup_confirmed"] is True
    assert result["release"]["terminal_state"] == "RELEASED"
    assert result["output_sha256"]
    assert result["caps_negotiated"]
