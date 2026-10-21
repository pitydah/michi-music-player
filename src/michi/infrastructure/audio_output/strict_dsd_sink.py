"""AP2-F08 — strict Native DSD sink recipe (pure, GI-free).

The recipe is the immutable bridge between a ``NativeDsdOutputPlan`` and the
GStreamer sink builder. It never selects a device, never converts to PCM and
never permits ``reversed-bytes=true`` at the ``alsasink`` boundary (§84.1,
§214.2). ``dsdconvert`` may only appear as an explicit representation
adaptation (grouping/layout/bit order), never as a DSD→PCM decoder.
"""

from __future__ import annotations

from dataclasses import dataclass

from michi.application.dsd_output_planner import (
    GST_DSD_FORMAT_BY_GROUPING,
    NativeDsdOutputPlan,
)
from michi.domain.dsd_signal import DsdOrganization, DsdPacking

_NATIVE_DSD_SINK = "alsasink"
_GROUPING_BY_PACKING = {
    DsdPacking.DSD_U8: "DSDU8",
    DsdPacking.DSD_U16LE: "DSDU16LE",
    DsdPacking.DSD_U16BE: "DSDU16BE",
    DsdPacking.DSD_U32LE: "DSDU32LE",
    DsdPacking.DSD_U32BE: "DSDU32BE",
}


class StrictDsdSinkError(ValueError):
    """Typed strict DSD recipe refusal."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class StrictDsdSinkRecipe:
    """Exact caps and device for the Native DSD ``alsasink`` branch."""

    plan_id: str
    device: str
    gst_dsd_format: str
    gst_rate_bytes_per_second_per_channel: int
    channels: int
    normalize_reversed_bytes: bool
    requires_dsdconvert: bool
    target_reversed_bytes: bool = False
    layout: str = "interleaved"

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise StrictDsdSinkError("DSD_RECIPE_PLAN_MISSING", "plan_id is empty")
        if not self.device.strip():
            raise StrictDsdSinkError("DSD_RECIPE_DEVICE_MISSING", "device is empty")
        if self.gst_dsd_format not in GST_DSD_FORMAT_BY_GROUPING.values():
            raise StrictDsdSinkError("DSD_RECIPE_FORMAT_INVALID", self.gst_dsd_format)
        if (
            not isinstance(self.gst_rate_bytes_per_second_per_channel, int)
            or isinstance(self.gst_rate_bytes_per_second_per_channel, bool)
            or self.gst_rate_bytes_per_second_per_channel <= 0
        ):
            raise StrictDsdSinkError("DSD_RECIPE_RATE_INVALID", "invalid DSD rate")
        if (
            not isinstance(self.channels, int)
            or isinstance(self.channels, bool)
            or self.channels <= 0
        ):
            raise StrictDsdSinkError("DSD_RECIPE_CHANNELS_INVALID", "invalid channels")
        if not isinstance(self.requires_dsdconvert, bool):
            raise StrictDsdSinkError(
                "DSD_RECIPE_CONVERSION_INVALID",
                "requires_dsdconvert must be a boolean",
            )
        if self.normalize_reversed_bytes and not self.requires_dsdconvert:
            raise StrictDsdSinkError(
                "DSD_RECIPE_CONVERSION_INVALID",
                "bit-order normalization requires dsdconvert",
            )
        if self.target_reversed_bytes:
            raise StrictDsdSinkError(
                "DSD_RECIPE_REVERSED_TARGET",
                "alsasink target must remain reversed-bytes=false",
            )
        if self.layout != "interleaved":
            raise StrictDsdSinkError(
                "DSD_RECIPE_LAYOUT_INVALID",
                "the Native DSD alsasink branch requires interleaved layout",
            )

    def caps_string(self) -> str:
        return (
            "audio/x-dsd,"
            f"format={self.gst_dsd_format},"
            f"rate={self.gst_rate_bytes_per_second_per_channel},"
            f"channels={self.channels},"
            f"layout={self.layout},"
            "reversed-bytes=false"
        )

    @property
    def needs_dsdconvert(self) -> bool:
        """Alias for the explicit representation adaptation decision."""
        return self.requires_dsdconvert

    @property
    def sink_factory(self) -> str:
        return _NATIVE_DSD_SINK


def recipe_from_native_plan(plan: NativeDsdOutputPlan) -> StrictDsdSinkRecipe:
    """Derive the strict sink recipe; every inconsistency is a typed refusal."""
    if not isinstance(plan, NativeDsdOutputPlan):
        raise StrictDsdSinkError(
            "DSD_RECIPE_PLAN_INVALID", "expected a NativeDsdOutputPlan"
        )
    if plan.sink_factory != _NATIVE_DSD_SINK:
        raise StrictDsdSinkError(
            "DSD_RECIPE_SINK_INVALID", "Native DSD requires alsasink"
        )
    if plan.gst_format != plan.alsa_tuple.gst_format:
        raise StrictDsdSinkError(
            "DSD_RECIPE_FORMAT_MISMATCH", "plan format/tuple mismatch"
        )
    if plan.gst_rate_bytes_per_second_per_channel != (
        plan.source.source_rate.gst_byte_rate_per_channel
    ):
        raise StrictDsdSinkError(
            "DSD_RECIPE_RATE_MISMATCH", "plan rate is not the source byte rate"
        )
    if plan.alsa_tuple.channels != plan.source.channels:
        raise StrictDsdSinkError(
            "DSD_RECIPE_CHANNELS_MISMATCH", "plan channels differ from source"
        )
    source_grouping = _GROUPING_BY_PACKING.get(plan.source.packing)
    if source_grouping is None:
        raise StrictDsdSinkError(
            "DSD_RECIPE_SOURCE_GROUPING_INVALID", plan.source.packing.value
        )
    needs_representation = (
        plan.normalize_reversed_bytes
        or source_grouping != plan.gst_format
        or plan.source.organization is not DsdOrganization.INTERLEAVED
    )
    return StrictDsdSinkRecipe(
        plan_id=plan.plan_id,
        device=plan.binding_locator,
        gst_dsd_format=plan.gst_format,
        gst_rate_bytes_per_second_per_channel=(
            plan.gst_rate_bytes_per_second_per_channel
        ),
        channels=plan.alsa_tuple.channels,
        normalize_reversed_bytes=plan.normalize_reversed_bytes,
        requires_dsdconvert=needs_representation,
        target_reversed_bytes=False,
    )
