"""Deterministic DSD→PCM plan and quality ladders (AP2-F10)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdPacking,
    DsdSignalFormat,
)

QUALITY_RATE_LADDERS: dict[str, tuple[int, ...]] = {
    "FAST": (88_200,),
    "BALANCED": (176_400, 88_200),
    "HIGH": (352_800, 176_400, 88_200),
    "REFERENCE": (705_600, 352_800, 176_400, 88_200),
}
DEFAULT_QUALITY_PROFILE = "HIGH"
RESAMPLER_CONTRACT = (
    ("quality", 10),
    ("resample-method", "kaiser"),
    ("sinc-filter-mode", "full"),
    ("sinc-filter-interpolation", "none"),
)


class DsdToPcmPlanError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def dsd_decoder_native_rate_hz(source_bps_per_channel: int) -> int:
    if (
        not isinstance(source_bps_per_channel, int)
        or isinstance(source_bps_per_channel, bool)
        or source_bps_per_channel <= 0
        or source_bps_per_channel % 8
    ):
        raise ValueError("invalid DSD source rate")
    return source_bps_per_channel // 8


def decoder_factory_for(source_format: DsdSignalFormat) -> str:
    if source_format.packing is not DsdPacking.DSD_U8:
        raise DsdToPcmPlanError(
            "DSD_PCM_DECODER_UNAVAILABLE",
            f"unsupported elementary packing {source_format.packing.value}",
        )
    # dsdconvert is an explicit node that normalizes channel organization to
    # interleaved before the decoder; bit order remains factory-selected.
    return {
        DsdBitOrder.LSBF: "avdec_dsd_lsbf",
        DsdBitOrder.MSBF: "avdec_dsd_msbf",
    }[source_format.bit_order]


@dataclass(frozen=True, slots=True)
class DsdToPcmPlan:
    plan_id: str
    source_identity: str
    source_format: DsdSignalFormat
    decoder_factory: str
    decoder_native_rate_hz: int
    target_rate_hz: int
    output_format: str
    channels: int
    quality_profile: str
    resampler_policy: tuple[tuple[str, Any], ...]
    backend: str
    backend_version: str
    binding_generation: int
    processing_graph_revision: int | None
    evidence_refs: tuple[str, ...]
    stable_device_id: str = ""
    binding_locator: str = ""
    host_generation: int = 0


class DsdToPcmPlanner:
    """Build one immutable plan; never guess a DAC target rate."""

    def plan(
        self,
        *,
        source_identity: str,
        source_format: DsdSignalFormat,
        quality_profile: str,
        binding_generation: int,
        available_output_rates: tuple[int, ...],
        decoder_available: bool,
        target_qualified: bool,
        dsp_active: bool = False,
        dsp_available: bool = True,
        processing_graph_revision: int | None = None,
        expected_graph_revision: int | None = None,
        backend_version: str = "",
        target_rate_hz: int | None = None,
        evidence_refs: tuple[str, ...] = (),
        stable_device_id: str = "",
        binding_locator: str = "",
        host_generation: int = 0,
    ) -> DsdToPcmPlan:
        if quality_profile not in QUALITY_RATE_LADDERS:
            raise DsdToPcmPlanError("DSD_PCM_QUALITY_PROFILE_UNKNOWN", quality_profile)
        if not decoder_available:
            raise DsdToPcmPlanError(
                "DSD_PCM_DECODER_UNAVAILABLE", "gst-libav decoder is not installed"
            )
        if not target_qualified:
            raise DsdToPcmPlanError(
                "DSD_PCM_TARGET_UNQUALIFIED", "PCM target is not qualified"
            )
        if dsp_active and not dsp_available:
            raise DsdToPcmPlanError(
                "DSD_PCM_DSP_UNAVAILABLE", "DSP backend is not available"
            )
        if (
            expected_graph_revision is not None
            and processing_graph_revision != expected_graph_revision
        ):
            raise DsdToPcmPlanError(
                "DSD_PCM_PROCESSING_GRAPH_STALE",
                f"{processing_graph_revision!r} != {expected_graph_revision!r}",
            )
        native = dsd_decoder_native_rate_hz(source_format.bit_rate_hz)
        candidates = tuple(
            rate
            for rate in QUALITY_RATE_LADDERS[quality_profile]
            if rate <= native and rate in available_output_rates
        )
        if target_rate_hz is not None:
            if target_rate_hz not in candidates:
                raise DsdToPcmPlanError(
                    "DSD_PCM_NO_QUALIFIED_TARGET_RATE",
                    f"requested {target_rate_hz} is not a qualified ladder rate",
                )
            target = target_rate_hz
        elif candidates:
            target = candidates[0]
        else:
            raise DsdToPcmPlanError(
                "DSD_PCM_NO_QUALIFIED_TARGET_RATE",
                f"no ladder rate for {quality_profile} at native {native}",
            )
        factory = decoder_factory_for(source_format)
        resampler = () if target == native else RESAMPLER_CONTRACT
        digest = hashlib.sha256(
            "|".join(
                (
                    source_identity,
                    str(source_format.bit_rate_hz),
                    source_format.bit_order.value,
                    source_format.organization.value,
                    source_format.packing.value,
                    ",".join(source_format.layout),
                    str(source_format.channels),
                    factory,
                    "F32LE",
                    str(native),
                    str(target),
                    quality_profile,
                    "|".join(f"{k}={v}" for k, v in resampler),
                    "gst-libav",
                    backend_version,
                    str(processing_graph_revision),
                    str(binding_generation),
                    "|".join(evidence_refs),
                )
            ).encode()
        ).hexdigest()
        return DsdToPcmPlan(
            plan_id=f"dsd2pcm:{digest[:32]}",
            source_identity=source_identity,
            source_format=source_format,
            decoder_factory=factory,
            decoder_native_rate_hz=native,
            target_rate_hz=target,
            output_format="F32LE",
            channels=source_format.channels,
            quality_profile=quality_profile,
            resampler_policy=resampler,
            backend="gst-libav",
            backend_version=backend_version,
            binding_generation=binding_generation,
            processing_graph_revision=processing_graph_revision,
            evidence_refs=evidence_refs,
            stable_device_id=stable_device_id,
            binding_locator=binding_locator,
            host_generation=host_generation,
        )
