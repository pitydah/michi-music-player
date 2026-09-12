"""DAC-V35-030/040-C07 — puertos de persistencia de output (spec §402).

Ownership (C07):
- AudioOutputProfileRepositoryPort: SOLO profile/selection (autoridad
  del AudioOutputProfileService);
- QualificationCachePort: SOLO cache rebuildable de qualification
  (autoridad del DacQualificationService).

El storage SQLite concreto puede ser compartido; la autoridad de
aplicación no.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from michi.domain.audio_evidence import CapabilityEvidence
from michi.domain.audio_output import AudioOutputProfile, AudioOutputSelection


@runtime_checkable
class AudioOutputProfileRepositoryPort(Protocol):
    def load_profiles(self) -> tuple[AudioOutputProfile, ...]: ...

    def save_profile(self, profile: AudioOutputProfile) -> None: ...

    def load_selection(self) -> AudioOutputSelection: ...

    def save_selection(self, selection: AudioOutputSelection) -> None: ...


@runtime_checkable
class QualificationCachePort(Protocol):
    def load_qualification_cache(
        self, stable_device_id: str
    ) -> tuple[CapabilityEvidence, ...]: ...

    def replace_qualification_cache(
        self, stable_device_id: str, evidence: tuple[CapabilityEvidence, ...]
    ) -> None: ...
