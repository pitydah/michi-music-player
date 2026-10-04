"""AP2-F01 — pure signal-domain language: family, layout and PCM parity.

Contract anchors: R11-F01 (create-only slice), R11-G03 (execution families),
spec §121 (PCM semantics of reference). These tests are the RED contract for
``michi.domain.audio_signal``; they must fail before the module exists and pin
semantics, never implementation text.
"""

from __future__ import annotations

import ast
import dataclasses
import sys
from pathlib import Path

import pytest

from michi.domain.audio_evidence import (
    DecodedSourceSignal,
    PcmTuple,
    intrinsic_pcm_significant_bits,
)
from michi.domain.audio_signal import (
    ChannelLayout,
    PcmSignalFormat,
    SignalFamily,
)

MODULE_PATH = Path(sys.modules["michi.domain.audio_signal"].__file__)


def _pcm_format(
    *,
    rate_hz: int = 44100,
    transport_format: str = "S32_LE",
    significant_bits: int | None = 24,
    layout: ChannelLayout | None = None,
) -> PcmSignalFormat:
    return PcmSignalFormat(
        rate_hz=rate_hz,
        transport_format=transport_format,
        significant_bits=significant_bits,
        layout=layout if layout is not None else ChannelLayout(positions=("FL", "FR")),
    )


def _imported_modules(source_path: Path) -> list[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append("." * node.level + (node.module or ""))
    return modules


def test_signal_family_pcm_and_dsd_values() -> None:
    assert SignalFamily.PCM.value == "pcm"
    assert SignalFamily.DSD.value == "dsd"


def test_signal_family_has_exactly_two_canonical_members() -> None:
    assert [member.name for member in SignalFamily] == ["PCM", "DSD"]


def test_signal_family_is_string_interoperable() -> None:
    # StrEnum: the vocabulary is directly usable in JSON/state artifacts.
    assert SignalFamily.PCM == "pcm"
    assert SignalFamily.DSD == "dsd"


def test_channel_layout_is_immutable() -> None:
    layout = ChannelLayout(positions=("FL", "FR"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        layout.positions = ("FL",)  # type: ignore[misc]


def test_channel_layout_channel_count_is_deterministic() -> None:
    assert ChannelLayout(positions=("FL", "FR")).channels == 2
    assert ChannelLayout(positions=("FL", "FR", "FC")).channels == 3
    assert ChannelLayout(positions=()).channels == 0


def test_channel_layout_preserves_position_order() -> None:
    positions = ("FL", "FR", "FC", "LFE")
    assert ChannelLayout(positions=positions).positions == positions


def test_channel_layout_equality_is_structural() -> None:
    assert ChannelLayout(positions=("FL", "FR")) == ChannelLayout(
        positions=("FL", "FR")
    )
    assert ChannelLayout(positions=("FL", "FR")) != ChannelLayout(
        positions=("FR", "FL")
    )


def test_pcm_format_is_immutable() -> None:
    fmt = _pcm_format()
    with pytest.raises(dataclasses.FrozenInstanceError):
        fmt.rate_hz = 48000  # type: ignore[misc]


def test_pcm_rate_is_preserved_exactly() -> None:
    for rate in (44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000):
        assert _pcm_format(rate_hz=rate).rate_hz == rate


def test_pcm_transport_format_is_preserved_exactly() -> None:
    for transport in ("S16_LE", "S24_3LE", "S24LE", "S32_LE", "F32LE"):
        assert _pcm_format(transport_format=transport).transport_format == transport


def test_pcm_known_significant_bits_stay_exact() -> None:
    assert _pcm_format(significant_bits=16).significant_bits == 16
    assert _pcm_format(significant_bits=24).significant_bits == 24


def test_pcm_unknown_significant_bits_stay_none() -> None:
    # §121 SIG-04: unknown precision stays None; never coerced from the carrier.
    assert _pcm_format(significant_bits=None).significant_bits is None


def test_pcm_layout_is_preserved() -> None:
    layout = ChannelLayout(positions=("FL", "FR", "FC"))
    assert _pcm_format(layout=layout).layout == layout


def test_pcm_format_rejects_non_positive_rate() -> None:
    for rate in (0, -1):
        with pytest.raises(ValueError):
            _pcm_format(rate_hz=rate)


def test_pcm_format_requires_non_blank_transport_format() -> None:
    with pytest.raises(ValueError):
        _pcm_format(transport_format="   ")


def test_pcm_format_rejects_non_positive_significant_bits() -> None:
    with pytest.raises(ValueError):
        _pcm_format(significant_bits=0)


def test_pcm_format_requires_at_least_one_channel() -> None:
    with pytest.raises(ValueError):
        _pcm_format(layout=ChannelLayout(positions=()))


def test_signal_module_imports_stay_pure_domain() -> None:
    imports = _imported_modules(MODULE_PATH)
    assert imports, "audio_signal must declare its imports"
    forbidden_prefixes = (
        "PySide6",
        "gi",
        "Gst",
        "sqlite3",
        "ctypes",
        "michi.presentation",
        "michi.infrastructure",
        "michi.bootstrap",
        "michi.application",
    )
    for name in imports:
        assert not any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in forbidden_prefixes
        ), f"forbidden import: {name}"
        top = name.split(".")[0]
        assert top in sys.stdlib_module_names or top == "michi", f"non-stdlib: {name}"
        if top == "michi":
            assert name == "michi.domain" or name.startswith("michi.domain."), name


def test_legacy_pcm_tuple_semantics_unchanged() -> None:
    value = PcmTuple(
        rate_hz=96000, transport_format="S32_LE", channels=2, significant_bits=24
    )
    assert (
        value.rate_hz,
        value.transport_format,
        value.channels,
        value.significant_bits,
    ) == (96000, "S32_LE", 2, 24)
    assert value == PcmTuple(96000, "S32_LE", 2, 24)
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.rate_hz = 44100  # type: ignore[misc]


def test_legacy_decoded_source_signal_semantics_unchanged() -> None:
    decoded = DecodedSourceSignal(
        encoding="PCM",
        rate_hz=44100,
        significant_bits=16,
        channels=2,
        channel_positions=("FL", "FR"),
    )
    assert (
        decoded.encoding,
        decoded.rate_hz,
        decoded.significant_bits,
        decoded.channels,
        decoded.channel_positions,
    ) == ("PCM", 44100, 16, 2, ("FL", "FR"))
    assert DecodedSourceSignal("PCM", 44100, 16, 2, None).channel_positions is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        decoded.channels = 1  # type: ignore[misc]


def test_legacy_significant_bits_classification_unchanged() -> None:
    assert intrinsic_pcm_significant_bits("S16_LE") == 16
    assert intrinsic_pcm_significant_bits("S24_3LE") == 24
    assert intrinsic_pcm_significant_bits("S24LE") == 24
    assert intrinsic_pcm_significant_bits("S32_LE") is None
    assert intrinsic_pcm_significant_bits(None) is None


def test_new_pcm_format_can_carry_every_legacy_tuple_fact() -> None:
    legacy = PcmTuple(
        rate_hz=192000, transport_format="S24_3LE", channels=2, significant_bits=24
    )
    signal = PcmSignalFormat(
        rate_hz=legacy.rate_hz,
        transport_format=legacy.transport_format,
        significant_bits=legacy.significant_bits,
        layout=ChannelLayout(positions=("FL", "FR")),
    )
    assert signal.rate_hz == legacy.rate_hz
    assert signal.transport_format == legacy.transport_format
    assert signal.significant_bits == legacy.significant_bits
    assert signal.layout.channels == legacy.channels
