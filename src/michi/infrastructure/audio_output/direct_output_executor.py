"""DAC-V35-050C1 — GStreamerDirectOutputExecutor core (spec §404).

Núcleo puro: OutputPlan -> StrictSinkRecipe -> execution_generation ->
DirectRuntimeSnapshot -> validate_runtime() -> DirectPrerollEvidence.

NO importa gi/Gst/GLib. NO conoce GStreamerAudioPort, OutputSession ni
PlaybackService. PREROLL VERIFIED != RUNNING: la sesión no se toca.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from michi.application.audio_output_ports import OutputExecutorAbortDisposition
from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_evidence import PcmTuple
from michi.domain.audio_output import OutputPlan, VolumePolicy
from michi.domain.signal_truth import (
    DecodedRuntimeEvidence,
    EngineRuntimeEvidence,
    OutputPlanEvidence,
    RuntimeAnomalyEvidence,
    RuntimeAnomalyKind,
    SignalTruthIdentity,
    SignalTruthRecorder,
    SourceFileFactsEvidence,
)
from michi.infrastructure.audio_output.runtime_inspector import (
    DirectPrerollEvidence,
    DirectRuntimeSnapshot,
    validate_runtime,
)
from michi.infrastructure.audio_output.strict_sink import (
    StrictSinkRecipe,
    recipe_from_plan,
)


class DirectExecutionState(Enum):
    IDLE = "idle"
    STAGED = "staged"
    PREROLL_VERIFIED = "preroll_verified"
    COMMITTED = "committed"


class DirectExecutorError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DirectExecutionHandle:
    """Identidad inmutable de UNA ejecución staged."""

    generation: int
    plan_id: str


@dataclass(frozen=True, slots=True)
class DirectLoadPreparation:
    """One-shot atomic payload for exactly one GStreamer load attempt."""

    handle: DirectExecutionHandle
    recipe: StrictSinkRecipe
    candidate_volume: float

    def __post_init__(self) -> None:
        if self.handle.plan_id != self.recipe.plan_id:
            raise DirectExecutorError(
                "DIRECT_STAGE_IDENTITY_MISMATCH",
                "handle and strict recipe belong to different plans",
            )
        if self.candidate_volume != 1.0:
            raise DirectExecutorError(
                "DIRECT_FIXED_UNITY_REQUIRED",
                "Direct FIXED candidate volume must be exactly unity",
            )


@dataclass(frozen=True, slots=True)
class _ExecutionSnapshot:
    state: DirectExecutionState
    handle: DirectExecutionHandle
    plan: OutputPlan
    recipe: StrictSinkRecipe
    evidence: DirectPrerollEvidence | None
    receipt: str
    signal_identity: SignalTruthIdentity | None


class DirectLoadStagePort(Protocol):
    def stage_direct_load(
        self,
        preparation: DirectLoadPreparation,
        *,
        executor: GStreamerDirectOutputExecutor,
    ) -> None: ...

    def discard_direct_load(
        self,
        handle: DirectExecutionHandle,
        *,
        executor: GStreamerDirectOutputExecutor,
    ) -> bool: ...


class GStreamerDirectOutputExecutor:
    """Sidecar de una única ejecución staged (sin cola, sin authority)."""

    def __init__(
        self,
        *,
        signal_truth: SignalTruthRecorder | None = None,
        alsa_runtime_observer=None,
    ) -> None:
        self._generation = 0
        self._state = DirectExecutionState.IDLE
        self._handle: DirectExecutionHandle | None = None
        self._plan: OutputPlan | None = None
        self._recipe: StrictSinkRecipe | None = None
        self._evidence: DirectPrerollEvidence | None = None
        self._receipt: str | None = None
        self._signal_truth = signal_truth
        self._alsa_runtime_observer = alsa_runtime_observer
        self._signal_identity: SignalTruthIdentity | None = None
        # DAC-V35-050R1: at most one committed execution survives while one
        # replacement candidate is provisional. It is private rollback state,
        # never a second output/session authority.
        self._committed: _ExecutionSnapshot | None = None
        self._port_provider: Callable[[], DirectLoadStagePort | None] | None = None

    @property
    def engine_id(self) -> AudioEngineId:
        return AudioEngineId.GSTREAMER

    def bind_port_provider(
        self, provider: Callable[[], DirectLoadStagePort | None]
    ) -> None:
        """Bind the canonical provider-owned port exactly once."""
        if self._port_provider is not None and self._port_provider is not provider:
            raise DirectExecutorError(
                "DIRECT_PORT_PROVIDER_ALREADY_BOUND",
                "the Direct executor already has a port provider",
            )
        self._port_provider = provider

    # ── lectura ───────────────────────────────────────────────────────
    @property
    def state(self) -> DirectExecutionState:
        return self._state

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def handle(self) -> DirectExecutionHandle | None:
        return self._handle

    # ── ejecución ─────────────────────────────────────────────────────
    def stage(self, plan: OutputPlan) -> DirectExecutionHandle:
        """Valida el plan (recipe_from_plan) y reemplaza la ejecución.

        Sólo existe UNA ejecución actual: stage(A) -> stage(B) deja A
        stale sin necesidad de abort explícito.
        """
        recipe = recipe_from_plan(plan)
        self._generation += 1
        handle = DirectExecutionHandle(
            generation=self._generation,
            plan_id=plan.plan_id,
        )
        self._handle = handle
        self._plan = plan
        self._recipe = recipe
        self._evidence = None
        self._receipt = None
        self._signal_identity = None
        self._committed = None
        self._state = DirectExecutionState.STAGED
        return handle

    def prepare(self, plan: OutputPlan) -> str:
        """Atomically stage plan + handle + recipe on the canonical port."""
        provider = self._port_provider
        if provider is None:
            raise DirectExecutorError(
                "DIRECT_PORT_UNAVAILABLE", "no canonical GStreamer port provider"
            )
        port = provider()
        if port is None:
            raise DirectExecutorError(
                "DIRECT_PORT_UNAVAILABLE", "GStreamer is not the open active engine"
            )

        if plan.volume_policy is not VolumePolicy.FIXED:
            raise DirectExecutorError(
                "DIRECT_VOLUME_POLICY_UNAVAILABLE",
                f"Direct volume policy {plan.volume_policy.value!r} is unavailable",
            )
        # Build/validate before replacing current execution. If recipe creation
        # fails, the previous execution remains untouched.
        recipe = recipe_from_plan(plan)
        previous = self._snapshot_current()
        previous_rollback = self._committed
        if self._state is DirectExecutionState.COMMITTED:
            self._committed = previous
        self._generation += 1
        handle = DirectExecutionHandle(self._generation, plan.plan_id)
        preparation = DirectLoadPreparation(handle, recipe, candidate_volume=1.0)
        receipt = f"direct:{handle.generation}:{handle.plan_id}"
        self._state = DirectExecutionState.STAGED
        self._handle = handle
        self._plan = plan
        self._recipe = recipe
        self._evidence = None
        self._receipt = receipt
        self._signal_identity = None
        try:
            port.stage_direct_load(preparation, executor=self)
        except Exception:
            with contextlib.suppress(Exception):
                port.discard_direct_load(handle, executor=self)
            self._restore(previous)
            self._committed = previous_rollback
            raise
        return receipt

    def commit(self, receipt: str) -> None:
        self._require_receipt(receipt)
        handle = self._handle
        assert handle is not None
        if not self.is_preroll_verified(handle):
            raise DirectExecutorError(
                "DIRECT_PREROLL_NOT_VERIFIED",
                "output commit requires verified runtime preroll evidence",
            )
        if (
            self._signal_truth is not None
            and self._signal_identity is not None
            and not self._signal_truth.commit_candidate(self._signal_identity)
        ):
            raise DirectExecutorError(
                "SIGNAL_TRUTH_PROMOTION_BLOCKED",
                "candidate cannot replace active truth before destructive boundary",
            )
        self._state = DirectExecutionState.COMMITTED
        self._committed = None

    def abort_receipt(
        self, receipt: str, reason: str
    ) -> OutputExecutorAbortDisposition:
        if receipt != self._receipt:
            return OutputExecutorAbortDisposition.STALE
        handle = self._handle
        if handle is not None:
            return self._abort_current(handle, reason)
        return OutputExecutorAbortDisposition.STALE

    # AudioOutputExecutorPort signature. Kept separate from the C1 handle API
    # through a small dispatcher so existing generation tests remain valid.
    def abort(self, handle_or_receipt, reason: str) -> OutputExecutorAbortDisposition:
        if isinstance(handle_or_receipt, str):
            return self.abort_receipt(handle_or_receipt, reason)
        handle = handle_or_receipt
        if self._handle is None or handle != self._handle:
            return OutputExecutorAbortDisposition.STALE
        return self._abort_current(handle, reason)

    def _abort_current(
        self, handle: DirectExecutionHandle, reason: str
    ) -> OutputExecutorAbortDisposition:
        was_committed = self._state is DirectExecutionState.COMMITTED
        self._discard_staged_load(handle)
        if self._signal_truth is not None and self._signal_identity is not None:
            if was_committed:
                self._signal_truth.terminate(self._signal_identity)
            else:
                self._signal_truth.discard_candidate(self._signal_identity)
        committed = self._committed
        if (
            reason == "load_failed"
            and committed is not None
            and committed.handle != handle
        ):
            self._restore(committed)
            self._committed = None
            return OutputExecutorAbortDisposition.PREDECESSOR_RESTORED
        self._clear()
        return OutputExecutorAbortDisposition.CANDIDATE_DISCARDED

    def mark_previous_source_released(self) -> None:
        """Record the backend's destructive load boundary.

        Called by the canonical GStreamer port only after the old pipeline
        reached NULL. A provisional Direct candidate remains current, but its
        rollback image is no longer physically valid. A committed Direct
        execution crossed by a Shared load is removed altogether.
        """
        if self._state is DirectExecutionState.COMMITTED:
            if self._signal_truth is not None and self._signal_identity is not None:
                self._signal_truth.retire_active(self._signal_identity)
            self._clear()
            return
        if (
            self._signal_truth is not None
            and self._committed is not None
            and self._committed.signal_identity is not None
        ):
            self._signal_truth.retire_active(self._committed.signal_identity)
        self._committed = None

    def begin_runtime(
        self, handle: DirectExecutionHandle, *, port_generation: int
    ) -> SignalTruthIdentity | None:
        """Start candidate evidence once the port owns its real generation."""
        self._require_current(handle)
        plan = self._plan
        if plan is None or self._signal_truth is None:
            return None
        identity = SignalTruthIdentity(
            plan_id=plan.plan_id,
            execution_generation=handle.generation,
            port_generation=port_generation,
            binding_generation=plan.binding.generation,
            stable_device_id=plan.stable_device_id,
            stable_endpoint_signature=plan.binding.stable_endpoint_signature,
        )
        self._signal_identity = identity
        self._signal_truth.begin_candidate(
            OutputPlanEvidence(
                identity=identity,
                requested_pcm=plan.requested_pcm,
                sink_factory=plan.sink.factory,
                sink_device=plan.sink.device,
                fixed_gain_required=plan.volume_policy is VolumePolicy.FIXED,
            )
        )
        source = plan.source_file_facts
        if source is not None:
            self._signal_truth.observe(
                SourceFileFactsEvidence(
                    identity=identity,
                    container=source.container,
                    codec=source.codec,
                    nominal_pcm=source.nominal_pcm,
                )
            )
        return identity

    def owns_committed_receipt(self, receipt: str) -> bool:
        return (
            self._state is DirectExecutionState.COMMITTED
            and self._receipt == receipt
            and self._handle is not None
        )

    def recipe_for_load(self, handle: DirectExecutionHandle) -> StrictSinkRecipe:
        """Receta de la ejecución vigente; un handle stale jamás la roba."""
        self._require_current(handle)
        if self._state is DirectExecutionState.IDLE or self._recipe is None:
            raise DirectExecutorError(
                "DIRECT_EXECUTION_NOT_STAGED", "sin ejecución staged vigente"
            )
        return self._recipe

    def verify_preroll(
        self,
        handle: DirectExecutionHandle,
        snapshot: DirectRuntimeSnapshot,
    ) -> DirectPrerollEvidence:
        """Valida generación ANTES de validate_runtime; fail-closed."""
        self._require_current(handle)
        if snapshot.execution_generation != handle.generation:
            raise DirectExecutorError(
                "DIRECT_STALE_EXECUTION",
                f"snapshot generation {snapshot.execution_generation} != "
                f"{handle.generation}",
            )
        if snapshot.plan_id != handle.plan_id:
            raise DirectExecutorError(
                "DIRECT_STALE_EXECUTION",
                f"snapshot plan_id {snapshot.plan_id!r} != {handle.plan_id!r}",
            )
        assert self._recipe is not None  # garantizado por _require_current
        self._record_signal_runtime(snapshot)
        try:
            evidence = validate_runtime(self._recipe, snapshot)
        except Exception:
            # Un mismatch deja la ejecución en STAGED sin evidencia.
            self._evidence = None
            self._state = DirectExecutionState.STAGED
            raise
        self._evidence = evidence
        self._state = DirectExecutionState.PREROLL_VERIFIED
        return evidence

    def _record_signal_runtime(self, snapshot: DirectRuntimeSnapshot) -> None:
        recorder = self._signal_truth
        identity = self._signal_identity
        plan = self._plan
        if recorder is None or identity is None or plan is None:
            return
        if (
            snapshot.decoded_format is not None
            and snapshot.decoded_rate_hz is not None
            and snapshot.decoded_channels is not None
        ):
            recorder.observe(
                DecodedRuntimeEvidence(
                    identity,
                    PcmTuple(
                        snapshot.decoded_rate_hz,
                        snapshot.decoded_format,
                        snapshot.decoded_channels,
                        snapshot.decoded_significant_bits,
                    ),
                )
            )
        effective = None
        if (
            snapshot.negotiated_format is not None
            and snapshot.negotiated_rate_hz is not None
            and snapshot.negotiated_channels is not None
        ):
            effective = PcmTuple(
                snapshot.negotiated_rate_hz,
                snapshot.negotiated_format,
                snapshot.negotiated_channels,
                snapshot.effective_significant_bits,
            )
        recorder.observe(
            EngineRuntimeEvidence(
                identity=identity,
                effective_pcm=effective,
                sink_factory=snapshot.sink_factory,
                sink_device=snapshot.sink_device,
                graph_factories=snapshot.graph_factories,
                graph_inspection_complete=snapshot.graph_inspection_complete,
                software_gain=snapshot.software_gain,
                muted=snapshot.muted,
                sink_provides_clock=snapshot.sink_provides_clock,
                sink_clock_is_pipeline_clock=snapshot.sink_clock_is_pipeline_clock,
                slave_method=snapshot.slave_method,
                transform_evidence=snapshot.transform_evidence,
            )
        )
        observer = self._alsa_runtime_observer
        if observer is not None:
            alsa = observer.observe(identity, plan.binding)
            if alsa is not None:
                recorder.observe(alsa)

    def record_runtime_anomaly(
        self, handle: DirectExecutionHandle, detail: str
    ) -> bool:
        """Record an ERROR/XRUN observation without owning recovery policy."""
        self._require_current(handle)
        if self._signal_truth is None or self._signal_identity is None:
            return False
        kind = (
            RuntimeAnomalyKind.XRUN
            if re.search(r"\bxrun\b", detail, flags=re.IGNORECASE)
            else RuntimeAnomalyKind.ERROR
        )
        return self._signal_truth.observe(
            RuntimeAnomalyEvidence(self._signal_identity, kind, detail)
        )

    def is_preroll_verified(self, handle: DirectExecutionHandle) -> bool:
        if self._handle is None or handle != self._handle:
            return False
        if self._state not in (
            DirectExecutionState.PREROLL_VERIFIED,
            DirectExecutionState.COMMITTED,
        ):
            return False
        evidence = self._evidence
        if evidence is None:
            return False
        return (
            evidence.execution_generation == handle.generation
            and evidence.plan_id == handle.plan_id
        )

    def evidence_for(
        self, handle: DirectExecutionHandle
    ) -> DirectPrerollEvidence | None:
        if self._handle is None or handle != self._handle:
            return None
        if self._state not in (
            DirectExecutionState.PREROLL_VERIFIED,
            DirectExecutionState.COMMITTED,
        ):
            return None
        return self._evidence

    # ── terminación ───────────────────────────────────────────────────
    def release(self, reason: str) -> None:
        """Libera la ejecución actual (idempotente)."""
        handle = self._handle
        if handle is not None:
            self._discard_staged_load(handle)
        if self._signal_truth is not None:
            if self._signal_identity is not None:
                self._signal_truth.terminate(self._signal_identity)
            if (
                self._committed is not None
                and self._committed.signal_identity is not None
            ):
                self._signal_truth.terminate(self._committed.signal_identity)
        self._clear()

    def _discard_staged_load(self, handle: DirectExecutionHandle) -> None:
        provider = self._port_provider
        if provider is None:
            return
        port = provider()
        if port is not None:
            port.discard_direct_load(handle, executor=self)

    def _clear(self) -> None:
        self._handle = None
        self._plan = None
        self._recipe = None
        self._evidence = None
        self._receipt = None
        self._signal_identity = None
        self._committed = None
        self._state = DirectExecutionState.IDLE

    def _snapshot_current(self) -> _ExecutionSnapshot | None:
        if (
            self._handle is None
            or self._plan is None
            or self._recipe is None
            or self._receipt is None
            or self._state is DirectExecutionState.IDLE
        ):
            return None
        return _ExecutionSnapshot(
            state=self._state,
            handle=self._handle,
            plan=self._plan,
            recipe=self._recipe,
            evidence=self._evidence,
            receipt=self._receipt,
            signal_identity=self._signal_identity,
        )

    def _restore(self, snapshot: _ExecutionSnapshot | None) -> None:
        if snapshot is None:
            self._handle = None
            self._plan = None
            self._recipe = None
            self._evidence = None
            self._receipt = None
            self._signal_identity = None
            self._state = DirectExecutionState.IDLE
            return
        self._state = snapshot.state
        self._handle = snapshot.handle
        self._plan = snapshot.plan
        self._recipe = snapshot.recipe
        self._evidence = snapshot.evidence
        self._receipt = snapshot.receipt
        self._signal_identity = snapshot.signal_identity

    # ── internos ──────────────────────────────────────────────────────
    def _require_current(self, handle: DirectExecutionHandle) -> None:
        if self._handle is None or handle != self._handle:
            raise DirectExecutorError(
                "DIRECT_STALE_EXECUTION", "handle no es la ejecución vigente"
            )

    def _require_receipt(self, receipt: str) -> None:
        if self._receipt is None or receipt != self._receipt:
            raise DirectExecutorError(
                "DIRECT_STALE_EXECUTION", "receipt is not the current execution"
            )
