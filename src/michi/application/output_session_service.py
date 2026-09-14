"""DAC-V35-040 — OutputSessionService (spec §0H.2/§21/§22/§403).

Implementa `PlaybackOutputTransactionPort` y es dueño de prepare/commit/
abort/release. NO selecciona el próximo track ni muta PlaybackState.

La state machine §21 valida transiciones; los callbacks de generations
viejas se descartan. Si el DAC seleccionado desaparece, el selected se
conserva, el active pasa a None y la sesión queda LOST (§22).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from michi.application.audio_output_planner import (
    OutputPlanner,
    PlannerFacts,
    PlannerRefusal,
)
from michi.application.audio_output_ports import (
    AudioOutputExecutorPort,
    OutputExecutorAbortDisposition,
)
from michi.application.ports import SharedOutputTransaction
from michi.domain.audio_device import BindingKind
from michi.domain.audio_evidence import DecodedSourceSignal
from michi.domain.audio_output import (
    FallbackKind,
    OutputPathPreference,
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
            OutputSessionState.LOST,
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


@dataclass(frozen=True, slots=True)
class OutputRequest:
    """Resolved output intent for one media path.

    ``facts is None`` is the explicit Shared path. A Direct request always
    carries complete planner facts; the executor never resolves policy again.
    """

    facts: PlannerFacts | None
    selected_device_id: str | None = None
    selected_profile_id: str | None = None

    @classmethod
    def shared(cls) -> OutputRequest:
        return cls(None)

    @classmethod
    def direct(cls, facts: PlannerFacts) -> OutputRequest:
        profile_id = facts.profile.profile_id if facts.profile is not None else None
        return cls(facts, facts.selected_device_id, profile_id)


@dataclass(frozen=True, slots=True)
class _DirectSessionSnapshot:
    """Private rollback image of the one committed Direct session."""

    plan: OutputPlan
    executor: AudioOutputExecutorPort
    receipt: str
    state: OutputSessionState
    path: Path | None
    selected_device_id: str | None
    selected_profile_id: str | None


class ProductiveOutputRequestResolver:
    """Assembles planner facts from canonical read authorities only."""

    def __init__(
        self,
        *,
        profiles,
        devices,
        qualification,
        engines,
        source_metadata,
    ) -> None:
        self._profiles = profiles
        self._devices = devices
        self._qualification = qualification
        self._engines = engines
        self._source_metadata = source_metadata

    def __call__(self, path: Path) -> OutputRequest:
        selection = self._profiles.load_selection()
        if selection.selected_profile_id is None:
            return OutputRequest.shared()
        profile = next(
            (
                item
                for item in self._profiles.load_profiles()
                if item.profile_id == selection.selected_profile_id
            ),
            None,
        )
        if profile is None:
            raise OutputSessionError(
                "SELECTED_PROFILE_MISSING",
                f"selected profile {selection.selected_profile_id!r} does not exist",
            )
        if profile.path is not OutputPathPreference.HARDWARE_DIRECT:
            return OutputRequest(
                None,
                selection.selected_device_id,
                selection.selected_profile_id,
            )
        selected_device_id = selection.selected_device_id or profile.stable_device_id
        metadata = self._source_metadata.extract(path)
        source = DecodedSourceSignal(
            encoding="pcm",
            rate_hz=metadata.sample_rate_hz,
            significant_bits=metadata.bit_depth or None,
            channels=metadata.channels,
            channel_positions=None,
        )
        active = self._engines.state.active_engine_id
        binding = None
        expected_generation = None
        available = False
        evidence = ()
        if selected_device_id is not None:
            bindings = self._devices.bindings_for(
                selected_device_id, BindingKind.ALSA_PCM
            )
            if len(bindings) > 1:
                raise OutputSessionError(
                    "MULTIPLE_ALSA_PLAYBACK_ENDPOINTS",
                    f"device {selected_device_id!r} has {len(bindings)} current "
                    "ALSA playback endpoints; explicit endpoint intent is required",
                )
            if bindings:
                (binding,) = bindings  # exact-one proof; ambiguity rejected above
            expected_generation = self._devices.generation_for(selected_device_id)
            available = selected_device_id in self._devices.available_ids()
            evidence = self._qualification.cached_evidence_current(selected_device_id)
        facts = PlannerFacts(
            active_engine_id=active.value if active is not None else "",
            profile=profile,
            selected_device_id=selected_device_id,
            binding=binding,
            source=source,
            evidence=evidence,
            expected_binding_generation=expected_generation,
            device_available=available,
        )
        return OutputRequest(
            facts,
            selected_device_id,
            selection.selected_profile_id,
        )


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
        request_provider: Callable[[Path], OutputRequest] | None = None,
        executors: Mapping[str, AudioOutputExecutorPort] | None = None,
        shared_transaction: SharedOutputTransaction | None = None,
    ) -> None:
        self._planner = planner
        self._facts_provider = facts_provider
        self._request_provider = request_provider
        self._executors = dict(executors or {})
        self._shared = shared_transaction or SharedOutputTransaction()
        self._state = OutputSessionState.IDLE
        self._generation = 0
        self._session_id: str | None = None
        self._plan: OutputPlan | None = None
        self._selected_device_id: str | None = None
        self._selected_profile_id: str | None = None
        self._error_code: str | None = None
        self._mode = "shared"
        self._path: Path | None = None
        self._token_value: str | None = None
        self._executor: AudioOutputExecutorPort | None = None
        self._executor_receipt: str | None = None
        self._shared_receipt: str | None = None
        self._previous_direct: _DirectSessionSnapshot | None = None
        self._lost_fallback: FallbackKind | None = None
        self._last_release_invalidated_media = False

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

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def release_invalidates_media(self) -> bool:
        return self._last_release_invalidated_media

    @property
    def requires_release_on_media_loss(self) -> bool:
        return self._mode == "direct" and self._executor is not None

    def allows_automatic_engine_fallback(self) -> bool:
        plan = self._plan
        if plan is None and self._previous_direct is not None:
            plan = self._previous_direct.plan
        fallback = plan.fallback if plan is not None else self._lost_fallback
        return fallback is not FallbackKind.STOP

    def classify_load_failure(self, previous_source_preserved: bool) -> str:
        """Retain a prior Direct lease only when the backend retained its source."""
        return "load_failed" if previous_source_preserved else "load_failed_source_lost"

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
        if self._state not in (
            OutputSessionState.IDLE,
            OutputSessionState.READY,
            OutputSessionState.RUNNING,
        ):
            raise OutputSessionError(
                "illegal_transition", f"prepare desde {self._state.value}"
            )
        request = self._request_for(path)
        previous_direct = self._committed_direct_snapshot()
        self._selected_device_id = request.selected_device_id
        self._selected_profile_id = request.selected_profile_id
        if request.facts is None:
            return self._prepare_shared(path, previous_direct=previous_direct)
        result = self._planner.plan(request.facts)
        if isinstance(result, PlannerRefusal):
            raise OutputSessionError(result.code, result.detail)
        executor = self._executors.get(result.engine_id)
        if executor is None:
            raise OutputSessionError(
                "ENGINE_UNSUPPORTED_FOR_DIRECT",
                f"no Direct executor for engine {result.engine_id!r}",
            )
        try:
            receipt = executor.prepare(result)
        except Exception as exc:
            code = getattr(exc, "code", "DIRECT_EXECUTOR_PREPARE_FAILED")
            raise OutputSessionError(code, str(exc)) from exc
        if self._mode == "shared" and self._shared_receipt is not None:
            self._shared.abort_media(self._shared_receipt, "superseded")
        return self._begin_session(
            result,
            path,
            executor,
            receipt,
            previous_direct=previous_direct,
        )

    def _request_for(self, path: Path) -> OutputRequest:
        if self._request_provider is not None:
            return self._request_provider(path)
        return OutputRequest.direct(self._facts_for(path))

    def _prepare_shared(
        self,
        path: Path,
        *,
        previous_direct: _DirectSessionSnapshot | None,
    ) -> str:
        old_shared_receipt = self._shared_receipt if self._mode == "shared" else None
        receipt = self._shared.prepare_for_media(path)
        if (
            self._mode == "direct"
            and self._state is OutputSessionState.READY
            and self._executor is not None
            and self._executor_receipt is not None
        ):
            try:
                disposition = self._executor.abort(
                    self._executor_receipt, "load_failed"
                )
            except Exception as exc:
                self._shared.abort_media(receipt, "direct_cancel_failed")
                code = getattr(exc, "code", "DIRECT_EXECUTOR_ABORT_FAILED")
                raise OutputSessionError(code, str(exc)) from exc
            if disposition is OutputExecutorAbortDisposition.STALE:
                self._shared.abort_media(receipt, "direct_restore_failed")
                raise OutputSessionError(
                    "DIRECT_EXECUTION_STALE",
                    "provisional Direct candidate no longer owns the executor",
                )
            if disposition is OutputExecutorAbortDisposition.CANDIDATE_DISCARDED:
                # The executor is the physical rollback authority. A logical
                # snapshot may survive the destructive boundary, but it is no
                # longer eligible to restore and must not follow Shared C.
                previous_direct = None
        if old_shared_receipt is not None and old_shared_receipt != receipt:
            self._shared.abort_media(old_shared_receipt, "superseded")
        self._generation += 1
        self._mode = "shared"
        self._path = Path(path)
        self._plan = None
        self._executor = None
        self._executor_receipt = None
        self._shared_receipt = receipt
        self._previous_direct = previous_direct
        self._token_value = f"output-tx:shared:{self._generation}"
        self._error_code = None
        self._last_release_invalidated_media = False
        self._lost_fallback = None
        if self._state is not OutputSessionState.IDLE:
            self._state = OutputSessionState.IDLE
        return self._token_value

    def _facts_for(self, path: Path) -> PlannerFacts:
        if self._facts_provider is None:
            raise OutputSessionError(
                "no_plan_source",
                "OutputSessionService sin facts_provider configurado",
            )
        return self._facts_provider(path)

    def _begin_session(
        self,
        plan: OutputPlan,
        path: Path,
        executor: AudioOutputExecutorPort,
        receipt: str,
        *,
        previous_direct: _DirectSessionSnapshot | None = None,
    ) -> str:
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
        self._path = Path(path)
        self._mode = "direct"
        self._executor = executor
        self._executor_receipt = receipt
        self._shared_receipt = None
        self._previous_direct = previous_direct
        self._session_id = f"session:{self._generation}"
        self._error_code = None
        self._transition(OutputSessionState.CONFIGURING)
        self._transition(OutputSessionState.READY)
        self._token_value = self._token()
        self._last_release_invalidated_media = False
        self._lost_fallback = None
        return self._token_value

    def commit_media(self, token: str, path: Path) -> None:
        if self._is_stale(token):
            return  # callback de generation vieja: descartado (§21)
        if self._path != Path(path):
            raise OutputSessionError("stale_path", "commit path does not own token")
        if self._mode == "shared":
            assert self._shared_receipt is not None
            self._shared.commit_media(self._shared_receipt, path)
            if self._previous_direct is not None:
                self._previous_direct.executor.release("switch_to_shared")
                self._previous_direct = None
            self._plan = None
            self._state = OutputSessionState.IDLE
            return
        if self._state is not OutputSessionState.READY:
            raise OutputSessionError(
                "illegal_transition", f"commit desde {self._state.value}"
            )
        assert self._executor is not None and self._executor_receipt is not None
        self._executor.commit(self._executor_receipt)
        self._previous_direct = None
        self._transition(OutputSessionState.RUNNING)

    def abort_media(self, token: str, reason: str) -> None:
        if self._is_stale(token):
            return
        if self._mode == "shared":
            if self._shared_receipt is not None:
                self._shared.abort_media(self._shared_receipt, reason)
            previous_is_live = True
            if self._previous_direct is not None:
                owns_committed = getattr(
                    self._previous_direct.executor, "owns_committed_receipt", None
                )
                if owns_committed is not None:
                    previous_is_live = owns_committed(self._previous_direct.receipt)
            if (
                self._previous_direct is not None
                and reason == "load_failed"
                and previous_is_live
            ):
                previous = self._previous_direct
                self._plan = previous.plan
                self._executor = previous.executor
                self._executor_receipt = previous.receipt
                self._state = previous.state
                self._path = previous.path
                self._selected_device_id = previous.selected_device_id
                self._selected_profile_id = previous.selected_profile_id
                self._mode = "direct"
                self._token_value = None
                self._shared_receipt = None
                self._previous_direct = None
                self._error_code = reason
                return
            if self._previous_direct is not None:
                self._previous_direct.executor.release(reason)
            self._clear_execution()
            return
        self._error_code = reason
        disposition = OutputExecutorAbortDisposition.STALE
        if self._executor is not None and self._executor_receipt is not None:
            disposition = self._executor.abort(self._executor_receipt, reason)
        if (
            self._previous_direct is not None
            and reason == "load_failed"
            and disposition is OutputExecutorAbortDisposition.PREDECESSOR_RESTORED
        ):
            previous = self._previous_direct
            self._plan = previous.plan
            self._executor = previous.executor
            self._executor_receipt = previous.receipt
            self._state = previous.state
            self._path = previous.path
            self._selected_device_id = previous.selected_device_id
            self._selected_profile_id = previous.selected_profile_id
            self._token_value = None
            self._previous_direct = None
            return
        self._transition(OutputSessionState.RELEASING)
        self._clear_execution(keep_error=True)
        self._transition(OutputSessionState.IDLE)

    def release_active(self, reason: str) -> None:
        was_direct = self._mode == "direct" and self._executor is not None
        self._last_release_invalidated_media = was_direct
        if self._mode == "shared":
            self._shared.release_active(reason)
            if self._previous_direct is not None:
                self._previous_direct.executor.release(reason)
            self._clear_execution()
            return
        if self._state is OutputSessionState.IDLE and not was_direct:
            return
        self._error_code = reason
        if self._executor is not None:
            self._executor.release(reason)
        if self._state is not OutputSessionState.RELEASING:
            self._transition(OutputSessionState.RELEASING)
        self._clear_execution(keep_error=True)
        self._transition(OutputSessionState.IDLE)

    # ── topología / fallas ────────────────────────────────────────────
    def device_lost(self) -> None:
        """§22: selected se conserva, active pasa a None, sesión LOST."""
        if self._state is OutputSessionState.IDLE:
            return
        self._lost_fallback = self._plan.fallback if self._plan is not None else None
        if self._executor is not None:
            self._executor.release("device_lost")
        self._executor = None
        self._executor_receipt = None
        self._shared_receipt = None
        self._previous_direct = None
        self._token_value = None
        self._transition(OutputSessionState.LOST)
        self._plan = None
        self._error_code = "device_lost"

    def fail(self, error_code: str) -> None:
        self._error_code = error_code
        if self._state is not OutputSessionState.FAILED:
            self._transition(OutputSessionState.FAILED)

    # ── internos ──────────────────────────────────────────────────────
    def _committed_direct_snapshot(self) -> _DirectSessionSnapshot | None:
        # A second/third candidate never becomes rollback authority. While a
        # candidate is READY, `_previous_direct` still identifies committed A.
        if self._previous_direct is not None:
            return self._previous_direct
        if (
            self._mode != "direct"
            or self._state
            not in (OutputSessionState.RUNNING, OutputSessionState.PAUSED)
            or self._plan is None
            or self._executor is None
            or self._executor_receipt is None
        ):
            return None
        return _DirectSessionSnapshot(
            plan=self._plan,
            executor=self._executor,
            receipt=self._executor_receipt,
            state=self._state,
            path=self._path,
            selected_device_id=self._selected_device_id,
            selected_profile_id=self._selected_profile_id,
        )

    def _token(self) -> str:
        return f"output-tx:{self._session_id}:{self._generation}"

    def _is_stale(self, token: str) -> bool:
        return self._token_value is None or token != self._token_value

    def _clear_execution(self, *, keep_error: bool = False) -> None:
        self._plan = None
        self._path = None
        self._token_value = None
        self._executor = None
        self._executor_receipt = None
        self._shared_receipt = None
        self._previous_direct = None
        self._lost_fallback = None
        self._mode = "shared"
        if not keep_error:
            self._error_code = None

    def _transition(self, target: OutputSessionState) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self._state, frozenset())
        if target not in allowed:
            raise OutputSessionError(
                "illegal_transition",
                f"{self._state.value} -> {target.value}",
            )
        self._state = target
