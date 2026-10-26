from __future__ import annotations

import importlib.util

import pytest

from michi.application.dsd_to_pcm_plan import DsdToPcmPlanner
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)
from tests.audio_phase2.test_dsd_source_truth import build_dsf

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="GStreamer Python bindings unavailable"
)


def _format() -> DsdSignalFormat:
    return DsdSignalFormat(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.LSBF,
        organization=DsdOrganization.PLANAR,
        layout=("FL", "FR"),
    )


def test_real_gst_libav_dsd64_to_pcm_fakesink(tmp_path):
    from michi.infrastructure.dsd.dsd_to_pcm import (
        DsdToPcmRuntime,
        discover_dsd_pcm_backend,
    )

    backend = discover_dsd_pcm_backend()
    assert backend.available
    source = tmp_path / "tone.dsf"
    source.write_bytes(build_dsf(sample_count=88_200, payload=bytes([0x69]) * 176_400))
    plan = DsdToPcmPlanner().plan(
        source_identity="track:test",
        source_format=_format(),
        quality_profile="FAST",
        binding_generation=1,
        available_output_rates=(88_200,),
        decoder_available=True,
        target_qualified=True,
        backend_version=backend.version,
    )
    evidence = DsdToPcmRuntime().run(
        plan, source, sink_factory="fakesink", timeout_s=30.0
    )
    assert evidence.status == "PASS"
    assert evidence.eos is True
    assert evidence.target_rate_hz == 88_200
    assert "F32LE" in evidence.negotiated_caps
    assert "rate=(int)88200" in evidence.negotiated_caps
    assert evidence.decoder_factory == "avdec_dsd_lsbf"
