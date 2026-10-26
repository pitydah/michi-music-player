from __future__ import annotations

from michi.application.dsd_conversion_evidence import (
    ConversionNode,
    build_dsd_conversion_evidence,
)
from michi.application.dsd_to_pcm_plan import DsdToPcmPlanner
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)


def _plan():
    return DsdToPcmPlanner().plan(
        source_identity="track:1",
        source_format=DsdSignalFormat(
            bit_rate_hz=2_822_400,
            channels=2,
            packing=DsdPacking.DSD_U8,
            bit_order=DsdBitOrder.LSBF,
            organization=DsdOrganization.PLANAR,
            layout=("FL", "FR"),
        ),
        quality_profile="FAST",
        binding_generation=1,
        available_output_rates=(88_200,),
        decoder_available=True,
        target_qualified=True,
    )


def test_conversion_path_has_explicit_nodes_and_no_bit_perfect_claim():
    evidence = build_dsd_conversion_evidence(_plan(), dsp_active=True)
    assert evidence.nodes[0] is ConversionNode.SOURCE_DSD
    assert ConversionNode.DSD_TO_PCM_DECODER in evidence.nodes
    assert ConversionNode.RESAMPLER in evidence.nodes
    assert ConversionNode.DSP_NODE in evidence.nodes
    assert evidence.bit_perfect_claim == "NOT_APPLICABLE"
    assert evidence.source_fidelity == "DSD"
    assert evidence.output_fidelity == "PCM_F32LE"


def test_native_rate_has_no_resampler_node():
    plan = DsdToPcmPlanner().plan(
        source_identity="track:1",
        source_format=DsdSignalFormat(
            bit_rate_hz=2_822_400,
            channels=2,
            packing=DsdPacking.DSD_U8,
            bit_order=DsdBitOrder.LSBF,
            organization=DsdOrganization.PLANAR,
            layout=("FL", "FR"),
        ),
        quality_profile="HIGH",
        binding_generation=1,
        available_output_rates=(352_800,),
        decoder_available=True,
        target_qualified=True,
    )
    evidence = build_dsd_conversion_evidence(plan)
    assert ConversionNode.RESAMPLER not in evidence.nodes
    assert ConversionNode.DSP_NODE not in evidence.nodes
