"""Presentation semantics for proven audio-output devices.

Admission and classification are intentionally separate:

    real ALSA playback capability -> admission authority (registry)
    observed topology/capture/name hints -> presentation classification only

No vendor/model/VID/PID allowlist or blacklist is permitted here. An unknown
playback-capable device must remain usable even when its semantic category is
uncertain.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from michi.domain.audio_device import AudioDeviceBinding, BindingKind


class AudioDeviceCategory(Enum):
    EXTERNAL_AUDIO = "external_audio"
    AUDIO_INTERFACE = "audio_interface"
    LOCAL_AUDIO = "local_audio"
    DISPLAY_AUDIO = "display_audio"
    OTHER_AUDIO = "other_audio"


class ClassificationConfidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class AudioDeviceClassification:
    category: AudioDeviceCategory
    confidence: ClassificationConfidence
    reason: str


_DISPLAY_TOKENS = (
    "hdmi",
    "displayport",
    "display port",
    "dp audio",
)


def current_playback_bindings(snapshot) -> tuple[AudioDeviceBinding, ...]:
    return tuple(
        binding
        for binding in snapshot.bindings
        if binding.kind is BindingKind.ALSA_PCM and binding.currently_available
    )


def has_current_playback(snapshot) -> bool:
    return bool(snapshot.available and current_playback_bindings(snapshot))


def classify_audio_device(snapshot) -> AudioDeviceClassification:
    """Classify for UI grouping after playback admission has succeeded.

    USB + capture is a useful generic signal for an audio interface, but it is
    not required for use. USB playback without capture is intentionally called
    External Audio rather than guessed to be a DAC/headphone/receiver.

    Linux commonly exposes both HDMI and DisplayPort sink paths through an HDA
    HDMI ALSA card; unless a DRM/EDID connector correlation proves the exact
    transport, the UI groups both as Display Audio instead of guessing HDMI vs
    DP from an ALSA device number.
    """
    identity = snapshot.identity
    if identity.bus == "usb":
        if snapshot.capture_capable:
            return AudioDeviceClassification(
                AudioDeviceCategory.AUDIO_INTERFACE,
                ClassificationConfidence.HIGH,
                "USB hardware exposes current ALSA playback plus capture capability",
            )
        return AudioDeviceClassification(
            AudioDeviceCategory.EXTERNAL_AUDIO,
            ClassificationConfidence.HIGH,
            "USB hardware exposes a current ALSA playback endpoint",
        )

    searchable = " ".join(
        value
        for value in (
            identity.manufacturer,
            identity.product,
            *(binding.locator for binding in snapshot.bindings),
        )
        if value
    ).casefold()
    if any(token in searchable for token in _DISPLAY_TOKENS):
        return AudioDeviceClassification(
            AudioDeviceCategory.DISPLAY_AUDIO,
            ClassificationConfidence.MEDIUM,
            "ALSA playback identity identifies a display-audio path; the exact "
            "HDMI/DP connector is not inferred",
        )
    if has_current_playback(snapshot):
        return AudioDeviceClassification(
            AudioDeviceCategory.LOCAL_AUDIO,
            ClassificationConfidence.MEDIUM,
            "non-USB hardware exposes a current ALSA playback endpoint",
        )
    return AudioDeviceClassification(
        AudioDeviceCategory.OTHER_AUDIO,
        ClassificationConfidence.LOW,
        "no stronger presentation classification is available",
    )


def category_label(category: AudioDeviceCategory) -> str:
    return {
        AudioDeviceCategory.EXTERNAL_AUDIO: "External Audio",
        AudioDeviceCategory.AUDIO_INTERFACE: "Audio Interface",
        AudioDeviceCategory.LOCAL_AUDIO: "Built-in / Local Audio",
        AudioDeviceCategory.DISPLAY_AUDIO: "Display Audio",
        AudioDeviceCategory.OTHER_AUDIO: "Other Audio",
    }[category]
