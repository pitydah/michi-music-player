"""DSP domain for Audio Phase 2 (AP2-F04, R11-F04).

Pure domain module: stdlib only, no Qt/GStreamer/ALSA/persistence imports and
no I/O. This module defines WHAT processing means; F05 later decides HOW a
backend executes it. CORE node kinds are exactly the eight canonical ones —
no Mixer/Limiter/Crossfeed/Loudness in CORE, no backend factory names.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias

_IR_ASSET_RE = re.compile(r"^ir:sha256:([0-9a-f]{64})$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_DITHER_TARGET_BITS = frozenset({8, 16, 20, 24, 32})
_PEQ_BAND_LIMIT = 64


class ProcessingNodeKind(StrEnum):
    """Canonical CORE node kinds (R11-F04). Nothing else is executable."""

    PREAMP = "preamp"
    GRAPHIC_EQ = "graphic_eq"
    PARAMETRIC_EQ = "parametric_eq"
    CONVOLUTION = "convolution"
    CHANNEL_DELAY = "channel_delay"
    CHANNEL_MAP = "channel_map"
    RESAMPLE = "resample"
    DITHER = "dither"


class BiquadType(StrEnum):
    """RBJ filter family (typed bands; never free-form strings)."""

    PEAK = "peak"
    LOW_SHELF = "low_shelf"
    HIGH_SHELF = "high_shelf"
    LOW_PASS = "low_pass"
    HIGH_PASS = "high_pass"
    NOTCH = "notch"
    BAND_PASS = "band_pass"
    ALL_PASS = "all_pass"


#: Filter types whose semantics do not use a gain parameter.
GAINLESS_BIQUAD_TYPES = frozenset(
    {
        BiquadType.LOW_PASS,
        BiquadType.HIGH_PASS,
        BiquadType.NOTCH,
        BiquadType.BAND_PASS,
        BiquadType.ALL_PASS,
    }
)


class ProcessingStrategy(StrEnum):
    """Semantic strategies selected by the compiler; factories are F05's job."""

    GAIN = "gain"
    GRAPHIC_EQ_NBANDS = "graphic_eq_nbands"
    BIQUAD_CASCADE = "biquad_cascade"
    CONVOLUTION_FIR = "convolution_fir"
    RESAMPLE = "resample"
    CHANNEL_DELAY = "channel_delay"
    CHANNEL_MAP = "channel_map"
    DITHER_TERMINAL = "dither_terminal"


class GraphicEqLayout(StrEnum):
    """First-class graphic EQ layouts. The layout defines the band centers."""

    MICHI_10_V1 = "michi_10_v1"
    ISO_31_V1 = "iso_31_v1"


GRAPHIC_EQ_CENTER_HZ: dict[GraphicEqLayout, tuple[float, ...]] = {
    GraphicEqLayout.MICHI_10_V1: (
        31.5,
        63.0,
        125.0,
        250.0,
        500.0,
        1000.0,
        2000.0,
        4000.0,
        8000.0,
        16000.0,
    ),
    GraphicEqLayout.ISO_31_V1: (
        20.0,
        25.0,
        31.5,
        40.0,
        50.0,
        63.0,
        80.0,
        100.0,
        125.0,
        160.0,
        200.0,
        250.0,
        315.0,
        400.0,
        500.0,
        630.0,
        800.0,
        1000.0,
        1250.0,
        1600.0,
        2000.0,
        2500.0,
        3150.0,
        4000.0,
        5000.0,
        6300.0,
        8000.0,
        10000.0,
        12500.0,
        16000.0,
        20000.0,
    ),
}

GRAPHIC_EQ_BAND_COUNTS: dict[GraphicEqLayout, int] = {
    layout: len(centers) for layout, centers in GRAPHIC_EQ_CENTER_HZ.items()
}


class ResampleQuality(StrEnum):
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"
    REFERENCE = "reference"


class DitherMode(StrEnum):
    """Explicit dither policy. Backend defaults are never assumed."""

    NONE = "none"
    TPDF = "tpdf"


class ProcessingAdaptationReason(StrEnum):
    """Canonical adaptation codes of the effective graph (R11-F04 §190)."""

    GRAPH_BYPASSED = "graph_bypassed"
    NODE_DISABLED = "node_disabled"
    INACTIVE_ABOVE_NYQUIST = "inactive_above_nyquist"
    UNSUPPORTED_CURRENT_SIGNAL = "unsupported_current_signal"
    ASSET_UNAVAILABLE = "asset_unavailable"
    ASSET_HASH_MISMATCH = "asset_hash_mismatch"
    CHANNEL_LAYOUT_UNAVAILABLE = "channel_layout_unavailable"


def _require_finite(value: float, field: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{field} must be a number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field} must be finite")


def _require_node_id(node_id: str) -> None:
    if not isinstance(node_id, str) or not node_id.strip():
        raise ValueError("processing node requires a non-empty node_id")


