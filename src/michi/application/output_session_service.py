"""DAC-V35-040 — OutputSessionService (spec §0H.2/§21/§22/§403).

Implementa `PlaybackOutputTransactionPort` y es dueño de prepare/commit/
abort/release. NO selecciona el próximo track ni muta PlaybackState.

La state machine §21 valida transiciones; los callbacks de generations
viejas se descartan. Si el DAC seleccionado desaparece, el selected se
conserva, el active pasa a None y la sesión queda LOST (§22).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from michi.application.audio_output_planner import (
    OutputPlanner,
    PlannerFacts,
    PlannerRefusal,
)
from michi.domain.audio_output import (
    OutputPlan,
    OutputSelectionState,
    OutputSessionState,
)

_ACTIVE_STATES = frozenset(
    {
        OutputSessionState.READY,
        OutputSessionState.RUNNING,
        OutputSessionState.PAUSED,
        OutputSessionState.RECONFIGURING,
        OutputSessionState.RECOVERING,
    }
)

_ALLOWED_TRANSITIONS: dict[OutputSessionState, frozenset[OutputSessionState]] = {
    OutputSessionState.IDLE: frozenset(
        {OutputSessionState.ACQUIRING, OutputSessionState.FAILED}
    ),
    OutputSessionState.ACQUIRING: frozenset(
        {
            OutputSessionState.CONFIGURING,
            OutputSessionState.IDLE,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.CONFIGURING: frozenset(
        {
            OutputSessionState.READY,
            OutputSessionState.IDLE,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.READY: frozenset(
        {
            OutputSessionState.RUNNING,
            OutputSessionState.RELEASING,
            OutputSessionState.RECONFIGURING,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.RUNNING: frozenset(
        {
            OutputSessionState.PAUSED,
            OutputSessionState.RELEASING,
            OutputSessionState.RECONFIGURING,
            OutputSessionState.RECOVERING,
            OutputSessionState.LOST,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.PAUSED: frozenset(
        {
            OutputSessionState.RUNNING,
            OutputSessionState.RELEASING,
            OutputSessionState.LOST,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.RECONFIGURING: frozenset(
        {
            OutputSessionState.READY,
            OutputSessionState.RUNNING,
            OutputSessionState.LOST,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.RECOVERING: frozenset(
        {
            OutputSessionState.READY,
            OutputSessionState.RUNNING,
            OutputSessionState.LOST,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.LOST: frozenset(
        {
            OutputSessionState.IDLE,
            OutputSessionState.ACQUIRING,
            OutputSessionState.RELEASING,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.FAILED: frozenset(
        {OutputSessionState.IDLE, OutputSessionState.RELEASING}
    ),
    OutputSessionState.RELEASING: frozenset(
        {OutputSessionState.IDLE, OutputSessionState.FAILED}
    ),
}


class OutputSessionError(RuntimeError):
    """Error tipado de sesión (illegal_transition, no_plan, stale_token)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class OutputSessionService:
    """Implementa el PlaybackOutputTransactionPort canónico (§0H.2).

    `prepare_for_media(path)` NO recibe OutputPlan: el assembly de
    planning/device/evidencia ocurre detrás de este subsistema vía el
    `facts_provider` inyectado por el wiring productivo.
    """

    def __init__(
        self,
        planner: OutputPlanner,
        *,
        facts_provider: Callable[[Path], PlannerFacts] | None = None,
    ) -> None:
        self._planner = planner
        self._facts_provider = facts_provider
        self._state = OutputSessionState.IDLE
        self._generation = 0
        self._session_id: str | None = None
        self._plan: OutputPlan | None = None
        self._selected_device_id: str | None = None
        self._selected_profile_id: str | None = None
        self._error_code: str | None = None

    # ── lectura ───────────────────────────────────────────────────────
    @property
    def state(self) -> OutputSessionState:
        return self._state

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def plan(self) -> OutputPlan | None:
        return self._plan

    def selection_state(self) -> OutputSelectionState:
        active = self._plan is not None and self._state in _ACTIVE_STATES
        return OutputSelectionState(
            selected_device_id=self._selected_device_id,
            selected_profile_id=self._selected_profile_id,
            active_device_id=self._plan.stable_device_id if active else None,
            active_plan_id=self._plan.plan_id if active else None,
            session_state=self._state,
            error_code=self._error_code,
        )

    def select(self, *, device_id: str | None, profile_id: str | None) -> None:
        """El intent seleccionado persiste aunque el device desaparezca."""
        self._selected_device_id = device_id
        self._selected_profile_id = profile_id

    # ── planificación ─────────────────────────────────────────────────
    def plan_for(self, facts: PlannerFacts) -> OutputPlan | PlannerRefusal:
        return self._planner.plan(facts)

    # ── PlaybackOutputTransactionPort (§0H.2) ─────────────────────────
    def prepare_for_media(self, path: Path) -> str:
        """Planifica internamente y devuelve un token opaco (READY).

        Firma EXACTA del port: PlaybackService nunca ve un OutputPlan.
        """
        facts = self._facts_for(path)
        result = self._planner.plan(facts)
        if isinstance(result, PlannerRefusal):
            raise OutputSessionError(result.code, result.detail)
        return self._begin_session(result)

    def _facts_for(self, path: Path) -> PlannerFacts:
        if self._facts_provider is None:
            raise OutputSessionError(
                "no_plan_source",
                "OutputSessionService sin facts_provider configurado",
            )
        return self._facts_provider(path)

    def _begin_session(self, plan: OutputPlan) -> str:
        if self._state is not OutputSessionState.IDLE:
            if self._state in (OutputSessionState.READY, OutputSessionState.RUNNING):
                # re-preparación explícita: reconfigure.
                self._transition(OutputSessionState.RELEASING)
                self._transition(OutputSessionState.IDLE)
            else:
                raise OutputSessionError(
                    "illegal_transition",
                    f"prepare desde {self._state.value}",
                )
        self._transition(OutputSessionState.ACQUIRING)
        self._generation += 1
        self._plan = plan
        self._session_id = f"session:{self._generation}"
        self._error_code = None
        self._transition(OutputSessionState.CONFIGURING)
        self._transition(OutputSessionState.READY)
        return self._token()

    def commit_media(self, token: str, path: Path) -> None:
        if self._is_stale(token):
            return  # callback de generation vieja: descartado (§21)
        if self._state is not OutputSessionState.READY:
            raise OutputSessionError(
                "illegal_transition", f"commit desde {self._state.value}"
            )
        self._transition(OutputSessionState.RUNNING)

    def abort_media(self, token: str, reason: str) -> None:
        if self._is_stale(token):
            return
        self._error_code = reason
        self._transition(OutputSessionState.RELEASING)
        self._plan = None
        self._transition(OutputSessionState.IDLE)

    def release_active(self, reason: str) -> None:
        if self._state is OutputSessionState.IDLE:
            return
        self._error_code = reason
        if self._state is not OutputSessionState.RELEASING:
            self._transition(OutputSessionState.RELEASING)
        self._plan = None
        self._transition(OutputSessionState.IDLE)

    # ── topología / fallas ────────────────────────────────────────────
    def device_lost(self) -> None:
        """§22: selected se conserva, active pasa a None, sesión LOST."""
        if self._state is OutputSessionState.IDLE:
            return
        self._transition(OutputSessionState.LOST)
        self._plan = None

    def fail(self, error_code: str) -> None:
        self._error_code = error_code
        if self._state is not OutputSessionState.FAILED:
            self._transition(OutputSessionState.FAILED)

    def mark_running(self) -> None:
        """Transición explícita usada por el executor (050) al preroll."""
        self._transition(OutputSessionState.RUNNING)

    # ── internos ──────────────────────────────────────────────────────
    def _token(self) -> str:
        return f"output-tx:{self._session_id}:{self._generation}"

    def _is_stale(self, token: str) -> bool:
        return token != self._token()

    def _transition(self, target: OutputSessionState) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self._state, frozenset())
        if target not in allowed:
            raise OutputSessionError(
                "illegal_transition",
                f"{self._state.value} -> {target.value}",
            )
        self._state = target
