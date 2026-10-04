"""Family-neutral audio-signal domain language for Audio Phase 2 (AP2-F01).

Pure domain module: stdlib only, no Qt/GStreamer/ALSA/application/persistence
imports. These types describe WHAT a signal is, never HOW a backend encodes it.

Contract anchors: R11-F01 (create-only slice) and spec 121 (PCM semantics of
reference). DSD/DoP formats belong to their own later phases; this module
carries only the PCM vocabulary F01 requires.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SignalFamily(StrEnum):
    """Canonical signal families. DSD gains its own formats in later phases."""

    PCM = "pcm"
    DSD = "dsd"


@dataclass(frozen=True, slots=True)
class ChannelLayout:
    """Ordered channel positions. The order is semantic and preserved exactly."""

    positions: tuple[str, ...]

    @property
    def channels(self) -> int:
        return len(self.positions)


@dataclass(frozen=True, slots=True)
class PcmSignalFormat:
    """What the PCM signal is: exact rate, carrier format and known precision.

    ``significant_bits`` stays ``None`` when the carrier does not prove the
    precision (121 SIG-04): S32_LE is 32 container bits, not 32 significant
    bits, and this type never coerces that unknown into a number.
    """

    rate_hz: int
    transport_format: str
    significant_bits: int | None
    layout: ChannelLayout

    def __post_init__(self) -> None:
        if self.rate_hz <= 0:
            raise ValueError("PCM rate_hz must be > 0")
        if not self.transport_format.strip():
            raise ValueError("PCM transport_format is required")
        if self.significant_bits is not None and self.significant_bits <= 0:
            raise ValueError("significant_bits must be positive when known")
        if self.layout.channels <= 0:
            raise ValueError("PCM layout must contain at least one channel")
