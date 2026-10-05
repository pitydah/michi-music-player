"""DSD signal domain for Audio Phase 2 (AP2-F07, R11-F07).

Pure domain module: stdlib only. DSD is first-class here — explicit units,
explicit packing, explicit layout — and there is no PCM field that could
masquerade as a DSD rate. Presentation labels (DSD64, DSD128, ...) are derived
projections, never stored authority.

The unit algebra follows the corrective seal 211: source bits per second per
channel, GStreamer bytes per second per channel, ALSA frame rates per grouping
width and DoP carrier frame rates are deliberately distinct types. No ALSA or
GStreamer call happens here; transport qualification belongs to F08.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, StrEnum

_DSD_BASE_BITS_PER_SECOND = 2_822_400  # DSD64: 44100 * 64


class DsdPacking(StrEnum):
    """Canonical DSD elementary packing vocabulary (byte groupings)."""

    DSD_U8 = "dsd_u8"
    DSD_U16LE = "dsd_u16le"
    DSD_U16BE = "dsd_u16be"
    DSD_U32LE = "dsd_u32le"
    DSD_U32BE = "dsd_u32be"


class DsdBitOrder(StrEnum):
    """Bit order within the DSD elementary stream.

    Real-format cross-check (FFmpeg ``dsfdec.c``): DSF ``bits-per-sample`` 1
    yields ``DSD_LSBF_PLANAR`` and 8 yields ``DSD_MSBF_PLANAR``; DSDIFF is
    MSB-first (WavPack sets ``QMODE_DSD_MSB_FIRST`` for DFF). Bit order is a
    distinct fact from byte grouping and is never encoded as UNKNOWN when the
    container proves it.
    """

    LSBF = "lsbf"
    MSBF = "msbf"


class DsdOrganization(StrEnum):
    """Channel organization of the elementary stream.

    DSF stores per-channel planar blocks; DSDIFF stores per-frame channel
    bytes (interleaved).
    """

    PLANAR = "planar"
    INTERLEAVED = "interleaved"


class AlsaDsdGrouping(Enum):
    """ALSA DSD groupings (seal 211.1); names are the UAPI format names."""

    DSD_U8 = ("SND_PCM_FORMAT_DSD_U8", 8)
    DSD_U16_LE = ("SND_PCM_FORMAT_DSD_U16_LE", 16)
    DSD_U16_BE = ("SND_PCM_FORMAT_DSD_U16_BE", 16)
    DSD_U32_LE = ("SND_PCM_FORMAT_DSD_U32_LE", 32)
    DSD_U32_BE = ("SND_PCM_FORMAT_DSD_U32_BE", 32)

    @property
    def bits_per_alsa_sample(self) -> int:
        return int(self.value[1])

    @property
    def alsa_format_name(self) -> str:
        return str(self.value[0])


@dataclass(frozen=True, slots=True)
class DsdSourceBitRate:
    """Source DSD bit rate: bits per second PER CHANNEL (seal 211)."""

    bits_per_second_per_channel: int

    def __post_init__(self) -> None:
        value = self.bits_per_second_per_channel
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError("DSD source bit rate must be a positive integer")
        if value % 8:
            raise ValueError("DSD source rate must be byte-addressable")

    @property
    def gst_byte_rate_per_channel(self) -> int:
        """GStreamer caps ``rate`` for DSD is BYTES per second per channel."""
        return self.bits_per_second_per_channel // 8

    @property
    def dop_carrier_frames_per_second(self) -> int:
        if self.bits_per_second_per_channel % 16:
            raise ValueError("DoP v1 requires a source rate divisible by 16")
        return self.bits_per_second_per_channel // 16


@dataclass(frozen=True, slots=True)
class GstDsdRate:
    bytes_per_second_per_channel: int


@dataclass(frozen=True, slots=True)
class AlsaDsdTransportRate:
    frames_per_second: int
    grouping: AlsaDsdGrouping


@dataclass(frozen=True, slots=True)
class DopCarrierRate:
    """DoP carrier frame rate arithmetic only; no framing lives here (F09)."""

    frames_per_second: int


def source_to_gst_rate(source: DsdSourceBitRate) -> GstDsdRate:
    if not isinstance(source, DsdSourceBitRate):
        raise TypeError("source must be a DsdSourceBitRate")
    return GstDsdRate(source.gst_byte_rate_per_channel)


def source_to_alsa_rate(
    source: DsdSourceBitRate,
    grouping: AlsaDsdGrouping,
) -> AlsaDsdTransportRate:
    if not isinstance(source, DsdSourceBitRate):
        raise TypeError("source must be a DsdSourceBitRate")
    if not isinstance(grouping, AlsaDsdGrouping):
        raise TypeError("grouping must be an AlsaDsdGrouping")
    width = grouping.bits_per_alsa_sample
    if source.bits_per_second_per_channel % width:
        raise ValueError("source DSD rate not divisible by ALSA grouping width")
    return AlsaDsdTransportRate(
        frames_per_second=source.bits_per_second_per_channel // width,
        grouping=grouping,
    )


def source_to_dop_rate(source: DsdSourceBitRate) -> DopCarrierRate:
    if not isinstance(source, DsdSourceBitRate):
        raise TypeError("source must be a DsdSourceBitRate")
    return DopCarrierRate(source.dop_carrier_frames_per_second)


@dataclass(frozen=True, slots=True)
class DsdSignalFormat:
    """What the DSD source is, with explicit units and representation facts.

    ``bit_rate_hz`` is the per-channel source bit rate in bits per second
    (never a PCM sample rate, never a byte rate, never a carrier rate).
    ``bit_order`` and ``organization`` are required for later lossless/native
    representation selection and are distinct from ``packing`` (byte grouping).
    This is an additive extension of the R11-F07 minimum shape; no PCM field
    can masquerade here.
    """

    bit_rate_hz: int
    channels: int
    packing: DsdPacking
    bit_order: DsdBitOrder
    organization: DsdOrganization
    layout: tuple[str, ...]

    def __post_init__(self) -> None:
        DsdSourceBitRate(self.bit_rate_hz)  # unit validation, same authority
        if not isinstance(self.channels, int) or isinstance(self.channels, bool):
            raise TypeError("DSD channels must be an integer")
        if self.channels <= 0:
            raise ValueError("DSD channels must be > 0")
        if not isinstance(self.packing, DsdPacking):
            raise TypeError("DSD packing must be a DsdPacking")
        if not isinstance(self.bit_order, DsdBitOrder):
            raise TypeError("DSD bit_order must be a DsdBitOrder")
        if not isinstance(self.organization, DsdOrganization):
            raise TypeError("DSD organization must be a DsdOrganization")
        if not isinstance(self.layout, tuple):
            raise TypeError("DSD layout must be a tuple of positions")
        if not self.layout:
            raise ValueError("DSD layout must be explicit")
        for position in self.layout:
            if not isinstance(position, str) or not position.strip():
                raise ValueError("DSD layout positions must be non-empty strings")
        if len(set(self.layout)) != len(self.layout):
            raise ValueError("DSD layout positions must be unique")
        if len(self.layout) != self.channels:
            raise ValueError("DSD layout length must agree with channels")

    @property
    def source_rate(self) -> DsdSourceBitRate:
        return DsdSourceBitRate(self.bit_rate_hz)

    @property
    def presentation_label(self) -> str | None:
        """Derived display label (DSD64...); never the stored authority."""
        if self.bit_rate_hz % _DSD_BASE_BITS_PER_SECOND:
            return None
        multiple = self.bit_rate_hz // _DSD_BASE_BITS_PER_SECOND
        if multiple <= 0 or multiple & (multiple - 1):
            return None
        return f"DSD{multiple * 64}"
