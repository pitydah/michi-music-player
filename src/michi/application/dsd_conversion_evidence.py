"""Honest Signal Truth/Path evidence for explicit DSD→PCM conversion."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from michi.application.dsd_to_pcm_plan import DsdToPcmPlan


class ConversionNode(StrEnum):
    SOURCE_DSD = "SOURCE_DSD"
    DSD_TO_PCM_DECODER = "DSD_TO_PCM_DECODER"
    PCM_LAYOUT_NORMALIZER = "PCM_LAYOUT_NORMALIZER"
    RESAMPLER = "RESAMPLER"
    DSP_NODE = "DSP_NODE"
    OUTPUT_NEGOTIATION = "OUTPUT_NEGOTIATION"
    DAC = "DAC"


@dataclass(frozen=True, slots=True)
class DsdConversionEvidence:
    plan_id: str
    source_rate_hz: int
    target_rate_hz: int
    decoder_factory: str
    backend: str
    backend_version: str
    quality_profile: str
    dsp_active: bool
    source_fidelity: str
    output_fidelity: str
    bit_perfect_claim: str
    nodes: tuple[ConversionNode, ...]


def build_dsd_conversion_evidence(
    plan: DsdToPcmPlan, *, dsp_active: bool = False
) -> DsdConversionEvidence:
    nodes = [ConversionNode.SOURCE_DSD, ConversionNode.DSD_TO_PCM_DECODER]
    if plan.channels or plan.output_format:
        nodes.append(ConversionNode.PCM_LAYOUT_NORMALIZER)
    if plan.resampler_policy:
        nodes.append(ConversionNode.RESAMPLER)
    if dsp_active:
        nodes.append(ConversionNode.DSP_NODE)
    nodes.extend([ConversionNode.OUTPUT_NEGOTIATION, ConversionNode.DAC])
    return DsdConversionEvidence(
        plan_id=plan.plan_id,
        source_rate_hz=plan.source_format.bit_rate_hz,
        target_rate_hz=plan.target_rate_hz,
        decoder_factory=plan.decoder_factory,
        backend=plan.backend,
        backend_version=plan.backend_version,
        quality_profile=plan.quality_profile,
        dsp_active=dsp_active,
        source_fidelity="DSD",
        output_fidelity="PCM_F32LE",
        bit_perfect_claim="NOT_APPLICABLE",
        nodes=tuple(nodes),
    )
