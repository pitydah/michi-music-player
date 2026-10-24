"""AP2-F09 — byte-exact DoP reference packer and streaming contracts."""

from __future__ import annotations

import random

import pytest

from michi.domain.dop import (
    DOP_MARKERS,
    DopCarrierLayout,
    DopPackingError,
    DopState,
    DopStreamingState,
    DopStreamPacker,
    encode_dop24,
    expected_carrier_rate,
    memory_contract_for,
    pack_dop_interleaved_stereo,
)
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)

LEFT = bytes.fromhex("11223344")
RIGHT = bytes.fromhex("55667788")
CANONICAL = bytes.fromhex("1122055566053344fa7788fa")


def _source(rate: int = 2_822_400, channels: int = 2) -> DsdSignalFormat:
    layout = ("FL", "FR") if channels == 2 else tuple(f"C{i}" for i in range(channels))
    return DsdSignalFormat(
        bit_rate_hz=rate,
        channels=channels,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.MSBF,
        organization=DsdOrganization.PLANAR,
        layout=layout,
    )


def test_canonical_0x05_0xfa_vector() -> None:
    result = pack_dop_interleaved_stereo(LEFT, RIGHT)
    assert result.payload == CANONICAL
    assert result.carrier_frames_written == 2
    assert result.next_state.marker_phase == 0
    assert CANONICAL[2] == 0x05 and CANONICAL[5] == 0x05
    assert CANONICAL[8] == 0xFA and CANONICAL[11] == 0xFA


@pytest.mark.parametrize(
    "rate,carrier",
    [
        (2_822_400, 176_400),
        (5_644_800, 352_800),
        (11_289_600, 705_600),
        (22_579_200, 1_411_200),
    ],
)
def test_carrier_rate_algebra(rate, carrier) -> None:
    assert expected_carrier_rate(rate).frames_per_second == carrier


def test_invalid_source_rate_is_typed() -> None:
    with pytest.raises(DopPackingError) as info:
        expected_carrier_rate(2_822_401)
    assert info.value.code == "DOP_SOURCE_RATE_INVALID"


def test_layout_encoders_are_exact() -> None:
    assert encode_dop24(
        0x11, 0x22, 0x05, DopCarrierLayout.PACKED_24_LE
    ) == bytes.fromhex("112205")
    assert encode_dop24(
        0x11, 0x22, 0x05, DopCarrierLayout.S32_LE_LSB24
    ) == bytes.fromhex("11220500")
    assert encode_dop24(
        0x11, 0x22, 0x05, DopCarrierLayout.S32_LE_MSB24
    ) == bytes.fromhex("00112205")


def test_memory_contracts_are_explicit() -> None:
    packed = memory_contract_for(DopCarrierLayout.PACKED_24_LE)
    lsb = memory_contract_for(DopCarrierLayout.S32_LE_LSB24)
    msb = memory_contract_for(DopCarrierLayout.S32_LE_MSB24)
    assert (packed.alsa_format, packed.container_bits, packed.padding_byte_offsets) == (
        "S24_3LE",
        24,
        (),
    )
    assert (lsb.marker_byte_offset, lsb.padding_byte_offsets) == (2, (3,))
    assert (
        msb.payload_byte_offsets,
        msb.marker_byte_offset,
        msb.padding_byte_offsets,
    ) == (
        (1, 2),
        3,
        (0,),
    )


def test_s32_layout_has_explicit_padding_and_marker() -> None:
    result = pack_dop_interleaved_stereo(
        LEFT, RIGHT, layout=DopCarrierLayout.S32_LE_LSB24
    )
    assert result.payload[:4] == bytes.fromhex("11220500")
    assert result.payload[4:8] == bytes.fromhex("55660500")


def test_bit_reversal_only_affects_payload() -> None:
    result = pack_dop_interleaved_stereo(LEFT, RIGHT, reverse_bits=True)
    assert result.payload[0:2] == bytes((0x88, 0x44))
    assert result.payload[2] == DOP_MARKERS[0]


def test_streaming_is_chunk_boundary_independent() -> None:
    one_shot = pack_dop_interleaved_stereo(LEFT, RIGHT).payload
    for sizes in ((1, 1, 1, 1), (2, 2), (3, 1), (1, 3)):
        packer = DopStreamPacker()
        out = bytearray()
        lo = ro = 0
        for size in sizes:
            out.extend(packer.pack_stereo(LEFT[lo : lo + size], RIGHT[ro : ro + size]))
            lo += size
            ro += size
        assert bytes(out) == one_shot
        assert packer.state.pending_left == bytearray()
        assert packer.state.pending_right == bytearray()


def test_random_splits_preserve_bytes() -> None:
    rng_left = random.Random(7)
    rng_right = random.Random(11)
    left = bytes(rng_left.randrange(256) for _ in range(64))
    right = bytes(rng_right.randrange(256) for _ in range(64))
    expected = pack_dop_interleaved_stereo(left, right).payload
    packer = DopStreamPacker()
    rng = random.Random(99)
    out = bytearray()
    lo = ro = 0
    while lo < len(left) or ro < len(right):
        take_l = min(len(left) - lo, rng.randint(0, 5))
        take_r = min(len(right) - ro, rng.randint(0, 5))
        out.extend(packer.pack_stereo(left[lo : lo + take_l], right[ro : ro + take_r]))
        lo += take_l
        ro += take_r
    assert bytes(out) == expected


