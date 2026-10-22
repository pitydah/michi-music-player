"""AP2-F08 — Native DSD output planner (pure application module).

Contract anchors: R11-F08, §84 (strict recipe), §211 (DSD rate algebra),
§213 (exact ALSA tuple), §214 (strict path), §225 (transaction) and §246
(planner V3). No GI, no ALSA, no filesystem, no threads: the planner receives
already-observed qualifications and selected-binding facts from the output
authority and either returns an immutable plan or a typed refusal.

A Native DSD plan is NOT a PCM plan and never carries a PCM identity. The
only authorized sink family is the explicit ``alsasink`` DSD branch; a raw
PCM conversion, a PCM DSP attachment or an unqualified binding is refused.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from michi.domain.dsd_signal import (
    AlsaDsdGrouping,
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
    source_to_gst_rate,
)

#: GStreamer DSD format strings for the ALSA UAPI groupings.
GST_DSD_FORMAT_BY_GROUPING: dict[AlsaDsdGrouping, str] = {
    AlsaDsdGrouping.DSD_U8: "DSDU8",
    AlsaDsdGrouping.DSD_U16_LE: "DSDU16LE",
    AlsaDsdGrouping.DSD_U16_BE: "DSDU16BE",
    AlsaDsdGrouping.DSD_U32_LE: "DSDU32LE",
    AlsaDsdGrouping.DSD_U32_BE: "DSDU32BE",
}
_GROUPING_BY_FORMAT_NAME = {
    grouping.alsa_format_name: grouping for grouping in AlsaDsdGrouping
}
_GROUPING_BY_PACKING = {
    DsdPacking.DSD_U8: AlsaDsdGrouping.DSD_U8,
    DsdPacking.DSD_U16LE: AlsaDsdGrouping.DSD_U16_LE,
    DsdPacking.DSD_U16BE: AlsaDsdGrouping.DSD_U16_BE,
    DsdPacking.DSD_U32LE: AlsaDsdGrouping.DSD_U32_LE,
    DsdPacking.DSD_U32BE: AlsaDsdGrouping.DSD_U32_BE,
}
#: Deterministic representation preference. This is a POLICY, not a
#: capability claim (§213: there is no universal U32 > U16 > U8 priority).
_GROUPING_PREFERENCE = {32: 0, 16: 1, 8: 2}
_NATIVE_DSD_SINK = "alsasink"


class NativeDsdPlannerError(ValueError):
    """Typed Native DSD planning refusal (never a silent fallback)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class AlsaDsdTuple:
    """One exact ALSA DSD candidate (§213).

    ``frame_rate_hz`` is the ALSA hardware frame rate for THIS grouping
    width, not the source bit rate and not the GStreamer byte rate.
    """

    format_name: str
    frame_rate_hz: int
    channels: int
    sample_width_bits: int
    source_bits_per_second_per_channel: int

    def __post_init__(self) -> None:
        if self.format_name not in _GROUPING_BY_FORMAT_NAME:
            raise NativeDsdPlannerError("DSD_ALSA_FORMAT_UNKNOWN", self.format_name)
        if (
            not isinstance(self.frame_rate_hz, int)
            or isinstance(self.frame_rate_hz, bool)
            or self.frame_rate_hz <= 0
        ):
            raise NativeDsdPlannerError(
                "DSD_ALSA_RATE_INVALID", "frame rate must be a positive integer"
            )
        if (
            not isinstance(self.channels, int)
            or isinstance(self.channels, bool)
            or self.channels <= 0
        ):
            raise NativeDsdPlannerError(
                "DSD_ALSA_CHANNELS_INVALID", "channels must be a positive integer"
            )
        if self.sample_width_bits not in {8, 16, 32}:
            raise NativeDsdPlannerError(
                "DSD_ALSA_GROUPING_INVALID",
                f"unsupported grouping width {self.sample_width_bits}",
            )
        if _GROUPING_BY_FORMAT_NAME[self.format_name].bits_per_alsa_sample != (
            self.sample_width_bits
        ):
            raise NativeDsdPlannerError(
                "DSD_ALSA_GROUPING_WIDTH_MISMATCH",
                "format name and declared grouping width disagree",
            )
        if (
            not isinstance(self.source_bits_per_second_per_channel, int)
            or isinstance(self.source_bits_per_second_per_channel, bool)
            or self.source_bits_per_second_per_channel <= 0
        ):
            raise NativeDsdPlannerError(
                "DSD_SOURCE_RATE_INVALID", "source bit rate must be positive"
            )
        if (
            self.frame_rate_hz * self.sample_width_bits
            != self.source_bits_per_second_per_channel
        ):
            raise NativeDsdPlannerError(
                "DSD_ALSA_GROUPING_RATE_MISMATCH",
                "ALSA frame rate * grouping width does not preserve source bits/s",
            )

    @property
    def grouping(self) -> AlsaDsdGrouping:
        return _GROUPING_BY_FORMAT_NAME[self.format_name]

    @property
    def gst_format(self) -> str:
        return GST_DSD_FORMAT_BY_GROUPING[self.grouping]


