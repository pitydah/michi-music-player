# -*- coding: utf-8 -*-
"""Audio Capabilities — checks if a DAC/profile combo supports a format."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from audio.format_probe import AudioFormatInfo
    from audio.output_device_manager import AudioDeviceInfo
    from audio.output_profiles import AudioOutputProfile


@dataclass
class CapabilityResult:
    supported: bool = False
    message: str = ""
    suggestions: list[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


def check_dac_capability(fmt: "AudioFormatInfo", profile: "AudioOutputProfile", device: "AudioDeviceInfo | None") -> CapabilityResult:
    """Check if a device+profile can handle a format.

    Args:
        fmt: AudioFormatInfo
        profile: AudioOutputProfile
        device: AudioDeviceInfo
    """
    if not device or not profile:
        return CapabilityResult(
            supported=True, message="Sin verificacion de dispositivo")

    # DSD checks
    if fmt.is_dsd:
        if fmt.is_dst:
            return CapabilityResult(
                supported=False,
                message="DST comprimido no soportado",
                suggestions=["dsd_to_pcm"])
        if profile.dsd_mode == "pcm":
            return CapabilityResult(
                supported=True,
                message=f"DSD se convertira a PCM ({_suggested_pcm_rate(fmt.dsd_rate)} Hz)")
        if profile.dsd_mode == "dop":
            if not device.supports_dop:
                return CapabilityResult(
                    supported=False,
                    message="DoP no soportado por este dispositivo",
                    suggestions=["dsd_to_pcm", "standard"])
            return CapabilityResult(supported=True, message="DoP activado")
        if profile.dsd_mode == "native":
            if not device.supports_native_dsd:
                return CapabilityResult(
                    supported=False,
                    message="DSD nativo no soportado por este dispositivo",
                    suggestions=["dsd_to_pcm", "dop_experimental"])
            return CapabilityResult(supported=True, message="DSD nativo activado")

    # PCM rate check
    if profile.bitperfect and fmt.sample_rate > 0:
        supported_rates = device.supported_rates
        if supported_rates and fmt.sample_rate not in supported_rates:
            return CapabilityResult(
                supported=False,
                message=f"Sample rate {fmt.sample_rate} Hz no soportado por "
                        f"{device.display_name} en modo bit-perfect",
                suggestions=["hifi_pcm", "standard"])

    return CapabilityResult(supported=True, message="Compatible")


def check_bitperfect_possible(profile: "AudioOutputProfile", device: "AudioDeviceInfo", fmt: "AudioFormatInfo") -> CapabilityResult:
    """Check if bit-perfect playback is actually possible."""
    if not profile.bitperfect:
        return CapabilityResult(
            supported=True, message="No aplica — perfil no bit-perfect")

    issues = []
    if not device.is_hw:
        issues.append(f"Dispositivo {device.display_name} no es ALSA hw directo")
    if fmt.is_dsd:
        issues.append("DSD requiere conversion — no bit-perfect")
    if fmt.is_stream:
        issues.append("Streaming no puede ser bit-perfect")

    if issues:
        return CapabilityResult(
            supported=False,
            message="; ".join(issues),
            suggestions=["hifi_pcm", "standard"])

    return CapabilityResult(
        supported=True,
        message=f"Bit-perfect posible: {fmt.sample_rate} Hz, "
                f"{fmt.bit_depth}-bit → {device.device_string}")


def _suggested_pcm_rate(dsd_rate: int) -> int:
    if dsd_rate >= 11289600:
        return 352800
    if dsd_rate >= 5644800:
        return 176400
    return 176400
