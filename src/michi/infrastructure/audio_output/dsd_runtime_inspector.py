"""AP2-F08 — Native DSD runtime branch inspector (pure, GI-free).

The inspector consumes CAPS OBSERVED from the selected branch (upstream to
downstream) and either proves the strict DSD route or raises a typed refusal.
It never opens a device and never runs a pipeline. The critical invariant is
§214.4: any ``audio/x-raw`` in the selected Native branch is a contradiction,
regardless of what the final sink negotiated.
"""

from __future__ import annotations

from dataclasses import dataclass

from michi.infrastructure.audio_output.strict_dsd_sink import StrictDsdSinkRecipe


class NativeDsdBranchError(ValueError):
    """Typed Native DSD branch refusal."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ObservedCaps:
    """One observed pad caps entry (media type + string fields)."""

    media_type: str
    fields: tuple[tuple[str, str], ...] = ()

    def get(self, name: str) -> str | None:
        for key, value in self.fields:
            if key == name:
                return value
        return None

    def as_dict(self) -> dict[str, str]:
        return dict(self.fields)


@dataclass(frozen=True, slots=True)
class NativeDsdBranchEvidence:
    """Observed DSD branch facts, published only for a proven branch."""

    dsd_caps: tuple[ObservedCaps, ...]
    raw_caps: tuple[ObservedCaps, ...]
    sink_caps: ObservedCaps
    sink_format: str
    sink_rate_bytes_per_second_per_channel: int
    sink_channels: int
    sink_layout: str
    sink_reversed_bytes: bool
    factories: tuple[str, ...] = ()
    graph_inspection_complete: bool = True

    @property
    def contains_audio_x_raw(self) -> bool:
        return bool(self.raw_caps)


def _required(field: str, caps: ObservedCaps) -> str:
    value = caps.get(field)
    if value is None or not value.strip():
        raise NativeDsdBranchError(
            "NATIVE_DSD_CAPS_INCOMPLETE",
            f"observed DSD caps omit {field}",
        )
    return value


def _parse_int(field: str, caps: ObservedCaps) -> int:
    raw = _required(field, caps)
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


def _parse_bool(field: str, caps: ObservedCaps) -> bool:
    raw = _required(field, caps).strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    raise NativeDsdBranchError(
        "NATIVE_DSD_CAPS_INVALID", f"{field}={raw!r} is not a boolean"
    )


def inspect_native_dsd_branch(
    observed_caps: tuple[ObservedCaps, ...],
    recipe: StrictDsdSinkRecipe,
    *,
    factories: tuple[str, ...] = (),
    graph_inspection_complete: bool = True,
) -> NativeDsdBranchEvidence:
    """Prove the selected branch is DSD-only and matches the strict recipe."""
    if not graph_inspection_complete:
        raise NativeDsdBranchError(
            "NATIVE_DSD_BRANCH_NOT_INSPECTABLE",
            "the selected Native branch was not fully inspectable",
        )
    dsd_caps = tuple(caps for caps in observed_caps if caps.media_type == "audio/x-dsd")
    raw_caps = tuple(caps for caps in observed_caps if caps.media_type == "audio/x-raw")
    if raw_caps:
        raise NativeDsdBranchError(
            "NATIVE_DSD_PCM_CONVERSION_DETECTED",
            f"selected Native branch contains {len(raw_caps)} audio/x-raw caps",
        )
    if not dsd_caps:
        raise NativeDsdBranchError(
            "NATIVE_DSD_BRANCH_NOT_PROVEN",
            "the selected branch exposed no audio/x-dsd caps",
        )

    sink = dsd_caps[-1]
    sink_format = _required("format", sink)
    sink_rate = _parse_int("rate", sink)
    sink_channels = _parse_int("channels", sink)
    sink_layout = _required("layout", sink)
    sink_reversed = _parse_bool("reversed-bytes", sink)

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
        dsd_caps=dsd_caps,
        raw_caps=raw_caps,
        sink_caps=sink,
        sink_format=sink_format,
        sink_rate_bytes_per_second_per_channel=sink_rate,
        sink_channels=sink_channels,
        sink_layout=sink_layout,
        sink_reversed_bytes=sink_reversed,
        factories=factories,
        graph_inspection_complete=True,
    )
