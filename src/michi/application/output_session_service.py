"""DAC-V35-040 — OutputSessionService (spec §0H.2/§21/§22/§403).

Implementa `PlaybackOutputTransactionPort` y es dueño de prepare/commit/
abort/release. NO selecciona el próximo track ni muta PlaybackState.

La state machine §21 valida transiciones; los callbacks de generations
viejas se descartan. Si el DAC seleccionado desaparece, el selected se
conserva, el active pasa a None y la sesión queda LOST (§22).
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path

from michi.application.audio_output_planner import (
    EXACT_TUPLE_UNKNOWN,
    OutputPlanner,
    PlannerFacts,
    PlannerRefusal,
)
from michi.application.audio_output_ports import (
    AudioOutputExecutorPort,
    OutputCleanupDiagnostic,
    OutputExecutorAbortDisposition,
    SourceCharacterizationError,
    SourceCharacterizerPort,
    VolumeAuthority,
)
from michi.application.carrier_resolution import CandidateCarrierResolver
from michi.application.ports import SharedOutputTransaction
from michi.domain.audio_device import BindingKind
from michi.domain.audio_evidence import PcmTuple, SourceFileFacts
from michi.domain.audio_output import (
    FallbackKind,
    OutputPathPreference,
    OutputPlan,
    OutputSelectionState,
    OutputSessionState,
    VolumePolicy,
    is_direct_path,
)
from michi.domain.managed_pcm_output import ManagedPcmOutputPlan
from michi.domain.signal_truth import OutputFamilyEvent, OutputFamilyState

logger = logging.getLogger(__name__)

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
        {
            OutputSessionState.ACQUIRING,
            OutputSessionState.LOST,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.ACQUIRING: frozenset(
        {
            OutputSessionState.CONFIGURING,
            OutputSessionState.IDLE,
            OutputSessionState.LOST,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.CONFIGURING: frozenset(
        {
            OutputSessionState.READY,
            OutputSessionState.IDLE,
            OutputSessionState.LOST,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.READY: frozenset(
        {
            OutputSessionState.RUNNING,
            OutputSessionState.RELEASING,
            OutputSessionState.RECONFIGURING,
            OutputSessionState.RECOVERING,
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
            OutputSessionState.IDLE,
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
            OutputSessionState.RECOVERING,
            OutputSessionState.RELEASING,
            OutputSessionState.FAILED,
        }
    ),
    OutputSessionState.FAILED: frozenset(
        {
            OutputSessionState.IDLE,
            OutputSessionState.RELEASING,
            OutputSessionState.LOST,
        }
    ),
    OutputSessionState.RELEASING: frozenset(
        {
            OutputSessionState.IDLE,
            OutputSessionState.LOST,
            OutputSessionState.FAILED,
        }
    ),
}


def _has_conclusive_evidence(pcm: PcmTuple, facts: PlannerFacts) -> bool:
    """True when this exact tuple already carries a conclusive claim."""
    key = (pcm.rate_hz, pcm.transport_format, pcm.channels)
    return any(
        item.stable_device_id == facts.selected_device_id
        and (item.tuple.rate_hz, item.tuple.transport_format, item.tuple.channels)
        == key
        and item.supported is not None
        for item in facts.evidence
    )


#: R110 §31: a genuine output release failure. Not a plain "stop" reason.
OUTPUT_RELEASE_FAILED = "OUTPUT_RELEASE_FAILED"


class OutputSessionError(RuntimeError):
    """Error tipado de sesión (illegal_transition, no_plan, stale_token)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class DirectTransitionKind(StrEnum):
    """Auditable classification for one Direct-to-Direct replacement."""

    SAME_TUPLE = "same_tuple"
    RECONFIGURE = "reconfigure"
    REACQUIRE = "reacquire"


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


