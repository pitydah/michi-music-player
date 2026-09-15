"""DAC-V35-050A — Normalized Direct runtime validation (spec §404).

Sólo normaliza/compara/valida/clasifica: NO importa gi/Gst/GLib.
"""

from __future__ import annotations

from dataclasses import dataclass

from michi.domain.audio_evidence import RuntimeTransformEvidence
from michi.infrastructure.audio_output.strict_sink import StrictSinkRecipe

DIRECT_STALE_EXECUTION = "DIRECT_STALE_EXECUTION"
DIRECT_SINK_MISMATCH = "DIRECT_SINK_MISMATCH"
DIRECT_DEVICE_MISMATCH = "DIRECT_DEVICE_MISMATCH"
DIRECT_CAPS_UNAVAILABLE = "DIRECT_CAPS_UNAVAILABLE"
DIRECT_FORMAT_MISMATCH = "DIRECT_FORMAT_MISMATCH"
DIRECT_RATE_MISMATCH = "DIRECT_RATE_MISMATCH"
DIRECT_CHANNEL_MISMATCH = "DIRECT_CHANNEL_MISMATCH"
DIRECT_RESAMPLER_ACTIVE = "DIRECT_RESAMPLER_ACTIVE"
DIRECT_RESAMPLER_STATE_UNKNOWN = "DIRECT_RESAMPLER_STATE_UNKNOWN"
DIRECT_CONVERTER_ACTIVE = "DIRECT_CONVERTER_ACTIVE"
DIRECT_CONVERTER_STATE_UNKNOWN = "DIRECT_CONVERTER_STATE_UNKNOWN"
DIRECT_REMIX_ACTIVE = "DIRECT_REMIX_ACTIVE"
DIRECT_GRAPH_INSPECTION_FAILED = "DIRECT_GRAPH_INSPECTION_FAILED"


