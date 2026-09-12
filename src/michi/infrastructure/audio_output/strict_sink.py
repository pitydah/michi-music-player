"""DAC-V35-050A — Strict Direct sink recipe (spec §404).

Receta inmutable y pura: NO importa gi/Gst/GLib y no recibe objetos Gst.
El executor no decide política: el planner ya decidió.
"""

from __future__ import annotations

from dataclasses import dataclass

from michi.domain.audio_output import OutputPlan, PathSemantics

# Mapping explícito y fail-closed ALSA -> GStreamer (nunca replace()).
# Privado: ningún consumidor externo debe mutarlo.
_ALSA_TO_GST_FORMAT: dict[str, str] = {
    "S16_LE": "S16LE",
    "S32_LE": "S32LE",
}


class StrictSinkError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class StrictSinkRecipe:
    """Receta inmutable del sink Direct (profundamente inmutable)."""

    plan_id: str
    sink_factory: str
    device: str
    media_type: str
    gst_format: str
    rate_hz: int
    channels: int
    layout: str

    def caps_string(self) -> str:
        return (
            f"{self.media_type},format={self.gst_format},"
            f"rate={self.rate_hz},channels={self.channels},"
            f"layout={self.layout}"
        )


def recipe_from_plan(plan: OutputPlan) -> StrictSinkRecipe:
    """Construye la receta estricta desde el plan inmutable.

    Fail-closed ante cualquier política no-Direct o formato no Stable.
    No consulta ningún servicio externo: sólo el plan.
    """
    if plan.engine_id != "gstreamer":
        raise StrictSinkError(
            "DIRECT_PLAN_INVALID", f"engine {plan.engine_id!r} no es gstreamer"
        )
    if plan.path_semantics is not PathSemantics.HARDWARE_RAW:
        raise StrictSinkError(
            "DIRECT_PLAN_INVALID", f"path {plan.path_semantics.value!r} no es raw"
        )
    if plan.sink.factory != "alsasink":
        raise StrictSinkError(
            "DIRECT_PLAN_INVALID", f"sink factory {plan.sink.factory!r}"
        )
    if plan.sink.device != plan.binding.locator:
        raise StrictSinkError(
            "DIRECT_PLAN_INVALID",
            "sink.device != binding.locator (el plan debe ser consistente)",
        )
    if not plan.binding.currently_available:
        raise StrictSinkError("DIRECT_PLAN_INVALID", "binding no disponible")
    if plan.allow_resample or plan.allow_remix or plan.allow_processing:
        raise StrictSinkError(
            "DIRECT_PLAN_INVALID", "políticas de processing/remix/resample activas"
        )
    pcm = plan.requested_pcm
    if pcm.rate_hz <= 0 or pcm.channels <= 0:
        raise StrictSinkError("DIRECT_PLAN_INVALID", "tuple PCM inválido")
    gst_format = _ALSA_TO_GST_FORMAT.get(pcm.transport_format)
    if gst_format is None:
        raise StrictSinkError(
            "DIRECT_PLAN_INVALID",
            f"formato ALSA no soportado por Stable: {pcm.transport_format!r}",
        )
    return StrictSinkRecipe(
        plan_id=plan.plan_id,
        sink_factory="alsasink",
        device=plan.binding.locator,
        media_type="audio/x-raw",
        gst_format=gst_format,
        rate_hz=pcm.rate_hz,
        channels=pcm.channels,
        layout="interleaved",
    )
