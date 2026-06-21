"""DSP State — tracks which digital processing features are active."""
from dataclasses import dataclass, field


@dataclass
class DspState:
    eq_enabled: bool = False
    eq_mode: str = "bypass"
    eq_bands_parametric: list = field(default_factory=list)
    eq_preamp_db: float = 0.0
    replaygain_enabled: bool = False
    replaygain_mode: str = "track"
    replaygain_db: float = 0.0
    crossfade_seconds: int = 0
    spectrum_enabled: bool = False
    transmit_enabled: bool = False
    digital_volume_enabled: bool = True

    def is_dsp_active(self) -> bool:
        """Returns True if ANY digital processing would break bit-perfect."""
        return (
            self.eq_enabled
            or self.replaygain_enabled
            or self.crossfade_seconds > 0
            or self.spectrum_enabled
            or self.transmit_enabled
        )
