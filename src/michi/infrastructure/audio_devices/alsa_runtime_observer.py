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
    def __init__(
        self,
        read_text: Callable[[str], str] | None = None,
        *,
        proc_asound_root: Path = Path("/proc/asound"),
    ) -> None:
        self._read_text = read_text or self._read
        self._proc_asound_root = proc_asound_root

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
        ):
            return None
        if binding.stable_endpoint_signature != identity.stable_endpoint_signature:
            if (
                binding.stable_endpoint_signature is None
                or identity.stable_endpoint_signature is None
            ):
                return None
            return self._binding_mismatch(
                identity, "ALSA binding endpoint signature conflicts with Signal Truth"
            )
        card_matches = self._card_matches_locator(binding)
        if card_matches is None:
            return None
        if not card_matches:
            return self._binding_mismatch(
                identity, "ALSA locator does not match the bound card/PCM endpoint"
            )
        resolved = self._resolve_runtime_subdevice(binding)
        if resolved is None:
            return None
        subdevice, path, fields = resolved
        locator_subdevice = self._locator_subdevice(binding.locator)
        if locator_subdevice is not None and locator_subdevice != subdevice:
            return self._binding_mismatch(
                identity,
                "ALSA locator subdevice conflicts with active runtime endpoint",
            )
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
            card_index=binding.card_index,
            pcm_device=binding.pcm_device,
            pcm_subdevice=subdevice,
            locator=binding.locator,
            stable_endpoint_signature=binding.stable_endpoint_signature,
            binding_generation=binding.generation,
        )

    @staticmethod
    def _binding_mismatch(
        identity: SignalTruthIdentity, detail: str
    ) -> RuntimeAnomalyEvidence:
        return RuntimeAnomalyEvidence(
            identity, RuntimeAnomalyKind.BINDING_MISMATCH, detail
        )

    @staticmethod
    def _locator_subdevice(locator: str) -> int | None:
        symbolic = re.fullmatch(
            r"hw:CARD=[^,]+,DEV=\d+,SUBDEV=(\d+)", locator, flags=re.IGNORECASE
        )
        if symbolic is not None:
            return int(symbolic.group(1))
        numeric = re.fullmatch(r"hw:\d+,\d+,(\d+)", locator)
        return int(numeric.group(1)) if numeric is not None else None

    def _resolve_runtime_subdevice(
        self, binding: AudioDeviceBinding
    ) -> tuple[int, str, _HwParams] | None:
        assert binding.card_index is not None and binding.pcm_device is not None
        if binding.pcm_subdevice is not None:
            candidates = (binding.pcm_subdevice,)
        else:
            pcm_root = (
                self._proc_asound_root
                / f"card{binding.card_index}"
                / f"pcm{binding.pcm_device}p"
            )
            try:
                entries = tuple(pcm_root.iterdir())
            except OSError:
                return None
            candidates = tuple(
                sorted(
                    int(match.group(1))
                    for entry in entries
                    if entry.is_dir()
                    and (match := re.fullmatch(r"sub(\d+)", entry.name)) is not None
                )
            )
        active: list[tuple[int, str, _HwParams]] = []
        for subdevice in candidates:
            path = str(
                self._proc_asound_root
                / f"card{binding.card_index}"
                / f"pcm{binding.pcm_device}p"
                / f"sub{subdevice}"
                / "hw_params"
            )
            try:
                text = self._read_text(path)
            except (OSError, UnicodeError):
                return None
            if text.strip() == "closed":
                continue
            fields = self._parse(text)
            if fields is None:
                return None
            active.append((subdevice, path, fields))
        return active[0] if len(active) == 1 else None

    def _card_matches_locator(self, binding: AudioDeviceBinding) -> bool | None:
        assert binding.card_index is not None and binding.pcm_device is not None
        symbolic = re.fullmatch(
            r"hw:CARD=([^,]+),DEV=(\d+)(?:,SUBDEV=\d+)?",
            binding.locator,
            flags=re.IGNORECASE,
        )
        if symbolic is not None:
            card_name, device = symbolic.groups()
            if int(device) != binding.pcm_device:
                return False
            if card_name.isdecimal():
                return int(card_name) == binding.card_index
            try:
                actual_card_name = self._read_text(
                    str(self._proc_asound_root / f"card{binding.card_index}" / "id")
                ).strip()
            except (OSError, UnicodeError):
                return None
            return bool(actual_card_name) and actual_card_name == card_name
        numeric = re.fullmatch(r"hw:(\d+),(\d+)(?:,\d+)?", binding.locator)
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