@dataclass(frozen=True, slots=True)
class NativeDsdQualification:
    """Observed exact-ALSA qualification for one selected binding."""

    stable_device_id: str
    binding_generation: int
    requested: AlsaDsdTuple
    supported: bool | None
    evidence_ref: str
    environment_fingerprint: str = ""
    disposition: str = ""

    def __post_init__(self) -> None:
        if not self.stable_device_id.strip():
            raise NativeDsdPlannerError(
                "DSD_QUALIFICATION_DEVICE_MISSING", "stable device id is empty"
            )
        if (
            not isinstance(self.binding_generation, int)
            or isinstance(self.binding_generation, bool)
            or self.binding_generation < 0
        ):
            raise NativeDsdPlannerError(
                "DSD_QUALIFICATION_GENERATION_INVALID",
                "binding generation must be a non-negative integer",
            )
        if not isinstance(self.requested, AlsaDsdTuple):
            raise NativeDsdPlannerError(
                "DSD_QUALIFICATION_TUPLE_INVALID",
                "requested must be an AlsaDsdTuple",
            )
        if self.supported not in (True, False, None):
            raise NativeDsdPlannerError(
                "DSD_QUALIFICATION_SUPPORT_INVALID",
                "supported must be True, False or None",
            )
        if not self.evidence_ref.strip():
            raise NativeDsdPlannerError(
                "DSD_QUALIFICATION_EVIDENCE_MISSING", "evidence_ref is empty"
            )


