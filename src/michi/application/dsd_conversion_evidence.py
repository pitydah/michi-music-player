"""Honest Signal Truth/Path evidence for explicit DSD→PCM conversion."""

from __future__ import annotations

from dataclasses import asdict, dataclass
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


class ConversionEvidenceLevel(StrEnum):
    PLANNED = "PLANNED"
    INSTALLED = "INSTALLED"
    OBSERVED = "OBSERVED"
    LAB = "LAB"


@dataclass(frozen=True, slots=True)
class ObservedConversionNode:
    node: ConversionNode
    level: ConversionEvidenceLevel
    detail: str


@dataclass(frozen=True, slots=True)
class DsdConversionPathSnapshot:
    plan_id: str
    nodes: tuple[ObservedConversionNode, ...]
    verdict: str


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
    observed_nodes: tuple[ObservedConversionNode, ...] = ()
    sink_factory: str = ""
    decoder_caps: str = ""
    output_caps: str = ""
    processing_graph_revision: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def build_dsd_conversion_evidence(
    plan: DsdToPcmPlan,
    *,
    dsp_active: bool = False,
    runtime_identity: dict | None = None,
) -> DsdConversionEvidence:
    identity = runtime_identity if isinstance(runtime_identity, dict) else {}
    processing = identity.get("processing")
    dsp_observed = bool(
        dsp_active
        and isinstance(processing, dict)
        and identity.get("processing_effective") is True
    )
    sink_factory = str(identity.get("sink_factory") or "")
    lab = sink_factory in {"fakesink", "appsink"}
    observed = [
        ObservedConversionNode(
            ConversionNode.SOURCE_DSD, ConversionEvidenceLevel.OBSERVED, "source truth"
        ),
        ObservedConversionNode(
            ConversionNode.DSD_TO_PCM_DECODER,
            ConversionEvidenceLevel.OBSERVED
            if identity.get("decoder_caps")
            else ConversionEvidenceLevel.INSTALLED,
            str(identity.get("decoder_factory") or plan.decoder_factory),
        ),
        ObservedConversionNode(
            ConversionNode.PCM_LAYOUT_NORMALIZER,
            ConversionEvidenceLevel.INSTALLED,
            f"F32LE interleaved channels={plan.channels}",
        ),
    ]
    if plan.resampler_policy:
        observed.append(
            ObservedConversionNode(
                ConversionNode.RESAMPLER,
                ConversionEvidenceLevel.OBSERVED
                if identity.get("target_rate_hz") == plan.target_rate_hz
                else ConversionEvidenceLevel.INSTALLED,
                "kaiser quality=10",
            )
        )
    if dsp_active:
        observed.append(
            ObservedConversionNode(
                ConversionNode.DSP_NODE,
                ConversionEvidenceLevel.OBSERVED
                if dsp_observed
                else ConversionEvidenceLevel.PLANNED,
                "graph_revision="
                + str(
                    processing.get("graph_revision")
                    if isinstance(processing, dict)
                    else None
                ),
            )
        )
    observed.append(
        ObservedConversionNode(
            ConversionNode.OUTPUT_NEGOTIATION,
            ConversionEvidenceLevel.OBSERVED
            if identity.get("output_caps")
            else ConversionEvidenceLevel.PLANNED,
            str(identity.get("output_caps") or ""),
        )
    )
    observed.append(
        ObservedConversionNode(
            ConversionNode.DAC,
            ConversionEvidenceLevel.LAB if lab else ConversionEvidenceLevel.PLANNED,
            sink_factory or "unobserved",
        )
    )
    nodes = tuple(item.node for item in observed)
    return DsdConversionEvidence(
        plan_id=plan.plan_id,
        source_rate_hz=plan.source_format.bit_rate_hz,
        target_rate_hz=plan.target_rate_hz,
        decoder_factory=plan.decoder_factory,
        backend=plan.backend,
        backend_version=plan.backend_version,
        quality_profile=plan.quality_profile,
        dsp_active=dsp_observed,
        source_fidelity="DSD",
        output_fidelity="PCM_F32LE",
        bit_perfect_claim="NOT_APPLICABLE",
        nodes=nodes,
        observed_nodes=tuple(observed),
        sink_factory=sink_factory,
        decoder_caps=str(identity.get("decoder_caps") or ""),
        output_caps=str(identity.get("output_caps") or ""),
        processing_graph_revision=(
            int(processing.get("graph_revision"))
            if isinstance(processing, dict)
            and processing.get("graph_revision") is not None
            else None
        ),
    )
