"""Audio Diagnostics — exposes the current audio route state."""
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

    def to_tooltip(self) -> str:
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
        return {
            "current_uri": self.current_uri,
            "profile": self.profile,
            "backend": self.backend,
            "device_name": self.device_name,
            "device_string": self.device_string,
            "input_codec": self.input_codec,
            "input_container": self.input_container,
            "input_sample_rate": self.input_sample_rate,
            "input_bit_depth": self.input_bit_depth,
            "input_channels": self.input_channels,
            "output_sample_rate": self.output_sample_rate,
            "output_format": self.output_format,
            "output_channels": self.output_channels,
            "dsd_mode": self.dsd_mode,
            "dsp_active": self.dsp_active,
            "eq_active": self.eq_active,
            "replaygain_active": self.replaygain_active,
            "spectrum_active": self.spectrum_active,
            "resampling_active": self.resampling_active,
            "bitperfect_status": self.bitperfect_status,
            "warnings": self.warnings,
        }
