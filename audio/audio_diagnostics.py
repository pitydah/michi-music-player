# -*- coding: utf-8 -*-
"""Audio Diagnostics — exposes the current audio route state."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AudioRouteDiagnostics:
    current_uri: str = ""
    profile: str = "standard"
    backend: str = "auto"
    device_name: str = ""
    device_string: str = ""
    input_codec: str = ""
    input_container: str = ""
    input_sample_rate: int = 0
    input_bit_depth: int = 0
    input_channels: int = 0
    output_sample_rate: int = 0
    output_format: str = ""
    output_channels: int = 0
    dsd_mode: str = ""
    dsp_active: bool = False
    eq_active: bool = False
    replaygain_active: bool = False
    spectrum_active: bool = False
    resampling_active: bool = False
    bitperfect_status: str = "unknown"  # yes/no/unknown
    warnings: list[str] = field(default_factory=list)

    def to_tooltip(self: "AudioRouteDiagnostics") -> str:
        lines = []
        if self.bitperfect_status == "yes":
            lines.append("Bit-Perfect: ACTIVE")
        elif self.bitperfect_status == "no":
            lines.append("Bit-Perfect: NO")
        else:
            lines.append("Bit-Perfect: UNKNOWN")
        lines.append(f"Perfil: {self.profile}")
        lines.append(f"Backend: {self.backend}")
        if self.device_name:
            lines.append(f"Dispositivo: {self.device_name}")
        if self.input_codec:
            lines.append(f"Codec: {self.input_codec} {self.input_sample_rate}/{self.input_bit_depth}-bit")
        if self.dsd_mode:
            lines.append(f"DSD: {self.dsd_mode}")
        if self.eq_active:
            lines.append("EQ: ACTIVO")
        if self.replaygain_active:
            lines.append("ReplayGain: ACTIVO")
        if self.spectrum_active:
            lines.append("Spectrum: ACTIVO")
        if self.resampling_active:
            lines.append("Resampling: ACTIVO")
        if self.dsp_active:
            lines.append("DSP: ACTIVO")
        if self.warnings:
            for w in self.warnings:
                lines.append(f"⚠ {w}")
        return "\n".join(lines)
