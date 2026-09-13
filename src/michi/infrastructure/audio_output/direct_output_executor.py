"""DAC-V35-050C1 — GStreamerDirectOutputExecutor core (spec §404).

Núcleo puro: OutputPlan -> StrictSinkRecipe -> execution_generation ->
DirectRuntimeSnapshot -> validate_runtime() -> DirectPrerollEvidence.

NO importa gi/Gst/GLib. NO conoce GStreamerAudioPort, OutputSession ni
PlaybackService. PREROLL VERIFIED != RUNNING: la sesión no se toca.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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


class GStreamerDirectOutputExecutor:
    """Sidecar de una única ejecución staged (sin cola, sin authority)."""

    def __init__(self) -> None:
        self._generation = 0
        self._state = DirectExecutionState.IDLE
        self._handle: DirectExecutionHandle | None = None
        self._recipe: StrictSinkRecipe | None = None
        self._evidence: DirectPrerollEvidence | None = None

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
        self._state = DirectExecutionState.STAGED
        return handle

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
    def abort(self, handle: DirectExecutionHandle, reason: str) -> None:
        """Terminaliza la ejecución. Un abort stale NO toca la vigente."""
        if self._handle is None or handle != self._handle:
            return
        self._handle = None
        self._recipe = None
        self._evidence = None
        self._state = DirectExecutionState.IDLE

    def release(self, reason: str) -> None:
        """Libera la ejecución actual (idempotente)."""
        self._handle = None
        self._recipe = None
        self._evidence = None
        self._state = DirectExecutionState.IDLE

    # ── internos ──────────────────────────────────────────────────────
    def _require_current(self, handle: DirectExecutionHandle) -> None:
        if self._handle is None or handle != self._handle:
            raise DirectExecutorError(
                "DIRECT_STALE_EXECUTION", "handle no es la ejecución vigente"
            )
