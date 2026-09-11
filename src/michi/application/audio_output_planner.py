"""DAC-V35-040 — OutputPlanner (spec §17/§18/§19/§403).

Puro y determinista: recibe hechos, NO hace I/O. Nunca abre ALSA,
arranca GStreamer, adquiere el device, cambia PipeWire ni arranca MPD.

Strict Direct (§18): resolve device -> binding -> hardware-raw ->
exact source-native target -> S32 carrier for 24-bit when precision is
preserved -> reject unsupported/unknown exact tuple -> no rate
fallback, no remix, no DSP, no different-device fallback -> emit
decisions and evidence references.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.audio_evidence import (
    CapabilityEvidence,
    DecodedSourceSignal,
    PcmTuple,
)
from michi.domain.audio_output import (
    AudioOutputProfile,
    FallbackKind,
    OutputPathPreference,
    OutputPlan,
    PathSemantics,
    RatePolicy,
)

ENGINE_GSTREAMER = "gstreamer"

# Decision codes (§19)
ENGINE_GSTREAMER_DIRECT = "ENGINE_GSTREAMER_DIRECT"
BINDING_ALSA_HW_SELECTED = "BINDING_ALSA_HW_SELECTED"
SOURCE_NATIVE_RATE_REQUIRED = "SOURCE_NATIVE_RATE_REQUIRED"
S32_CARRIER_PRESERVES_24_BITS = "S32_CARRIER_PRESERVES_24_BITS"
STRICT_NO_RESAMPLE = "STRICT_NO_RESAMPLE"
STRICT_NO_REMIX = "STRICT_NO_REMIX"
FIXED_VOLUME_SELECTED = "FIXED_VOLUME_SELECTED"
FALLBACK_STOP = "FALLBACK_STOP"

# Refusal codes (§403)
SELECTED_DEVICE_MISSING = "SELECTED_DEVICE_MISSING"
DEVICE_UNAVAILABLE = "DEVICE_UNAVAILABLE"
NO_ALSA_HW_BINDING = "NO_ALSA_HW_BINDING"
ENGINE_NOT_GSTREAMER = "ENGINE_NOT_GSTREAMER"
PATH_NOT_HARDWARE_DIRECT = "PATH_NOT_HARDWARE_DIRECT"
SOURCE_RATE_UNKNOWN = "SOURCE_RATE_UNKNOWN"
SOURCE_CHANNELS_UNSUPPORTED = "SOURCE_CHANNELS_UNSUPPORTED"
EXACT_TUPLE_UNSUPPORTED = "EXACT_TUPLE_UNSUPPORTED"
EXACT_TUPLE_UNKNOWN = "EXACT_TUPLE_UNKNOWN"
BINDING_GENERATION_CHANGED = "BINDING_GENERATION_CHANGED"


@dataclass(frozen=True, slots=True)
class PlannerFacts:
    active_engine_id: str
    profile: AudioOutputProfile | None
    selected_device_id: str | None
    binding: AudioDeviceBinding | None
    source: DecodedSourceSignal
    evidence: tuple[CapabilityEvidence, ...] = ()
    expected_binding_generation: int | None = None
    device_available: bool = True


@dataclass(frozen=True, slots=True)
class PlannerRefusal:
    code: str
    detail: str
    decision_codes: tuple[str, ...] = ()


def _tuple_key(pcm: PcmTuple) -> tuple[int, str, int]:
    return (pcm.rate_hz, pcm.transport_format, pcm.channels)


def carrier_tuple(source: DecodedSourceSignal) -> PcmTuple | None:
    """Target exacto source-native (§18.4/§18.5).

    El carrier S32 se permite para fuente de 24 bits SOLO porque la
    precisión significativa se preserva (sbits=24). 16-bit usa S16_LE;
    significant_bits desconocidos -> None (no se adivina).
    """
    bits = source.significant_bits
    if bits is None or source.rate_hz <= 0 or source.channels <= 0:
        return None
    transport_format = "S16_LE" if bits <= 16 else "S32_LE"
    return PcmTuple(
        rate_hz=source.rate_hz,
        transport_format=transport_format,
        channels=source.channels,
        significant_bits=bits,
    )


class OutputPlanner:
    def plan(self, facts: PlannerFacts) -> OutputPlan | PlannerRefusal:
        decisions: list[str] = []

        # 1. device seleccionado
        if not facts.selected_device_id:
            return PlannerRefusal(SELECTED_DEVICE_MISSING, "no hay device seleccionado")
        if not facts.device_available:
            return PlannerRefusal(
                DEVICE_UNAVAILABLE,
                f"device {facts.selected_device_id} no disponible",
            )

        # 2. profile persistido
        profile = facts.profile
        if profile is None:
            return PlannerRefusal(
                PATH_NOT_HARDWARE_DIRECT, "no hay output profile seleccionado"
            )

        # 3. engine activo
        if facts.active_engine_id != ENGINE_GSTREAMER:
            return PlannerRefusal(
                ENGINE_NOT_GSTREAMER,
                f"engine {facts.active_engine_id!r} no soporta Direct",
            )
        decisions.append(ENGINE_GSTREAMER_DIRECT)

        # 4. hardware-raw
        if profile.path is not OutputPathPreference.HARDWARE_DIRECT:
            return PlannerRefusal(
                PATH_NOT_HARDWARE_DIRECT,
                f"path {profile.path.value!r} no es hardware-direct",
                tuple(decisions),
            )

        # 5. binding ALSA hw actual
        binding = facts.binding
        if (
            binding is None
            or binding.kind is not BindingKind.ALSA_PCM
            or not binding.currently_available
        ):
            return PlannerRefusal(
                NO_ALSA_HW_BINDING,
                "no hay binding ALSA hw disponible",
                tuple(decisions),
            )
        decisions.append(BINDING_ALSA_HW_SELECTED)

        # 6. generation del binding
        if (
            facts.expected_binding_generation is not None
            and binding.generation != facts.expected_binding_generation
        ):
            return PlannerRefusal(
                BINDING_GENERATION_CHANGED,
                f"generation {binding.generation} != esperada "
                f"{facts.expected_binding_generation}",
                tuple(decisions),
            )

        # 7. source-native
        if profile.rate_policy is RatePolicy.SOURCE_NATIVE:
            decisions.append(SOURCE_NATIVE_RATE_REQUIRED)

        # 8. target exacto
        requested = carrier_tuple(facts.source)
        if requested is None:
            return PlannerRefusal(
                SOURCE_RATE_UNKNOWN,
                "rate/significant_bits de la fuente desconocidos: "
                "sin prueba exacta no se adivina",
                tuple(decisions),
            )
        if requested.significant_bits == 24 and requested.transport_format == "S32_LE":
            decisions.append(S32_CARRIER_PRESERVES_24_BITS)

        # 9. evidencia exacta del tuple
        matches = [
            item
            for item in facts.evidence
            if item.stable_device_id == facts.selected_device_id
            and _tuple_key(item.tuple) == _tuple_key(requested)
        ]
        if not matches:
            return PlannerRefusal(
                EXACT_TUPLE_UNKNOWN,
                f"sin evidencia para {_tuple_key(requested)}: se requiere probe exacto",
                tuple(decisions),
            )
        if not any(item.supported is True for item in matches):
            if any(item.supported is False for item in matches):
                return PlannerRefusal(
                    EXACT_TUPLE_UNSUPPORTED,
                    f"ALSA rechazó exactamente {_tuple_key(requested)}",
                    tuple(decisions),
                )
            return PlannerRefusal(
                EXACT_TUPLE_UNKNOWN,
                "evidencia ambigua (BUSY/REMOVED/TIMEOUT): sin claim",
                tuple(decisions),
            )

        # 10. canales (sin remix)
        if requested.channels != facts.source.channels:
            return PlannerRefusal(
                SOURCE_CHANNELS_UNSUPPORTED,
                "no hay remix de canales en Strict Direct",
                tuple(decisions),
            )

        # 11. decisiones finales
        decisions.append(STRICT_NO_RESAMPLE)
        decisions.append(STRICT_NO_REMIX)
        if profile.volume_policy.value == "fixed":
            decisions.append(FIXED_VOLUME_SELECTED)
        if profile.fallback is FallbackKind.STOP:
            decisions.append(FALLBACK_STOP)

        evidence_refs = tuple(
            ref
            for item in matches
            if item.supported is True
            for ref in item.evidence_refs
        )
        plan_id = self._plan_id(facts, requested, binding)
        return OutputPlan(
            plan_id=plan_id,
            stable_device_id=facts.selected_device_id,
            binding=binding,
            path_semantics=PathSemantics.HARDWARE_RAW,
            requested_pcm=requested,
            engine_id=facts.active_engine_id,
            volume_policy=profile.volume_policy,
            allow_resample=False,
            allow_remix=False,
            allow_processing=False,
            fallback=profile.fallback,
            evidence_refs=evidence_refs,
            decision_codes=tuple(decisions),
        )

    @staticmethod
    def _plan_id(
        facts: PlannerFacts,
        requested: PcmTuple,
        binding: AudioDeviceBinding,
    ) -> str:
        digest = hashlib.sha256(
            (
                f"{facts.selected_device_id}|{binding.locator}|"
                f"{binding.generation}|{requested.rate_hz}|"
                f"{requested.transport_format}|{requested.channels}|"
                f"{requested.significant_bits}|{facts.active_engine_id}"
            ).encode()
        ).hexdigest()
        return f"plan:{digest[:16]}"