@dataclass(frozen=True, slots=True)
class NativeDsdOutputPlan:
    """Immutable Native DSD execution plan (no PCM fields, no DSP)."""

    plan_id: str
    stable_device_id: str
    binding_locator: str
    binding_generation: int
    source: DsdSignalFormat
    alsa_tuple: AlsaDsdTuple
    gst_format: str
    gst_rate_bytes_per_second_per_channel: int
    normalize_reversed_bytes: bool
    sink_factory: str
    decision_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    execution_id: str

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise NativeDsdPlannerError("DSD_PLAN_ID_MISSING", "plan_id is empty")
        if not self.stable_device_id.strip():
            raise NativeDsdPlannerError(
                "DSD_PLAN_DEVICE_MISSING", "stable device id is empty"
            )
        if not self.binding_locator.strip():
            raise NativeDsdPlannerError(
                "DSD_PLAN_BINDING_MISSING", "binding locator is empty"
            )
        if (
            not isinstance(self.binding_generation, int)
            or isinstance(self.binding_generation, bool)
            or self.binding_generation < 0
        ):
            raise NativeDsdPlannerError(
                "DSD_PLAN_GENERATION_INVALID", "invalid binding generation"
            )
        if not isinstance(self.source, DsdSignalFormat):
            raise NativeDsdPlannerError(
                "DSD_SOURCE_INVALID", "source is not a DsdSignalFormat"
            )
        if not isinstance(self.alsa_tuple, AlsaDsdTuple):
            raise NativeDsdPlannerError(
                "DSD_ALSA_TUPLE_INVALID", "alsa_tuple is not an AlsaDsdTuple"
            )
        if self.sink_factory != _NATIVE_DSD_SINK:
            raise NativeDsdPlannerError(
                "DSD_SINK_FACTORY_INVALID",
                "Native DSD requires the explicit alsasink branch",
            )
        if self.gst_format != self.alsa_tuple.gst_format:
            raise NativeDsdPlannerError(
                "DSD_GST_FORMAT_MISMATCH", "gst format does not match ALSA tuple"
            )
        if self.gst_rate_bytes_per_second_per_channel != (
            self.source.source_rate.gst_byte_rate_per_channel
        ):
            raise NativeDsdPlannerError(
                "DSD_GST_RATE_MISMATCH",
                "GStreamer rate is not the source byte rate per second per channel",
            )
        if self.alsa_tuple.channels != self.source.channels:
            raise NativeDsdPlannerError(
                "DSD_CHANNELS_MISMATCH", "ALSA tuple channels differ from source"
            )
        if self.alsa_tuple.source_bits_per_second_per_channel != (
            self.source.bit_rate_hz
        ):
            raise NativeDsdPlannerError(
                "DSD_SOURCE_RATE_MISMATCH", "ALSA tuple does not preserve source rate"
            )
        if self.normalize_reversed_bytes != (self.source.bit_order is DsdBitOrder.LSBF):
            raise NativeDsdPlannerError(
                "DSD_BIT_ORDER_POLICY_MISMATCH",
                "normalize policy must follow the observed source bit order",
            )
        if not self.decision_codes or not all(
            isinstance(code, str) and code.strip() for code in self.decision_codes
        ):
            raise NativeDsdPlannerError(
                "DSD_PLAN_DECISIONS_MISSING", "decision codes are empty"
            )
        if not self.evidence_refs or not all(
            isinstance(ref, str) and ref.strip() for ref in self.evidence_refs
        ):
            raise NativeDsdPlannerError(
                "DSD_PLAN_EVIDENCE_MISSING", "evidence refs are empty"
            )
        if not self.execution_id.strip():
            raise NativeDsdPlannerError(
                "DSD_EXECUTION_ID_MISSING", "execution id is empty"
            )

    @property
    def represents_dsd_to_gst_conversion(self) -> bool:
        """A representation adaptation is required if grouping/layout/order change."""
        source_grouping = _GROUPING_BY_PACKING.get(self.source.packing)
        return (
            self.normalize_reversed_bytes
            or source_grouping is not self.alsa_tuple.grouping
            or self.source.organization is not DsdOrganization.INTERLEAVED
        )


