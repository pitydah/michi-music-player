"""DAC-V35-050A — Normalized Direct runtime validation (spec §404).

Sólo normaliza/compara/valida/clasifica: NO importa gi/Gst/GLib.
"""

from __future__ import annotations

from dataclasses import dataclass

from michi.infrastructure.audio_output.strict_sink import StrictSinkRecipe

DIRECT_STALE_EXECUTION = "DIRECT_STALE_EXECUTION"
DIRECT_SINK_MISMATCH = "DIRECT_SINK_MISMATCH"
DIRECT_DEVICE_MISMATCH = "DIRECT_DEVICE_MISMATCH"
DIRECT_CAPS_UNAVAILABLE = "DIRECT_CAPS_UNAVAILABLE"
DIRECT_FORMAT_MISMATCH = "DIRECT_FORMAT_MISMATCH"
DIRECT_RATE_MISMATCH = "DIRECT_RATE_MISMATCH"
DIRECT_CHANNEL_MISMATCH = "DIRECT_CHANNEL_MISMATCH"
DIRECT_RESAMPLER_PRESENT = "DIRECT_RESAMPLER_PRESENT"


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


def validate_runtime(
    recipe: StrictSinkRecipe,
    snapshot: DirectRuntimeSnapshot,
) -> DirectPrerollEvidence:
    """Valida el snapshot contra la receta exacta (fail-closed)."""
    if snapshot.plan_id != recipe.plan_id:
        raise DirectRuntimeValidationError(
            DIRECT_STALE_EXECUTION,
            f"plan_id {snapshot.plan_id!r} != {recipe.plan_id!r}",
        )
    if snapshot.sink_factory != recipe.sink_factory:
        raise DirectRuntimeValidationError(
            DIRECT_SINK_MISMATCH,
            f"sink {snapshot.sink_factory!r} != {recipe.sink_factory!r}",
        )
    if snapshot.sink_device != recipe.device:
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
    if "audioresample" in snapshot.graph_factories:
        raise DirectRuntimeValidationError(
            DIRECT_RESAMPLER_PRESENT,
            "audioresample presente con allow_resample=False",
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
