"""DAC-V35-010 — audio device domain types (spec §7/§8/§9).

Identidad estable, binding runtime y observaciones normalizadas. Los
adapters EMITEN observaciones; el registry canónico decide la identidad
(§10). Estos tipos no conocen ni deciden formatos, perfiles de salida ni
GStreamer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IdentityConfidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class AudioDeviceIdentity:
    stable_device_id: str

    vendor_id: str | None
    product_id: str | None
    serial: str | None

    manufacturer: str | None
    product: str | None

    physical_path: str | None
    bus: str | None

    confidence: IdentityConfidence


class BindingKind(Enum):
    ALSA_PCM = "alsa_pcm"
    PIPEWIRE_NODE = "pipewire_node"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class AudioDeviceBinding:
    kind: BindingKind
    locator: str

    generation: int
    currently_available: bool

    card_index: int | None = None
    pcm_device: int | None = None
    pcm_subdevice: int | None = None


@dataclass(frozen=True, slots=True)
class DeviceObservation:
    source: str
    observed_at_ns: int

    vendor_id: str | None
    product_id: str | None
    serial: str | None

    manufacturer: str | None
    product: str | None

    physical_path: str | None

    binding: AudioDeviceBinding | None
