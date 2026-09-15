"""Exact-binding ALSA ``hw_params`` observer for DAC-V35-070.

The adapter performs one bounded read for the concrete current binding and
returns a normalized immutable event. Missing, stale, closed, or malformed
readback is absence of evidence, never fabricated capability.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    AlsaRuntimeEvidence,
    RuntimeAnomalyEvidence,
    RuntimeAnomalyKind,
    SignalTruthIdentity,
)


@dataclass(frozen=True, slots=True)
class _HwParams:
    rate_hz: int
    transport_format: str
    channels: int
    significant_bits: int | None
    access: str | None
    subformat: str | None
    period_size: int | None
    buffer_size: int | None


class AlsaHwParamsObserver:
    def __init__(self, read_text: Callable[[str], str] | None = None) -> None:
        self._read_text = read_text or self._read

    @staticmethod
    def _read(path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def observe(
        self,
        identity: SignalTruthIdentity,
        binding: AudioDeviceBinding,
    ) -> AlsaRuntimeEvidence | RuntimeAnomalyEvidence | None:
        if (
            binding.kind is not BindingKind.ALSA_PCM
            or not binding.currently_available
            or binding.generation != identity.binding_generation
            or binding.card_index is None
            or binding.pcm_device is None
            or binding.pcm_subdevice is None
            or binding.stable_endpoint_signature != identity.stable_endpoint_signature
        ):
            return None
        card_matches = self._card_matches_locator(binding)
        if card_matches is None:
            return None
        if not card_matches:
            return RuntimeAnomalyEvidence(
                identity,
                RuntimeAnomalyKind.BINDING_MISMATCH,
                "ALSA locator does not match the bound card/PCM endpoint",
            )
        path = (
            f"/proc/asound/card{binding.card_index}/"
            f"pcm{binding.pcm_device}p/sub{binding.pcm_subdevice}/hw_params"
        )
        try:
            text = self._read_text(path)
        except (OSError, UnicodeError):
            return None
        fields = self._parse(text)
        if fields is None:
            return None
        return AlsaRuntimeEvidence(
            identity=identity,
            negotiated_pcm=PcmTuple(
                rate_hz=fields.rate_hz,
                transport_format=fields.transport_format,
                channels=fields.channels,
                significant_bits=fields.significant_bits,
            ),
            access=fields.access,
            subformat=fields.subformat,
            period_size=fields.period_size,
            buffer_size=fields.buffer_size,
            proc_path=path,
        )

    def _card_matches_locator(self, binding: AudioDeviceBinding) -> bool | None:
        assert binding.card_index is not None and binding.pcm_device is not None
        symbolic = re.fullmatch(
            r"hw:CARD=([^,]+),DEV=(\d+)", binding.locator, flags=re.IGNORECASE
        )
        if symbolic is not None:
            card_name, device = symbolic.groups()
            if int(device) != binding.pcm_device:
                return False
            if card_name.isdecimal():
                return int(card_name) == binding.card_index
            try:
                actual_card_name = self._read_text(
                    f"/proc/asound/card{binding.card_index}/id"
                ).strip()
            except (OSError, UnicodeError):
                return None
            return bool(actual_card_name) and actual_card_name == card_name
        numeric = re.fullmatch(r"hw:(\d+),(\d+)", binding.locator)
        if numeric is not None:
            card, device = (int(value) for value in numeric.groups())
            return card == binding.card_index and device == binding.pcm_device
        return False

    @staticmethod
    def _parse(text: str) -> _HwParams | None:
        if text.strip() == "closed":
            return None
        raw: dict[str, str] = {}
        for line in text.splitlines():
            key, separator, value = line.partition(":")
            if separator:
                raw[key.strip()] = value.strip()
        required = ("format", "rate", "channels")
        if any(not raw.get(key) for key in required):
            return None
        try:
            rate = int(raw["rate"].split()[0])
            channels = int(raw["channels"])
            period_size = int(raw["period_size"]) if raw.get("period_size") else None
            buffer_size = int(raw["buffer_size"]) if raw.get("buffer_size") else None
            significant_bits = int(raw["msbits"]) if raw.get("msbits") else None
        except (ValueError, IndexError):
            return None
        numeric_values = (rate, channels, period_size, buffer_size, significant_bits)
        if any(value is not None and value <= 0 for value in numeric_values):
            return None
        return _HwParams(
            rate_hz=rate,
            transport_format=raw["format"],
            channels=channels,
            significant_bits=significant_bits,
            access=raw.get("access"),
            subformat=raw.get("subformat"),
            period_size=period_size,
            buffer_size=buffer_size,
        )
