"""Application ports for Audio Phase 2 processing (AP2-F04, R11-F04 / §129).

Ports express Michi semantics only: concrete GStreamer/Camilla/PipeWire types
never cross this boundary. No execution happens in F04; these interfaces exist
so a later phase can bind a probed backend without redefining the domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from michi.domain.audio_processing import CompiledProcessingPlan, ProcessingProfile
from michi.domain.audio_processing_evidence import ProcessingRuntimeSnapshot
from michi.domain.audio_signal import PcmSignalFormat


@dataclass(frozen=True, slots=True)
class ProcessingRuntimeHandle:
    handle_id: str
    graph_id: str
    graph_revision: int
    execution_generation: int


@dataclass(frozen=True, slots=True)
class ProcessingInstallResult:
    handle: ProcessingRuntimeHandle
    accepted_input: PcmSignalFormat
    expected_output: PcmSignalFormat
    expected_latency_samples: int


@dataclass(frozen=True, slots=True)
class ProcessingCommitResult:
    handle: ProcessingRuntimeHandle
    active_revision: int


class ProcessingRuntimeError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@runtime_checkable
class AudioProcessingRuntimePort(Protocol):
    @property
    def backend_id(self) -> str: ...

    def prepare(
        self,
        plan: CompiledProcessingPlan,
        input_signal: PcmSignalFormat,
        *,
        execution_generation: int,
    ) -> ProcessingInstallResult: ...

    def preroll(self, handle: ProcessingRuntimeHandle) -> ProcessingRuntimeSnapshot: ...

    def commit(self, handle: ProcessingRuntimeHandle) -> ProcessingCommitResult: ...

    def abort(self, handle: ProcessingRuntimeHandle, reason: str) -> None: ...

    def replace(
        self,
        current: ProcessingRuntimeHandle,
        plan: CompiledProcessingPlan,
        input_signal: PcmSignalFormat,
        *,
        execution_generation: int,
    ) -> ProcessingInstallResult: ...

    def bypass(self, handle: ProcessingRuntimeHandle) -> None: ...

    def release(self, reason: str) -> None: ...

    def snapshot(self) -> ProcessingRuntimeSnapshot | None: ...


@runtime_checkable
class ImpulseResponseStorePort(Protocol):
    def load_float32_mono(self, ir_id: str) -> tuple[float, ...]: ...

    def metadata(self, ir_id: str) -> dict[str, object]: ...


@runtime_checkable
class ProcessingProfileRepositoryPort(Protocol):
    def load_profiles(self) -> tuple[ProcessingProfile, ...]: ...

    def save_profile(self, profile: ProcessingProfile) -> None: ...

    def delete_profile(self, profile_id: str) -> None: ...

    def load_selected_profile_id(self) -> str | None: ...

    def save_selected_profile_id(self, profile_id: str | None) -> None: ...
