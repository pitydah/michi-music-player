"""AP2-F09 — DoP domain contracts and pure framing reference.

DoP is a transport family, not PCM music: DSD source bytes are packed with
0x05/0xFA markers into a PCM-compatible carrier. This module implements the
byte-exact reference packer, streaming state, carrier rate arithmetic, memory
layouts and the capability/interpretation vocabulary. The productive native
packer is blocked on ADR 0012's packaging gate; Python is the conformance
oracle, never the productive per-sample hot path.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum

from michi.domain.dsd_signal import (
    DopCarrierRate,
    DsdSignalFormat,
    source_to_dop_rate,
)

DOP_MARKERS: tuple[int, int] = (0x05, 0xFA)
DOP_PACKER_REVISION = "dop-python-reference-v1"
DOP_CORE_CHANNELS = 2


class DopCarrierLayout(StrEnum):
    PACKED_24_LE = "packed_24_le"
    S32_LE_LSB24 = "s32_le_lsb24"
    S32_LE_MSB24 = "s32_le_msb24"


class DopCarrierSupport(StrEnum):
    QUALIFIED = "qualified"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"
    INCONCLUSIVE = "inconclusive"


class DopInterpretationState(StrEnum):
    UNKNOWN = "unknown"
    DECLARED = "declared"
    USER_CONFIRMED = "user_confirmed"
    DEVICE_OBSERVED = "device_observed"
    PHYSICALLY_QUALIFIED = "physically_qualified"
    CONTRADICTED = "contradicted"


_INTERPRETATION_ORDER = {
    DopInterpretationState.UNKNOWN: 0,
    DopInterpretationState.DECLARED: 1,
    DopInterpretationState.USER_CONFIRMED: 2,
    DopInterpretationState.DEVICE_OBSERVED: 3,
    DopInterpretationState.PHYSICALLY_QUALIFIED: 4,
}


class DopPackingError(ValueError):
    """Typed framing refusal (channel/payload/layout)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DopState:
    marker_phase: int = 0

    def __post_init__(self) -> None:
        if self.marker_phase not in (0, 1):
            raise DopPackingError("DOP_MARKER_PHASE_INVALID", "phase must be 0 or 1")


@dataclass(slots=True)
class DopStreamingState:
    marker_phase: int = 0
    pending_left: bytearray = field(default_factory=bytearray)
    pending_right: bytearray = field(default_factory=bytearray)
    discontinuity_generation: int = 0
    last_reset_reason: str | None = None

    def __post_init__(self) -> None:
        if self.marker_phase not in (0, 1):
            raise DopPackingError("DOP_MARKER_PHASE_INVALID", "phase must be 0 or 1")

    def reset_for_discontinuity(self, reason: str) -> None:
        self.marker_phase = 0
        self.pending_left.clear()
        self.pending_right.clear()
        self.discontinuity_generation += 1
        self.last_reset_reason = str(reason)


