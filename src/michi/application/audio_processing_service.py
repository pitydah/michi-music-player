"""AP2-F05 — parent semantic processing authority (PARENT-SAFE).

Owns the SEMANTIC processing state only: capability decisions from child
facts, the requested/effective processing revisions, and the readback-first
commit decisions. It NEVER creates a Gst object and never runs in the child.

Requested != Effective: an effective revision is published only after the
child returns primitive readback that the parent has validated against the
compiled plan.
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from michi.application.effective_processing_graph import (
    EffectiveProcessingGraphResolver,
)
from michi.application.processing_graph_compiler import (
    CompiledProcessingPlan,
    ProcessingBackendCapabilities,
    ProcessingGraphCompiler,
)
from michi.domain.audio_processing import ProcessingStrategy
from michi.domain.signal_truth import (
    ProcessingTruthEvent,
    ProcessingTruthState,
)

#: Strategies the F05 native builder actually implements TODAY. Factory
#: presence alone never implies support: the effective set is the
#: intersection of these and the real child-reported factories.
IMPLEMENTED_STRATEGIES: frozenset[ProcessingStrategy] = frozenset(
    {
        ProcessingStrategy.GAIN,
        ProcessingStrategy.GRAPHIC_EQ_NBANDS,
        ProcessingStrategy.BIQUAD_CASCADE,
    }
)

#: RBJ Q for a one-octave peaking band (graphic EQ native mapping).
_GRAPHIC_OCTAVE_Q = 2.0**0.5 / (2.0 - 1.0)

#: Strategy -> factories whose real availability is required. Graphic EQ is
#: mapped to an audioiirfilter biquad cascade because `equalizer-nbands`
#: does not expose its band properties in every real environment (GStreamer
#: 1.28 reports only `num-bands`); the capability probe still records the
#: equalizer facts as diagnostics.
_STRATEGY_FACTORIES: dict[ProcessingStrategy, tuple[str, ...]] = {
    ProcessingStrategy.GAIN: ("volume",),
    ProcessingStrategy.GRAPHIC_EQ_NBANDS: ("audioiirfilter",),
    ProcessingStrategy.BIQUAD_CASCADE: ("audioiirfilter",),
    ProcessingStrategy.CONVOLUTION_FIR: ("audiofirfilter",),
    ProcessingStrategy.RESAMPLE: ("audioresample",),
    ProcessingStrategy.CHANNEL_DELAY: ("audioconvert",),
    ProcessingStrategy.CHANNEL_MAP: ("audioconvert",),
    ProcessingStrategy.DITHER_TERMINAL: ("audioconvert",),
}


@dataclass(frozen=True, slots=True)
class ProcessingCandidateIdentity:
    """Generation-bound identity of one prepared processing candidate."""

    candidate_id: str
    plan_id: str
    graph_revision: int
    host_generation: int
    pipeline_generation: int
    processing_generation: int


@dataclass(frozen=True, slots=True)
class ProcessingCommitReceipt:
    """Child receipt proving the PRODUCTION runtime accepted the candidate."""

    candidate: ProcessingCandidateIdentity
    installed: bool
    observed_plan_id: str
    observed_graph_revision: int
    observed_pipeline_generation: int
    observed_processing_generation: int
    observed_host_generation: int
    observed_candidate_id: str
    native_runtime_identity: str


class ProcessingCapabilityState(StrEnum):
    UNKNOWN = "unknown"
    QUERIED = "queried"
    UNAVAILABLE = "unavailable"


class ProcessingEffectiveState(StrEnum):
    BYPASSED = "bypassed"
    PREPARING = "preparing"
    EFFECTIVE = "effective"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ProcessingCapabilityFacts:
    """Primitive capability facts reported by the child (never Gst objects)."""

    gstreamer_version: str | None
    runtime_failure: str | None
    factories: dict[str, dict[str, Any]]
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


class AudioProcessingService:
    """Semantic processing authority: capabilities, revisions, commit gate."""

    def __init__(
        self,
        *,
        capability_query: Callable[[], dict[str, Any]] | None = None,
        native_mapping: object | None = None,
        transport: object | None = None,
        async_submit: Callable[[Callable, Callable], None] | None = None,
        truth_recorder: object | None = None,
        truth_dispatch: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._capability_query = capability_query
        self._async_submit = async_submit
        self._transport = transport
        # ADDITIVE: the canonical SignalTruthRecorder (never a second one).
        self._truth_recorder = truth_recorder
        self._truth_dispatch: Callable[[Callable[[], None]], None] | None = (
            truth_dispatch
        )
        # Infrastructure-owned native mapping (pure math + DTO shaping); the
        # application layer never imports infrastructure.
        self._native_mapping = native_mapping
        self._capability_state = ProcessingCapabilityState.UNKNOWN
        self._capabilities = ProcessingBackendCapabilities(
            backend_id="gstreamer-host",
            strategies=frozenset(),
        )
        self._facts: ProcessingCapabilityFacts | None = None
        self._requested_revision = 0
        self._effective_revision = 0
        self._effective_state = ProcessingEffectiveState.BYPASSED
        self._effective_plan_id: str | None = None
        self._host_generation: int | None = None
        self._prepared_plans: dict[str, CompiledProcessingPlan] = {}
        self._last_receipt_runtime_identity: str | None = None
        self._last_receipt_readback_proven = False
        # SHORT-LIVED state protection only: never held across IPC. The
        # owner (Qt) and host-loss callbacks must never wait on a
        # transaction. Transactions are serialized by ONE dedicated worker.
        self._state_lock = threading.Lock()
        self._tx_queue: deque = deque()
        self._tx_thread: threading.Thread | None = None
        self._tx_active_revision: int | None = None
        self._accepting = True
        self._shutdown_error: Exception | None = None
        self._host_lost_reason: str | None = None

    # ── lectura ───────────────────────────────────────────────────────
    @property
    def capability_state(self) -> ProcessingCapabilityState:
        return self._capability_state

    @property
    def capabilities(self) -> ProcessingBackendCapabilities:
        return self._capabilities

    @property
    def facts(self) -> ProcessingCapabilityFacts | None:
        return self._facts

    @property
    def requested_revision(self) -> int:
        return self._requested_revision

    @property
    def effective_revision(self) -> int:
        return self._effective_revision

    @property
    def effective_state(self) -> ProcessingEffectiveState:
        return self._effective_state

    @property
    def effective_plan_id(self) -> str | None:
        return self._effective_plan_id

    # ── wire (parent semantic -> child native) ───────────────────────
    def plan_to_wire(self, plan: CompiledProcessingPlan) -> dict[str, Any]:
        """Build the bounded native execution DTO for one compiled plan."""
        mapping = self._native_mapping
        if mapping is None:
            raise ProcessingReadbackMismatchError(
                "DSP_NATIVE_MAPPING_UNAVAILABLE",
                "no native mapping is composed for this processing service",
            )
        return mapping.plan_to_wire(plan)

    # ── capacidades (child-native, parent-decided) ────────────────────
    def refresh_capabilities(
        self, *, host_generation: int | None = None
    ) -> ProcessingBackendCapabilities:
        """Query the child and decide which strategies are REALLY supported."""
        if self._capability_query is None:
            with self._state_lock:
                self._capability_state = ProcessingCapabilityState.UNAVAILABLE
                self._capabilities = ProcessingBackendCapabilities(
                    backend_id="gstreamer-host", strategies=frozenset()
                )
                self._facts = None
            return self.capabilities
        try:
            raw = self._capability_query()
        except Exception:  # noqa: BLE001 - host loss/unavailable is typed state
            with self._state_lock:
                self._capability_state = ProcessingCapabilityState.UNAVAILABLE
                self._capabilities = ProcessingBackendCapabilities(
                    backend_id="gstreamer-host", strategies=frozenset()
                )
                self._facts = None
                # A capability refresh never silently keeps an effective
                # runtime whose native evidence belongs to a dead host.
                if self._effective_state is ProcessingEffectiveState.EFFECTIVE:
                    self._effective_state = ProcessingEffectiveState.UNAVAILABLE
                    self._effective_plan_id = None
            return self.capabilities
        facts = ProcessingCapabilityFacts(
            gstreamer_version=raw.get("gstreamer_version"),
            runtime_failure=raw.get("runtime_failure"),
            factories={
                str(name): dict(value)
                for name, value in (raw.get("factories") or {}).items()
                if isinstance(value, dict)
            },
            raw=dict(raw),
        )
        if facts.runtime_failure is not None:
            # Contradiction is forbidden: a broken child runtime can NEVER
            # advertise supported strategies from stale/partial facts.
            with self._state_lock:
                self._facts = facts
                self._capability_state = ProcessingCapabilityState.UNAVAILABLE
                self._capabilities = ProcessingBackendCapabilities(
                    backend_id="gstreamer-host", strategies=frozenset()
                )
                if self._effective_state is ProcessingEffectiveState.EFFECTIVE:
                    self._effective_state = ProcessingEffectiveState.UNAVAILABLE
                    self._effective_plan_id = None
            return self.capabilities
        with self._state_lock:
            self._facts = facts
            self._capability_state = ProcessingCapabilityState.QUERIED
        strategies = frozenset(
            strategy
            for strategy in IMPLEMENTED_STRATEGIES
            if self._factory_available(facts, *_STRATEGY_FACTORIES.get(strategy, ()))
        )
        capabilities = ProcessingBackendCapabilities(
            backend_id="gstreamer-host",
            strategies=strategies,
            factories=frozenset(
                name
                for name, value in facts.factories.items()
                if value.get("available")
            ),
        )
        with self._state_lock:
            self._capabilities = capabilities
            if host_generation is not None:
                if (
                    self._host_generation is not None
                    and host_generation != self._host_generation
                ):
                    # A DIFFERENT, freshly queried host cannot inherit the
                    # previous host's loss reason.
                    self._host_lost_reason = None
                self._host_generation = host_generation
        return capabilities

    @staticmethod
    def _factory_available(facts: ProcessingCapabilityFacts, *names: str) -> bool:
        return all(
            bool(facts.factories.get(name, {}).get("available")) for name in names
        )

    # ── intención / revisión efectiva ─────────────────────────────────
    def _record_processing(
        self,
        state: ProcessingTruthState,
        *,
        plan_id: str | None = None,
        detail: str | None = None,
        pipeline_generation: int | None = None,
        runtime_identity: str | None = None,
        readback_proven: bool = False,
        host_generation: int | None = None,
    ) -> None:
        recorder = self._truth_recorder
        if recorder is None:
            return
        # Never a preservation proof from processing; tri-state preserved.
        bit_perfect = False if state is ProcessingTruthState.EFFECTIVE else None
        event = ProcessingTruthEvent(
            state=state,
            processing_generation=self._requested_revision,
            plan_id=plan_id,
            bit_perfect=bit_perfect,
            detail=detail,
            host_generation=(
                host_generation
                if host_generation is not None
                else self._host_generation
            ),
            pipeline_generation=pipeline_generation,
            runtime_identity=runtime_identity,
            readback_proven=readback_proven,
        )

        def write() -> None:
            if not self._accepting and state is not ProcessingTruthState.UNAVAILABLE:
                # Teardown: only the terminal UNAVAILABLE event may land.
                return
            try:
                recorder.record_processing_event(event)
            except Exception:  # noqa: BLE001 - passive truth never breaks DSP
                return

        dispatcher = self._truth_dispatch
        if dispatcher is None:
            write()
            return
        try:
            dispatcher(write)
        except Exception:  # noqa: BLE001 - truth delivery never breaks DSP
            write()

    def note_requested(self) -> int:
        """New requested processing intent: an effective revision is now
        PREPARING (requested != effective) until a commit proves it."""
        with self._state_lock:
            self._requested_revision += 1
            self._effective_state = ProcessingEffectiveState.PREPARING
            revision = self._requested_revision
        self._record_processing(ProcessingTruthState.REQUESTED)
        return revision

    def validate_readback(
        self,
        plan: CompiledProcessingPlan,
        observed: dict[str, Any],
        *,
        mode: str = "candidate",
    ) -> None:
        """Compare expected compiled plan vs child readback, fail closed."""
        if observed.get("plan_id") != plan.plan_id:
            raise ProcessingReadbackMismatchError(
                "DSP_READBACK_PLAN_MISMATCH",
                f"readback plan {observed.get('plan_id')!r} != {plan.plan_id!r}",
            )
        if observed.get("graph_revision") != plan.graph_revision:
            raise ProcessingReadbackMismatchError(
                "DSP_READBACK_REVISION_MISMATCH",
                "readback graph revision does not match the compiled plan",
            )
        nodes = observed.get("nodes")
        if not isinstance(nodes, list):
            raise ProcessingReadbackMismatchError(
                "DSP_READBACK_MISSING", "child reported no node readback"
            )
        node_ids = [
            str(node.get("node_id")) for node in nodes if isinstance(node, dict)
        ]
        if len(node_ids) != len(set(node_ids)):
            raise ProcessingReadbackMismatchError(
                "DSP_READBACK_DUPLICATE_NODE",
                "child reported duplicate native node ids",
            )
        expected_ids = [node.node_id for node in plan.nodes]
        if set(node_ids) != set(expected_ids):
            raise ProcessingReadbackMismatchError(
                "DSP_READBACK_NODE_SET_MISMATCH",
                f"observed {sorted(node_ids)} != expected {sorted(expected_ids)}",
            )
        by_id = {
            str(node.get("node_id")): node for node in nodes if isinstance(node, dict)
        }
        for expected in plan.nodes:
            actual = by_id.get(expected.node_id)
            if actual is None:
                raise ProcessingReadbackMismatchError(
                    "DSP_READBACK_MISSING",
                    f"node {expected.node_id!r} missing from readback",
                )
            if actual.get("strategy") != expected.strategy.value:
                raise ProcessingReadbackMismatchError(
                    "DSP_READBACK_STRATEGY_MISMATCH",
                    f"node {expected.node_id!r} strategy {actual.get('strategy')!r}",
                )
            mapping = self._native_mapping
            if mapping is None:
                raise ProcessingReadbackMismatchError(
                    "DSP_NATIVE_MAPPING_UNAVAILABLE",
                    "no native mapping is composed for this processing service",
                )
            try:
                expected_properties = mapping.expected_native_properties(
                    expected, rate_hz=plan.sample_contract.input_rate_hz
                )
            except ValueError as exc:
                raise ProcessingReadbackMismatchError(
                    "DSP_READBACK_UNSUPPORTED", str(exc)
                ) from exc
            if not _values_equal(actual.get("observed"), expected_properties):
                raise ProcessingReadbackMismatchError(
                    "DSP_READBACK_VALUE_MISMATCH",
                    f"node {expected.node_id!r} observed properties differ",
                )
            expected_factories = sorted(mapping.expected_native_factories(expected))
            observed_factories = sorted(
                str(name) for name in (actual.get("factories") or [])
            )
            if observed_factories != expected_factories:
                raise ProcessingReadbackMismatchError(
                    "DSP_READBACK_FACTORY_MISMATCH",
                    f"node {expected.node_id!r} factories "
                    f"{observed_factories} != {expected_factories}",
                )
        global_factories = sorted(
            str(name) for name in (observed.get("graph_factories") or [])
        )
        mapping = self._native_mapping
        if mapping is None:
            raise ProcessingReadbackMismatchError(
                "DSP_NATIVE_MAPPING_UNAVAILABLE",
                "no native mapping is composed for this processing service",
            )
        expected_global = sorted(mapping.expected_global_factories(plan, mode=mode))
        if global_factories != expected_global:
            raise ProcessingReadbackMismatchError(
                "DSP_READBACK_TOPOLOGY_MISMATCH",
                f"native topology {global_factories} != {expected_global}",
            )
        caps = observed.get("working_caps")
        contract = plan.sample_contract
        if not isinstance(caps, dict):
            raise ProcessingReadbackMismatchError(
                "DSP_READBACK_MISSING", "child reported no negotiated working caps"
            )
        if (
            caps.get("format") != contract.working_format
            or int(caps.get("rate_hz", 0)) != contract.input_rate_hz
            or int(caps.get("channels", 0)) != contract.channels_in
        ):
            raise ProcessingReadbackMismatchError(
                "DSP_READBACK_CAPS_MISMATCH",
                f"working caps {caps!r} do not match {contract.working_format}",
            )

    # ── transacción (PREPARE -> validate -> COMMIT -> receipt) ────────
    def begin_candidate(
        self,
        plan: CompiledProcessingPlan,
        *,
        host_generation: int,
        transport: object | None = None,
        processing_generation: int | None = None,
    ) -> ProcessingCandidateIdentity:
        """Prepare + readback-validate a candidate; EFFECTIVE is NOT touched.

        ``processing_generation`` is supplied by the serialized transaction
        worker (assigned on the owner at enqueue time); direct callers get a
        fresh revision.
        """
        generation = (
            self.note_requested()
            if processing_generation is None
            else int(processing_generation)
        )
        active_transport = transport if transport is not None else self._transport
        if active_transport is None:
            raise ProcessingTransactionError(
                "DSP_TRANSPORT_UNAVAILABLE",
                "no processing transport is composed for this service",
            )
        wire = self.plan_to_wire(plan)
        observed = active_transport.prepare_candidate(
            wire, processing_generation=generation
        )
        try:
            self.validate_readback(plan, observed)
        except Exception as original:
            # B1: explicit child abort; a FAILED abort is a double fault and
            # must never be silenced: ownership is uncertain, the error is
            # typed and both causes are preserved.
            abort = getattr(active_transport, "abort_candidate", None)
            abort_error: Exception | None = None
            if callable(abort):
                try:
                    aborted = abort()
                except Exception as exc:  # noqa: BLE001 - preserved below
                    abort_error = exc
                else:
                    if aborted is False:
                        abort_error = ProcessingTransactionError(
                            "DSP_CANDIDATE_ABORT_REJECTED",
                            "the child rejected the candidate abort",
                        )
                    elif aborted is None:
                        abort_error = ProcessingTransactionError(
                            "DSP_CANDIDATE_ABORT_UNPROVEN",
                            "the child returned no abort result",
                        )
            if abort_error is not None:
                abort_code = (
                    abort_error.code
                    if isinstance(abort_error, ProcessingTransactionError)
                    else "DSP_CANDIDATE_ABORT_FAILED"
                )
                raise ProcessingTransactionError(
                    abort_code,
                    "candidate readback was invalid AND its abort was not "
                    f"proven; native ownership is uncertain (readback: "
                    f"{original}; abort: {abort_error})",
                    payload={
                        "readback_error": str(original),
                        "abort_error": str(abort_error),
                        "abort_code": abort_code,
                        "candidate_retained": True,
                    },
                ) from original
            raise
        with self._state_lock:
            self._prepared_plans[plan.plan_id] = plan
        pipeline_generation = int(observed.get("pipeline_generation") or 0)
        self._record_processing(
            ProcessingTruthState.PREPARING,
            plan_id=plan.plan_id,
            pipeline_generation=pipeline_generation,
            host_generation=host_generation,
        )
        return ProcessingCandidateIdentity(
            candidate_id=(
                f"{plan.plan_id}:{generation}:{host_generation}:{pipeline_generation}"
            ),
            plan_id=plan.plan_id,
            graph_revision=plan.graph_revision,
            host_generation=host_generation,
            pipeline_generation=pipeline_generation,
            processing_generation=generation,
        )

    def commit_candidate(
        self,
        candidate: ProcessingCandidateIdentity,
        *,
        transport: object | None = None,
    ) -> ProcessingCommitReceipt:
        """Authorize the destructive commit and require a real receipt.

        EFFECTIVE can only be reached through a validated receipt: the child
        must have installed the candidate into the productive runtime.
        """
        with self._state_lock:
            current_requested = self._requested_revision
        if candidate.processing_generation != current_requested:
            raise ProcessingStaleCommitError(
                "DSP_STALE_COMMIT",
                f"candidate revision {candidate.processing_generation} is "
                f"stale (requested {current_requested})",
            )
        active_transport = transport if transport is not None else self._transport
        if active_transport is None:
            raise ProcessingTransactionError(
                "DSP_TRANSPORT_UNAVAILABLE",
                "no processing transport is composed for this service",
            )
        try:
            payload = active_transport.commit_candidate(
                plan_id=candidate.plan_id,
                processing_generation=candidate.processing_generation,
                pipeline_generation=candidate.pipeline_generation,
                candidate_id=candidate.candidate_id,
            )
        except Exception as exc:  # noqa: BLE001 - duck-typed transport boundary
            code = str(getattr(exc, "code", None) or "DSP_COMMIT_FAILED")
            error_payload = getattr(exc, "payload", None) or {}
            untouched = bool(error_payload.get("predecessor_untouched"))
            restored = bool(error_payload.get("predecessor_restored"))
            if not (untouched or restored):
                # The destructive boundary may have been crossed without a
                # proven restoration: the physical truth is UNKNOWN, so the
                # effective state is explicitly UNAVAILABLE (never a clean
                # BYPASSED claim) and no plan id survives.
                self._effective_state = ProcessingEffectiveState.UNAVAILABLE
                self._effective_plan_id = None
            elif self._effective_plan_id is not None:
                self._effective_state = ProcessingEffectiveState.EFFECTIVE
            raise ProcessingTransactionError(code, str(exc)) from exc
        if not isinstance(payload, dict):
            raise ProcessingTransactionError(
                "DSP_COMMIT_RECEIPT_INVALID", "child returned no receipt object"
            )
        receipt = ProcessingCommitReceipt(
            candidate=candidate,
            installed=bool(payload.get("installed")),
            observed_plan_id=str(payload.get("observed_plan_id") or ""),
            observed_graph_revision=int(payload.get("observed_graph_revision") or -1),
            observed_pipeline_generation=int(payload.get("pipeline_generation") or -1),
            observed_processing_generation=int(
                payload.get("processing_generation") or -1
            ),
            observed_host_generation=int(payload.get("host_generation") or -1),
            observed_candidate_id=str(payload.get("candidate_id") or ""),
            native_runtime_identity=str(payload.get("runtime_identity") or ""),
        )
        prepared_plan = None
        with self._state_lock:
            prepared_plan = self._prepared_plans.get(candidate.plan_id)
        try:
            validated = self._validate_receipt(receipt)
            post_install = payload.get("observed")
            if prepared_plan is not None:
                if not isinstance(post_install, dict):
                    raise ProcessingTransactionError(
                        "DSP_COMMIT_RECEIPT_INVALID",
                        "receipt carries no post-install readback",
                    )
                if post_install.get("caps_source") != "negotiated":
                    raise ProcessingTransactionError(
                        "DSP_CAPS_NOT_NEGOTIATED",
                        "productive commit requires negotiated working caps",
                    )
                self.validate_readback(prepared_plan, post_install, mode="filter")
            return validated
        except Exception as exc:  # noqa: BLE001 - containment below
            # A receipt that CLAIMS an install means the destructive boundary
            # MAY have been crossed, even when the receipt contract itself is
            # invalid. Contain through a PROVEN bypass when possible; the
            # state is never EFFECTIVE and never claims a clean bypass. If the
            # child never claimed an install, nothing is contained and the
            # predecessor state is untouched.
            attempted = bool(receipt.installed)
            contained = False
            if attempted:
                containment = getattr(active_transport, "bypass_processing", None)
                if callable(containment):
                    try:
                        result = containment()
                        contained = bool(
                            isinstance(result, dict) and result.get("bypassed")
                        )
                    except Exception:  # noqa: BLE001 - containment best effort
                        contained = False
                with self._state_lock:
                    self._effective_state = ProcessingEffectiveState.UNAVAILABLE
                    self._effective_plan_id = None
            payload_extra = {
                "containment_attempted": attempted,
                "containment_proven": contained,
                "predecessor_untouched": not attempted,
            }
            if isinstance(exc, ProcessingTransactionError):
                exc.payload = payload_extra
                raise
            raise ProcessingTransactionError(
                "DSP_COMMIT_POST_VALIDATION_FAILED",
                f"installed candidate could not be validated: {exc}",
                payload=payload_extra,
            ) from exc

    def _validate_receipt(
        self, receipt: ProcessingCommitReceipt
    ) -> ProcessingCommitReceipt:
        candidate = receipt.candidate
        if not receipt.installed:
            raise ProcessingTransactionError(
                "DSP_COMMIT_NOT_INSTALLED",
                "the candidate was not installed into the productive runtime",
            )
        if receipt.observed_plan_id != candidate.plan_id:
            raise ProcessingTransactionError(
                "DSP_COMMIT_RECEIPT_MISMATCH",
                f"receipt plan {receipt.observed_plan_id!r} != {candidate.plan_id!r}",
            )
        if receipt.observed_graph_revision != candidate.graph_revision:
            raise ProcessingTransactionError(
                "DSP_COMMIT_RECEIPT_MISMATCH",
                "receipt graph revision does not match the candidate",
            )
        if receipt.observed_pipeline_generation != candidate.pipeline_generation:
            raise ProcessingTransactionError(
                "DSP_COMMIT_RECEIPT_MISMATCH",
                "receipt pipeline generation does not match the candidate",
            )
        if receipt.observed_processing_generation != candidate.processing_generation:
            raise ProcessingTransactionError(
                "DSP_COMMIT_RECEIPT_MISMATCH",
                "receipt processing generation does not match the candidate",
            )
        if receipt.observed_host_generation != candidate.host_generation:
            raise ProcessingTransactionError(
                "DSP_COMMIT_RECEIPT_MISMATCH",
                "receipt host generation does not match the candidate",
            )
        if receipt.observed_candidate_id != candidate.candidate_id:
            raise ProcessingTransactionError(
                "DSP_COMMIT_RECEIPT_MISMATCH",
                "receipt candidate id does not match the candidate",
            )
        if not receipt.native_runtime_identity:
            raise ProcessingTransactionError(
                "DSP_COMMIT_RECEIPT_MISMATCH",
                "receipt carries no native runtime identity",
            )
        return receipt

    # ── API productiva (paquete A) ────────────────────────────────────
    def apply_processing_async(
        self,
        graph: object,
        signal: object,
        *,
        assets: tuple = (),
        policy: object | None = None,
        on_done: Callable[[dict[str, Any]], None] | None = None,
        on_failed: Callable[[Exception], None] | None = None,
        async_submit: Callable[[Callable, Callable], None] | None = None,
    ) -> None:
        """Owner-safe DSP apply serialized by ONE dedicated transaction worker.

        The owner only assigns the intent revision and enqueues (short); the
        long IPC work runs on the transaction worker with NO state lock held;
        completions land on the owner through the canonical executor. A newer
        intent supersedes queued work and fences the running transaction.
        """
        submit = async_submit if async_submit is not None else self._async_submit
        if submit is None:
            raise ProcessingTransactionError(
                "DSP_ASYNC_UNAVAILABLE",
                "no async executor is composed for processing",
            )
        revision = self.note_requested()

        def run(tx_revision: int) -> dict[str, Any]:
            self.refresh_capabilities()
            effective = EffectiveProcessingGraphResolver().resolve(
                graph, input_signal=signal, assets=assets
            )
            plan = ProcessingGraphCompiler().compile(
                effective,
                backend=self.capabilities,
                assets=assets,
                sample_policy=policy,
            )
            transport = self._transport
            host_generation = int(getattr(transport, "host_generation", lambda: 0)())
            candidate = self.begin_candidate(
                plan,
                host_generation=host_generation,
                transport=transport,
                processing_generation=tx_revision,
            )
            receipt = self.commit_candidate(candidate, transport=transport)
            published = self.publish_effective(receipt)
            return {
                "plan_id": plan.plan_id,
                "graph_revision": plan.graph_revision,
                "revision": published,
                "candidate_id": candidate.candidate_id,
                "runtime_identity": receipt.native_runtime_identity,
            }

        def completed(value, error) -> None:
            if error is not None:
                if on_failed is not None:
                    on_failed(error)
                return
            if on_done is not None:
                on_done(value)

        self._enqueue_transaction(revision=revision, run=run, completed=completed)

    def disable_processing_async(
        self,
        *,
        on_done: Callable[[bool], None] | None = None,
        on_failed: Callable[[Exception], None] | None = None,
        async_submit: Callable[[Callable, Callable], None] | None = None,
    ) -> None:
        """Owner-safe bypass serialized through the same transaction worker."""
        submit = async_submit if async_submit is not None else self._async_submit
        if submit is None:
            raise ProcessingTransactionError(
                "DSP_ASYNC_UNAVAILABLE",
                "no async executor is composed for processing",
            )
        revision = self.note_requested()

        def run(tx_revision: int) -> bool:
            return self.bypass_processing(
                transport=self._transport, processing_generation=tx_revision
            )

        def completed(value, error) -> None:
            if error is not None:
                if on_failed is not None:
                    on_failed(error)
                return
            if on_done is not None:
                on_done(bool(value))

        self._enqueue_transaction(revision=revision, run=run, completed=completed)

    # ── serialización de transacciones (UN worker, cero locks en IPC) ──
    def _enqueue_transaction(
        self,
        *,
        revision: int,
        run: Callable[[int], object],
        completed: Callable[[object, Exception | None], None],
    ) -> None:
        dropped: list[tuple[int, Callable]] = []
        with self._state_lock:
            if not self._accepting:
                completed(
                    None,
                    self._shutdown_error
                    or ProcessingTransactionError(
                        "DSP_SHUTDOWN", "processing service is shut down"
                    ),
                )
                return
            # Newest intent wins: queued (not yet running) older work is
            # dropped as stale instead of executing obsolete natively.
            keep = deque()
            while self._tx_queue:
                item = self._tx_queue.popleft()
                if item[0] < revision:
                    # (revision, run, completed): a dropped intent must be
                    # completed EXACTLY once through its completion callback.
                    dropped.append((item[0], item[2]))
                else:
                    keep.append(item)
            self._tx_queue = keep
            self._tx_queue.append((revision, run, completed))
            if len(self._tx_queue) > 32:
                # Bounded queue: never grow without limit under intent
                # storms. The OLDEST queued intent is superseded explicitly.
                stale = self._tx_queue.popleft()
                dropped.append((stale[0], stale[2]))
            if self._tx_thread is None or not self._tx_thread.is_alive():
                self._tx_thread = threading.Thread(
                    target=self._tx_loop, name="michi-dsp-tx", daemon=True
                )
                self._tx_thread.start()
        for stale_revision, stale_completed in dropped:
            stale_completed(
                None,
                ProcessingStaleCommitError(
                    "DSP_STALE_INTENT",
                    f"queued processing revision {stale_revision} was superseded",
                ),
            )

    def _tx_loop(self) -> None:
        while True:
            with self._state_lock:
                if not self._tx_queue:
                    self._tx_thread = None
                    return
                revision, run, completed = self._tx_queue.popleft()
                self._tx_active_revision = revision
            try:
                value = run(revision)
            except Exception as exc:  # noqa: BLE001 - typed delivery
                error: Exception | None = exc
                value = None
            else:
                error = None
            finally:
                with self._state_lock:
                    self._tx_active_revision = None
            self._deliver_completion(completed, value, error)

    def _deliver_completion(
        self,
        completed: Callable[[object, Exception | None], None],
        value: object,
        error: Exception | None,
    ) -> None:
        """Deliver on the owner via the canonical executor (no state lock)."""
        submit = self._async_submit
        if submit is None:
            completed(value, error)
            return

        def noop() -> None:
            return None

        def owner_completion(_ignored, _ignored_error) -> None:
            completed(value, error)

        submit(noop, owner_completion)

    def shutdown(self, *, timeout_s: float = 5.0) -> None:
        """Explicit lifecycle: reject new work, complete pending intents with
        a typed DSP_SHUTDOWN, drain references and join the worker bounded.

        Safe to call from the owner/teardown thread; idempotent.
        """
        with self._state_lock:
            if not self._accepting:
                return
            self._accepting = False
            self._shutdown_error = ProcessingTransactionError(
                "DSP_SHUTDOWN", "processing service was shut down"
            )
            pending = list(self._tx_queue)
            self._tx_queue.clear()
            self._prepared_plans.clear()
            thread = self._tx_thread
        for _revision, _run, completed in pending:
            try:
                completed(None, self._shutdown_error)
            except Exception:  # noqa: BLE001 - pending completion is terminal
                continue
        if thread is not None and thread is not threading.current_thread():
            thread.join(max(0.0, float(timeout_s)))

    @property
    def is_accepting(self) -> bool:
        return self._accepting

    def mark_host_lost(self, reason: str) -> None:
        """Host boundary gone: retire DSP evidence IMMEDIATELY.

        Takes ONLY the short state lock: the owner/Qt callback never waits
        for a blocked DSP transaction. Requested intent survives; no
        automatic reactivation is possible without a new receipt.
        """
        with self._state_lock:
            self._host_lost_reason = str(reason)
            self._capability_state = ProcessingCapabilityState.UNAVAILABLE
            self._capabilities = ProcessingBackendCapabilities(
                backend_id="gstreamer-host", strategies=frozenset()
            )
            self._facts = None
            if self._effective_state in (
                ProcessingEffectiveState.EFFECTIVE,
                ProcessingEffectiveState.PREPARING,
            ):
                self._effective_state = ProcessingEffectiveState.UNAVAILABLE
                self._effective_plan_id = None
        self._record_processing(ProcessingTruthState.UNAVAILABLE, detail=str(reason))

    def processing_truth(self) -> dict[str, Any]:
        """Semantic processing truth for presentation (F11 consumes this).

        ``bit_perfect`` is False while any processing revision is EFFECTIVE:
        a transforming path is never presented as bit-perfect.
        """
        with self._state_lock:
            effective = self._effective_state is ProcessingEffectiveState.EFFECTIVE
            return {
                "capability_state": self._capability_state.value,
                "requested_revision": self._requested_revision,
                "effective_revision": self._effective_revision,
                "effective_state": self._effective_state.value,
                "effective_plan_id": self._effective_plan_id,
                # Tri-state: True ONLY with positive preservation evidence
                # (none for Shared PCM yet); False while processing is
                # effective; None = NOT ESTABLISHED.
                "bit_perfect": False if effective else None,
                "bit_perfect_evidence": (
                    "processing_effective" if effective else "not_established"
                ),
                "host_lost_reason": self._host_lost_reason,
                "strategies": sorted(
                    strategy.value for strategy in self._capabilities.strategies
                ),
            }

    def bypass_processing(
        self,
        *,
        transport: object | None = None,
        processing_generation: int | None = None,
    ) -> bool:
        """Transactional bypass: EFFECTIVE only after a PROVEN removal."""
        active_transport = transport if transport is not None else self._transport
        if active_transport is None:
            raise ProcessingTransactionError(
                "DSP_TRANSPORT_UNAVAILABLE",
                "no processing transport is composed for this service",
            )
        if processing_generation is not None:
            with self._state_lock:
                current = self._requested_revision
            if int(processing_generation) != current:
                raise ProcessingStaleCommitError(
                    "DSP_STALE_INTENT",
                    f"bypass revision {processing_generation} is stale "
                    f"(requested {current})",
                )
        payload = active_transport.bypass_processing()
        if not isinstance(payload, dict) or not payload.get("bypassed"):
            raise ProcessingTransactionError(
                "DSP_BYPASS_UNPROVEN",
                "the runtime did not prove the processing filter removal",
            )
        with self._state_lock:
            if processing_generation is None:
                self._requested_revision += 1
                revision = self._requested_revision
            else:
                revision = int(processing_generation)
            self._effective_revision = revision
            self._effective_plan_id = None
            self._effective_state = ProcessingEffectiveState.BYPASSED
        self._record_processing(ProcessingTruthState.BYPASSED, readback_proven=True)
        return True

    def publish_effective(self, receipt: ProcessingCommitReceipt) -> int:
        """Publish EFFECTIVE — ONLY from a validated commit receipt."""
        self._validate_receipt(receipt)
        candidate = receipt.candidate
        with self._state_lock:
            current_requested = self._requested_revision
        if candidate.processing_generation != current_requested:
            raise ProcessingStaleCommitError(
                "DSP_STALE_COMMIT",
                f"candidate revision {candidate.processing_generation} is "
                f"stale (requested {current_requested})",
            )
        with self._state_lock:
            # ATOMIC validity fence: the state read here is the state the
            # EFFECTIVE claim rests on. A receipt whose host/pipeline/
            # processing generations are no longer current (host loss, new
            # host, newer intent) may NEVER publish.
            if self._host_lost_reason is not None:
                raise ProcessingStaleCommitError(
                    "DSP_STALE_COMMIT",
                    "host was lost before the receipt could be published",
                )
            if (
                self._host_generation is not None
                and candidate.host_generation != self._host_generation
            ):
                raise ProcessingStaleCommitError(
                    "DSP_STALE_COMMIT",
                    f"candidate host generation {candidate.host_generation} "
                    f"is not the current host {self._host_generation}",
                )
            if candidate.processing_generation != self._requested_revision:
                raise ProcessingStaleCommitError(
                    "DSP_STALE_COMMIT",
                    f"candidate revision {candidate.processing_generation} "
                    f"is stale (requested {self._requested_revision})",
                )
            self._effective_revision = candidate.processing_generation
            self._effective_plan_id = candidate.plan_id
            self._effective_state = ProcessingEffectiveState.EFFECTIVE
            self._last_receipt_runtime_identity = receipt.native_runtime_identity
            self._last_receipt_readback_proven = True
        self._record_processing(
            ProcessingTruthState.EFFECTIVE,
            plan_id=candidate.plan_id,
            pipeline_generation=candidate.pipeline_generation,
            runtime_identity=self._last_receipt_runtime_identity,
            readback_proven=bool(self._last_receipt_readback_proven),
            host_generation=candidate.host_generation,
        )
        return candidate.processing_generation

    def invalidate_effective(self, reason: str) -> None:
        """Host loss / runtime invalidity: effective evidence is retired.

        Requested intent survives (profiles are user intent); effective truth
        does not.
        """
        if self._effective_state is ProcessingEffectiveState.EFFECTIVE:
            self._effective_state = ProcessingEffectiveState.UNAVAILABLE
        elif self._effective_state is ProcessingEffectiveState.PREPARING:
            self._effective_state = ProcessingEffectiveState.BYPASSED
        self._effective_plan_id = None
        _ = reason


#: Native property round-trips (e.g. volume linear <-> dB) justify a small
#: documented tolerance; exact structural equality is still required.
_READBACK_ABS_TOLERANCE = 1e-6


def _values_equal(observed: Any, expected: Any) -> bool:
    if isinstance(expected, bool) or isinstance(observed, bool):
        return observed is expected
    if isinstance(expected, (int, float)) and isinstance(observed, (int, float)):
        return abs(float(observed) - float(expected)) <= _READBACK_ABS_TOLERANCE
    if isinstance(expected, list) and isinstance(observed, list):
        return len(observed) == len(expected) and all(
            _values_equal(item, target)
            for item, target in zip(observed, expected, strict=False)
        )
    if isinstance(expected, dict) and isinstance(observed, dict):
        return set(observed) == set(expected) and all(
            _values_equal(observed[key], expected[key]) for key in expected
        )
    return observed == expected


def json_normalize(value: Any) -> Any:
    """Wire-shape normalization: tuples become lists (JSON has no tuples)."""
    if isinstance(value, dict):
        return {str(key): json_normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_normalize(item) for item in value]
    return value


class ProcessingTransactionError(RuntimeError):
    """Typed transaction failure (commit/receipt/transport)."""

    def __init__(
        self, code: str, detail: str, payload: dict[str, Any] | None = None
    ) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.payload: dict[str, Any] = dict(payload or {})


class ProcessingStaleCommitError(RuntimeError):
    """A candidate prepared for an older revision may never publish."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class ProcessingReadbackMismatchError(RuntimeError):
    """Typed readback refusal: the candidate must be aborted."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