def _require_sha256(value: str, field: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise ValueError(f"{field} must be a lowercase 64-hex sha256")


@dataclass(frozen=True, slots=True)
class PreampNode:
    node_id: str
    gain_db: float
    kind: ProcessingNodeKind = ProcessingNodeKind.PREAMP

    def __post_init__(self) -> None:
        _require_node_id(self.node_id)
        _require_finite(self.gain_db, "preamp gain_db")
        if not -60.0 <= self.gain_db <= 24.0:
            raise ValueError("preamp gain outside safe configuration range")


@dataclass(frozen=True, slots=True)
class GraphicEqNode:
    """Graphic EQ stores layout identity plus ordered gains — never Q values."""

    node_id: str
    layout_id: GraphicEqLayout
    gains_db: tuple[float, ...]
    enabled: bool = True
    kind: ProcessingNodeKind = ProcessingNodeKind.GRAPHIC_EQ

    def __post_init__(self) -> None:
        _require_node_id(self.node_id)
        expected = GRAPHIC_EQ_BAND_COUNTS.get(self.layout_id)
        if expected is None:
            raise ValueError(f"unknown graphic EQ layout: {self.layout_id!r}")
        if len(self.gains_db) != expected:
            raise ValueError(
                f"graphic EQ layout {self.layout_id.value} requires {expected} gains"
            )
        for gain in self.gains_db:
            _require_finite(gain, "graphic EQ gain")

    @property
    def is_flat(self) -> bool:
        return all(gain == 0.0 for gain in self.gains_db)


@dataclass(frozen=True, slots=True)
class PeqBand:
    band_id: str
    filter_type: BiquadType
    frequency_hz: float
    q: float
    gain_db: float
    enabled: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.band_id, str) or not self.band_id.strip():
            raise ValueError("PEQ band requires a non-empty band_id")
        if not isinstance(self.filter_type, BiquadType):
            raise TypeError("PEQ band filter_type must be a BiquadType")
        _require_finite(self.frequency_hz, "PEQ frequency_hz")
        if self.frequency_hz <= 0:
            raise ValueError("PEQ frequency must be > 0")
        _require_finite(self.q, "PEQ q")
        if self.q <= 0:
            raise ValueError("PEQ Q must be > 0")
        _require_finite(self.gain_db, "PEQ gain_db")
        if self.filter_type in GAINLESS_BIQUAD_TYPES and self.gain_db != 0.0:
            raise ValueError(
                f"{self.filter_type.value} has no gain parameter; gain must be 0"
            )


@dataclass(frozen=True, slots=True)
class ParametricEqNode:
    node_id: str
    bands: tuple[PeqBand, ...]
    kind: ProcessingNodeKind = ProcessingNodeKind.PARAMETRIC_EQ

    def __post_init__(self) -> None:
        _require_node_id(self.node_id)
        if len(self.bands) > _PEQ_BAND_LIMIT:
            raise ValueError(f"PEQ supports at most {_PEQ_BAND_LIMIT} bands")
        for band in self.bands:
            if not isinstance(band, PeqBand):
                raise TypeError("PEQ bands must be PeqBand values")
        if len({band.band_id for band in self.bands}) != len(self.bands):
            raise ValueError("PEQ band ids must be unique")


@dataclass(frozen=True, slots=True)
class ConvolutionNode:
    """One semantic convolution. References an immutable asset, not a path."""

    node_id: str
    asset_id: str
    asset_sha256: str
    gain_db: float = 0.0
    enabled: bool = True
    kind: ProcessingNodeKind = ProcessingNodeKind.CONVOLUTION

    def __post_init__(self) -> None:
        _require_node_id(self.node_id)
        match = (
            _IR_ASSET_RE.match(self.asset_id)
            if isinstance(self.asset_id, str)
            else None
        )
        if match is None:
            raise ValueError("convolution asset_id must be 'ir:sha256:<64-hex>'")
        _require_sha256(self.asset_sha256, "convolution asset_sha256")
        if match.group(1) != self.asset_sha256:
            raise ValueError("convolution asset_id and asset_sha256 must agree")
        _require_finite(self.gain_db, "convolution gain_db")


@dataclass(frozen=True, slots=True)
class ChannelDelayNode:
    node_id: str
    delays_us: tuple[int, ...]
    kind: ProcessingNodeKind = ProcessingNodeKind.CHANNEL_DELAY

    def __post_init__(self) -> None:
        _require_node_id(self.node_id)
        if not self.delays_us:
            raise ValueError("channel delay requires per-channel values")
        for value in self.delays_us:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError("channel delay cannot be negative")


@dataclass(frozen=True, slots=True)
class ChannelMapNode:
    node_id: str
    output_to_input: tuple[int | None, ...]
    kind: ProcessingNodeKind = ProcessingNodeKind.CHANNEL_MAP

    def __post_init__(self) -> None:
        _require_node_id(self.node_id)
        if not self.output_to_input:
            raise ValueError("channel map requires an explicit mapping")
        for value in self.output_to_input:
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError("channel map indices must be >= 0 or None")


@dataclass(frozen=True, slots=True)
class ResampleNode:
    node_id: str
    target_rate_hz: int
    quality: ResampleQuality
    kind: ProcessingNodeKind = ProcessingNodeKind.RESAMPLE

    def __post_init__(self) -> None:
        _require_node_id(self.node_id)
        if not isinstance(self.quality, ResampleQuality):
            raise TypeError("resample quality must be a ResampleQuality")
        if not isinstance(self.target_rate_hz, int) or self.target_rate_hz <= 0:
            raise ValueError("resample target rate must be > 0")


