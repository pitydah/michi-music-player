"""DAC-V35-050C1 — GStreamerDirectOutputExecutor core (spec §404).

Núcleo puro: OutputPlan -> StrictSinkRecipe -> execution_generation ->
DirectRuntimeSnapshot -> validate_runtime() -> DirectPrerollEvidence.

NO importa gi/Gst/GLib. NO conoce GStreamerAudioPort, OutputSession ni
PlaybackService. PREROLL VERIFIED != RUNNING: la sesión no se toca.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_output import OutputPlan
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

    def __post_init__(self) -> None:
        if self.handle.plan_id != self.recipe.plan_id:
            raise DirectExecutorError(
                "DIRECT_STAGE_IDENTITY_MISMATCH",
                "handle and strict recipe belong to different plans",
            )


class DirectLoadStagePort(Protocol):
    def stage_direct_load(
        self,
        preparation: DirectLoadPreparation,
        *,
        executor: GStreamerDirectOutputExecutor,
    ) -> None: ...


class GStreamerDirectOutputExecutor:
    """Sidecar de una única ejecución staged (sin cola, sin authority)."""

    def __init__(self) -> None:
        self._generation = 0
        self._state = DirectExecutionState.IDLE
        self._handle: DirectExecutionHandle | None = None
        self._recipe: StrictSinkRecipe | None = None
        self._evidence: DirectPrerollEvidence | None = None
        self._receipt: str | None = None
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
        self._recipe = recipe
        self._evidence = None
        self._receipt = None
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

        # Build/validate before replacing current execution. If recipe creation
        # fails, the previous execution remains untouched.
        recipe = recipe_from_plan(plan)
        previous = (
            self._generation,
            self._state,
            self._handle,
            self._recipe,
            self._evidence,
            self._receipt,
        )
        self._generation += 1
        handle = DirectExecutionHandle(self._generation, plan.plan_id)
        preparation = DirectLoadPreparation(handle, recipe)
        receipt = f"direct:{handle.generation}:{handle.plan_id}"
        self._state = DirectExecutionState.STAGED
        self._handle = handle
        self._recipe = recipe
        self._evidence = None
        self._receipt = receipt
        try:
            port.stage_direct_load(preparation, executor=self)
        except Exception:
            (
                self._generation,
                self._state,
                self._handle,
                self._recipe,
                self._evidence,
                self._receipt,
            ) = previous
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

    def abort_receipt(self, receipt: str, reason: str) -> None:
        if receipt != self._receipt:
            return
        handle = self._handle
        if handle is not None:
            self.abort(handle, reason)

    # AudioOutputExecutorPort signature. Kept separate from the C1 handle API
    # through a small dispatcher so existing generation tests remain valid.
    def abort(self, handle_or_receipt, reason: str) -> None:
        if isinstance(handle_or_receipt, str):
            self.abort_receipt(handle_or_receipt, reason)
            return
        handle = handle_or_receipt
        if self._handle is None or handle != self._handle:
            return
        self._clear()

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

    def is_preroll_verified(self, handle: DirectExecutionHandle) -> bool:
        if self._handle is None or handle != self._handle:
            return False
        if self._state is not DirectExecutionState.PREROLL_VERIFIED:
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
        if self._state is not DirectExecutionState.PREROLL_VERIFIED:
            return None
        return self._evidence

    # ── terminación ───────────────────────────────────────────────────
    def release(self, reason: str) -> None:
        """Libera la ejecución actual (idempotente)."""
        self._clear()

    def _clear(self) -> None:
        self._handle = None
        self._recipe = None
        self._evidence = None
        self._receipt = None
        self._state = DirectExecutionState.IDLE

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