def test_unequal_chunk_arrival_is_buffered() -> None:
    packer = DopStreamPacker()
    assert packer.pack_stereo(LEFT[:2], b"") == b""
    out = packer.pack_stereo(b"", RIGHT[:2])
    assert out == bytes.fromhex("112205556605")
    assert packer.marker_phase == 1


def test_empty_chunks_do_not_change_phase() -> None:
    packer = DopStreamPacker()
    assert packer.pack_stereo(b"", b"") == b""
    assert packer.marker_phase == 0


def test_discontinuity_resets_phase_and_pending() -> None:
    packer = DopStreamPacker()
    packer.pack_stereo(LEFT[:1], RIGHT[:1])
    assert packer.state.pending_left
    packer.reset_for_discontinuity("seek")
    assert packer.state.pending_left == bytearray()
    assert packer.state.pending_right == bytearray()
    assert packer.marker_phase == 0
    assert packer.state.discontinuity_generation == 1
    assert packer.state.last_reset_reason == "seek"
    assert packer.pack_stereo(LEFT[:2], RIGHT[:2]) == bytes.fromhex("112205556605")


def test_incomplete_frame_at_finish_is_typed() -> None:
    packer = DopStreamPacker()
    packer.pack_stereo(b"\x11", b"\x55")
    with pytest.raises(DopPackingError) as info:
        packer.finish()
    assert info.value.code == "DOP_INCOMPLETE_FRAME"


def test_channel_length_mismatch_and_odd_payload() -> None:
    with pytest.raises(DopPackingError) as info:
        pack_dop_interleaved_stereo(b"\x11\x22", b"\x55")
    assert info.value.code == "DOP_CHANNEL_LENGTH_MISMATCH"
    with pytest.raises(DopPackingError) as info:
        pack_dop_interleaved_stereo(b"\x11", b"\x55")
    assert info.value.code == "DOP_ODD_PAYLOAD"


def test_multichannel_source_is_refused() -> None:
    from michi.domain.dop import validate_stereo_source

    with pytest.raises(DopPackingError) as info:
        validate_stereo_source(_source(channels=3))
    assert info.value.code == "DOP_MULTICHANNEL_UNSUPPORTED"


def test_streaming_state_rejects_invalid_phase() -> None:
    with pytest.raises(DopPackingError):
        DopState(2)
    with pytest.raises(DopPackingError):
        DopStreamingState(marker_phase=2)


def test_memory_contract_rejects_malformed_offsets() -> None:
    from dataclasses import replace

    base = memory_contract_for(DopCarrierLayout.PACKED_24_LE)
    cases = (
        {"payload_byte_offsets": (0, 0)},
        {"payload_byte_offsets": (-1, 1)},
        {"payload_byte_offsets": (0, 3)},
        {"marker_byte_offset": 1},
        {"padding_byte_offsets": (0,)},
        {"container_bits": 16},
        {"significant_transport_bits": 16},
        {"endianness": "big"},
    )
    for overrides in cases:
        with pytest.raises(DopPackingError):
            replace(base, **overrides)


def test_streaming_backlog_is_bounded() -> None:
    from michi.domain.dop import MAX_PENDING_BYTES

    packer = DopStreamPacker()
    with pytest.raises(DopPackingError) as info:
        packer.pack_stereo(b"\x00" * (MAX_PENDING_BYTES + 1), b"")
    assert info.value.code == "DOP_BUFFER_BACKLOG_EXCEEDED"
    assert packer.state.pending_left == bytearray()
    assert packer.state.pending_right == bytearray()
    assert packer.state.invalidated is True
    with pytest.raises(DopPackingError) as info:
        packer.pack_stereo(b"\x11\x22", b"\x55\x66")
    assert info.value.code == "DOP_STREAM_INVALIDATED"
    packer.reset_for_discontinuity("overflow_recovery")
    assert packer.state.invalidated is False
    assert packer.pack_stereo(b"\x11\x22", b"\x55\x66") == bytes.fromhex("112205556605")


def test_result_counters_are_unambiguous() -> None:
    result = pack_dop_interleaved_stereo(LEFT, RIGHT)
    assert result.source_bytes_consumed == 4
    assert result.source_bytes_per_channel_total == 4
    assert result.carrier_frames_written == 2
    assert result.carrier_bytes_written == 12


@pytest.mark.parametrize("seed", [0, 1, 7, 42])
def test_randomized_chunk_property(seed) -> None:
    rng = random.Random(seed)
    left = bytes(rng.randrange(256) for _ in range(32))
    right = bytes(rng.randrange(256) for _ in range(32))
    expected = pack_dop_interleaved_stereo(left, right).payload
    packer = DopStreamPacker()
    out = bytearray()
    lo = ro = 0
    while lo < len(left):
        take = rng.randint(1, 5)
        out.extend(packer.pack_stereo(left[lo : lo + take], right[ro : ro + take]))
        lo += take
        ro += take
    assert bytes(out) == expected
