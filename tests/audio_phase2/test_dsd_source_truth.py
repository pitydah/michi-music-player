"""AP2-F07 — DSD source truth: units, packing, DSF/DFF characterization.

Contract anchors: R11-F07 (DsdSignalFormat with explicit units; DSD64 labels
derived, never stored; no PCM field reuse), §211 (DSD rate algebra: source
bits/s per channel vs Gst bytes/s vs ALSA grouping vs DoP carrier frames),
§212 (container facts, elementary stream truth and decoded truth are separate;
unknown != unsupported).

The characterizer is a deterministic static parser: it never starts a
GStreamer pipeline, never touches ALSA and makes no output-capability claim.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import struct
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
)
from michi.domain.dsd_signal import (
    AlsaDsdGrouping,
    DopCarrierRate,
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


# --------------------------------------------------------------------------- #
# deterministic synthetic fixtures (no copyrighted audio, structure-only)
# --------------------------------------------------------------------------- #

_DSF_SILENCE = bytes([0x69]) * 4096  # DSD idle pattern (structural payload)


def build_dsf(
    *,
    rate: int = 2_822_400,
    channel_type: int = 2,
    channels: int = 2,
    bits_per_sample: int = 8,
    sample_count: int = 8192,
    block_size: int = 4096,
    format_id: int = 0,
    payload: bytes | None = None,
    truncate_to: int | None = None,
    bad_magic: bool = False,
) -> bytes:
    payload = payload if payload is not None else _DSF_SILENCE
    data_size = len(payload)
    fmt = (
        (b"fmt " if not bad_magic else b"fmtX")
        + struct.pack("<Q", 52)
        + struct.pack("<I", 1)  # format version
        + struct.pack("<I", format_id)
        + struct.pack("<I", channel_type)
        + struct.pack("<I", channels)
        + struct.pack("<I", rate)
        + struct.pack("<I", bits_per_sample)
        + struct.pack("<Q", sample_count)
        + struct.pack("<I", block_size)
        + struct.pack("<I", 0)  # reserved
    )
    header_size = 28 + 52 + 12
    file_size = header_size + data_size
    dsd = (
        (b"DSD " if not bad_magic else b"DSX ")
        + struct.pack("<Q", 28)
        + struct.pack("<Q", file_size)
        + struct.pack("<Q", 0)  # metadata pointer
    )
    data = b"data" + struct.pack("<Q", data_size) + payload
    blob = dsd + fmt + data
    if truncate_to is not None:
        blob = blob[:truncate_to]
    return blob


def _dff_chunk(chunk_id: bytes, payload: bytes) -> bytes:
    blob = chunk_id + struct.pack(">I", len(payload)) + payload
    if len(payload) % 2:
        blob += b"\x00"
    return blob


def build_dff(
    *,
    rate: int = 2_822_400,
    channel_ids: tuple[bytes, ...] = (b"SLFT", b"SRGT"),
    compression: bytes | None = b"DSD ",
    payload: bytes | None = None,
    truncate_to: int | None = None,
    bad_magic: bool = False,
) -> bytes:
    payload = payload if payload is not None else _DSF_SILENCE
    fs = _dff_chunk(b"FS  ", struct.pack(">I", rate))
    chnl = _dff_chunk(
        b"CHNL", struct.pack(">H", len(channel_ids)) + b"".join(channel_ids)
    )
    cmpr = (
        _dff_chunk(b"CMPR", compression + b"\x00") if compression is not None else b""
    )
    prop_body = b"SND " + fs + chnl + cmpr
    prop = _dff_chunk(b"PROP", prop_body)
    fver = _dff_chunk(b"FVER", struct.pack(">I", 0x01050000))
    dsd_data = _dff_chunk(b"DSD ", payload)
    body = fver + prop + dsd_data
    form = (b"FRM8" if not bad_magic else b"FRMX") + struct.pack(">I", 4 + len(body))
    blob = form + b"DSD " + body
    if truncate_to is not None:
        blob = blob[:truncate_to]
    return blob


def _write(tmp_path: Path, name: str, blob: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(blob)
    return path


def _characterize(tmp_path: Path, name: str, blob: bytes) -> DsdSourceCharacterization:
    return DsdSourceCharacterizer().characterize(_write(tmp_path, name, blob))


# --------------------------------------------------------------------------- #
# §211 unit algebra
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
    with pytest.raises(ValueError):
        DsdSourceBitRate(0)
    with pytest.raises(ValueError):
        DsdSourceBitRate(-2_822_400)
    with pytest.raises(ValueError):
        DsdSourceBitRate(2_822_401)  # not byte-addressable


def test_dop_carrier_rate_requires_divisibility_by_16() -> None:
    source = DsdSourceBitRate(352_808)  # byte-addressable, but not divisible by 16
    with pytest.raises(ValueError):
        _ = source.dop_carrier_frames_per_second


def test_alsa_grouping_widths_and_names() -> None:
    assert AlsaDsdGrouping.DSD_U8.bits_per_alsa_sample == 8
    assert AlsaDsdGrouping.DSD_U16_LE.bits_per_alsa_sample == 16
    assert AlsaDsdGrouping.DSD_U32_BE.bits_per_alsa_sample == 32
    assert AlsaDsdGrouping.DSD_U8.alsa_format_name == "SND_PCM_FORMAT_DSD_U8"
    assert AlsaDsdGrouping.DSD_U32_LE.alsa_format_name == "SND_PCM_FORMAT_DSD_U32_LE"


def test_alsa_transport_rate_rejects_indivisible_grouping() -> None:
    source = DsdSourceBitRate(4_000_000)  # divisible by 32
    rate = source_to_alsa_rate(source, AlsaDsdGrouping.DSD_U32_LE)
    assert rate.frames_per_second == 125_000
    with pytest.raises(ValueError):
        # byte-addressable but not divisible by the 32-bit grouping width
        source_to_alsa_rate(DsdSourceBitRate(352_808), AlsaDsdGrouping.DSD_U32_LE)


# --------------------------------------------------------------------------- #
# DsdSignalFormat domain
# --------------------------------------------------------------------------- #


def _stereo_signal(**overrides) -> DsdSignalFormat:
    base = dict(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=DsdPacking.DSD_U8,
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


def test_presentation_label_is_derived_not_stored() -> None:
    assert _stereo_signal(bit_rate_hz=2_822_400).presentation_label == "DSD64"
    assert _stereo_signal(bit_rate_hz=5_644_800).presentation_label == "DSD128"
    assert _stereo_signal(bit_rate_hz=11_289_600).presentation_label == "DSD256"
    assert _stereo_signal(bit_rate_hz=3_000_000).presentation_label is None
    field_names = {field.name for field in dataclasses.fields(DsdSignalFormat)}
    assert "label" not in field_names
    assert {"bit_rate_hz", "channels", "packing", "layout"} == field_names


def test_dsd_signal_format_validates_units_and_layout() -> None:
    with pytest.raises(ValueError):
        _stereo_signal(bit_rate_hz=0)
    with pytest.raises(ValueError):
        _stereo_signal(bit_rate_hz=2_822_401)  # not byte-addressable
    with pytest.raises(ValueError):
        _stereo_signal(channels=0)
    with pytest.raises(ValueError):
        _stereo_signal(layout=("FL",))
    with pytest.raises(ValueError):
        _stereo_signal(channels=2, layout=("FL", "FR", "FC"))
    with pytest.raises(ValueError):
        _stereo_signal(layout=("FL", "FL"))
    with pytest.raises(TypeError):
        _stereo_signal(packing="dsd_u8")


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
# DSF characterization
# --------------------------------------------------------------------------- #


def test_valid_dsf_is_typed_as_dsd_source_truth(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "silence.dsf", build_dsf())
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.failure_code is None
    assert result.container_facts.container == "dsf"
    assert result.container_facts.nominal_dsd_bits_per_second_per_channel == 2_822_400
    assert result.elementary.encoding is ElementaryEncoding.DSD
    assert result.signal is not None
    assert result.signal.bit_rate_hz == 2_822_400
    assert result.signal.channels == 2
    assert result.signal.packing is DsdPacking.DSD_U8
    assert result.signal.layout == ("FL", "FR")
    assert result.signal.presentation_label == "DSD64"


def test_dsf_truth_follows_bytes_not_the_extension(tmp_path: Path) -> None:
    blob = build_dsf(rate=5_644_800)
    wrong_name = _characterize(tmp_path, "not-really.wav", blob)
    right_name = _characterize(tmp_path, "silence.dsf", blob)
    assert wrong_name.status is DsdSourceStatus.DSD_PROVEN
    assert wrong_name.signal == right_name.signal


def test_dsf_extension_with_invalid_bytes_is_not_dsd(tmp_path: Path) -> None:
    result = _characterize(
        tmp_path, "fake.dsf", bytes(hashlib.sha256(b"nope").digest())
    )
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"
    assert result.signal is None


def test_truncated_dsf_fails_closed(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "cut.dsf", build_dsf(truncate_to=40))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"
    assert result.signal is None


def test_dsf_unsupported_format_id_is_not_proven(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "dstish.dsf", build_dsf(format_id=1))
    assert result.status is DsdSourceStatus.UNSUPPORTED_ENCODING
    assert result.failure_code == "SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN"
    assert result.signal is None


def test_dsf_unknown_grouping_fails_closed(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "bit1.dsf", build_dsf(bits_per_sample=1))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_GROUPING_UNKNOWN"
    assert result.signal is None


def test_dsf_invalid_rate_is_a_unit_failure(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "weird.dsf", build_dsf(rate=2_822_401))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_RATE_UNIT_INVALID"


def test_dsf_unknown_channel_type_fails_closed(tmp_path: Path) -> None:
    result = _characterize(
        tmp_path, "surround.dsf", build_dsf(channel_type=7, channels=6)
    )
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN"
    assert result.signal is None


def test_dsf_mono_layout_is_supported(tmp_path: Path) -> None:
    result = _characterize(
        tmp_path,
        "mono.dsf",
        build_dsf(channel_type=1, channels=1, payload=b"\x69" * 4096),
    )
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.signal is not None
    assert result.signal.layout == ("FC",)


# --------------------------------------------------------------------------- #
# DFF characterization
# --------------------------------------------------------------------------- #


def test_valid_dff_is_typed_as_dsd_source_truth(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "silence.dff", build_dff())
    assert result.status is DsdSourceStatus.DSD_PROVEN
    assert result.container_facts.container == "dff"
    assert result.elementary.encoding is ElementaryEncoding.DSD
    assert result.signal is not None
    assert result.signal.bit_rate_hz == 2_822_400
    assert result.signal.layout == ("FL", "FR")


def test_dst_compressed_dff_is_unsupported_not_unknown(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "compressed.dff", build_dff(compression=b"DST "))
    assert result.status is DsdSourceStatus.UNSUPPORTED_ENCODING
    assert result.failure_code == "SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN"
    assert result.container_facts.container == "dff"
    assert result.elementary.encoding is ElementaryEncoding.COMPRESSED
    assert result.signal is None


def test_dff_missing_compression_fails_closed(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "nocmpr.dff", build_dff(compression=None))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN"
    assert result.signal is None


def test_truncated_dff_fails_closed(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "cut.dff", build_dff(truncate_to=20))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CONTAINER_UNKNOWN"


def test_dff_invalid_rate_is_a_unit_failure(tmp_path: Path) -> None:
    result = _characterize(tmp_path, "weird.dff", build_dff(rate=1_000_001))
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_RATE_UNIT_INVALID"


def test_dff_unknown_channel_ids_fail_closed(tmp_path: Path) -> None:
    result = _characterize(
        tmp_path, "odd.dff", build_dff(channel_ids=(b"XX01", b"XX02"))
    )
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN"


# --------------------------------------------------------------------------- #
# failure semantics
# --------------------------------------------------------------------------- #


def test_missing_file_is_transient_unknown_not_unsupported(tmp_path: Path) -> None:
    missing = tmp_path / "gone.dsf"
    result = DsdSourceCharacterizer().characterize(missing)
    assert result.status is DsdSourceStatus.UNKNOWN
    assert result.failure_code == "SOURCE_DSD_TRANSIENT_UNAVAILABLE"
    assert result.signal is None
    assert result.elementary.encoding is ElementaryEncoding.UNKNOWN


def test_directory_path_is_transient_unknown(tmp_path: Path) -> None:
    result = DsdSourceCharacterizer().characterize(tmp_path)
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


def test_characterization_is_deterministic(tmp_path: Path) -> None:
    blob = build_dsf()
    first = _characterize(tmp_path, "a.dsf", blob)
    second = _characterize(tmp_path, "a.dsf", blob)
    assert first == second


def test_fixture_hashes_are_pinned() -> None:
    # Deterministic structural fixtures: any accidental builder drift breaks
    # these pins, which keeps the parser tests reproducible.
    assert (
        hashlib.sha256(build_dsf()).hexdigest()
        == "d5c7d7ba223b6b72ef0ae4dd846ff63d0ee5d9f7fbced073a5aed4f628f9f558"
    )
    assert (
        hashlib.sha256(build_dff()).hexdigest()
        == "19845ab34c08fd693b93f92ee449ec0ef095b7a4bb1d989cda5d2e0e2fbae4aa"
    )


# --------------------------------------------------------------------------- #
# independence / no output claims
# --------------------------------------------------------------------------- #


def test_characterizer_module_never_touches_gstreamer_alsa_or_output(
    tmp_path: Path,
) -> None:
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
    result = _characterize(tmp_path, "p.dsf", build_dsf())
    assert "native_branch" not in {field.name for field in dataclasses.fields(result)}
    assert "dop" not in {field.name for field in dataclasses.fields(result)}


def test_characterization_exposes_elementary_and_container_separately(
    tmp_path: Path,
) -> None:
    result = _characterize(tmp_path, "s.dsf", build_dsf())
    assert isinstance(result.container_facts, ContainerAudioFacts)
    assert isinstance(result.elementary, ElementaryStreamObservation)
    assert result.elementary.provider == "static-parser"
    assert result.evidence_refs
    assert all(ref for ref in result.evidence_refs)


def test_dop_rate_math_does_not_construct_framing() -> None:
    rate = source_to_dop_rate(DsdSourceBitRate(2_822_400))
    assert isinstance(rate, DopCarrierRate)
    assert not hasattr(rate, "marker")
    assert not hasattr(rate, "pack")
