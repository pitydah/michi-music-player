"""BitperfectReport — data model for bit-perfect verification results."""

from dataclasses import dataclass, field


@dataclass
class BitperfectReport:
    """Comprehensive report about bit-perfect status for the current playback.

    States:
        off:             profile is not bit-perfect
        requested:       user asked for bit-perfect but no active playback yet
        not_verified:    could not read hw_params or cannot confirm
        verified:        sample rate, format/channels and clean path match
        broken:          resampling, DSP, ReplayGain, software volume,
                         plughw/default, PipeWire/Pulse or format mismatch
    """
    requested: bool = False
    possible: bool = False
    verified: bool = False
    status: str = "off"
    reasons: list[str] = field(default_factory=list)
    input_sample_rate: int = 0
    input_bit_depth: int = 0
    input_channels: int = 0
    output_sample_rate: int = 0
    output_format: str = ""
    output_channels: int = 0
    device: str = ""

    def is_clean(self) -> bool:
        return self.status == "verified"