class DirectRuntimeValidationError(RuntimeError):
    """Fail-closed tipado de la validación Direct (código estable)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DirectRuntimeSnapshot:
    """Snapshot normalizado del runtime real (sin objetos Gst)."""

    execution_generation: int
    port_generation: int
    plan_id: str

    sink_factory: str
    sink_device: str

    negotiated_format: str | None
    negotiated_rate_hz: int | None
    negotiated_channels: int | None

    graph_factories: tuple[str, ...]
    transform_evidence: RuntimeTransformEvidence = RuntimeTransformEvidence()

    decoded_format: str | None = None
    decoded_rate_hz: int | None = None
    decoded_channels: int | None = None
    decoded_significant_bits: int | None = None
    effective_significant_bits: int | None = None
    graph_inspection_complete: bool = True
    software_gain: float | None = None
    muted: bool | None = None
    sink_provides_clock: bool | None = None
    sink_clock_is_pipeline_clock: bool | None = None
    slave_method: str | None = None


@dataclass(frozen=True, slots=True)
class DirectPrerollEvidence:
    """Evidencia inmutable de un preroll Direct validado."""

    execution_generation: int
    port_generation: int
    plan_id: str

    sink_factory: str
    sink_device: str

    negotiated_format: str
    negotiated_rate_hz: int
    negotiated_channels: int

    graph_factories: tuple[str, ...]


def validate_runtime_semantics(
    recipe: StrictSinkRecipe,
    snapshot: DirectRuntimeSnapshot,
    *,
    require_sink_identity: bool = True,
) -> DirectPrerollEvidence:
    """Validate one normalized runtime snapshot without duplicating rules.

    Hardware-independent real-GStreamer gates may disable only physical sink
    identity checks.  Caps, graph completeness, and transform semantics remain
    identical to production validation.
    """
    if snapshot.plan_id != recipe.plan_id:
        raise DirectRuntimeValidationError(
            DIRECT_STALE_EXECUTION,
            f"plan_id {snapshot.plan_id!r} != {recipe.plan_id!r}",
        )
    if require_sink_identity and snapshot.sink_factory != recipe.sink_factory:
        raise DirectRuntimeValidationError(
            DIRECT_SINK_MISMATCH,
            f"sink {snapshot.sink_factory!r} != {recipe.sink_factory!r}",
        )
    if require_sink_identity and snapshot.sink_device != recipe.device:
        raise DirectRuntimeValidationError(
            DIRECT_DEVICE_MISMATCH,
            f"device {snapshot.sink_device!r} != {recipe.device!r}",
        )
    if (
        snapshot.negotiated_format is None
        or snapshot.negotiated_rate_hz is None
        or snapshot.negotiated_channels is None
    ):
        raise DirectRuntimeValidationError(
            DIRECT_CAPS_UNAVAILABLE, "caps negociados ausentes"
        )
    if snapshot.negotiated_format != recipe.gst_format:
        raise DirectRuntimeValidationError(
            DIRECT_FORMAT_MISMATCH,
            f"format {snapshot.negotiated_format!r} != {recipe.gst_format!r}",
        )
    if snapshot.negotiated_rate_hz != recipe.rate_hz:
        raise DirectRuntimeValidationError(
            DIRECT_RATE_MISMATCH,
            f"rate {snapshot.negotiated_rate_hz} != {recipe.rate_hz}",
        )
    if snapshot.negotiated_channels != recipe.channels:
        raise DirectRuntimeValidationError(
            DIRECT_CHANNEL_MISMATCH,
            f"channels {snapshot.negotiated_channels} != {recipe.channels}",
        )
    if (
        not snapshot.graph_inspection_complete
        or "__inspection_failed__" in snapshot.graph_factories
    ):
        raise DirectRuntimeValidationError(
            DIRECT_GRAPH_INSPECTION_FAILED,
            "runtime graph could not be inspected completely",
        )
    transforms = snapshot.transform_evidence
    if transforms.resampler_present:
        if transforms.resampler_transforming is True:
            raise DirectRuntimeValidationError(
                DIRECT_RESAMPLER_ACTIVE,
                "audioresample changed the negotiated sample rate",
            )
        if transforms.resampler_transforming is None:
            raise DirectRuntimeValidationError(
                DIRECT_RESAMPLER_STATE_UNKNOWN,
                "audioresample activity could not be determined",
            )
    if transforms.remix_transforming is True and not transforms.converter_present:
        raise DirectRuntimeValidationError(
            DIRECT_REMIX_ACTIVE,
            "selected-branch channel layout or count changed",
        )
    if transforms.converter_present:
        if (
            transforms.converter_transforming is True
            or transforms.remix_transforming is True
        ):
            raise DirectRuntimeValidationError(
                DIRECT_CONVERTER_ACTIVE,
                "audioconvert changed negotiated signal properties",
            )
        if (
            transforms.converter_transforming is None
            or transforms.remix_transforming is None
        ):
            raise DirectRuntimeValidationError(
                DIRECT_CONVERTER_STATE_UNKNOWN,
                "audioconvert activity could not be determined",
            )
    return DirectPrerollEvidence(
        execution_generation=snapshot.execution_generation,
        port_generation=snapshot.port_generation,
        plan_id=recipe.plan_id,
        sink_factory=snapshot.sink_factory,
        sink_device=snapshot.sink_device,
        negotiated_format=snapshot.negotiated_format,
        negotiated_rate_hz=snapshot.negotiated_rate_hz,
        negotiated_channels=snapshot.negotiated_channels,
        graph_factories=snapshot.graph_factories,
    )


def validate_runtime(
    recipe: StrictSinkRecipe,
    snapshot: DirectRuntimeSnapshot,
) -> DirectPrerollEvidence:
    """Production Direct validation with exact ALSA sink/device identity."""
    return validate_runtime_semantics(
        recipe,
        snapshot,
        require_sink_identity=True,
    )
