"""DAC-V35-030 — output profile domain types (spec §15/§402).

El profile EXPRESA política; nunca fabrica capability de hardware. El
preset canónico Stable Direct:

    path HARDWARE_DIRECT / rate SOURCE_NATIVE / volume FIXED
    allow_resample=false / allow_remix=false / allow_processing=false
    fallback STOP
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from michi.domain.audio_device import AudioDeviceBinding
from michi.domain.audio_evidence import PcmTuple


class OutputPathPreference(Enum):
    DESKTOP = "desktop"
    MANAGED = "managed"
    HARDWARE_DIRECT = "hardware_direct"


class RatePolicy(Enum):
    SOURCE_NATIVE = "source_native"
    SYSTEM = "system"


class VolumePolicy(Enum):
    FIXED = "fixed"
    SOFTWARE = "software"
    HARDWARE = "hardware"


class FallbackKind(Enum):
    STOP = "stop"
    ASK = "ask"
    DESKTOP_DEFAULT = "desktop_default"
    SPECIFIC_DEVICE = "specific_device"


@dataclass(frozen=True, slots=True)
class AudioOutputProfile:
    profile_id: str
    stable_device_id: str | None

    path: OutputPathPreference
    rate_policy: RatePolicy
    volume_policy: VolumePolicy

    allow_resample: bool
    allow_remix: bool
    allow_processing: bool

    fallback: FallbackKind

    fallback_device_id: str | None = None
    resync_delay_ms: int = 0


@dataclass(frozen=True, slots=True)
class AudioOutputSelection:
    """Selección vigente (singleton autoritativo, §0I)."""

    selected_profile_id: str | None
    selected_device_id: str | None
    updated_at_ms: int


def stable_direct_preset(profile_id: str, stable_device_id: str) -> AudioOutputProfile:
    """Preset canónico Stable Direct (§15)."""
    return AudioOutputProfile(
        profile_id=profile_id,
        stable_device_id=stable_device_id,
        path=OutputPathPreference.HARDWARE_DIRECT,
        rate_policy=RatePolicy.SOURCE_NATIVE,
        volume_policy=VolumePolicy.FIXED,
        allow_resample=False,
        allow_remix=False,
        allow_processing=False,
        fallback=FallbackKind.STOP,
    )


class PathSemantics(Enum):
    HARDWARE_RAW = "hardware_raw"
    ALSA_PLUGIN = "alsa_plugin"
    SYSTEM_SERVER = "system_server"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class GstSinkSpec:
    """Sink estricto derivado del plan (§20). El factory consume el plan;
    nunca decide política.

    DAC-E: profundamente inmutable — campos tipados, sin property bag
    mutable. Para Stable el sink sólo necesita alsasink + device.
    """

    factory: str
    device: str


@dataclass(frozen=True, slots=True)
class OutputPlan:
    """El objeto más importante de Stable (§17 + completitud §403).

    Inmutable y autosuficiente para el executor (C09): incluye sink
    estricto, resync delay, preconditions, binding generation, políticas
    y evidence refs. El executor NO consulta profile/policy services.
    """

    plan_id: str

    stable_device_id: str
    binding: AudioDeviceBinding

    path_semantics: PathSemantics
    requested_pcm: PcmTuple

    engine_id: str

    volume_policy: VolumePolicy

    allow_resample: bool
    allow_remix: bool
    allow_processing: bool

    fallback: FallbackKind

    sink: GstSinkSpec
    resync_delay_ms: int
    preconditions: tuple[str, ...]

    evidence_refs: tuple[str, ...]
    decision_codes: tuple[str, ...]


def sink_spec_for(plan: OutputPlan) -> GstSinkSpec:
    if plan.path_semantics is not PathSemantics.HARDWARE_RAW:
        raise ValueError("Stable Direct requires hardware-raw path")
    return plan.sink


class OutputSessionState(Enum):
    IDLE = "idle"
    ACQUIRING = "acquiring"
    CONFIGURING = "configuring"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    RECONFIGURING = "reconfiguring"
    RECOVERING = "recovering"
    LOST = "lost"
    FAILED = "failed"
    RELEASING = "releasing"


@dataclass(frozen=True, slots=True)
class OutputSelectionState:
    selected_device_id: str | None
    selected_profile_id: str | None

    active_device_id: str | None
    active_plan_id: str | None

    session_state: OutputSessionState
    error_code: str | None
