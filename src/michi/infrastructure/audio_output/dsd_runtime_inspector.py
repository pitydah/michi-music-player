"""AP2-F08 — Native DSD runtime branch inspector (pure, GI-free).

The inspector consumes PAD-IDENTIFIED observations from the selected branch
and proves the strict DSD route or raises a typed refusal. It never opens a
device and never runs a pipeline. Only ``NEGOTIATED_CURRENT`` caps on the
actual ``alsasink`` sink pad of the selected execution can prove the format;
template capabilities are never evidence of an execution.
"""

from __future__ import annotations

from dataclasses import dataclass

from michi.infrastructure.audio_output.strict_dsd_sink import StrictDsdSinkRecipe

NEGOTIATED_CURRENT = "NEGOTIATED_CURRENT"
TEMPLATE_CAPABILITY = "TEMPLATE_CAPABILITY"
UNAVAILABLE = "UNAVAILABLE"
CONTRADICTORY = "CONTRADICTORY"
_CAPS_STATES = frozenset(
    {NEGOTIATED_CURRENT, TEMPLATE_CAPABILITY, UNAVAILABLE, CONTRADICTORY}
)


class NativeDsdBranchError(ValueError):
    """Typed Native DSD branch refusal."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ObservedPad:
    """One observed pad with identity, role, linkage and caps state."""

    element_name: str
    factory: str
    pad_name: str
    direction: str
    role: str
    media_type: str
    fields: tuple[tuple[str, str], ...]
    caps_state: str
    linked: bool
    selected_device: str = ""
    execution_id: str = ""
    binding_generation: int = 0

    def __post_init__(self) -> None:
        if not self.element_name.strip() or not self.factory.strip():
            raise NativeDsdBranchError(
                "NATIVE_DSD_PAD_IDENTITY_MISSING", "element/factory are required"
            )
        if not self.pad_name.strip() or self.direction not in ("sink", "src"):
            raise NativeDsdBranchError(
                "NATIVE_DSD_PAD_IDENTITY_MISSING", "pad name/direction are invalid"
            )
        if self.role not in ("source", "dsdconvert", "capsfilter", "sink", "other"):
            raise NativeDsdBranchError("NATIVE_DSD_PAD_ROLE_INVALID", self.role)
        if self.caps_state not in _CAPS_STATES:
            raise NativeDsdBranchError("NATIVE_DSD_CAPS_STATE_INVALID", self.caps_state)
        if not isinstance(self.linked, bool):
            raise NativeDsdBranchError(
                "NATIVE_DSD_PAD_IDENTITY_MISSING", "linked must be boolean"
            )
        if not isinstance(self.selected_device, str) or not isinstance(
            self.execution_id, str
        ):
            raise NativeDsdBranchError(
                "NATIVE_DSD_PAD_IDENTITY_MISSING",
                "selected_device/execution_id must be strings",
            )
        if not isinstance(self.binding_generation, int) or isinstance(
            self.binding_generation, bool
        ):
            raise NativeDsdBranchError(
                "NATIVE_DSD_PAD_IDENTITY_MISSING", "generation must be an integer"
            )

    def get(self, name: str) -> str | None:
        for key, value in self.fields:
            if key == name:
                return value
        return None

    def as_dict(self) -> dict:
        return {
            "element_name": self.element_name,
            "factory": self.factory,
            "pad_name": self.pad_name,
            "direction": self.direction,
            "role": self.role,
            "media_type": self.media_type,
            "fields": [list(item) for item in self.fields],
            "caps_state": self.caps_state,
            "linked": self.linked,
            "selected_device": self.selected_device,
            "execution_id": self.execution_id,
            "binding_generation": self.binding_generation,
        }


@dataclass(frozen=True, slots=True)
class NativeDsdBranchEvidence:
    """Observed DSD branch facts, published only for a proven branch."""

    dsd_observations: tuple[ObservedPad, ...]
    raw_observations: tuple[ObservedPad, ...]
    sink_pad: ObservedPad
    sink_format: str
    sink_rate_bytes_per_second_per_channel: int
    sink_channels: int
    sink_layout: str
    sink_reversed_bytes: bool
    graph_inspection_complete: bool = True

    @property
    def contains_audio_x_raw(self) -> bool:
        return bool(self.raw_observations)


def _required(pad: ObservedPad, field: str) -> str:
    value = pad.get(field)
    if value is None or not value.strip():
        raise NativeDsdBranchError(
            "NATIVE_DSD_CAPS_INCOMPLETE",
            f"{pad.element_name}.{pad.pad_name} omits {field}",
        )
    return value


def _parse_int(pad: ObservedPad, field: str) -> int:
    raw = _required(pad, field)
    try:
        value = int(raw)
    except ValueError as exc:
        raise NativeDsdBranchError(
            "NATIVE_DSD_CAPS_INVALID", f"{field}={raw!r} is not an integer"
        ) from exc
    if value <= 0:
        raise NativeDsdBranchError(
            "NATIVE_DSD_CAPS_INVALID", f"{field} must be positive"
        )
    return value


def _parse_bool(pad: ObservedPad, field: str) -> bool:
    raw = _required(pad, field).strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    raise NativeDsdBranchError(
        "NATIVE_DSD_CAPS_INVALID", f"{field}={raw!r} is not a boolean"
    )


def inspect_native_dsd_branch(
    observations: tuple[ObservedPad, ...],
    recipe: StrictDsdSinkRecipe,
    *,
    expected_execution_id: str,
    expected_binding_generation: int,
    expected_device: str,
    graph_inspection_complete: bool = True,
) -> NativeDsdBranchEvidence:
    """Prove the selected branch is DSD-only and matches the strict recipe."""
    if not graph_inspection_complete:
        raise NativeDsdBranchError(
            "NATIVE_DSD_BRANCH_NOT_INSPECTABLE",
            "the selected Native branch was not fully inspectable",
        )
    if not expected_execution_id.strip() or not expected_device.strip():
        raise NativeDsdBranchError(
            "NATIVE_DSD_EXECUTION_IDENTITY_MISSING",
            "execution id and selected device are required",
        )
    forged = tuple(
        pad
        for pad in observations
        if pad.execution_id and pad.execution_id != expected_execution_id
    )
    if forged:
        raise NativeDsdBranchError(
            "NATIVE_DSD_STALE_EXECUTION",
            "observations belong to a different execution",
        )
    unplanned_decoders = tuple(
        pad.factory
        for pad in observations
        if pad.factory.startswith("avdec_")
        or pad.factory in ("decodebin3", "uridecodebin3")
    )
    if unplanned_decoders:
        raise NativeDsdBranchError(
            "NATIVE_DSD_UNPLANNED_DECODER",
            f"selected Native branch contains {unplanned_decoders}",
        )
    raw_observations = tuple(
        pad
        for pad in observations
        if pad.media_type == "audio/x-raw" and pad.caps_state == NEGOTIATED_CURRENT
    )
    if raw_observations:
        raise NativeDsdBranchError(
            "NATIVE_DSD_PCM_CONVERSION_DETECTED",
            f"selected Native branch contains {len(raw_observations)} "
            "negotiated audio/x-raw pads",
        )

    sinks = tuple(
        pad
        for pad in observations
        if pad.role == "sink" and pad.direction == "sink" and pad.factory == "alsasink"
    )
    if len(sinks) != 1:
        raise NativeDsdBranchError(
            "NATIVE_DSD_SINK_IDENTITY_MISSING",
            f"expected exactly one alsasink sink pad, observed {len(sinks)}",
        )
    sink = sinks[0]
    if not sink.linked:
        raise NativeDsdBranchError(
            "NATIVE_DSD_SINK_PAD_UNLINKED", "alsasink sink pad is not linked"
        )
    if sink.caps_state != NEGOTIATED_CURRENT:
        raise NativeDsdBranchError(
            "NATIVE_DSD_SINK_CAPS_NOT_NEGOTIATED",
            f"alsasink sink caps state is {sink.caps_state}",
        )
    if sink.selected_device != expected_device or sink.selected_device != recipe.device:
        raise NativeDsdBranchError(
            "NATIVE_DSD_SINK_DEVICE_MISMATCH",
            f"sink device {sink.selected_device!r} != {recipe.device!r}",
        )
    if (
        sink.execution_id != expected_execution_id
        or sink.binding_generation != expected_binding_generation
    ):
        raise NativeDsdBranchError(
            "NATIVE_DSD_STALE_EXECUTION",
            "alsasink evidence identity/generation is stale",
        )

    foreign_devices = tuple(
        pad
        for pad in observations
        if pad is not sink
        and pad.selected_device
        and pad.selected_device != expected_device
    )
    if foreign_devices:
        raise NativeDsdBranchError(
            "NATIVE_DSD_STALE_DEVICE",
            "observations include pads belonging to another selected device",
        )

    dsd_observations = tuple(
        pad
        for pad in observations
        if pad.media_type == "audio/x-dsd" and pad.caps_state == NEGOTIATED_CURRENT
    )
    if not any(pad.role in ("source", "dsdconvert") for pad in dsd_observations):
        raise NativeDsdBranchError(
            "NATIVE_DSD_BRANCH_NOT_PROVEN",
            "no negotiated upstream DSD source/conversion was observed",
        )

    sink_format = _required(sink, "format")
    sink_rate = _parse_int(sink, "rate")
    sink_channels = _parse_int(sink, "channels")
    sink_layout = _required(sink, "layout")
    sink_reversed = _parse_bool(sink, "reversed-bytes")

    if sink_format != recipe.gst_dsd_format:
        raise NativeDsdBranchError(
            "NATIVE_DSD_FORMAT_MISMATCH",
            f"sink format {sink_format} != recipe {recipe.gst_dsd_format}",
        )
    if sink_rate != recipe.gst_rate_bytes_per_second_per_channel:
        raise NativeDsdBranchError(
            "NATIVE_DSD_RATE_MISMATCH",
            f"sink rate {sink_rate} != recipe "
            f"{recipe.gst_rate_bytes_per_second_per_channel}",
        )
    if sink_channels != recipe.channels:
        raise NativeDsdBranchError(
            "NATIVE_DSD_CHANNELS_MISMATCH",
            f"sink channels {sink_channels} != recipe {recipe.channels}",
        )
    if sink_layout != "interleaved":
        raise NativeDsdBranchError(
            "NATIVE_DSD_LAYOUT_UNSUPPORTED",
            f"sink layout {sink_layout!r} is not interleaved",
        )
    if sink_reversed:
        raise NativeDsdBranchError(
            "NATIVE_DSD_REVERSED_BYTES_AT_SINK",
            "alsasink must receive reversed-bytes=false",
        )

    return NativeDsdBranchEvidence(
        dsd_observations=dsd_observations,
        raw_observations=raw_observations,
        sink_pad=sink,
        sink_format=sink_format,
        sink_rate_bytes_per_second_per_channel=sink_rate,
        sink_channels=sink_channels,
        sink_layout=sink_layout,
        sink_reversed_bytes=sink_reversed,
        graph_inspection_complete=True,
    )
