"""AP2-F07 — DSD source truth sealed against real DSF and DSDIFF formats.

Contract anchors: R11-F07 (explicit units, derived-only labels, no PCM field
reuse), §211 (DSD rate algebra), §212 (container / elementary / decoded truth
separation). Format layouts are pinned against independent implementations:
FFmpeg ``dsfdec.c`` (DSF) and WavPack ``dsf.c`` / ``dsdiff.c`` (DSF/DFF).

The characterizer is a deterministic static parser: no GStreamer pipeline, no
ALSA, no output-capability claim.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from michi.application.dsd_source_characterizer import (
    ContainerAudioFacts,
    DsdSourceCharacterization,
    DsdSourceCharacterizer,
    DsdSourceStatus,
    ElementaryEncoding,
    ElementaryStreamObservation,
    EvidenceKind,
)
from michi.domain.dsd_signal import (
    AlsaDsdGrouping,
    DopCarrierRate,
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
    DsdSourceBitRate,
    source_to_alsa_rate,
    source_to_dop_rate,
    source_to_gst_rate,
)

DOMAIN_MODULE = Path(sys.modules["michi.domain.dsd_signal"].__file__)
CHARACTERIZER_MODULE = Path(
    sys.modules["michi.application.dsd_source_characterizer"].__file__
)

_DSF_FIXED_HEADER = 92
_DSF_BLOCK = 4096
_DFF_MAX_PROP_CAP = 4 * 1024 * 1024


# --------------------------------------------------------------------------- #
# deterministic real-format builders (test-side construction only)
# --------------------------------------------------------------------------- #


def _dsf_payload(
    channels: int, sample_count: int, block: int, byte: int = 0x69
) -> bytes:
    blocks = (sample_count + block * 8 - 1) // (block * 8)
    return bytes([byte]) * (blocks * block * channels)


def build_dsf(
    *,
    rate: int = 2_822_400,
    chan_type: int = 2,
    channels: int = 2,
    bits: int = 8,
    sample_count: int = 8192,
    block_size: int = _DSF_BLOCK,
    format_id: int = 0,
    version: int = 1,
    reserved: int = 0,
    payload: bytes | None = None,
    data_chunk_size: int | None = None,
    file_size_override: int | None = None,
    meta_tail: bytes = b"",
    meta_pointer: int | None = None,
    chunk_sizes: tuple[int, int] = (28, 52),
    truncate_to: int | None = None,
) -> bytes:
    """Real DSF: every chunk size includes its 12-byte header."""
    if payload is None:
        payload = _dsf_payload(channels, sample_count, block_size)
    data_chunk_size = 12 + len(payload) if data_chunk_size is None else data_chunk_size
    file_size = _DSF_FIXED_HEADER + len(payload) + len(meta_tail)
    if file_size_override is not None:
        file_size = file_size_override
    if meta_pointer is None:
        meta_pointer = _DSF_FIXED_HEADER + len(payload) if meta_tail else 0
    header = (
        b"DSD "
        + struct.pack("<Q", chunk_sizes[0])
        + struct.pack("<Q", file_size)
        + struct.pack("<Q", meta_pointer)
        + b"fmt "
        + struct.pack("<Q", chunk_sizes[1])
        + struct.pack("<I", version)
        + struct.pack("<I", format_id)
        + struct.pack("<I", chan_type)
        + struct.pack("<I", channels)
        + struct.pack("<I", rate)
        + struct.pack("<I", bits)
        + struct.pack("<Q", sample_count)
        + struct.pack("<I", block_size)
        + struct.pack("<I", reserved)
        + b"data"
        + struct.pack("<Q", data_chunk_size)
    )
    blob = header + payload + meta_tail
    return blob[:truncate_to] if truncate_to is not None else blob


def _dff_chunk(chunk_id: bytes, payload: bytes) -> bytes:
    """Real DSDIFF chunk: 4-byte ID + 64-bit big-endian size + data (+ pad)."""
    blob = chunk_id + struct.pack(">q", len(payload)) + payload
    if len(payload) % 2:
        blob += b"\x00"
    return blob


def build_dff(
    *,
    rate: int = 2_822_400,
    channel_ids: tuple[bytes, ...] = (b"SLFT", b"SRGT"),
    declared_channels: int | None = None,
    compression: bytes | None = b"DSD ",
    cmpr_payload_override: bytes | None = None,
    payload: bytes | None = None,
    form_size_override: int | None = None,
    extra_prop_child: bytes = b"",
    extra_top_child: bytes = b"",
    truncate_to: int | None = None,
    fver_first: bool = True,
    fver_version: int = 0x01050000,
    prop_type: bytes = b"SND ",
    prop_body_override: bytes | None = None,
    omit_prop: bool = False,
    omit_data: bool = False,
    dst: bool = False,
    dsti: bool = False,
    duplicate_prop: bool = False,
) -> bytes:
    payload = payload if payload is not None else bytes([0x55]) * 4096
    declared = declared_channels if declared_channels is not None else len(channel_ids)
    fs = _dff_chunk(b"FS  ", struct.pack(">I", rate))
    chnl_payload = struct.pack(">H", declared) + b"".join(channel_ids)
    chnl = _dff_chunk(b"CHNL", chnl_payload)
    cmpr = b""
    if compression is not None:
        if cmpr_payload_override is not None:
            cmpr = _dff_chunk(b"CMPR", cmpr_payload_override)
        else:
            name = b"\x00"
            cmpr_payload = compression + name
            if len(cmpr_payload) % 2:
                cmpr_payload += b"\x00"
            cmpr = _dff_chunk(b"CMPR", cmpr_payload)
    if prop_body_override is not None:
        prop_body = prop_body_override
    else:
        prop_body = prop_type + fs + chnl + cmpr + extra_prop_child
    prop = _dff_chunk(b"PROP", prop_body)
    fver = _dff_chunk(b"FVER", struct.pack(">I", fver_version))
    top = [fver, prop] if fver_first else [prop, fver]
    if omit_prop:
        top = [fver]
    dst_index = _dff_chunk(b"DSTI", b"\x00" * 4) if dsti else b""
    data = b"" if omit_data else _dff_chunk(b"DST " if dst else b"DSD ", payload)
    body = (
        b"".join(top)
        + dst_index
        + extra_top_child
        + (prop if duplicate_prop else b"")
        + data
    )
    form_size = 4 + len(body) if form_size_override is None else form_size_override
    blob = b"FRM8" + struct.pack(">q", form_size) + b"DSD " + body
    return blob[:truncate_to] if truncate_to is not None else blob


def build_legacy_8byte_header_dff() -> bytes:
    """The pre-corrective wrong model (4+4 headers) must never parse as DFF."""
    payload = bytes([0x55]) * 512

    def legacy_chunk(chunk_id: bytes, body: bytes) -> bytes:
        blob = chunk_id + struct.pack(">I", len(body)) + body
        return blob + (b"\x00" if len(body) % 2 else b"")

    fs = legacy_chunk(b"FS  ", struct.pack(">I", 2_822_400))
    chnl = legacy_chunk(b"CHNL", struct.pack(">H", 2) + b"SLFT" + b"SRGT")
    cmpr = legacy_chunk(b"CMPR", b"DSD " + b"\x00" + b"\x00")
    prop = legacy_chunk(b"PROP", b"SND " + fs + chnl + cmpr)
    fver = legacy_chunk(b"FVER", struct.pack(">I", 0x01050000))
    data = legacy_chunk(b"DSD ", payload)
    body = fver + prop + data
    return b"FRM8" + struct.pack(">I", 4 + len(body)) + b"DSD " + body


def _write(tmp_path: Path, name: str, blob: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(blob)
    return path


def _characterize(tmp_path: Path, name: str, blob: bytes) -> DsdSourceCharacterization:
    return DsdSourceCharacterizer().characterize(_write(tmp_path, name, blob))


# --------------------------------------------------------------------------- #
# golden fixtures: explicit offsets, independent of the builders
# --------------------------------------------------------------------------- #


def golden_dsf_msbf() -> bytes:
    """DSF hand-laid out by specification offsets (little-endian).

    offsets:  0 DSD | 4 ckSize=28 | 12 fileSize | 20 meta=0 | 28 "fmt " |
    32 ckSize=52 | 40 version=1 | 44 formatId=0 | 48 chanType=2 | 52 chans=2 |
    56 bitsPerSecond=2822400 | 60 bitsPerSample=8 | 64 sampleCount=8192 |
    72 blockSize=4096 | 76 reserved=0 | 80 "data" | 84 ckSize=12+payload.
    """
    payload = bytes([0x69]) * (_DSF_BLOCK * 2)
    blob = bytearray(_DSF_FIXED_HEADER + len(payload))
    blob[0:4] = b"DSD "
    blob[4:12] = struct.pack("<Q", 28)
    blob[12:20] = struct.pack("<Q", len(blob))
    blob[20:28] = struct.pack("<Q", 0)
    blob[28:32] = b"fmt "
    blob[32:40] = struct.pack("<Q", 52)
    blob[40:44] = struct.pack("<I", 1)
    blob[44:48] = struct.pack("<I", 0)
    blob[48:52] = struct.pack("<I", 2)
    blob[52:56] = struct.pack("<I", 2)
    blob[56:60] = struct.pack("<I", 2_822_400)
    blob[60:64] = struct.pack("<I", 8)
    blob[64:72] = struct.pack("<Q", 8192)
    blob[72:76] = struct.pack("<I", _DSF_BLOCK)
    blob[76:80] = struct.pack("<I", 0)
    blob[80:84] = b"data"
    blob[84:92] = struct.pack("<Q", 12 + len(payload))
    blob[92:] = payload
    return bytes(blob)


def golden_dff_stereo() -> bytes:
    """DSDIFF hand-laid out by specification offsets (big-endian).

    FRM8 header: 0 "FRM8" | 4 ckSize=fileSize-12 | 12 "DSD " form type.
    Chunk header: 4-byte ID + 64-bit ckDataSize (12 bytes) for every chunk.
    PROP data is "SND " plus child chunks (FS, CHNL, CMPR).
    """
    payload = bytes([0x55]) * 4096
    fs = b"FS  " + struct.pack(">q", 4) + struct.pack(">I", 2_822_400)
    chan_ids = b"SLFT" + b"SRGT"
    chnl = (
        b"CHNL" + struct.pack(">q", 2 + len(chan_ids)) + struct.pack(">H", 2) + chan_ids
    )
    cmpr_data = b"DSD " + b"\x00" + b"\x00"  # 4-byte type + padded pascal name
    cmpr = b"CMPR" + struct.pack(">q", len(cmpr_data)) + cmpr_data
    prop_body = b"SND " + fs + chnl + cmpr
    prop = b"PROP" + struct.pack(">q", len(prop_body)) + prop_body
    fver = b"FVER" + struct.pack(">q", 4) + struct.pack(">I", 0x01050000)
    dsd = b"DSD " + struct.pack(">q", len(payload)) + payload
    body = fver + prop + dsd
    return b"FRM8" + struct.pack(">q", 4 + len(body)) + b"DSD " + body


def test_golden_fixture_hashes_are_pinned() -> None:
    assert (
        hashlib.sha256(golden_dsf_msbf()).hexdigest()
        == "5ef1237e7673db5a1ea579f86f80c721ae3d8ebe9b0618c7c988d3a8501d8e14"
    )
    assert (
        hashlib.sha256(golden_dff_stereo()).hexdigest()
        == "df5338c0b1b16c1385ff4ca51c0cf57fa99eadb764470081cec9c60560d25e58"
    )


def test_golden_dsf_proves_stereo_msb_planar_truth(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "golden.dsf", golden_dsf_msbf())
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.signal is not None
    assert result.signal.bit_rate_hz == 2_822_400
    assert result.signal.channels == 2
    assert result.signal.packing is DsdPacking.DSD_U8
    assert result.signal.bit_order is DsdBitOrder.MSBF
    assert result.signal.organization is DsdOrganization.PLANAR
    assert result.signal.layout == ("FL", "FR")
    assert result.signal.presentation_label == "DSD64"


def test_golden_dff_proves_stereo_msb_interleaved_truth(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "golden.dff", golden_dff_stereo())
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.signal is not None
    assert result.container_facts.container == "dff"
    assert result.signal.bit_rate_hz == 2_822_400
    assert result.signal.bit_order is DsdBitOrder.MSBF
    assert result.signal.organization is DsdOrganization.INTERLEAVED
    assert result.signal.layout == ("FL", "FR")


# --------------------------------------------------------------------------- #
# §211 unit algebra (unchanged authority)
# --------------------------------------------------------------------------- #


def test_dsd_rate_algebra_matches_the_canonical_table() -> None:
    cases = (
        (2_822_400, 352_800, 352_800, 176_400, 88_200, 176_400),
        (5_644_800, 705_600, 705_600, 352_800, 176_400, 352_800),
        (11_289_600, 1_411_200, 1_411_200, 705_600, 352_800, 705_600),
        (22_579_200, 2_822_400, 2_822_400, 1_411_200, 705_600, 1_411_200),
        (45_158_400, 5_644_800, 5_644_800, 2_822_400, 1_411_200, 2_822_400),
    )
    for bits, gst, u8, u16, u32, dop in cases:
        source = DsdSourceBitRate(bits)
        assert source_to_gst_rate(source).bytes_per_second_per_channel == gst
        assert (
            source_to_alsa_rate(source, AlsaDsdGrouping.DSD_U8).frames_per_second == u8
        )
        assert (
            source_to_alsa_rate(source, AlsaDsdGrouping.DSD_U16_LE).frames_per_second
            == u16
        )
        assert (
            source_to_alsa_rate(source, AlsaDsdGrouping.DSD_U32_LE).frames_per_second
            == u32
        )
        assert source_to_dop_rate(source).frames_per_second == dop


def test_source_bit_rate_requires_byte_addressable_positive_rates() -> None:
    for value in (0, -2_822_400, 2_822_401):
        with pytest.raises(ValueError):
            DsdSourceBitRate(value)


def test_dop_carrier_rate_requires_divisibility_by_16() -> None:
    source = DsdSourceBitRate(352_808)
    with pytest.raises(ValueError):
        _ = source.dop_carrier_frames_per_second


def test_alsa_grouping_widths_and_names() -> None:
    assert AlsaDsdGrouping.DSD_U8.bits_per_alsa_sample == 8
    assert AlsaDsdGrouping.DSD_U16_LE.bits_per_alsa_sample == 16
    assert AlsaDsdGrouping.DSD_U32_BE.bits_per_alsa_sample == 32
    assert AlsaDsdGrouping.DSD_U8.alsa_format_name == "SND_PCM_FORMAT_DSD_U8"
    assert AlsaDsdGrouping.DSD_U32_LE.alsa_format_name == "SND_PCM_FORMAT_DSD_U32_LE"


def test_alsa_transport_rate_rejects_indivisible_grouping() -> None:
    rate = source_to_alsa_rate(DsdSourceBitRate(4_000_000), AlsaDsdGrouping.DSD_U32_LE)
    assert rate.frames_per_second == 125_000
    with pytest.raises(ValueError):
        source_to_alsa_rate(DsdSourceBitRate(352_808), AlsaDsdGrouping.DSD_U32_LE)


# --------------------------------------------------------------------------- #
# DsdSignalFormat domain (bit order and organization are first-class)
# --------------------------------------------------------------------------- #


def _stereo_signal(**overrides) -> DsdSignalFormat:
    base = dict(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.MSBF,
        organization=DsdOrganization.PLANAR,
        layout=("FL", "FR"),
    )
    base.update(overrides)
    return DsdSignalFormat(**base)


def test_dsd_signal_format_is_immutable_and_unit_explicit() -> None:
    signal = _stereo_signal()
    assert signal.bit_rate_hz == 2_822_400
    assert signal.source_rate == DsdSourceBitRate(2_822_400)
    with pytest.raises(dataclasses.FrozenInstanceError):
        signal.bit_rate_hz = 5_644_800  # type: ignore[misc]


def test_bit_order_is_distinct_from_packing() -> None:
    lsbf = _stereo_signal(bit_order=DsdBitOrder.LSBF)
    msbf = _stereo_signal(bit_order=DsdBitOrder.MSBF)
    assert lsbf.packing is msbf.packing is DsdPacking.DSD_U8
    assert lsbf.bit_order is not msbf.bit_order
    assert [member.value for member in DsdBitOrder] == ["lsbf", "msbf"]
    assert [member.value for member in DsdOrganization] == [
        "planar",
        "interleaved",
    ]


def test_presentation_label_is_derived_not_stored() -> None:
    assert _stereo_signal(bit_rate_hz=2_822_400).presentation_label == "DSD64"
    assert _stereo_signal(bit_rate_hz=5_644_800).presentation_label == "DSD128"
    assert _stereo_signal(bit_rate_hz=11_289_600).presentation_label == "DSD256"
    assert _stereo_signal(bit_rate_hz=45_158_400).presentation_label == "DSD1024"
    assert _stereo_signal(bit_rate_hz=3_000_000).presentation_label is None
    field_names = {field.name for field in dataclasses.fields(DsdSignalFormat)}
    assert "label" not in field_names
    assert {
        "bit_rate_hz",
        "channels",
        "packing",
        "bit_order",
        "organization",
        "layout",
    } == field_names


def test_dsd_signal_format_validates_units_and_layout() -> None:
    for overrides in (
        {"bit_rate_hz": 0},
        {"bit_rate_hz": 2_822_401},
        {"channels": 0},
        {"layout": ("FL",)},
        {"channels": 2, "layout": ("FL", "FR", "FC")},
        {"layout": ("FL", "FL")},
        {"packing": "dsd_u8"},
        {"bit_order": "msbf"},
        {"organization": "planar"},
    ):
        with pytest.raises((ValueError, TypeError)):
            _stereo_signal(**overrides)


def test_no_pcm_fields_can_masquerade_in_the_dsd_type() -> None:
    signal = _stereo_signal()
    assert not hasattr(signal, "significant_bits")
    assert not hasattr(signal, "sample_rate_hz")
    assert not hasattr(signal, "transport_format")


def test_domain_module_imports_stay_pure() -> None:
    imports = {
        node.names[0].name if isinstance(node, ast.Import) else node.module
        for node in ast.walk(ast.parse(DOMAIN_MODULE.read_text(encoding="utf-8")))
        if isinstance(node, (ast.Import, ast.ImportFrom))
    }
    for name in imports:
        assert name is not None
        assert not name.startswith(
            ("PySide6", "gi", "Gst", "michi.infrastructure", "michi.application")
        )


# --------------------------------------------------------------------------- #
# DSF real-format behaviour
# --------------------------------------------------------------------------- #


def test_valid_builder_dsf_is_typed_as_dsd_source_truth(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "silence.dsf", build_dsf())
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.container_facts.container == "dsf"
    assert result.container_facts.nominal_dsd_bits_per_second_per_channel == 2_822_400
    assert result.elementary.encoding is ElementaryEncoding.DSD
    assert result.signal is not None
    assert result.signal.bit_order is DsdBitOrder.MSBF
    assert result.signal.organization is DsdOrganization.PLANAR


def test_dsf_bits_per_sample_1_is_lsb_first_not_unknown(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "lsbf.dsf", build_dsf(bits=1))
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.signal is not None
    assert result.signal.bit_order is DsdBitOrder.LSBF
    assert result.signal.organization is DsdOrganization.PLANAR


def test_dsf_bits_per_sample_8_is_msb_first(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "msbf.dsf", build_dsf(bits=8))
    assert result.signal is not None
    assert result.signal.bit_order is DsdBitOrder.MSBF


def test_dsf_payload_only_data_size_is_rejected(tmp_path: Path) -> None:
    # The pre-corrective assumption (size == payload) must never parse: the
    # real DSF data-chunk size includes its 12-byte header.
    payload = _dsf_payload(2, 8192, _DSF_BLOCK)
    blob = build_dsf(data_chunk_size=len(payload))
    result = _characterize(tmp_path, "wrong-size.dsf", blob)
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


def test_dsf_truth_follows_bytes_not_the_extension(tmp_path: Path) -> None:
    blob = build_dsf(rate=5_644_800)
    wrong_name = _characterize(tmp_path, "not-really.wav", blob)
    right_name = _characterize(tmp_path, "silence.dsf", blob)
    assert wrong_name.status is DsdSourceStatus.DSD_PROVEN
    assert wrong_name.signal == right_name.signal


def test_dsf_extension_with_invalid_bytes_is_not_dsd(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "fake.dsf", b"\x00" * 256)
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"
    assert result.signal is None


def test_truncated_dsf_sections_fail_closed(tmp_path: Path) -> None:
    for name, blob in (
        ("cut-dsd.dsf", build_dsf(truncate_to=20)),
        ("cut-fmt.dsf", build_dsf(truncate_to=60)),
        ("cut-data.dsf", build_dsf(truncate_to=_DSF_FIXED_HEADER - 4)),
    ):
        result = _characterize(tmp_path, name, blob)
        assert result.status is DsdSourceStatus.UNKNOWN
        assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"
        assert result.signal is None


def test_dsf_declared_payload_beyond_eof_fails_closed(tmp_path: Path) -> None:
    blob = build_dsf(truncate_to=_DSF_FIXED_HEADER + 64)
    result = _characterize(tmp_path, "short.dsf", blob)
    assert result.status is DsdSourceStatus.UNKNOWN


def test_dsf_file_size_mismatch_fails_closed(tmp_path: Path) -> None:
    result = _characterize(
        tmp_path, "size.dsf", build_dsf(file_size_override=10_000_000)
    )
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


def test_dsf_chunk_size_and_header_failures(tmp_path: Path) -> None:
    for name, blob in (
        ("bad-dsd-size.dsf", build_dsf(chunk_sizes=(30, 52))),
        ("bad-fmt-size.dsf", build_dsf(chunk_sizes=(28, 64))),
    ):
        result = _characterize(tmp_path, name, blob)
        assert result.status is DsdSourceStatus.UNKNOWN


def test_dsf_unknown_format_id_is_unknown_not_compressed(tmp_path: Path) -> None:
    for format_id in (1, 2, 0xFF):
        result = _characterize(
            tmp_path, f"id{format_id}.dsf", build_dsf(format_id=format_id)
        )
        assert result.status is DsdSourceStatus.UNKNOWN
        assert result.elementary.encoding is ElementaryEncoding.UNKNOWN
        assert result.failure_code == "SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN"
        assert result.signal is None


def test_dsf_invalid_rate_is_a_unit_failure(tmp_path: Path) -> None:
    for rate in (0, 2_822_401):
        result = _characterize(tmp_path, "weird.dsf", build_dsf(rate=rate))
        assert result.status is DsdSourceStatus.UNKNOWN
        assert result.failure_code == "SOURCE_DSD_RATE_UNIT_INVALID"


def test_dsf_invalid_bits_and_block_fail_closed(tmp_path: Path) -> None:
    for name, blob in (
        ("bits.dsf", build_dsf(bits=4)),
        ("block0.dsf", build_dsf(block_size=0, payload=b"\x69" * 8192)),
        ("block2048.dsf", build_dsf(block_size=2048)),
        ("count.dsf", build_dsf(sample_count=0, payload=b"")),
    ):
        result = _characterize(tmp_path, name, blob)
        assert result.status is DsdSourceStatus.UNKNOWN
        assert result.failure_code == "SOURCE_DSD_GROUPING_UNKNOWN"


def test_dsf_zero_file_size_is_not_accepted(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "zero-size.dsf", build_dsf(file_size_override=0))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


@pytest.mark.parametrize(
    "chan_type,channels,layout",
    (
        (1, 1, ("FC",)),
        (2, 2, ("FL", "FR")),
        (3, 3, ("FL", "FR", "FC")),
        (4, 4, ("FL", "FR", "BL", "BR")),
        # Type 5 follows WavPack's DSD channel mask (FL+FR+FC+LFE); FFmpeg's
        # generic 4POINT0 maps the same type to FL+FR+FC+BC and diverges.
        (5, 4, ("FL", "FR", "FC", "LFE")),
        (6, 5, ("FL", "FR", "FC", "BL", "BR")),
        (7, 6, ("FL", "FR", "FC", "LFE", "BL", "BR")),
    ),
)
def test_dsf_standard_channel_layouts(
    tmp_path: Path, chan_type: int, channels: int, layout: tuple[str, ...]
) -> None:
    result = _characterize(
        tmp_path, f"t{chan_type}.dsf", build_dsf(chan_type=chan_type, channels=channels)
    )
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.signal is not None
    assert result.signal.layout == layout


def test_dsf_channel_type_count_contradiction_fails_closed(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "contra.dsf", build_dsf(chan_type=3, channels=2))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN"


def test_dsf_reserved_channel_type_fails_closed(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "res.dsf", build_dsf(chan_type=8, channels=2))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN"


def test_dsf_legal_trailing_metadata_is_not_payload_corruption(
    tmp_path: Path,
) -> None:
    tail = b"ID3\x04\x00\x00\x00\x00\x00\x00"
    result = _characterize(tmp_path, "meta.dsf", build_dsf(meta_tail=tail))
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.signal is not None


def test_dsf_metadata_pointer_inside_payload_fails_closed(tmp_path: Path) -> None:
    result = _characterize(
        tmp_path, "badmeta.dsf", build_dsf(meta_tail=b"ID3xxxxx", meta_pointer=10)
    )
    assert result.status is DsdSourceStatus.UNKNOWN


def test_dsf_hostile_declared_sizes_fail_closed(tmp_path: Path) -> None:
    blob = build_dsf(data_chunk_size=0xFFFFFFFFFFFFFFFF)
    result = _characterize(tmp_path, "hostile.dsf", blob)
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.signal is None


# --------------------------------------------------------------------------- #
# DSDIFF/DFF real-format behaviour
# --------------------------------------------------------------------------- #


def test_valid_builder_dff_is_typed_as_dsd_source_truth(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "silence.dff", build_dff())
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.container_facts.container == "dff"
    assert result.signal is not None
    assert result.signal.bit_order is DsdBitOrder.MSBF
    assert result.signal.organization is DsdOrganization.INTERLEAVED
    assert result.signal.layout == ("FL", "FR")


def test_legacy_8byte_header_dff_is_rejected(tmp_path: Path) -> None:
    # The pre-corrective 4+4 header model must not parse as real DSDIFF.
    result = _characterize(tmp_path, "legacy.dff", build_legacy_8byte_header_dff())
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.signal is None


def test_dff_form_size_mismatch_fails_closed(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "size.dff", build_dff(form_size_override=123_456))
    assert result.status is DsdSourceStatus.UNKNOWN


def test_dff_unset_form_size_sentinel_is_accepted(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "unset.dff", build_dff(form_size_override=-1))
    assert result.status is DsdSourceStatus.DSD_PROVEN


def test_dff_dst_compression_is_unsupported(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "dst.dff", build_dff(compression=b"DST "))
    assert result.status is DsdSourceStatus.UNSUPPORTED_ENCODING
    assert result.elementary.encoding is ElementaryEncoding.COMPRESSED
    assert result.signal is None


def test_dff_missing_compression_is_unknown_not_unsupported(
    tmp_path: Path,
) -> None:
    result = _characterize(tmp_path, "nocmpr.dff", build_dff(compression=None))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN"
    assert result.signal is None


def test_dff_truncated_and_oversized_chunks_fail_closed(tmp_path: Path) -> None:
    for name, blob in (
        ("cut.dff", build_dff(truncate_to=20)),
        ("cut-size.dff", build_dff(truncate_to=4)),
        ("huge.dff", build_dff()[:-100]),
    ):
        result = _characterize(tmp_path, name, blob)
        assert result.status is DsdSourceStatus.UNKNOWN
        assert result.signal is None


def test_dff_invalid_rate_is_a_unit_failure(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "rate.dff", build_dff(rate=1_000_001))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_RATE_UNIT_INVALID"


def test_dff_prop_child_beyond_boundary_fails_closed(tmp_path: Path) -> None:
    child = b"FS  " + struct.pack(">q", 999) + b"\x00" * 8
    result = _characterize(tmp_path, "boundary.dff", build_dff(extra_prop_child=child))
    assert result.status is DsdSourceStatus.UNKNOWN


def test_dff_zero_size_prop_child_fails_closed(tmp_path: Path) -> None:
    child = b"FS  " + struct.pack(">q", 0)
    result = _characterize(tmp_path, "zero.dff", build_dff(extra_prop_child=child))
    assert result.status is DsdSourceStatus.UNKNOWN


def test_dff_unknown_child_chunks_are_skipped_safely(tmp_path: Path) -> None:
    unknown_prop = b"XPRO" + struct.pack(">q", 3) + b"abc\x00"  # odd -> padded
    unknown_top = b"XTRA" + struct.pack(">q", 5) + b"12345\x00"
    result = _characterize(
        tmp_path,
        "kids.dff",
        build_dff(extra_prop_child=unknown_prop, extra_top_child=unknown_top),
    )
    assert result.status is DsdSourceStatus.DSD_PROVEN


def test_dff_hostile_prop_size_fails_closed_without_allocation(
    tmp_path: Path,
) -> None:
    blob = build_dff()
    prop_offset = blob.find(b"PROP")
    assert prop_offset > 0
    blob = (
        blob[: prop_offset + 4]
        + struct.pack(">q", _DFF_MAX_PROP_CAP + 1)
        + blob[prop_offset + 12 :]
    )
    result = _characterize(tmp_path, "hostile-prop.dff", blob)
    assert result.status is DsdSourceStatus.UNKNOWN


@pytest.mark.parametrize(
    "channel_ids,layout",
    (
        ((b"SLFT", b"SRGT"), ("FL", "FR")),
        ((b"MLFT", b"MRGT"), ("FL", "FR")),
        (
            (b"MLFT", b"MRGT", b"C   ", b"LFE ", b"LS  ", b"RS  "),
            ("FL", "FR", "FC", "LFE", "SL", "SR"),
        ),
    ),
)
def test_dff_standard_channel_ids(
    tmp_path: Path, channel_ids: tuple[bytes, ...], layout: tuple[str, ...]
) -> None:
    result = _characterize(tmp_path, "ids.dff", build_dff(channel_ids=channel_ids))
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.signal is not None
    assert result.signal.layout == layout


def test_dff_unknown_channel_id_fails_closed(tmp_path: Path) -> None:
    result = _characterize(
        tmp_path, "unknown-id.dff", build_dff(channel_ids=(b"XX01", b"XX02"))
    )
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN"


def test_dff_duplicate_semantic_position_fails_closed(tmp_path: Path) -> None:
    result = _characterize(
        tmp_path, "dup.dff", build_dff(channel_ids=(b"SLFT", b"MLFT"))
    )
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN"


def test_dff_channel_count_mismatch_fails_closed(tmp_path: Path) -> None:
    # CHNL declares 3 channels but the chunk only carries room for 2 ids:
    # structurally inconsistent, so the container itself fails closed.
    result = _characterize(
        tmp_path,
        "count.dff",
        build_dff(channel_ids=(b"SLFT", b"SRGT"), declared_channels=3),
    )
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"
    assert result.signal is None


def test_dff_requires_fver_first(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "no-fver-first.dff", build_dff(fver_first=False))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


def test_dff_fver_version_is_validated(tmp_path: Path) -> None:
    result = _characterize(
        tmp_path, "bad-version.dff", build_dff(fver_version=0x01040000)
    )
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


def test_dff_duplicate_required_chunks_fail_closed(tmp_path: Path) -> None:
    duplicate_fver = _dff_chunk(b"FVER", struct.pack(">I", 0x01050000))
    for name, blob in (
        ("dup-fver.dff", build_dff(extra_top_child=duplicate_fver)),
        ("dup-prop.dff", build_dff(duplicate_prop=True)),
    ):
        result = _characterize(tmp_path, name, blob)
        assert result.status is DsdSourceStatus.UNKNOWN
        assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


def test_dff_prop_type_must_be_snd(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "bad-prop-type.dff", build_dff(prop_type=b"XXXX"))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


def test_dff_cmpr_name_structure_is_validated(tmp_path: Path) -> None:
    for name, payload in (
        ("cmpr-short.dff", b"DSD "),  # no Pascal name at all
        ("cmpr-overrun.dff", b"DSD \x09ab"),  # name length overruns the chunk
        ("cmpr-slack.dff", b"DSD \x00\x00\x00\x00"),  # >1 padding byte
    ):
        result = _characterize(tmp_path, name, build_dff(cmpr_payload_override=payload))
        assert result.status is DsdSourceStatus.UNKNOWN
        assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


def test_dff_top_level_dst_evidence_is_never_raw(tmp_path: Path) -> None:
    # A DST index chunk under an uncompressed CMPR declaration is
    # contradictory structure: fail closed, never pick a side.
    contradiction = _characterize(tmp_path, "dst-index.dff", build_dff(dsti=True))
    assert contradiction.status is DsdSourceStatus.UNKNOWN
    assert contradiction.signal is None

    # Positively DST-compressed shapes (CMPR declares DST): UNSUPPORTED.
    for name, blob in (
        ("dst-data.dff", build_dff(dst=True, compression=b"DST ")),
        ("dst-index-cmpr.dff", build_dff(dsti=True, compression=b"DST ")),
    ):
        result = _characterize(tmp_path, name, blob)
        assert result.status is DsdSourceStatus.UNSUPPORTED_ENCODING
        assert result.elementary.encoding is ElementaryEncoding.COMPRESSED
        assert result.container_facts.container == "dff"
        assert result.signal is None


def test_dff_non_normative_channel_order_fails_closed(tmp_path: Path) -> None:
    result = _characterize(
        tmp_path, "reversed.dff", build_dff(channel_ids=(b"SRGT", b"SLFT"))
    )
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN"


def test_dff_missing_prop_can_never_prove_dsd(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "no-prop.dff", build_dff(omit_prop=True))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.signal is None


def test_dff_missing_required_prop_children_fail_closed(tmp_path: Path) -> None:
    fs = _dff_chunk(b"FS  ", struct.pack(">I", 2_822_400))
    chnl = _dff_chunk(b"CHNL", struct.pack(">H", 2) + b"SLFT" + b"SRGT")
    cmpr_payload = b"DSD " + b"\x00" + b"\x00"
    cmpr = _dff_chunk(b"CMPR", cmpr_payload)
    for name, body in (
        ("no-fs.dff", b"SND " + chnl + cmpr),
        ("no-chnl.dff", b"SND " + fs + cmpr),
        ("no-cmpr.dff", b"SND " + fs + chnl),
    ):
        result = _characterize(tmp_path, name, build_dff(prop_body_override=body))
        assert result.status is DsdSourceStatus.UNKNOWN
        assert result.signal is None


def test_dff_duplicate_prop_children_fail_closed(tmp_path: Path) -> None:
    fs = _dff_chunk(b"FS  ", struct.pack(">I", 2_822_400))
    chnl = _dff_chunk(b"CHNL", struct.pack(">H", 2) + b"SLFT" + b"SRGT")
    cmpr_payload = b"DSD " + b"\x00" + b"\x00"
    cmpr = _dff_chunk(b"CMPR", cmpr_payload)
    for name, body in (
        ("dup-fs.dff", b"SND " + fs + fs + chnl + cmpr),
        ("dup-chnl.dff", b"SND " + fs + chnl + chnl + cmpr),
        ("dup-cmpr.dff", b"SND " + fs + chnl + cmpr + cmpr),
    ):
        result = _characterize(tmp_path, name, build_dff(prop_body_override=body))
        assert result.status is DsdSourceStatus.UNKNOWN
        assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


def test_dff_missing_or_duplicate_dsd_audio_chunk_fail_closed(
    tmp_path: Path,
) -> None:
    missing = _characterize(tmp_path, "no-data.dff", build_dff(omit_data=True))
    assert missing.status is DsdSourceStatus.UNKNOWN
    assert missing.signal is None

    duplicate = _characterize(
        tmp_path,
        "two-data.dff",
        build_dff(extra_top_child=_dff_chunk(b"DSD ", bytes([0x55]) * 512)),
    )
    assert duplicate.status is DsdSourceStatus.UNKNOWN
    assert duplicate.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


def test_dff_compression_and_payload_contradictions_fail_closed(
    tmp_path: Path,
) -> None:
    # CMPR declares uncompressed while a real DST chunk carries the audio:
    # contradictory structure, never silently resolved.
    contradiction = _characterize(tmp_path, "cmpr-dsd-dst.dff", build_dff(dst=True))
    assert contradiction.status is DsdSourceStatus.UNKNOWN
    assert contradiction.failure_code == "SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN"
    assert contradiction.signal is None

    # CMPR declares DST while a raw DSD data chunk is present: the positive
    # compression declaration governs (UNSUPPORTED), never a false raw proof.
    declared_dst = _characterize(
        tmp_path, "cmpr-dst-raw.dff", build_dff(compression=b"DST ")
    )
    assert declared_dst.status is DsdSourceStatus.UNSUPPORTED_ENCODING
    assert declared_dst.signal is None

    # Unknown compression codecs are positively identified as non-raw.
    unknown_codec = _characterize(
        tmp_path,
        "cmpr-unknown.dff",
        build_dff(compression=b"XYZ!", cmpr_payload_override=b"XYZ!\x00\x00"),
    )
    assert unknown_codec.status is DsdSourceStatus.UNSUPPORTED_ENCODING
    assert unknown_codec.signal is None


def test_dff_truth_follows_bytes_not_the_extension(tmp_path: Path) -> None:
    blob = build_dff()
    wrong_name = _characterize(tmp_path, "not-really.dff2", blob)
    right_name = _characterize(tmp_path, "silence.dff", blob)
    assert wrong_name.status is DsdSourceStatus.DSD_PROVEN
    assert wrong_name.signal == right_name.signal


# --------------------------------------------------------------------------- #
# failure semantics, evidence identity, TOCTOU
# --------------------------------------------------------------------------- #


def test_missing_file_is_transient_unknown_not_unsupported(tmp_path: Path) -> None:
    result = DsdSourceCharacterizer().characterize(tmp_path / "gone.dsf")
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_TRANSIENT_UNAVAILABLE"
    assert result.elementary.encoding is ElementaryEncoding.UNKNOWN
    assert result.signal is None


def test_directory_path_is_transient_unknown(tmp_path: Path) -> None:
    result = DsdSourceCharacterizer().characterize(tmp_path)
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_TRANSIENT_UNAVAILABLE"


def test_non_regular_file_is_transient_unknown() -> None:
    devnull = Path("/dev/null")
    if not devnull.exists():
        pytest.skip("platform without /dev/null")
    result = DsdSourceCharacterizer().characterize(devnull)
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_TRANSIENT_UNAVAILABLE"


def test_io_error_is_unknown_and_never_a_negative_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, "x.dsf", build_dsf())
    real_open = Path.open

    def failing_open(self, *args, **kwargs):
        if self == path:
            raise OSError("device busy")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    result = DsdSourceCharacterizer().characterize(path)
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_TRANSIENT_UNAVAILABLE"


def test_source_change_during_characterization_is_transient(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, "changing.dsf", build_dsf())
    real_fstat = os.fstat
    calls = {"count": 0}

    class _Stat:
        def __init__(self, base, size):
            self.st_mode = base.st_mode
            self.st_size = size
            self.st_mtime_ns = base.st_mtime_ns
            self.st_ino = base.st_ino

    def drifting_fstat(fd):
        base = real_fstat(fd)
        calls["count"] += 1
        if calls["count"] >= 2:
            return _Stat(base, base.st_size + 1)
        return base

    monkeypatch.setattr(os, "fstat", drifting_fstat)
    result = DsdSourceCharacterizer().characterize(path)
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_TRANSIENT_UNAVAILABLE"


def test_characterization_is_deterministic(tmp_path: Path) -> None:
    blob = build_dsf()
    first = _characterize(tmp_path, "a.dsf", blob)
    second = _characterize(tmp_path, "a.dsf", blob)
    assert first == second


def test_characterization_never_reads_the_whole_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    large_payload = bytes([0x69]) * (1024 * 1024)
    blob = build_dsf(sample_count=(1024 * 1024 // 2) * 8, payload=large_payload)
    path = _write(tmp_path, "large.dsf", blob)
    read_bytes = {"total": 0}
    real_open = Path.open

    class _CountingReader:
        def __init__(self, handle):
            self._handle = handle

        def read(self, size=-1):
            data = self._handle.read(size)
            read_bytes["total"] += len(data)
            return data

        def seek(self, *args):
            return self._handle.seek(*args)

        def fileno(self):
            return self._handle.fileno()

        def close(self):
            return self._handle.close()

    def counting_open(self, *args, **kwargs):
        return _CountingReader(real_open(self, *args, **kwargs))

    monkeypatch.setattr(Path, "open", counting_open)
    result = DsdSourceCharacterizer().characterize(path)
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert read_bytes["total"] < len(large_payload)


def test_same_basename_different_structures_have_distinct_evidence_refs(
    tmp_path: Path,
) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    first = _characterize(left, "same.dsf", build_dsf(rate=2_822_400))
    second = _characterize(right, "same.dsf", build_dsf(rate=5_644_800))
    assert first.status is DsdSourceStatus.DSD_PROVEN
    assert second.status is DsdSourceStatus.DSD_PROVEN
    assert first.container_facts.evidence_ref != second.container_facts.evidence_ref
    assert first.evidence_refs[0] != second.evidence_refs[0]


def test_characterization_exposes_elementary_and_container_separately(
    tmp_path: Path,
) -> None:
    result = _characterize(tmp_path, "s.dsf", golden_dsf_msbf())
    assert isinstance(result.container_facts, ContainerAudioFacts)
    assert isinstance(result.elementary, ElementaryStreamObservation)
    assert result.elementary.provider == "static-parser"
    assert result.elementary.evidence_kind is EvidenceKind.STATIC_FILE_STRUCTURE
    assert result.elementary.media_type == "audio/x-dsd"
    assert ("format", "dsd_u8") in result.elementary.structure_fields
    assert result.evidence_refs
    assert all(ref for ref in result.evidence_refs)
    assert result.signal is not None
    assert "structural" in result.container_facts.evidence_ref


def test_static_evidence_is_not_runtime_gst_caps(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "s.dsf", golden_dsf_msbf())
    # The static parser can only ever emit STATIC_FILE_STRUCTURE evidence and
    # must not expose runtime-gst-caps-shaped fields.
    assert result.elementary.evidence_kind is EvidenceKind.STATIC_FILE_STRUCTURE
    assert EvidenceKind.RUNTIME_GST_CAPS.value == "runtime_gst_caps"
    for forbidden in (
        "caps_media_type",
        "caps_fields",
        "runtime_branch",
        "native_branch_available",
        "dac_capability",
    ):
        assert not hasattr(result.elementary, forbidden), forbidden
        assert not hasattr(result, forbidden), forbidden
    # The type can represent the reserved runtime evidence kind, but this
    # module never constructs it: a consumer must discriminate explicitly.
    observation = ElementaryStreamObservation(
        encoding=ElementaryEncoding.DSD,
        evidence_kind=EvidenceKind.RUNTIME_GST_CAPS,
        media_type=None,
        structure_fields=(),
        provider="runtime-probe",
        evidence_ref="runtime:probe",
    )
    assert observation.evidence_kind is EvidenceKind.RUNTIME_GST_CAPS
    source = CHARACTERIZER_MODULE.read_text(encoding="utf-8")
    assert "EvidenceKind.RUNTIME_GST_CAPS" not in source


def test_structural_ref_schema_is_strengthened() -> None:
    from michi.application.dsd_source_characterizer import _structural_ref

    ref = _structural_ref("dsf", b"abc", 3)
    assert ref.startswith("dsf:structural:v2:")
    # Audit-grade evidence uses the FULL digest; truncation is presentation-only.
    assert len(ref.split(":")[-1]) == 64
    assert ref == _structural_ref("dsf", b"abc", 3)
    # Same size, different structural bytes.
    assert ref != _structural_ref("dsf", b"abd", 3)
    # Same structural prefix, different later bytes.
    assert ref != _structural_ref("dsf", b"abcd", 3)
    assert ref != _structural_ref("dsf", b"abc", 4)
    assert ref != _structural_ref("dff", b"abc", 3)


def test_dop_rate_math_does_not_construct_framing() -> None:
    rate = source_to_dop_rate(DsdSourceBitRate(2_822_400))
    assert isinstance(rate, DopCarrierRate)
    assert not hasattr(rate, "marker")
    assert not hasattr(rate, "pack")


# --------------------------------------------------------------------------- #
# independence / no output claims / optional external validation
# --------------------------------------------------------------------------- #


def test_characterizer_module_never_touches_gstreamer_alsa_or_output() -> None:
    source = CHARACTERIZER_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "import gi",
        "gi.repository",
        "Gst",
        "alsasink",
        "set_state",
        "playbin",
        "playback_service",
        "output_session",
        "bootstrap",
    ):
        assert forbidden not in source, forbidden


def test_dff_hostile_channel_count_never_allocates(tmp_path: Path) -> None:
    fs = _dff_chunk(b"FS  ", struct.pack(">I", 2_822_400))
    hostile_chnl = _dff_chunk(b"CHNL", struct.pack(">H", 0xFFFF))  # count 65535
    cmpr = _dff_chunk(b"CMPR", b"DSD " + b"\x00" + b"\x00")
    result = _characterize(
        tmp_path,
        "hostile-chnl.dff",
        build_dff(prop_body_override=b"SND " + fs + hostile_chnl + cmpr),
    )
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


@pytest.mark.skipif(
    shutil.which("ffprobe") is None,
    reason="ffprobe not installed (optional independent cross-check)",
)
def test_golden_dsf_is_recognized_by_an_independent_validator(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path, "golden.dsf", golden_dsf_msbf())
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=format_name", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "dsf" in completed.stdout


@pytest.mark.skipif(
    shutil.which("wavpack") is None,
    reason="wavpack not installed (optional independent DFF cross-check)",
)
def test_golden_dff_is_recognized_by_an_independent_validator(
    tmp_path: Path,
) -> None:
    # WavPack's own DSDIFF reader imports the container end to end; a zero exit
    # status is independent proof that the structural layout is real.
    for name, data in (
        ("golden.dff", golden_dff_stereo()),
        ("builder.dff", build_dff()),
    ):
        path = _write(tmp_path, name, data)
        completed = subprocess.run(
            ["wavpack", "-y", "-q", str(path), "-o", str(tmp_path / f"{name}.wv")],
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