@dataclass(frozen=True, slots=True)
class DopCarrierMemoryContract:
    layout: DopCarrierLayout
    alsa_format: str
    container_bits: int
    significant_transport_bits: int
    payload_byte_offsets: tuple[int, int]
    marker_byte_offset: int
    padding_byte_offsets: tuple[int, ...]
    padding_value: int

    def __post_init__(self) -> None:
        if not isinstance(self.layout, DopCarrierLayout):
            raise DopPackingError("DOP_LAYOUT_INVALID", "layout must be explicit")
        offsets = (self.payload_byte_offsets[0], self.marker_byte_offset)
        if len(self.payload_byte_offsets) != 2:
            raise DopPackingError("DOP_LAYOUT_INVALID", "two payload offsets required")
        if any(offset < 0 or offset >= self.container_bits // 8 for offset in offsets):
            raise DopPackingError("DOP_LAYOUT_INVALID", "offset outside container")
        if self.significant_transport_bits != 24:
            raise DopPackingError(
                "DOP_LAYOUT_INVALID", "DoP transport is 24 significant bits"
            )
        if self.padding_value != 0:
            raise DopPackingError("DOP_LAYOUT_INVALID", "padding must be zero")


_MEMORY_CONTRACTS = {
    DopCarrierLayout.PACKED_24_LE: DopCarrierMemoryContract(
        layout=DopCarrierLayout.PACKED_24_LE,
        alsa_format="S24_3LE",
        container_bits=24,
        significant_transport_bits=24,
        payload_byte_offsets=(0, 1),
        marker_byte_offset=2,
        padding_byte_offsets=(),
        padding_value=0,
    ),
    DopCarrierLayout.S32_LE_LSB24: DopCarrierMemoryContract(
        layout=DopCarrierLayout.S32_LE_LSB24,
        alsa_format="S32_LE",
        container_bits=32,
        significant_transport_bits=24,
        payload_byte_offsets=(0, 1),
        marker_byte_offset=2,
        padding_byte_offsets=(3,),
        padding_value=0,
    ),
    DopCarrierLayout.S32_LE_MSB24: DopCarrierMemoryContract(
        layout=DopCarrierLayout.S32_LE_MSB24,
        alsa_format="S32_LE",
        container_bits=32,
        significant_transport_bits=24,
        payload_byte_offsets=(1, 2),
        marker_byte_offset=3,
        padding_byte_offsets=(0,),
        padding_value=0,
    ),
}
#: Production candidate layouts; MSB24 stays disabled until a real target proves it.
PRODUCTION_DOP_LAYOUTS: tuple[DopCarrierLayout, ...] = (
    DopCarrierLayout.PACKED_24_LE,
    DopCarrierLayout.S32_LE_LSB24,
)


def memory_contract_for(layout: DopCarrierLayout) -> DopCarrierMemoryContract:
    try:
        return _MEMORY_CONTRACTS[layout]
    except KeyError as exc:
        raise DopPackingError("DOP_LAYOUT_UNKNOWN", str(layout)) from exc


def encode_dop24(
    payload0: int, payload1: int, marker: int, layout: DopCarrierLayout
) -> bytes:
    values = (payload0 & 0xFF, payload1 & 0xFF, marker & 0xFF)
    if layout is DopCarrierLayout.PACKED_24_LE:
        return bytes(values)
    if layout is DopCarrierLayout.S32_LE_LSB24:
        return bytes((*values, 0x00))
    if layout is DopCarrierLayout.S32_LE_MSB24:
        return bytes((0x00, *values))
    raise DopPackingError("DOP_LAYOUT_UNKNOWN", str(layout))


_REVERSE_BITS = bytes(int(f"{value:08b}"[::-1], 2) for value in range(256))


def _reverse_payload(data: bytes) -> bytes:
    return bytes(_REVERSE_BITS[value] for value in data)


@dataclass(frozen=True, slots=True)
class DopPacketResult:
    payload: bytes
    next_state: DopState
    source_bytes_consumed: int
    carrier_frames_written: int


def expected_carrier_rate(dsd_bit_rate_hz: int) -> DopCarrierRate:
    """DoP v1: two DSD bytes (16 bits) per carrier frame per channel."""
    if (
        not isinstance(dsd_bit_rate_hz, int)
        or isinstance(dsd_bit_rate_hz, bool)
        or dsd_bit_rate_hz <= 0
        or dsd_bit_rate_hz % 16
    ):
        raise DopPackingError(
            "DOP_SOURCE_RATE_INVALID",
            "DSD bit rate must be positive and divisible by 16",
        )
    from michi.domain.dsd_signal import DsdSourceBitRate

    return source_to_dop_rate(DsdSourceBitRate(dsd_bit_rate_hz))


def _validate_stereo(left: bytes, right: bytes) -> None:
    if not isinstance(left, bytes) or not isinstance(right, bytes):
        raise DopPackingError("DOP_PAYLOAD_INVALID", "payloads must be bytes")
    if len(left) != len(right):
        raise DopPackingError(
            "DOP_CHANNEL_LENGTH_MISMATCH", "left/right must have equal length"
        )
    if len(left) % 2:
        raise DopPackingError(
            "DOP_ODD_PAYLOAD", "a complete frame requires two bytes per channel"
        )


def pack_dop_interleaved_stereo(
    left: bytes,
    right: bytes,
    *,
    state: DopState | None = None,
    reverse_bits: bool = False,
    layout: DopCarrierLayout = DopCarrierLayout.PACKED_24_LE,
) -> DopPacketResult:
    """One-shot reference framing (canonical vector and conformance)."""
    _validate_stereo(left, right)
    state = state or DopState()
    if reverse_bits:
        left = _reverse_payload(left)
        right = _reverse_payload(right)
    out = bytearray()
    phase = state.marker_phase
    for offset in range(0, len(left), 2):
        marker = DOP_MARKERS[phase]
        out.extend(encode_dop24(left[offset], left[offset + 1], marker, layout))
        out.extend(encode_dop24(right[offset], right[offset + 1], marker, layout))
        phase ^= 1
    return DopPacketResult(
        payload=bytes(out),
        next_state=DopState(phase),
        source_bytes_consumed=len(left),
        carrier_frames_written=len(left) // 2,
    )


class DopStreamPacker:
    """Stateful, chunk-boundary-independent reference packer."""

    def __init__(
        self,
        *,
        layout: DopCarrierLayout = DopCarrierLayout.PACKED_24_LE,
        reverse_bits: bool = False,
    ) -> None:
        self.layout = layout
        self.reverse_bits = bool(reverse_bits)
        if layout not in _MEMORY_CONTRACTS:
            raise DopPackingError("DOP_LAYOUT_UNKNOWN", str(layout))
        self.state = DopStreamingState()

    @property
    def marker_phase(self) -> int:
        return self.state.marker_phase

    def reset_for_discontinuity(self, reason: str) -> None:
        self.state.reset_for_discontinuity(reason)

    def _take_pair(self, buffer: bytearray) -> tuple[int, int] | None:
        if len(buffer) < 2:
            return None
        return buffer[0], buffer[1]

    def pack_stereo(self, left: bytes, right: bytes) -> bytes:
        if not isinstance(left, bytes) or not isinstance(right, bytes):
            raise DopPackingError("DOP_PAYLOAD_INVALID", "payloads must be bytes")
        self.state.pending_left.extend(left)
        self.state.pending_right.extend(right)
        out = bytearray()
        while True:
            pair_left = self._take_pair(self.state.pending_left)
            pair_right = self._take_pair(self.state.pending_right)
            if pair_left is None or pair_right is None:
                break
            del self.state.pending_left[:2]
            del self.state.pending_right[:2]
            if self.reverse_bits:
                pair_left = (_REVERSE_BITS[pair_left[0]], _REVERSE_BITS[pair_left[1]])
                pair_right = (
                    _REVERSE_BITS[pair_right[0]],
                    _REVERSE_BITS[pair_right[1]],
                )
            marker = DOP_MARKERS[self.state.marker_phase]
            out.extend(encode_dop24(*pair_left, marker, self.layout))
            out.extend(encode_dop24(*pair_right, marker, self.layout))
            self.state.marker_phase ^= 1
        return bytes(out)

    def finish(self) -> bytes:
        if self.state.pending_left or self.state.pending_right:
            raise DopPackingError(
                "DOP_INCOMPLETE_FRAME",
                "stream ended with an incomplete source frame",
            )
        return b""


@dataclass(frozen=True, slots=True)
class DopCarrierQualification:
    stable_device_id: str
    carrier_layout_id: str
    carrier_rate_hz: int
    alsa_format: str
    channels: int
    support: DopCarrierSupport
    environment_fingerprint: str
    evidence_refs: tuple[str, ...]
    binding_generation: int | None = None

    def __post_init__(self) -> None:
        if (
            not self.stable_device_id.strip()
            or not self.environment_fingerprint.strip()
        ):
            raise DopPackingError(
                "DOP_CARRIER_QUALIFICATION_INVALID", "identity/evidence required"
            )
        if self.carrier_rate_hz <= 0 or self.channels != DOP_CORE_CHANNELS:
            raise DopPackingError("DOP_CARRIER_QUALIFICATION_INVALID", "rate/channels")
        if not isinstance(self.support, DopCarrierSupport):
            raise DopPackingError("DOP_CARRIER_QUALIFICATION_INVALID", "support")
        if not self.evidence_refs or not all(ref.strip() for ref in self.evidence_refs):
            raise DopPackingError("DOP_CARRIER_QUALIFICATION_INVALID", "evidence")


@dataclass(frozen=True, slots=True)
class DopDeviceInterpretationEvidence:
    stable_device_id: str
    source_dsd_multiplier: int | None
    state: DopInterpretationState
    source: str
    device_revision: str | None
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.stable_device_id.strip() or not self.source.strip():
            raise DopPackingError("DOP_INTERPRETATION_INVALID", "identity/source")
        if not isinstance(self.state, DopInterpretationState):
            raise DopPackingError("DOP_INTERPRETATION_INVALID", "state")
        if not self.evidence_refs:
            raise DopPackingError("DOP_INTERPRETATION_INVALID", "evidence")


@dataclass(frozen=True, slots=True)
class DopPolicyDecision:
    explicit_requested: bool
    auto_allowed: bool
    minimum_interpretation_state: DopInterpretationState = (
        DopInterpretationState.DECLARED
    )

    def __post_init__(self) -> None:
        if not isinstance(self.explicit_requested, bool) or not isinstance(
            self.auto_allowed, bool
        ):
            raise DopPackingError("DOP_POLICY_INVALID", "policy flags must be bool")
        if not isinstance(self.minimum_interpretation_state, DopInterpretationState):
            raise DopPackingError("DOP_POLICY_INVALID", "invalid interpretation state")


def interpretation_rank(state: DopInterpretationState) -> int:
    return _INTERPRETATION_ORDER[state]


def stable_dop_plan_hash(payload: dict) -> str:
    return (
        "dop:"
        + hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ).hexdigest()
    )


def validate_stereo_source(source: DsdSignalFormat) -> None:
    if not isinstance(source, DsdSignalFormat):
        raise DopPackingError("DOP_SOURCE_INVALID", "source must be DsdSignalFormat")
    if source.channels != DOP_CORE_CHANNELS:
        raise DopPackingError(
            "DOP_MULTICHANNEL_UNSUPPORTED",
            "DoP CORE supports exactly two channels",
        )
