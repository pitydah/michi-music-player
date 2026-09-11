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
