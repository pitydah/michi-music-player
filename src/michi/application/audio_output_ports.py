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

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class OutputCleanupDiagnostic:
    """Typed evidence that physical cleanup failed after logical invalidation."""

    reason: str
    code: str
    detail: str


class VolumeAuthority(Enum):
    """Current owner of effective loudness for the resolved output path."""

    FIXED = "fixed"
    DEVICE_EXTERNAL = "device_external"
    ALSA_HARDWARE = "alsa_hardware"
    MICHI_SOFTWARE = "michi_software"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AppliedVolume:
    """Confirmed effective volume result returned to PlaybackState authority."""

    requested_percent: int
    effective_percent: int
    muted: bool
    mode: str
    signal_mutated: bool
    device_db: float | None = None


class OutputVolumeLockedError(RuntimeError):
    """The current output policy forbids software volume attenuation."""


class DeviceControlUnavailableError(RuntimeError):
    """No qualified hardware-volume mapping can execute this command."""


class UnknownVolumeAuthorityError(RuntimeError):
    """Direct volume authority is unknown and therefore fails closed."""


class VolumeRestoreError(RuntimeError):
    """Restore partially applied; ``applied`` is the last confirmed truth."""

    def __init__(self, message: str, applied: AppliedVolume) -> None:
        super().__init__(message)
        self.applied = applied


@runtime_checkable
class PlaybackVolumePort(Protocol):
    def apply_volume(self, value: int) -> AppliedVolume: ...

    def apply_muted(self, muted: bool) -> AppliedVolume: ...

    def restore(self, value: int, muted: bool) -> AppliedVolume: ...

    def synchronize(self) -> AppliedVolume: ...

    def preference(self) -> tuple[int, bool]: ...


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
