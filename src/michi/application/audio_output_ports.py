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

from enum import Enum
from typing import Protocol, runtime_checkable

from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_evidence import CapabilityEvidence
from michi.domain.audio_output import (
    AudioOutputProfile,
    AudioOutputSelection,
    OutputPlan,
)


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


class OutputExecutorAbortDisposition(Enum):
    """Transactional result of aborting one output-executor receipt.

    The result distinguishes restoration from successful retirement and from
    a stale caller. It exposes no executor-internal rollback representation.
    """

    PREDECESSOR_RESTORED = "predecessor_restored"
    CANDIDATE_DISCARDED = "candidate_discarded"
    STALE = "stale"


@runtime_checkable
class AudioOutputExecutorPort(Protocol):
    """Executes one immutable output plan without performing policy lookups."""

    @property
    def engine_id(self) -> AudioEngineId: ...

    def prepare(self, plan: OutputPlan) -> str: ...

    def commit(self, receipt: str) -> None: ...

    def abort(self, receipt: str, reason: str) -> OutputExecutorAbortDisposition:
        """Abort exactly one receipt and report its transactional disposition."""
        ...

    def owns_committed_receipt(self, receipt: str) -> bool:
        """Whether receipt still denotes the physically restorable execution."""
        ...

    def release(self, reason: str) -> None: ...
