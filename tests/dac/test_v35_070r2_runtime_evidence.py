"""DAC-V35-070R2 portable significant-bit runtime-evidence gates."""

from __future__ import annotations

import pytest

from michi.domain.audio_evidence import intrinsic_pcm_significant_bits

_QT_APP = None


@pytest.fixture(autouse=True)
def _qt_runtime():
    global _QT_APP
    from PySide6.QtWidgets import QApplication

    _QT_APP = QApplication.instance() or QApplication([])
    yield _QT_APP


@pytest.mark.parametrize("fmt", ["S8", "U8", "s8", "u8"])
def test_r2_01_eight_bit_formats_have_intrinsic_precision(fmt: str) -> None:
    assert intrinsic_pcm_significant_bits(fmt) == 8


@pytest.mark.parametrize("fmt", ["S16_LE", "S16LE", "U16_LE", "U16LE"])
def test_r2_02_sixteen_bit_little_endian_is_intrinsic(fmt: str) -> None:
    assert intrinsic_pcm_significant_bits(fmt) == 16


@pytest.mark.parametrize("fmt", ["S16_BE", "S16BE", "U16_BE", "U16BE"])
def test_r2_03_sixteen_bit_big_endian_is_intrinsic(fmt: str) -> None:
    assert intrinsic_pcm_significant_bits(fmt) == 16


@pytest.mark.parametrize("fmt", ["S24_3LE", "S24_3BE", "U24_3LE", "U24_3BE"])
def test_r2_04_packed_twenty_four_bit_formats_are_intrinsic(fmt: str) -> None:
    assert intrinsic_pcm_significant_bits(fmt) == 24


@pytest.mark.parametrize("fmt", ["S24_32LE", "S24_32BE", "U24_32LE", "U24_32BE"])
def test_r2_05_twenty_four_in_thirty_two_container_is_unknown(fmt: str) -> None:
    assert intrinsic_pcm_significant_bits(fmt) is None


@pytest.mark.parametrize("fmt", ["S24LE", "S24BE", "U24LE", "U24BE"])
def test_r2_06_gstreamer_packed_twenty_four_bit_is_intrinsic(fmt: str) -> None:
    assert intrinsic_pcm_significant_bits(fmt) == 24


@pytest.mark.parametrize("fmt", ["S32_LE", "S32LE", "U32_BE", "U32BE"])
def test_r2_07_thirty_two_bit_containers_are_unknown(fmt: str) -> None:
    assert intrinsic_pcm_significant_bits(fmt) is None


@pytest.mark.parametrize("fmt", ["F32LE", "F64BE", "FLOAT", "DOUBLE"])
def test_r2_08_float_formats_are_unknown(fmt: str) -> None:
    assert intrinsic_pcm_significant_bits(fmt) is None


@pytest.mark.parametrize("fmt", [None, "", "UNKNOWN", " S32_LE garbage "])
def test_r2_09_missing_or_invalid_formats_are_unknown(fmt: str | None) -> None:
    assert intrinsic_pcm_significant_bits(fmt) is None


def test_r2_10_gstreamer_custom_sbits_cannot_fill_s32_runtime_truth() -> None:
    from tests.dac.test_v35_070r1_gstreamer_provenance import _snapshot

    snapshot = _snapshot(("A", "B"))

    assert snapshot.effective_significant_bits is None


def test_r2_11_gstreamer_packed_format_derives_intrinsic_decoder_sbits() -> None:
    from tests.dac.test_v35_070r1_gstreamer_provenance import _snapshot

    snapshot = _snapshot(("A", "B"))

    assert snapshot.decoded_format == "S24_3LE"
    assert snapshot.decoded_significant_bits == 24


def test_r2_12_procfs_msbits_cannot_fill_s32_runtime_truth() -> None:
    from michi.infrastructure.audio_devices.alsa_runtime_observer import (
        AlsaHwParamsObserver,
    )

    parsed = AlsaHwParamsObserver._parse(
        "format: S32_LE\nrate: 96000\nchannels: 2\nmsbits: 24\n"
    )

    assert parsed is not None
    assert parsed.significant_bits is None


def test_r2_13_procfs_unambiguous_s16_format_derives_intrinsic_sbits() -> None:
    from michi.infrastructure.audio_devices.alsa_runtime_observer import (
        AlsaHwParamsObserver,
    )

    parsed = AlsaHwParamsObserver._parse(
        "format: S16_LE\nrate: 48000\nchannels: 2\nmsbits: 7\n"
    )

    assert parsed is not None
    assert parsed.significant_bits == 16


def test_r2_14_procfs_unambiguous_packed_s24_derives_intrinsic_sbits() -> None:
    from michi.infrastructure.audio_devices.alsa_runtime_observer import (
        AlsaHwParamsObserver,
    )

    parsed = AlsaHwParamsObserver._parse("format: S24_3BE\nrate: 96000\nchannels: 2\n")

    assert parsed is not None
    assert parsed.significant_bits == 24


def test_r2_15_procfs_invalid_numeric_fields_still_fail_closed() -> None:
    from michi.infrastructure.audio_devices.alsa_runtime_observer import (
        AlsaHwParamsObserver,
    )

    assert AlsaHwParamsObserver._parse("format: S16_LE\nrate: 0\nchannels: 2\n") is None


def _productive_s32_snapshot(tmp_path):
    from tests.dac.test_v35_070r1_productive_provenance import (
        _load_and_accept,
        _runtime_reader,
    )
    from tests.dac.test_v35_productive_direct_composition import (
        _close_graph,
        _direct_graph,
    )

    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_runtime_reader())
    try:
        return _load_and_accept(graph, bindings, tmp_path / "r2.flac")
    finally:
        _close_graph(graph)


def test_r2_16_productive_composition_does_not_claim_direct_from_s32(
    tmp_path,
) -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    assert _productive_s32_snapshot(tmp_path).verdict is SignalTruthVerdict.UNKNOWN


def test_r2_17_productive_s32_reports_significant_bits_unknown(tmp_path) -> None:
    from michi.domain.signal_truth import SignalTruthReason

    snapshot = _productive_s32_snapshot(tmp_path)

    assert SignalTruthReason.ST_SIGNIFICANT_BITS_UNKNOWN in snapshot.reasons


def test_r2_18_productive_fake_decoder_does_not_fabricate_s32_sbits(
    tmp_path,
) -> None:
    snapshot = _productive_s32_snapshot(tmp_path)

    assert snapshot.decoded_runtime is not None
    assert snapshot.decoded_runtime.pcm.significant_bits is None


def test_r2_19_productive_engine_does_not_fabricate_s32_sbits(tmp_path) -> None:
    snapshot = _productive_s32_snapshot(tmp_path)

    assert snapshot.engine_effective is not None
    assert snapshot.engine_effective.effective_pcm is not None
    assert snapshot.engine_effective.effective_pcm.significant_bits is None


def test_r2_20_productive_alsa_proc_msbits_does_not_elevate_truth(tmp_path) -> None:
    snapshot = _productive_s32_snapshot(tmp_path)

    assert snapshot.device_negotiated is not None
    assert snapshot.device_negotiated.negotiated_pcm.significant_bits is None
