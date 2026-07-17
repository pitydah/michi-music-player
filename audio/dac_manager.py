# -*- coding: utf-8 -*-
"""DAC Manager — device refresh, route selection, plugin check."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal

from audio.output_device_manager import AudioDeviceInfo, list_devices
from audio.output_profiles import AudioOutputProfile
from audio.format_probe import AudioFormatInfo
from audio.audio_route_plan import AudioRoutePlan


class DacManager(QObject):
    devices_refreshed = Signal(list)
    route_planned = Signal(object)  # AudioRoutePlan

    def __init__(self, parent: Any = None):
        super().__init__(parent)
        self._devices: list[AudioDeviceInfo] = []
        self._plugin_cache: dict[str, bool] = {}

    def refresh_devices(self) -> None:
        self._devices = list_devices()
        self.devices_refreshed.emit(self._devices)

    def devices(self) -> list[AudioDeviceInfo]:
        if not self._devices:
            self.refresh_devices()
        return self._devices

    def select_output_route(self, fmt: AudioFormatInfo,
                            profile: AudioOutputProfile,
                            device: AudioDeviceInfo | None) -> AudioRoutePlan:
        """Build the best route plan for a format/profile/device combo."""
        plan = AudioRoutePlan(
            profile=profile.key,
            backend=device.backend if device else "auto",
            device_string=device.device_string if device else "autoaudiosink",
        )

        # DSD routing
        if fmt.is_dsd:
            return self._plan_dsd(fmt, profile, device, plan)

        # Streaming
        if fmt.is_stream:
            plan.use_audioconvert = True
            plan.use_audioresample = True
            plan.use_eq = False
            plan.use_spectrum = False
            plan.bitperfect_expected = False
            plan.fallback_suggestion = ""
            return plan

        # Bit-perfect PCM
        if profile.bitperfect:
            return self._plan_bitperfect(fmt, profile, device, plan)

        # Hi-Fi / Standard
        plan.use_volume = profile.allows_volume_digital
        plan.use_eq = profile.allows_eq
        plan.use_replaygain = profile.allows_replaygain
        plan.use_spectrum = profile.allows_spectrum
        plan.use_transmit = profile.allows_transmit
        plan.use_audioconvert = profile.allows_convert
        plan.use_audioresample = profile.allows_resample
        plan.bitperfect_expected = False

        if profile.key == "hifi_pcm":
            plan.force_rate = fmt.sample_rate if fmt.sample_rate > 0 else 0
            if plan.force_rate:
                plan.use_audioresample = False

        self.route_planned.emit(plan)
        return plan

    def _plan_bitperfect(self, fmt: AudioFormatInfo, profile: AudioOutputProfile, device: AudioDeviceInfo | None, plan: AudioRoutePlan) -> AudioRoutePlan:
        if not device or not device.is_hw or device.is_plug:
            plan.warnings.append(
                "Bit-perfect requiere ALSA hw directo. "
                "Selecciona un DAC hw:X,Y.")
            plan.fallback_suggestion = "hifi_pcm"
            plan.bitperfect_expected = False
            return plan

        plan.use_volume = False
        plan.use_eq = False
        plan.use_replaygain = False
        plan.use_spectrum = False
        plan.use_transmit = False
        plan.use_audioconvert = False
        plan.use_audioresample = False
        plan.force_rate = fmt.sample_rate if fmt.sample_rate > 0 else 0
        plan.bitperfect_expected = True
        self.route_planned.emit(plan)
        return plan

    def _plan_dsd(self, fmt: AudioFormatInfo, profile: AudioOutputProfile, device: AudioDeviceInfo | None, plan: AudioRoutePlan) -> AudioRoutePlan:
        plan.use_volume = False
        plan.use_eq = False
        plan.use_replaygain = False
        plan.use_spectrum = False

        if fmt.is_dst:
            plan.warnings.append("DST comprimido no soportado")
            plan.fallback_suggestion = "standard"
            plan.bitperfect_expected = False
            return plan

        if profile.dsd_mode == "pcm":
            plan.dsd_mode = "pcm"
            if fmt.dsd_rate >= 11289600:
                plan.force_rate = 352800
            else:
                plan.force_rate = 176400
            plan.use_audioconvert = True
            plan.use_audioresample = True
            plan.bitperfect_expected = False
            plan.warnings.append(f"DSD convertido a PCM {plan.force_rate} Hz")
        elif profile.dsd_mode == "dop":
            if not device or not device.supports_dop:
                plan.dsd_mode = ""
                plan.warnings.append("DoP no soportado por este dispositivo")
                plan.fallback_suggestion = "dsd_to_pcm"
            else:
                plan.dsd_mode = "dop"
                plan.use_audioconvert = False
                plan.use_audioresample = False

        self.route_planned.emit(plan)
        return plan

    def test_output_device(self, device: AudioDeviceInfo,
                           profile: AudioOutputProfile) -> tuple[bool, str]:
        """Quick test: can we build a minimal pipeline for this device?"""
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        try:
            sink_name = device.device_string.split(maxsplit=1)[0]
            sink = Gst.ElementFactory.make(sink_name, None)
            if not sink:
                return False, f"No se pudo crear {sink_name}"
            return True, "Dispositivo disponible"
        except Exception as e:
            return False, str(e)

    def check_plugins(self) -> dict[str, bool]:
        """Check which GStreamer plugins are available."""
        if self._plugin_cache:
            return self._plugin_cache
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        plugins = [
            "playbin", "decodebin", "audioconvert", "audioresample",
            "volume", "equalizer-nbands", "rgvolume",
            "appsrc", "appsink", "alsasink", "pipewiresink",
            "pulsesink", "jackaudiosink", "autoaudiosink",
            "avdec_dsd_lsbf", "avdec_dsd_msbf",
        ]
        for p in plugins:
            self._plugin_cache[p] = Gst.ElementFactory.make(p, None) is not None
        return self._plugin_cache

    def missing_plugins(self) -> list[str]:
        return [k for k, v in self.check_plugins().items() if not v]