@dataclass(frozen=True, slots=True)
class NativeDsdPlanner:
    """Pure planner: selected binding facts + observed qualifications -> plan."""

    def plan(
        self,
        *,
        stable_device_id: str,
        binding_locator: str,
        binding_generation: int,
        source: DsdSignalFormat,
        qualifications: tuple[NativeDsdQualification, ...],
        execution_id: str,
        source_proven: bool,
        active_engine_id: str,
        processing_active: bool = False,
    ) -> NativeDsdOutputPlan:
        if active_engine_id != "gstreamer":
            raise NativeDsdPlannerError(
                "DSD_ENGINE_UNSUPPORTED", "Native DSD core requires GStreamer"
            )
        if processing_active:
            raise NativeDsdPlannerError(
                "DSD_PCM_PROCESSING_ACTIVE",
                "PCM DSP cannot be attached to a Native DSD execution",
            )
        if not source_proven:
            raise NativeDsdPlannerError(
                "DSD_SOURCE_NOT_PROVEN",
                "the source must be characterized as DSD before planning",
            )
        if not isinstance(source, DsdSignalFormat):
            raise NativeDsdPlannerError(
                "DSD_SOURCE_INVALID", "source is not a DsdSignalFormat"
            )
        if not stable_device_id.strip() or not binding_locator.strip():
            raise NativeDsdPlannerError(
                "DSD_BINDING_INVALID", "selected binding must name device and locator"
            )
        if (
            not isinstance(binding_generation, int)
            or isinstance(binding_generation, bool)
            or binding_generation < 0
        ):
            raise NativeDsdPlannerError(
                "DSD_BINDING_INVALID", "invalid binding generation"
            )
        if not execution_id.strip():
            raise NativeDsdPlannerError(
                "DSD_EXECUTION_ID_MISSING", "execution id is empty"
            )

        source_rate = source.source_rate
        candidates: list[tuple[NativeDsdQualification, AlsaDsdTuple]] = []
        negative_for_binding = False
        for qualification in qualifications:
            requested = qualification.requested
            if qualification.stable_device_id != stable_device_id:
                continue
            if qualification.binding_generation != binding_generation:
                continue
            if requested.source_bits_per_second_per_channel != source.bit_rate_hz:
                continue
            if requested.channels != source.channels:
                continue
            if qualification.supported is True:
                candidates.append((qualification, requested))
            elif qualification.supported is False:
                negative_for_binding = True

        if not candidates:
            if negative_for_binding:
                raise NativeDsdPlannerError(
                    "DSD_EXACT_TUPLE_UNSUPPORTED",
                    "the selected binding rejected every exact Native DSD tuple",
                )
            raise NativeDsdPlannerError(
                "DSD_EXACT_TUPLE_UNKNOWN",
                "the selected binding has no qualified Native DSD tuple",
            )

        chosen_qualification, chosen = sorted(
            candidates,
            key=lambda pair: (
                _GROUPING_PREFERENCE.get(pair[1].sample_width_bits, 99),
                pair[1].format_name,
            ),
        )[0]

        gst_format = chosen.gst_format
        gst_rate = source_to_gst_rate(source_rate).bytes_per_second_per_channel
        normalize = source.bit_order is DsdBitOrder.LSBF
        decisions = [
            "DSD_SOURCE_PROVEN",
            "ALSA_EXACT_TUPLE_SUPPORTED",
            "NATIVE_DSD_ONLY",
        ]
        if normalize:
            decisions.append("REVERSED_BYTES_NORMALIZATION")
        if (
            _GROUPING_BY_PACKING.get(source.packing) is not chosen.grouping
            or source.organization is not DsdOrganization.INTERLEAVED
        ):
            decisions.append("DSD_REPRESENTATION_ADAPTATION")

        canonical = {
            "stable_device_id": stable_device_id,
            "binding_locator": binding_locator,
            "binding_generation": binding_generation,
            "source": {
                "bit_rate_hz": source.bit_rate_hz,
                "channels": source.channels,
                "packing": source.packing.value,
                "bit_order": source.bit_order.value,
                "organization": source.organization.value,
                "layout": list(source.layout),
            },
            "alsa_tuple": {
                "format_name": chosen.format_name,
                "frame_rate_hz": chosen.frame_rate_hz,
                "channels": chosen.channels,
                "sample_width_bits": chosen.sample_width_bits,
                "source_bits_per_second_per_channel": (
                    chosen.source_bits_per_second_per_channel
                ),
            },
            "gst_format": gst_format,
            "gst_rate_bytes_per_second_per_channel": gst_rate,
            "normalize_reversed_bytes": normalize,
            "sink_factory": _NATIVE_DSD_SINK,
            "execution_id": execution_id,
        }
        digest = hashlib.sha256(
            json.dumps(
                canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        evidence_refs = (
            chosen_qualification.evidence_ref,
            f"native-dsd-plan:{digest}",
        )
        return NativeDsdOutputPlan(
            plan_id=f"native-dsd:{digest[:32]}",
            stable_device_id=stable_device_id,
            binding_locator=binding_locator,
            binding_generation=binding_generation,
            source=source,
            alsa_tuple=chosen,
            gst_format=gst_format,
            gst_rate_bytes_per_second_per_channel=gst_rate,
            normalize_reversed_bytes=normalize,
            sink_factory=_NATIVE_DSD_SINK,
            decision_codes=tuple(decisions),
            evidence_refs=evidence_refs,
            execution_id=execution_id,
        )
