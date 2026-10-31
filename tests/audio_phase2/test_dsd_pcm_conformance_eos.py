"""AP2-F10 C7 — the conformance capture must reach EOS.

The measurement sink must consume the whole stream so EOS reaches the bus.
An appsink blocks its streaming thread once its queue is full; a fakesink with
the capture pad probe drains to EOS. The probe must also be installed before the
pipeline prerolls, otherwise the first buffers are missing from the capture.
"""

from __future__ import annotations

import importlib.util
import shutil

import pytest

from tools.audio_phase2.dsd2pcm_conformance import (
    CORPUS_SAMPLE_COUNT,
    _dsf_blob,
    run,
)

_HAS_GI = importlib.util.find_spec("gi") is not None
_HAS_FFMPEG = shutil.which("ffmpeg") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI or not _HAS_FFMPEG,
    reason="GStreamer bindings or ffmpeg unavailable",
)


def test_tone_capture_reaches_eos_and_matches_the_reference(tmp_path) -> None:
    source = tmp_path / "tone_1khz.dsf"
    source.write_bytes(
        _dsf_blob(sample_count=CORPUS_SAMPLE_COUNT, frequency_hz=1_000)
    )
    result = run(
        fixture=source,
        target_rate=88_200,
        profile="HIGH",
        expected_frequency_hz=1_000,
        fixture_name="tone_1khz",
    )
    assert result["sample_count"] > 0
    assert result["cleanup_confirmed"] is True
    assert result["eos_observed"] is True
    assert result["reference"]["status"] == "PASS"
    assert result["numeric_checks"]["magnitude_error_le_0_10_db"] == "PASS"
    assert result["status"] == "PASS"
