"""AP2-F09 — independent golden corpus conformance (Python reference)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from michi.domain.dop import (
    DopCarrierLayout,
    DopPackingError,
    DopStreamPacker,
    expected_carrier_rate,
    pack_dop_interleaved_stereo,
)

ROOT = Path(__file__).parent / "conformance"
VECTORS = ROOT / "vectors"


def _load(name: str) -> dict:
    return json.loads((VECTORS / name).read_text())


def _pack(vector: dict) -> bytes:
    left = bytes.fromhex(vector["source"]["left_hex"])
    right = bytes.fromhex(vector["source"]["right_hex"])
    layout = DopCarrierLayout(vector["layout"])
    chunks = vector.get("chunks")
    if chunks:
        packer = DopStreamPacker(layout=layout, reverse_bits=vector["reverse_bits"])
        out = bytearray()
        lo = ro = 0
        for size in chunks:
            take = int(size)
            out.extend(packer.pack_stereo(left[lo : lo + take], right[ro : ro + take]))
            lo += take
            ro += take
        return bytes(out)
    return pack_dop_interleaved_stereo(
        left,
        right,
        layout=layout,
        reverse_bits=vector["reverse_bits"],
    ).payload


def test_manifest_matches_vectors() -> None:
    manifest = json.loads((ROOT / "manifest.sha256").read_text())
    for name, digest in manifest.items():
        assert hashlib.sha256((VECTORS / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize(
    "name",
    [
        "dop64_packed24.json",
        "dop128_packed24.json",
        "s32_lsb24.json",
        "s32_msb24_reference.json",
        "bit_reversal.json",
        "odd_chunk_split.json",
        "marker_phase.json",
        "rates.json",
    ],
)
def test_golden_vector(name: str) -> None:
    vector = _load(name)
    assert _pack(vector).hex() == vector["expected_hex"]


def test_rate_vectors_are_mathematical_only() -> None:
    vector = _load("rates.json")
    for label, carrier in vector["rates"].items():
        source_bits = int(label) * 44_100
        assert expected_carrier_rate(source_bits).frames_per_second == carrier


def test_negative_vectors_are_typed() -> None:
    vector = _load("negative_cases.json")
    for case in vector["cases"]:
        if "rate_hz" in case:
            with pytest.raises(DopPackingError) as info:
                expected_carrier_rate(case["rate_hz"])
        else:
            with pytest.raises(DopPackingError) as info:
                pack_dop_interleaved_stereo(
                    bytes.fromhex(case["left_hex"]), bytes.fromhex(case["right_hex"])
                )
        assert info.value.code == case["error"]