@dataclass(frozen=True, slots=True)
class DitherNode:
    node_id: str
    mode: DitherMode
    target_bits: int
    kind: ProcessingNodeKind = ProcessingNodeKind.DITHER

    def __post_init__(self) -> None:
        _require_node_id(self.node_id)
        if not isinstance(self.mode, DitherMode):
            raise TypeError("dither mode must be a DitherMode")
        if self.target_bits not in _DITHER_TARGET_BITS:
            raise ValueError("unsupported dither target precision")


ProcessingNode: TypeAlias = (
    PreampNode
    | GraphicEqNode
    | ParametricEqNode
    | ConvolutionNode
    | ChannelDelayNode
    | ChannelMapNode
    | ResampleNode
    | DitherNode
)


@dataclass(frozen=True, slots=True)
class ProcessingGraph:
    """Immutable saved intent. An edit creates a NEW revision; bypass keeps intent."""

    graph_id: str
    revision: int
    nodes: tuple[ProcessingNode, ...]
    bypassed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.graph_id, str) or not self.graph_id.strip():
            raise ValueError("processing graph requires a graph_id")
        if not isinstance(self.revision, int) or self.revision < 0:
            raise ValueError("processing graph revision must be >= 0")
        if len({node.node_id for node in self.nodes}) != len(self.nodes):
            raise ValueError("processing node ids must be unique")


@dataclass(frozen=True, slots=True)
class ProcessingProfile:
    """Profile identity and graph revision are distinct concepts."""

    profile_id: str
    display_name: str
    graph: ProcessingGraph
    enabled: bool = True
    auto_headroom: bool = False
    target_device_id: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("processing profile requires a profile_id")


@dataclass(frozen=True, slots=True)
class ProcessingSampleContract:
    """Explicit representation boundaries (R11-G04). Never implicit."""

    input_format: str
    working_format: str
    output_format: str | None
    input_rate_hz: int
    output_rate_hz: int
    channels_in: int
    channels_out: int
    input_conversion: bool
    output_quantization: bool
    dither_mode: str
    noise_shaping_mode: str


@dataclass(frozen=True, slots=True)
class ImpulseResponseMetadata:
    """Immutable IR asset facts; F04 never reads the IR file itself.

    ``asset_id`` and ``sha256`` are validated as forms but NOT forced to agree:
    a store reporting an asset whose bytes hash differently is exactly the
    integrity signal the resolver must surface as ``ASSET_HASH_MISMATCH``.
    """

    asset_id: str
    sha256: str
    rate_hz: int
    channels: int

    def __post_init__(self) -> None:
        match = (
            _IR_ASSET_RE.match(self.asset_id)
            if isinstance(self.asset_id, str)
            else None
        )
        if match is None:
            raise ValueError("IR asset_id must be 'ir:sha256:<64-hex>'")
        _require_sha256(self.sha256, "IR sha256")
        if self.rate_hz <= 0:
            raise ValueError("IR rate must be > 0")
        if self.channels <= 0:
            raise ValueError("IR channels must be > 0")


def _validate_properties(properties: tuple[tuple[str, object], ...]) -> None:
    seen: set[str] = set()
    for pair in properties:
        if not (isinstance(pair, tuple) and len(pair) == 2):
            raise ValueError("compiled node properties must be (key, value) pairs")
        key, value = pair
        if not isinstance(key, str) or not key.strip():
            raise ValueError("compiled node property keys must be non-empty strings")
        if key in seen:
            raise ValueError("compiled node property keys must be unique")
        seen.add(key)
        if not isinstance(value, (str, int, float, bool, type(None), tuple)):
            raise TypeError(f"compiled node property {key!r} must be a scalar or tuple")


@dataclass(frozen=True, slots=True)
class CompiledProcessingNode:
    node_id: str
    kind: ProcessingNodeKind
    strategy: ProcessingStrategy
    properties: tuple[tuple[str, object], ...]
    expected_latency_samples: int
    asset_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_node_id(self.node_id)
        if not isinstance(self.strategy, ProcessingStrategy):
            raise TypeError("compiled node strategy must be a ProcessingStrategy")
        if self.expected_latency_samples < 0:
            raise ValueError("compiled node latency must be >= 0")
        _validate_properties(self.properties)


@dataclass(frozen=True, slots=True)
class CompiledProcessingPlan:
    """Execution-significant truth: strategies, sample contract, dimensions."""

    plan_id: str
    graph_id: str
    graph_revision: int
    backend_id: str
    sample_contract: ProcessingSampleContract
    nodes: tuple[CompiledProcessingNode, ...]
    total_latency_samples: int
    asset_hashes: tuple[str, ...]
    changes_sample_values: bool
    changes_representation: bool
    changes_rate: bool
    changes_channels: bool
    changes_timing: bool
    changes_channel_assignment: bool
    quantization_boundary: bool
    adaptation_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
