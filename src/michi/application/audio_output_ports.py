"""DAC-V35-030 — puertos de persistencia de output profile (spec §402)."""

from __future__ import annotations

from typing import Protocol

from michi.domain.audio_evidence import CapabilityEvidence
from michi.domain.audio_output import AudioOutputProfile, AudioOutputSelection


class AudioOutputProfileRepositoryPort(Protocol):
    def load_profiles(self) -> tuple[AudioOutputProfile, ...]: ...

    def save_profile(self, profile: AudioOutputProfile) -> None: ...

    def load_selection(self) -> AudioOutputSelection: ...

    def save_selection(self, selection: AudioOutputSelection) -> None: ...

    def load_qualification_cache(
        self, stable_device_id: str
    ) -> tuple[CapabilityEvidence, ...]: ...

    def replace_qualification_cache(
        self, stable_device_id: str, evidence: tuple[CapabilityEvidence, ...]
    ) -> None: ...