@dataclass(frozen=True, slots=True)
class ManagedOutputPrepared:
    """Worker-phase managed execution, committed by the owner.

    The application layer never imports the infrastructure receipt: the
    prepared value carries the immutable plan, the execution id and the
    primitive runtime identity the owner needs for the session commit.
    """

    plan: ManagedPcmOutputPlan
    execution_id: str
    runtime_identity: dict


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
        source_characterizer: SourceCharacterizerPort,
    ) -> None:
        self._profiles = profiles
        self._devices = devices
        self._qualification = qualification
        self._engines = engines
        self._source_metadata = source_metadata
        self._source_characterizer = source_characterizer

    def snapshot_output_intent(self):
        """Immutable output-intent snapshot (monotonic revision + ids).

        Duck-typed: legacy/fake providers without the capture simply disable
        the intent fence (the media generation fence still applies).
        """
        capture = getattr(self._profiles, "snapshot_output_intent", None)
        if callable(capture):
            return capture()
        return None

    def pending_device_id(self, path: Path) -> str | None:
        """Cheap selected-device peek for in-flight preparation diagnostics.

        Runs on the owner BEFORE the async worker starts: only the
        selection/profile read (no metadata, no characterization), so a
        topology loss can still cancel the matching pending preparation.
        """
        selection = self._profiles.load_selection()
        if selection.selected_profile_id is None:
            return None
        profile = next(
            (
                item
                for item in self._profiles.load_profiles()
                if item.profile_id == selection.selected_profile_id
            ),
            None,
        )
        if profile is None or not is_direct_path(profile.path):
            return None
        return selection.selected_device_id or profile.stable_device_id

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
        if not is_direct_path(profile.path):
            return OutputRequest(
                None,
                selection.selected_device_id,
                selection.selected_profile_id,
            )
        selected_device_id = selection.selected_device_id or profile.stable_device_id
        metadata = self._source_metadata.extract(path)
        source_file_facts = SourceFileFacts(
            container=metadata.container or None,
            codec=metadata.codec or None,
            nominal_pcm=PcmTuple(
                metadata.sample_rate_hz,
                "",
                metadata.channels,
                # Lossy/zero bit depth is unknown evidence, never fabricated.
                metadata.bit_depth or None,
            ),
        )
        try:
            decoded_source = self._source_characterizer.characterize(path)
        except SourceCharacterizationError as exc:
            raise OutputSessionError(exc.code, exc.detail) from exc
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
            decoded_source=decoded_source,
            source_file_facts=source_file_facts,
            evidence=evidence,
            expected_binding_generation=expected_generation,
            device_available=available,
        )
        return OutputRequest(
            facts,
            selected_device_id,
            selection.selected_profile_id,
        )

    def qualify_request(self, request: OutputRequest) -> OutputRequest:
        """Probe at most the request's one exact tuple and refresh its facts."""
        request, outcome = self.probe_request(request)
        return self.apply_qualification(request, outcome)

    def probe_request(self, request: OutputRequest):
        """Worker phase: bounded exact-open over policy-authorized candidates.

        At most the resolver's candidate set (<= 3) is probed, in priority
        order, and probing stops at the first positive carrier or the first
        inconclusive result. No cache or session mutation happens here.
        """
        facts = request.facts
        if (
            facts is None
            or facts.binding is None
            or facts.selected_device_id is None
            or facts.profile is None
        ):
            return request, None
        candidates = CandidateCarrierResolver().candidates(
            facts.decoded_source,
            allow_adaptation=(
                facts.profile.path is OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE
            ),
        )
        if not candidates:
            return request, None
        outcomes = []
        for candidate in candidates:
            if _has_conclusive_evidence(candidate.tuple, facts):
                continue
            outcome = self._qualification.probe_for_play(
                stable_device_id=facts.selected_device_id,
                locator=facts.binding.locator,
                rate_hz=candidate.tuple.rate_hz,
                transport_format=candidate.tuple.transport_format,
                channels=candidate.tuple.channels,
                binding_generation=facts.expected_binding_generation,
            )
            outcomes.append(outcome)
            if outcome.evidence.supported is not False:
                # Positive carrier found, or BUSY/REMOVED/TIMEOUT: stop.
                break
        return request, tuple(outcomes)

    def apply_qualification(self, request: OutputRequest, outcome) -> OutputRequest:
        """Owner phase: classify, cache, and refresh only a current result."""
        if outcome is None:
            return request
        facts = request.facts
        if facts is None or facts.selected_device_id is None:
            return request
        outcomes = outcome if isinstance(outcome, tuple) else (outcome,)
        if not outcomes:
            return request
        current_fingerprint = self._qualification.current_environment_fingerprint(
            facts.selected_device_id
        )
        for item in outcomes:
            if item.evidence.supported is None:
                disposition = item.disposition.casefold()
                if "busy" in disposition:
                    code = "ALSA_DEVICE_BUSY"
                elif disposition in {"removed", "device_removed", "no_device"}:
                    code = "OUTPUT_DEVICE_LOST"
                elif disposition == "timeout":
                    code = "EXACT_QUALIFICATION_TIMEOUT"
                else:
                    code = "EXACT_QUALIFICATION_INCONCLUSIVE"
                raise OutputSessionError(
                    code,
                    item.detail or f"exact qualification ended as {item.disposition}",
                )
            if item.evidence.environment_fingerprint != current_fingerprint:
                # Topology changed between the worker probe and this commit:
                # never cache, never plan, never claim (R1.3 §20).
                raise OutputSessionError(
                    "EXACT_QUALIFICATION_STALE",
                    "environment changed before owner commit",
                )
        for item in outcomes:
            self._qualification.cache_conclusive_evidence(item.evidence)
        return replace(
            request,
            facts=replace(
                facts,
                evidence=self._qualification.cached_evidence_current(
                    facts.selected_device_id
                ),
            ),
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
        plan_still_current: Callable[[OutputPlan], bool] | None = None,
        async_submit: Callable[[Callable, Callable], None] | None = None,
        cancel_prepare_work: Callable[[], None] | None = None,
        managed_prepare: (
            Callable[[Path, PlannerFacts], ManagedOutputPrepared] | None
        ) = None,
        managed_abort: (Callable[[ManagedOutputPrepared, str], None] | None) = None,
        managed_plan_still_current: (
            Callable[[ManagedPcmOutputPlan], bool] | None
        ) = None,
        truth_recorder=None,
    ) -> None:
        self._planner = planner
        self._facts_provider = facts_provider
        self._request_provider = request_provider
        self._executors = dict(executors or {})
        self._shared = shared_transaction or SharedOutputTransaction()
        self._plan_still_current = plan_still_current or (lambda _plan: True)
        self._async_submit = async_submit
        self._cancel_prepare_work = cancel_prepare_work
        self._managed_prepare = managed_prepare
        self._managed_abort = managed_abort
        self._managed_plan_still_current = managed_plan_still_current
        # ADDITIVE: the ONE canonical recorder (never a second one).
        self._truth_recorder = truth_recorder
        self._async_prepare_generation = 0
        self._pending_prepare_device_id: str | None = None
        self._state = OutputSessionState.IDLE
        self._generation = 0
        self._session_id: str | None = None
        self._plan: OutputPlan | None = None
        self._managed_plan: ManagedPcmOutputPlan | None = None
        self._managed_prepared: ManagedOutputPrepared | None = None
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
        self._last_release_invalidated_media = False
        self._lost_device_id: str | None = None
        self._lost_binding_generation = 0
        self._last_transition_kind: DirectTransitionKind | None = None
        self._last_cleanup_diagnostic: OutputCleanupDiagnostic | None = None
        self._subscribers: list[Callable[[], None]] = []

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
    def active_plan(self) -> OutputPlan | None:
        return self._plan if self._state in _ACTIVE_STATES else None

    @property
    def active_device_id(self) -> str | None:
        if (
            self._mode == "managed"
            and self._state in _ACTIVE_STATES
            and self._managed_plan is not None
        ):
            return self._managed_plan.stable_device_id
        plan = self.active_plan
        return plan.stable_device_id if plan is not None else None

    @property
    def last_transition_kind(self) -> DirectTransitionKind | None:
        return self._last_transition_kind

    @property
    def last_cleanup_diagnostic(self) -> OutputCleanupDiagnostic | None:
        return self._last_cleanup_diagnostic

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def volume_policy(self) -> VolumePolicy | None:
        """Resolved immutable Direct/Managed policy; Shared has none."""
        if self._mode == "direct" and self._plan:
            return self._plan.volume_policy
        if self._mode == "managed" and self._managed_plan is not None:
            try:
                return VolumePolicy(self._managed_plan.volume_policy)
            except ValueError:
                return None
        return None

    @property
    def volume_authority(self) -> VolumeAuthority | None:
        """Current Direct authority derived only from the resolved plan."""
        policy = self.volume_policy
        if policy is None:
            return None
        if policy is VolumePolicy.FIXED:
            return VolumeAuthority.FIXED
        if policy is VolumePolicy.HARDWARE:
            return VolumeAuthority.ALSA_HARDWARE
        return VolumeAuthority.UNKNOWN

    @property
    def release_invalidates_media(self) -> bool:
        return self._last_release_invalidated_media

    @property
    def requires_release_on_media_loss(self) -> bool:
        if self._mode == "managed":
            return self._managed_prepared is not None
        return self._mode == "direct" and self._executor is not None

    def allows_automatic_engine_fallback(self) -> bool:
        if self._state is OutputSessionState.LOST:
            return False
        plan = self._plan
        if plan is None and self._previous_direct is not None:
            plan = self._previous_direct.plan
        if plan is None:
            # Managed is a specific-DAC family: never fall back to another
            # engine or the default output.
            return False if self._mode == "managed" else self._mode == "shared"
        return plan.fallback is not FallbackKind.STOP

    def classify_load_failure(self, previous_source_preserved: bool) -> str:
        """Retain a prior Direct lease only when the backend retained its source."""
        return "load_failed" if previous_source_preserved else "load_failed_source_lost"

    def selection_state(self) -> OutputSelectionState:
        if (
            self._mode == "managed"
            and self._state in _ACTIVE_STATES
            and self._managed_plan is not None
        ):
            return OutputSelectionState(
                selected_device_id=self._selected_device_id,
                selected_profile_id=self._selected_profile_id,
                active_device_id=self._managed_plan.stable_device_id,
                active_plan_id=self._managed_plan.plan_id,
                session_state=self._state,
                error_code=self._error_code,
            )
        active = self._plan is not None and self._state in _ACTIVE_STATES
        active_plan = self._plan if active else None
        if (
            self._previous_direct is not None
            and self._state is OutputSessionState.READY
        ):
            # A READY replacement is still a candidate and must never be
            # projected as active before media acceptance. Keep the committed
            # predecessor only while the executor still proves its ownership;
            # after the destructive boundary no device is active yet.
            previous = self._previous_direct
            owns_committed = getattr(previous.executor, "owns_committed_receipt", None)
            predecessor_is_active = owns_committed is None or owns_committed(
                previous.receipt
            )
            active_plan = previous.plan if predecessor_is_active else None
        return OutputSelectionState(
            selected_device_id=self._selected_device_id,
            selected_profile_id=self._selected_profile_id,
            active_device_id=(
                active_plan.stable_device_id if active_plan is not None else None
            ),
            active_plan_id=active_plan.plan_id if active_plan is not None else None,
            session_state=self._state,
            error_code=self._error_code,
        )

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        for callback in tuple(self._subscribers):
            callback()

    def select(self, *, device_id: str | None, profile_id: str | None) -> None:
        """El intent seleccionado persiste aunque el device desaparezca."""
        self._selected_device_id = device_id
        self._selected_profile_id = profile_id
        self._notify()

    # ── planificación ─────────────────────────────────────────────────
    def plan_for(self, facts: PlannerFacts) -> OutputPlan | PlannerRefusal:
        return self._planner.plan(facts)

    # ── PlaybackOutputTransactionPort (§0H.2) ─────────────────────────
    def prepare_for_media(self, path: Path) -> str:
        """Planifica internamente y devuelve un token opaco (READY).

        Firma EXACTA del port: PlaybackService nunca ve un OutputPlan.
        """
        self.cancel_pending_prepare()
        if self._state not in (
            OutputSessionState.IDLE,
            OutputSessionState.READY,
            OutputSessionState.RUNNING,
        ):
            raise OutputSessionError(
                "illegal_transition", f"prepare desde {self._state.value}"
            )
        request = self._request_for(path)
        return self._prepare_request(path, request)

    def prepare_for_media_async(
        self,
        path: Path,
        on_prepared: Callable[[str], None],
        on_failed: Callable[[Exception], None],
    ) -> None:
        """True async preparation: the OWNER returns before characterizing.

        Owner (here): allocate the preparation generation, peek the selected
        device for pending-preparation diagnostics, snapshot nothing else and
        return to the event loop.
        Worker: build the immutable request (metadata + source
        characterization + blocking qualification probe) and the plan; no
        OutputSession state is touched off-owner.
        Owner completion: revalidate the generation and selected-device
        identity, then run ``_prepare_request`` — the semantic commit — and
        publish the callback. A stale completion can never commit.
        """
        self._async_prepare_generation += 1
        generation = self._async_prepare_generation
        intent = self._capture_output_intent()
        pending_device = getattr(self._request_provider, "pending_device_id", None)
        if callable(pending_device):
            try:
                self._pending_prepare_device_id = pending_device(path)
            except Exception:  # noqa: BLE001 - diagnostics only, never fatal
                self._pending_prepare_device_id = None

        def work():
            request = self._request_for(path)
            if self._is_managed_request(request):
                prepared = self._run_managed_prepare(path, request.facts)
                return request, None, prepared
            result = (
                self._planner.plan(request.facts) if request.facts is not None else None
            )
            needs_probe = (
                isinstance(result, PlannerRefusal)
                and result.code == EXACT_TUPLE_UNKNOWN
                and hasattr(self._request_provider, "qualify_request")
            )
            outcome = (
                self._request_provider.probe_request(request) if needs_probe else None
            )
            return request, outcome, None

        def _prepared_from(value):
            if not isinstance(value, tuple) or len(value) != 3:
                return None
            return value[2] if isinstance(value[2], ManagedOutputPrepared) else None

        def completed(value, error) -> None:
            if generation != self._async_prepare_generation:
                # A worker-phase Managed execution that can no longer commit
                # MUST be stopped: a superseded preparation never keeps
                # playing or holds the selected device.
                self._managed_abort_quietly(
                    _prepared_from(value), "superseded_before_commit"
                )
                on_failed(
                    OutputSessionError(
                        "OUTPUT_PREPARATION_STALE",
                        "output preparation was superseded",
                    )
                )
                return
            self._pending_prepare_device_id = None
            if error is not None:
                on_failed(error)
                return
            # Output-intent freshness: a worker built for an older selection
            # can NEVER commit over a newer user intent, independently of the
            # media-request generation. The monotonic revision makes value
            # equality (ABA) insufficient to pass.
            if intent is not None and self._capture_output_intent() != intent:
                self._managed_abort_quietly(
                    _prepared_from(value), "intent_changed_before_commit"
                )
                on_failed(
                    OutputSessionError(
                        "OUTPUT_PREPARATION_STALE",
                        "output intent changed while preparing",
                    )
                )
                return
            request, outcome, managed_prepared = value
            try:
                if managed_prepared is not None:
                    token = self._begin_managed_session(
                        path,
                        request,
                        managed_prepared,
                        previous_direct=self._committed_direct_snapshot(),
                    )
                    on_prepared(token)
                    return
                if outcome is not None:
                    probed_request, probe_outcome = outcome
                    request = self._request_provider.apply_qualification(
                        probed_request, probe_outcome
                    )
                token = self._prepare_request(path, request)
            except Exception as exc:  # noqa: BLE001 - owner completion boundary
                on_failed(exc)
                return
            on_prepared(token)

        if self._async_submit is None:
            # Explicit synchronous composition (legacy/test graphs): run the
            # same split inline, with the same typed failure delivery.
            try:
                completed(work(), None)
            except Exception as exc:  # noqa: BLE001 - inline boundary
                completed(None, exc)
        else:
            self._async_submit(work, completed)

    def cancel_pending_prepare(self) -> None:
        """Invalidate worker continuations AND abort characterization work.

        Generation invalidation alone left a superseded source-
        characterization subprocess running for its whole bounded budget;
        the composition injects the canonical cancel hook so a superseded
        preparation releases that worker immediately.
        """
        self._async_prepare_generation += 1
        self._pending_prepare_device_id = None
        cancel = self._cancel_prepare_work
        if cancel is not None:
            with contextlib.suppress(Exception):
                cancel()

    def _prepare_request(self, path: Path, request: OutputRequest) -> str:
        if self._state not in (
            OutputSessionState.IDLE,
            OutputSessionState.READY,
            OutputSessionState.RUNNING,
        ):
            raise OutputSessionError(
                "illegal_transition", f"prepare desde {self._state.value}"
            )
        previous_direct = self._committed_direct_snapshot()
        self._selected_device_id = request.selected_device_id
        self._selected_profile_id = request.selected_profile_id
        if self._is_managed_request(request):
            return self._prepare_managed_request(
                path, request, previous_direct=previous_direct
            )
        if request.facts is None:
            return self._prepare_shared(path, previous_direct=previous_direct)
        result = self._planner.plan(request.facts)
        if isinstance(result, PlannerRefusal):
            raise OutputSessionError(result.code, result.detail)
        if self._mode == "managed" and self._managed_prepared is not None:
            prepared = self._managed_prepared
            self._managed_prepared = None
            self._managed_plan = None
            self._managed_abort_quietly(prepared, "switch_to_direct")
        executor = self._executors.get(result.engine_id)
        if executor is None:
            raise OutputSessionError(
                "ENGINE_UNSUPPORTED_FOR_DIRECT",
                f"no Direct executor for engine {result.engine_id!r}",
            )
        try:
            plan_is_current = self._plan_still_current(result)
        except Exception as exc:
            raise OutputSessionError(
                "OUTPUT_BINDING_VALIDATION_FAILED",
                "Direct binding freshness could not be validated",
            ) from exc
        if not plan_is_current:
            raise OutputSessionError(
                "OUTPUT_BINDING_STALE",
                "Direct binding changed before candidate preparation",
            )
        try:
            receipt = executor.prepare(result)
        except Exception as exc:
            code = getattr(exc, "code", "DIRECT_EXECUTOR_PREPARE_FAILED")
            raise OutputSessionError(code, str(exc)) from exc
        try:
            plan_is_current = self._plan_still_current(result)
        except Exception as exc:
            self._discard_stale_candidate(executor, receipt)
            raise OutputSessionError(
                "OUTPUT_BINDING_VALIDATION_FAILED",
                "Direct binding freshness could not be validated",
            ) from exc
        if not plan_is_current:
            self._discard_stale_candidate(executor, receipt)
            raise OutputSessionError(
                "OUTPUT_BINDING_STALE",
                "Direct binding changed while the candidate was being prepared",
            )
        if self._mode == "shared" and self._shared_receipt is not None:
            self._shared.abort_media(self._shared_receipt, "superseded")
        return self._begin_session(
            result,
            path,
            executor,
            receipt,
            previous_direct=previous_direct,
        )

    @staticmethod
    def _discard_stale_candidate(
        executor: AudioOutputExecutorPort, receipt: str
    ) -> None:
        try:
            disposition = executor.abort(receipt, "binding_stale_during_prepare")
            if disposition is OutputExecutorAbortDisposition.STALE:
                executor.release("binding_stale_during_prepare")
        except Exception:
            with suppress(Exception):
                executor.release("binding_stale_during_prepare")

    def _capture_output_intent(self):
        capture = getattr(self._request_provider, "snapshot_output_intent", None)
        if not callable(capture):
            return None
        try:
            return capture()
        except Exception:  # noqa: BLE001 - diagnostics-grade capture
            return None

    def _request_for(self, path: Path) -> OutputRequest:
        if self._request_provider is not None:
            return self._request_provider(path)
        return OutputRequest.direct(self._facts_for(path))

    def _is_managed_request(self, request: OutputRequest) -> bool:
        facts = request.facts
        return (
            facts is not None
            and facts.profile is not None
            and facts.profile.path is OutputPathPreference.MANAGED
        )

    def _run_managed_prepare(self, path: Path, facts) -> ManagedOutputPrepared:
        if self._managed_prepare is None:
            raise OutputSessionError(
                "MANAGED_OUTPUT_UNAVAILABLE",
                "no Managed preparation is composed for this session",
            )
        try:
            prepared = self._managed_prepare(path, facts)
        except OutputSessionError:
            raise
        except Exception as exc:  # noqa: BLE001 - typed owner boundary
            code = getattr(exc, "code", "MANAGED_OUTPUT_PREPARE_FAILED")
            raise OutputSessionError(code, str(exc)) from exc
        if not isinstance(prepared, ManagedOutputPrepared):
            raise OutputSessionError(
                "MANAGED_OUTPUT_PREPARE_FAILED",
                "managed preparation returned an invalid value",
            )
        return prepared

    def _prepare_managed_request(
        self,
        path: Path,
        request: OutputRequest,
        *,
        previous_direct: _DirectSessionSnapshot | None,
    ) -> str:
        prepared = self._run_managed_prepare(path, request.facts)
        return self._begin_managed_session(
            path, request, prepared, previous_direct=previous_direct
        )

    def _begin_managed_session(
        self,
        path: Path,
        request: OutputRequest,
        prepared: ManagedOutputPrepared,
        *,
        previous_direct: _DirectSessionSnapshot | None,
    ) -> str:
        checker = self._managed_plan_still_current
        if checker is not None:
            try:
                current = bool(checker(prepared.plan))
            except Exception as exc:  # noqa: BLE001 - fail closed
                self._managed_abort_quietly(prepared, "binding_validation_failed")
                raise OutputSessionError(
                    "OUTPUT_BINDING_VALIDATION_FAILED",
                    "Managed binding freshness could not be validated",
                ) from exc
            if not current:
                self._managed_abort_quietly(prepared, "binding_stale_during_prepare")
                raise OutputSessionError(
                    "OUTPUT_BINDING_STALE",
                    "Managed binding changed before candidate preparation",
                )
        current = self._managed_prepared
        if current is not None and current is not prepared:
            self._managed_prepared = None
            self._managed_plan = None
            self._managed_abort_quietly(current, "superseded")
        if self._mode == "shared" and self._shared_receipt is not None:
            with suppress(Exception):
                self._shared.abort_media(self._shared_receipt, "superseded")
        if previous_direct is not None:
            with suppress(Exception):
                previous_direct.executor.release("switch_to_managed")
        if self._state is not OutputSessionState.IDLE:
            if self._state in (
                OutputSessionState.READY,
                OutputSessionState.RUNNING,
            ):
                self._transition(OutputSessionState.RECONFIGURING)
            elif self._state is OutputSessionState.PAUSED:
                self._transition(OutputSessionState.RELEASING)
                self._transition(OutputSessionState.IDLE)
            else:
                raise OutputSessionError(
                    "illegal_transition",
                    f"prepare desde {self._state.value}",
                )
        if self._state is OutputSessionState.IDLE:
            self._transition(OutputSessionState.ACQUIRING)
        self._generation += 1
        self._mode = "managed"
        self._managed_plan = prepared.plan
        self._managed_prepared = prepared
        self._plan = None
        self._path = Path(path)
        self._executor = None
        self._executor_receipt = prepared.execution_id
        self._shared_receipt = None
        self._previous_direct = None
        self._session_id = f"session:{self._generation}"
        self._error_code = None
        self._last_transition_kind = None
        self._last_release_invalidated_media = False
        if self._state is OutputSessionState.ACQUIRING:
            self._transition(OutputSessionState.CONFIGURING)
        self._transition(OutputSessionState.READY)
        self._token_value = f"output-tx:managed:{self._generation}"
        self._record_output_family(OutputFamilyState.READY, prepared)
        return self._token_value

    def _record_output_family(
        self,
        state: OutputFamilyState,
        prepared: ManagedOutputPrepared | None = None,
    ) -> None:
        recorder = self._truth_recorder
        if recorder is None:
            return
        current = prepared or self._managed_prepared
        plan = current.plan if current is not None else self._managed_plan
        if plan is None:
            return
        runtime = dict(current.runtime_identity) if current is not None else {}
        with suppress(Exception):
            recorder.record_output_family_event(
                OutputFamilyEvent(
                    family="managed",
                    state=state,
                    device_id=plan.stable_device_id,
                    execution_id=current.execution_id if current else None,
                    processing_plan_id=plan.processing_plan_id,
                    transform_policy=plan.transform_policy,
                    runtime_identity=runtime,
                    # Never a Direct preservation proof: tri-state, not True.
                    bit_perfect=None,
                )
            )

    def _managed_abort_quietly(
        self, prepared: ManagedOutputPrepared | None, reason: str
    ) -> None:
        if prepared is None:
            return
        abort = self._managed_abort
        if abort is None:
            return
        with suppress(Exception):
            abort(prepared, reason)

    def _prepare_shared(
        self,
        path: Path,
        *,
        previous_direct: _DirectSessionSnapshot | None,
    ) -> str:
        if self._mode == "managed" and self._managed_prepared is not None:
            prepared = self._managed_prepared
            self._managed_prepared = None
            self._managed_plan = None
            self._managed_abort_quietly(prepared, "switch_to_shared")
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
        if self._state is not OutputSessionState.IDLE:
            self._state = OutputSessionState.IDLE
        self._notify()
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
        replacement_kind = (
            self._classify_direct_transition(previous_direct.plan, plan)
            if previous_direct is not None
            else None
        )
        if self._state is not OutputSessionState.IDLE:
            if self._state in (OutputSessionState.READY, OutputSessionState.RUNNING):
                self._transition(
                    OutputSessionState.RECOVERING
                    if replacement_kind is DirectTransitionKind.REACQUIRE
                    else OutputSessionState.RECONFIGURING
                )
            else:
                raise OutputSessionError(
                    "illegal_transition",
                    f"prepare desde {self._state.value}",
                )
        if self._state is OutputSessionState.IDLE:
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
        self._last_transition_kind = replacement_kind
        if self._state is OutputSessionState.ACQUIRING:
            self._transition(OutputSessionState.CONFIGURING)
        self._transition(OutputSessionState.READY)
        self._token_value = self._token()
        self._last_release_invalidated_media = False
        return self._token_value

    @staticmethod
    def _classify_direct_transition(
        previous: OutputPlan, current: OutputPlan
    ) -> DirectTransitionKind:
        if (
            previous.stable_device_id != current.stable_device_id
            or previous.binding.generation != current.binding.generation
            or previous.binding.locator != current.binding.locator
            or previous.path_semantics != current.path_semantics
        ):
            return DirectTransitionKind.REACQUIRE
        if (
            previous.requested_pcm != current.requested_pcm
            or previous.volume_policy != current.volume_policy
            or previous.fallback != current.fallback
            or previous.allow_resample != current.allow_resample
            or previous.allow_remix != current.allow_remix
            or previous.allow_processing != current.allow_processing
            or previous.sink != current.sink
        ):
            return DirectTransitionKind.RECONFIGURE
        return DirectTransitionKind.SAME_TUPLE

    def commit_media(self, token: str, path: Path) -> None:
        if self._is_stale(token):
            return  # callback de generation vieja: descartado (§21)
        if self._path != Path(path):
            raise OutputSessionError("stale_path", "commit path does not own token")
        if self._mode == "managed":
            if self._state is not OutputSessionState.READY:
                raise OutputSessionError(
                    "illegal_transition", f"commit desde {self._state.value}"
                )
            self._previous_direct = None
            self._transition(OutputSessionState.RUNNING)
            self._record_output_family(OutputFamilyState.RUNNING)
            return
        if self._mode == "shared":
            assert self._shared_receipt is not None
            self._shared.commit_media(self._shared_receipt, path)
            if self._previous_direct is not None:
                self._previous_direct.executor.release("switch_to_shared")
                self._previous_direct = None
            self._plan = None
            self._state = OutputSessionState.IDLE
            self._notify()
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
        if self._mode == "managed":
            self._error_code = reason
            prepared = self._managed_prepared
            self._managed_prepared = None
            self._managed_plan = None
            if self._state is not OutputSessionState.LOST:
                self._transition(OutputSessionState.RELEASING)
            self._managed_abort_quietly(prepared, reason)
            self._record_output_family(OutputFamilyState.UNAVAILABLE, prepared)
            self._clear_execution(keep_error=True)
            if self._state is not OutputSessionState.IDLE:
                self._transition(OutputSessionState.IDLE)
            self._notify()
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
                self._notify()
                return
            if self._previous_direct is not None:
                self._previous_direct.executor.release(reason)
            self._clear_execution()
            self._notify()
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
            self._notify()
            return
        self._transition(OutputSessionState.RELEASING)
        self._clear_execution(keep_error=True)
        self._transition(OutputSessionState.IDLE)

    def release_active(self, reason: str) -> None:
        self.cancel_pending_prepare()
        was_specific = (
            self._mode == "direct"
            and self._executor is not None
            or self._mode == "managed"
            and self._managed_prepared is not None
        )
        self._last_release_invalidated_media = was_specific
        if self._mode == "managed":
            prepared = self._managed_prepared
            self._managed_prepared = None
            self._managed_plan = None
            if self._state not in (
                OutputSessionState.IDLE,
                OutputSessionState.RELEASING,
            ):
                self._transition(OutputSessionState.RELEASING)
            self._managed_abort_quietly(prepared, reason)
            self._record_output_family(OutputFamilyState.RELEASED, prepared)
            self._error_code = None
            self._clear_execution(keep_error=True)
            if self._state is not OutputSessionState.IDLE:
                self._transition(OutputSessionState.IDLE)
            self._notify()
            return
        if self._mode == "shared":
            self._shared.release_active(reason)
            if self._previous_direct is not None:
                self._previous_direct.executor.release(reason)
            self._clear_execution()
            self._notify()
            return
        if self._state is OutputSessionState.IDLE and not was_specific:
            return
        # R110 §21/§29: a normal release/stop is a COMMAND, not a failure — but
        # the release is a TRANSACTION. The failure presentation is only retired
        # AFTER the physical release succeeded, and a release that genuinely
        # fails leaves a typed current failure instead of a fabricated clean
        # state. Projecting a plain reason made every clean stop render as
        # "Output unavailable"; clearing before the call would hide a real one.
        if self._executor is not None:
            try:
                self._executor.release(reason)
            except Exception as exc:  # noqa: BLE001 — release boundary
                self._error_code = OUTPUT_RELEASE_FAILED
                self._notify()
                raise OutputSessionError(
                    OUTPUT_RELEASE_FAILED,
                    f"output release failed: {exc}",
                ) from exc
        self._error_code = None
        if self._state is not OutputSessionState.RELEASING:
            self._transition(OutputSessionState.RELEASING)
        self._clear_execution(keep_error=True)
        self._transition(OutputSessionState.IDLE)

    # ── topología / fallas ────────────────────────────────────────────
    def device_lost(
        self,
        stable_device_id: str | None = None,
        generation: int | None = None,
    ) -> None:
        """Invalidate topology-dependent authority, then attempt cleanup."""
        previous = self._previous_direct
        managed_prepared = self._managed_prepared
        managed_plan = self._managed_plan
        if self._state is OutputSessionState.LOST or (
            self._state is OutputSessionState.IDLE
            and self._executor is None
            and previous is None
            and managed_prepared is None
        ):
            return
        current_plan = self._plan
        loss_plan = current_plan
        if stable_device_id is not None:
            if (
                current_plan is not None
                and current_plan.stable_device_id == stable_device_id
            ):
                loss_plan = current_plan
            elif (
                previous is not None
                and previous.plan.stable_device_id == stable_device_id
            ):
                loss_plan = previous.plan
        resolved_device_id = stable_device_id or (
            loss_plan.stable_device_id
            if loss_plan is not None
            else (managed_plan.stable_device_id if managed_plan is not None else None)
        )
        loss_generation = (
            loss_plan.binding.generation
            if loss_plan is not None
            else (managed_plan.binding_generation if managed_plan is not None else 0)
        )
        if generation is not None:
            loss_generation = max(loss_generation, generation)
        wait_for_rebind = (
            stable_device_id is None or resolved_device_id == self._selected_device_id
        )
        self._lost_device_id = resolved_device_id
        self._lost_binding_generation = loss_generation

        executors: list[AudioOutputExecutorPort] = []
        for candidate in (
            self._executor,
            previous.executor if previous is not None else None,
        ):
            if candidate is not None and all(
                candidate is not item for item in executors
            ):
                executors.append(candidate)
        # Topology truth already says the device is absent. Invalidate every
        # logical lease before attempting fallible physical cleanup so an
        # exception can never preserve stale output authority.
        if self._state is not OutputSessionState.LOST:
            self._transition(OutputSessionState.LOST)
        self._executor = None
        self._executor_receipt = None
        self._shared_receipt = None
        self._previous_direct = None
        self._token_value = None
        self._plan = None
        self._managed_plan = None
        self._managed_prepared = None
        self._path = None
        self._session_id = None
        self._mode = "lost" if wait_for_rebind else "shared"
        self._last_release_invalidated_media = bool(executors) or (
            managed_prepared is not None
        )
        self._error_code = "device_lost"
        self._last_cleanup_diagnostic = None
        if not wait_for_rebind:
            self._lost_device_id = None
            self._lost_binding_generation = 0
            self._transition(OutputSessionState.IDLE)
        if managed_prepared is not None:
            self._record_output_family(OutputFamilyState.UNAVAILABLE, managed_prepared)
        self._managed_abort_quietly(managed_prepared, "device_lost")
        for executor in executors:
            try:
                executor.release("device_lost")
            except Exception as exc:  # noqa: BLE001 - physical cleanup boundary
                if self._last_cleanup_diagnostic is None:
                    self._last_cleanup_diagnostic = OutputCleanupDiagnostic(
                        reason="device_lost",
                        code=getattr(exc, "code", "DIRECT_EXECUTOR_RELEASE_FAILED"),
                        detail=str(exc),
                    )
                logger.exception("Direct executor release failed after topology loss")
        self._notify()

    def topology_lost(self, stable_device_id: str, generation: int) -> None:
        """Apply one canonical topology loss to the matching active Direct lease."""
        if not self.topology_loss_applies(stable_device_id):
            return
        self.cancel_pending_prepare()
        self.device_lost(stable_device_id, generation)

    def topology_loss_applies(self, stable_device_id: str) -> bool:
        """Whether current or still-restorable Direct ownership uses a device.

        During A→B replacement, B is the logical candidate while A can remain
        the physical predecessor until the executor's destructive boundary.
        The executor remains the sole authority on whether A is still owned.
        """
        if self._pending_prepare_device_id == stable_device_id:
            return True
        if (
            self._mode == "direct"
            and self._plan is not None
            and self._state in _ACTIVE_STATES
            and self._plan.stable_device_id == stable_device_id
        ):
            return True
        if (
            self._mode == "managed"
            and self._managed_plan is not None
            and self._state in _ACTIVE_STATES
            and self._managed_plan.stable_device_id == stable_device_id
        ):
            return True
        previous = self._previous_direct
        if previous is None or previous.plan.stable_device_id != stable_device_id:
            return False
        owns_committed = getattr(previous.executor, "owns_committed_receipt", None)
        if owns_committed is None:
            return True  # Conservative compatibility for an older executor double.
        try:
            return bool(owns_committed(previous.receipt))
        except Exception:  # noqa: BLE001 - uncertainty cannot dismiss device loss
            logger.exception(
                "could not validate predecessor ownership on topology loss"
            )
            return True

    def rebind_after_topology_change(
        self, stable_device_id: str, generation: int
    ) -> bool:
        """Acknowledge a newer same-device binding without activating playback."""
        if (
            self._state is not OutputSessionState.LOST
            or stable_device_id != self._lost_device_id
            or stable_device_id != self._selected_device_id
            or generation <= self._lost_binding_generation
        ):
            return False
        self._transition(OutputSessionState.RECOVERING)
        self._transition(OutputSessionState.IDLE)
        self._mode = "shared"
        self._lost_device_id = None
        self._lost_binding_generation = 0
        self._error_code = None
        self._notify()
        return True

    def fail(self, error_code: str) -> None:
        self._error_code = error_code
        if self._state is not OutputSessionState.FAILED:
            self._transition(OutputSessionState.FAILED)
        else:
            self._notify()

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
        self._managed_plan = None
        self._managed_prepared = None
        self._path = None
        self._token_value = None
        self._executor = None
        self._executor_receipt = None
        self._shared_receipt = None
        self._previous_direct = None
        self._lost_device_id = None
        self._lost_binding_generation = 0
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
        self._notify()
