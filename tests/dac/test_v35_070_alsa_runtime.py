"""DAC-V35-070 exact-binding ALSA runtime evidence gates ST70-35..39."""

from __future__ import annotations

from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.signal_truth import SignalTruthIdentity
from michi.infrastructure.audio_devices.alsa_runtime_observer import (
    AlsaHwParamsObserver,
)


def _identity(*, binding_generation: int = 3) -> SignalTruthIdentity:
    return SignalTruthIdentity(
        "plan-1",
        2,
        9,
        binding_generation,
        "usb:2622:0105:DX5ABC123",
        "ep:dx5:0",
    )


def _binding(*, generation: int = 3, card: int | None = 4) -> AudioDeviceBinding:
    return AudioDeviceBinding(
        BindingKind.ALSA_PCM,
        "hw:CARD=DX5,DEV=2",
        generation,
        True,
        card_index=card,
        pcm_device=2,
        pcm_subdevice=1,
        stable_endpoint_signature="ep:dx5:0",
    )


_HW_PARAMS = """access: RW_INTERLEAVED
format: S32_LE
subformat: STD
channels: 2
rate: 96000 (96000/1)
period_size: 1024
buffer_size: 4096
msbits: 24
"""


def test_st70_35_reads_only_exact_bound_pcm_subdevice() -> None:
    reads: list[str] = []

    def read_text(path: str) -> str:
        reads.append(path)
        return "DX5\n" if path.endswith("/id") else _HW_PARAMS

    event = AlsaHwParamsObserver(read_text).observe(_identity(), _binding())

    assert reads == [
        "/proc/asound/card4/id",
        "/proc/asound/card4/pcm2p/sub1/hw_params",
    ]
    assert event is not None
    assert event.negotiated_pcm.rate_hz == 96_000
    assert event.negotiated_pcm.transport_format == "S32_LE"
    assert event.negotiated_pcm.significant_bits == 24
    assert event.period_size == 1024
    assert event.buffer_size == 4096


def test_st70_36_stale_binding_generation_is_not_read() -> None:
    reads: list[str] = []
    event = AlsaHwParamsObserver(lambda path: reads.append(path) or _HW_PARAMS).observe(
        _identity(binding_generation=4), _binding(generation=3)
    )
    assert event is None
    assert reads == []


def test_st70_37_incomplete_binding_never_guesses_card_or_subdevice() -> None:
    reads: list[str] = []
    event = AlsaHwParamsObserver(lambda path: reads.append(path) or _HW_PARAMS).observe(
        _identity(), _binding(card=None)
    )
    assert event is None
    assert reads == []


def test_st70_38_closed_or_malformed_hw_params_is_missing_evidence() -> None:
    observer = AlsaHwParamsObserver(
        lambda path: "DX5\n" if path.endswith("/id") else "closed\n"
    )
    assert observer.observe(_identity(), _binding()) is None
    malformed = AlsaHwParamsObserver(
        lambda path: "DX5\n" if path.endswith("/id") else "format: S32_LE\n"
    )
    assert malformed.observe(_identity(), _binding()) is None


def test_st70_39_s32_without_msbits_does_not_infer_32_significant_bits() -> None:
    text = _HW_PARAMS.replace("msbits: 24\n", "")
    event = AlsaHwParamsObserver(
        lambda path: "DX5\n" if path.endswith("/id") else text
    ).observe(_identity(), _binding())
    assert event is not None
    assert event.negotiated_pcm.significant_bits is None


def test_card_name_mismatch_emits_typed_contradiction_without_hw_params_read() -> None:
    reads: list[str] = []

    def read_text(path: str) -> str:
        reads.append(path)
        return "OTHER\n"

    event = AlsaHwParamsObserver(read_text).observe(_identity(), _binding())
    assert event is not None
    assert event.kind.value == "binding_mismatch"
    assert reads == ["/proc/asound/card4/id"]


def test_non_positive_hw_params_is_missing_evidence() -> None:
    text = _HW_PARAMS.replace("msbits: 24", "msbits: 0")
    observer = AlsaHwParamsObserver(
        lambda path: "DX5\n" if path.endswith("/id") else text
    )
    assert observer.observe(_identity(), _binding()) is None
