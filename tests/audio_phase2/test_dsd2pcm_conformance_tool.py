from __future__ import annotations

import importlib.util

import pytest

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="GStreamer Python bindings unavailable"
)


def test_metrics_survive_all_invalid_and_mixed_samples():
    import math
    import struct

    from tools.audio_phase2.dsd2pcm_conformance import _metrics

    all_invalid = struct.pack("<4f", math.nan, math.inf, -math.inf, math.nan)
    result = _metrics(all_invalid, 2, 88_200)
    assert result["sample_count"] == 2
    assert result["nan_inf"] == 4
    assert result["peak"] is None
    assert result["rms"] is None
    assert result["dc"] is None
    assert result["channel_balance_db"] is None

    mixed = struct.pack("<4f", 0.0, 1.0, math.nan, 0.0)
    result = _metrics(mixed, 2, 88_200)
    assert result["sample_count"] == 2
    assert result["nan_inf"] == 1
    assert result["peak"] == 1.0
    assert math.isfinite(result["rms"])
    assert math.isfinite(result["dc"])


def test_conformance_harness_captures_real_f32le_and_releases():
    from tools.audio_phase2.dsd2pcm_conformance import run

    result = run(fixture=None, target_rate=88_200, profile="FAST")
    assert result["status"] == "PASS"
    assert result["eos_observed"] is True
    assert result["sample_count"] > 0
    assert result["metrics"]["nan_inf"] == 0
    assert result["cleanup_confirmed"] is True
    assert result["release"]["terminal_state"] == "RELEASED"
    assert result["output_sha256"]
    assert result["caps_negotiated"]


def test_stopband_stimulus_measures_the_resampler_rejection(tmp_path):
    pytest.importorskip("numpy")
    from tools.audio_phase2.dsd2pcm_conformance import (
        _dsf_blob,
        run,
    )

    source = tmp_path / "stopband.dsf"
    source.write_bytes(_dsf_blob(sample_count=70_560, frequency_hz=80_000))
    result = run(
        fixture=source,
        target_rate=88_200,
        profile="HIGH",
        expected_frequency_hz=0,
        fixture_name="stopband_80khz",
        stopband_hz=80_000,
    )
    assert result["stopband"]["alias_hz"] == 8_200
    assert result["stopband"]["rejection_db"] >= 80.0
    # End-to-end alias rejection is bounded by the modulator and the analysis
    # bandwidth; it is INFORMATIONAL. The mandatory >=80 dB criterion is the
    # isolated resampler sweep.
    assert result["stopband"]["disposition"].startswith("INFORMATIONAL")
    assert "resampler_stopband_ge_80_db" not in result["numeric_checks"]
    assert result["numeric_checks"]["no_unexpected_clipping"] == "NOT_APPLICABLE"
