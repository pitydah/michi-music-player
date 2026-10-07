"""AP2-F05 — parent semantic processing authority (PARENT-SAFE).

Owns the SEMANTIC processing state only: capability decisions from child
facts, the requested/effective processing revisions, and the readback-first
commit decisions. It NEVER creates a Gst object and never runs in the child.

Requested != Effective: an effective revision is published only after the
child returns primitive readback that the parent has validated against the
compiled plan.
"""

from __future__ import annotations

import contextlib
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

#: Strategies the F05 native builder actually implements TODAY. Factory
#: presence alone never implies support: the effective set is the
#: intersection of these and the real child-reported factories.
IMPLEMENTED_STRATEGIES: frozenset[ProcessingStrategy] = frozenset(
    {
        ProcessingStrategy.GAIN,
        ProcessingStrategy.GRAPHIC_EQ_NBANDS,
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
    ) -> None:
        self._capability_query = capability_query
        self._async_submit = async_submit
        self._transport = transport
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
            self._capability_state = ProcessingCapabilityState.UNAVAILABLE
            self._capabilities = ProcessingBackendCapabilities(
                backend_id="gstreamer-host", strategies=frozenset()
            )
            self._facts = None
            return self._capabilities
        try:
            raw = self._capability_query()
        except Exception:  # noqa: BLE001 - host loss/unavailable is typed state
            self._capability_state = ProcessingCapabilityState.UNAVAILABLE
            self._capabilities = ProcessingBackendCapabilities(
                backend_id="gstreamer-host", strategies=frozenset()
            )
            self._facts = None
            # A capability refresh never silently keeps an effective runtime
            # whose native evidence belongs to a dead host.
            self.invalidate_effective("capability query failed")
            return self._capabilities
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
        self._facts = facts
        if facts.runtime_failure is not None:
            # Contradiction is forbidden: a broken child runtime can NEVER
            # advertise supported strategies from stale/partial facts.
            self._capability_state = ProcessingCapabilityState.UNAVAILABLE
            self._capabilities = ProcessingBackendCapabilities(
                backend_id="gstreamer-host", strategies=frozenset()
            )
            self.invalidate_effective("capability runtime failure")
            return self._capabilities
        self._capability_state = ProcessingCapabilityState.QUERIED
        strategies = frozenset(
            strategy
            for strategy in IMPLEMENTED_STRATEGIES
            if self._factory_available(facts, *_STRATEGY_FACTORIES.get(strategy, ()))
        )
        self._capabilities = ProcessingBackendCapabilities(
            backend_id="gstreamer-host",
            strategies=strategies,
            factories=frozenset(
                name
                for name, value in facts.factories.items()
                if value.get("available")
            ),
        )
        if host_generation is not None:
            self._host_generation = host_generation
        return self._capabilities

    @staticmethod
    def _factory_available(facts: ProcessingCapabilityFacts, *names: str) -> bool:
        return all(
            bool(facts.factories.get(name, {}).get("available")) for name in names
        )

    # ── intención / revisión efectiva ─────────────────────────────────
    def note_requested(self) -> int:
        """New requested processing intent: an effective revision is now
        PREPARING (requested != effective) until a commit proves it."""
        self._requested_revision += 1
        self._effective_state = ProcessingEffectiveState.PREPARING
        return self._requested_revision

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
    ) -> ProcessingCandidateIdentity:
        """Prepare + readback-validate a candidate; EFFECTIVE is NOT touched."""
        generation = self.note_requested()
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
        except Exception:
            # B1: a prepared candidate that fails validation is explicitly
            # aborted in the child; its ownership is never silently retained.
            abort = getattr(active_transport, "abort_candidate", None)
            if callable(abort):
                with contextlib.suppress(Exception):
                    abort()
            raise
        self._prepared_plans[plan.plan_id] = plan
        pipeline_generation = int(observed.get("pipeline_generation") or 0)
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
        if candidate.processing_generation != self._requested_revision:
            raise ProcessingStaleCommitError(
                "DSP_STALE_COMMIT",
                f"candidate revision {candidate.processing_generation} is "
                f"stale (requested {self._requested_revision})",
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
        prepared_plan = self._prepared_plans.get(candidate.plan_id)
        post_install = payload.get("observed")
        if prepared_plan is not None:
            if not isinstance(post_install, dict):
                raise ProcessingTransactionError(
                    "DSP_COMMIT_RECEIPT_INVALID",
                    "receipt carries no post-install readback",
                )
            # The PRODUCTIVE installed graph must satisfy the same exact
            # readback contract as the validated candidate, PLUS negotiated
            # caps: EFFECTIVE can never rest on "configured" caps alone.
            if post_install.get("caps_source") != "negotiated":
                raise ProcessingTransactionError(
                    "DSP_CAPS_NOT_NEGOTIATED",
                    "productive commit requires negotiated working caps",
                )
            self.validate_readback(prepared_plan, post_install, mode="filter")
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
        return self._validate_receipt(receipt)

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
        """Owner-safe DSP apply: prepare/readback/commit/public on a worker.

        The completion callback is delivered by the injected executor (the
        canonical Qt owner dispatch in production). EFFECTIVE is published
        only through a validated commit receipt.
        """
        submit = async_submit if async_submit is not None else self._async_submit
        if submit is None:
            raise ProcessingTransactionError(
                "DSP_ASYNC_UNAVAILABLE",
                "no async executor is composed for processing",
            )

        def work() -> dict[str, Any]:
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
                plan, host_generation=host_generation, transport=transport
            )
            receipt = self.commit_candidate(candidate, transport=transport)
            revision = self.publish_effective(receipt)
            return {
                "plan_id": plan.plan_id,
                "graph_revision": plan.graph_revision,
                "revision": revision,
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

        submit(work, completed)

    def disable_processing_async(
        self,
        *,
        on_done: Callable[[bool], None] | None = None,
        on_failed: Callable[[Exception], None] | None = None,
        async_submit: Callable[[Callable, Callable], None] | None = None,
    ) -> None:
        """Owner-safe bypass: removal must be PROVEN before BYPASSED."""
        submit = async_submit if async_submit is not None else self._async_submit
        if submit is None:
            raise ProcessingTransactionError(
                "DSP_ASYNC_UNAVAILABLE",
                "no async executor is composed for processing",
            )

        def work() -> bool:
            return self.bypass_processing(transport=self._transport)

        def completed(value, error) -> None:
            if error is not None:
                if on_failed is not None:
                    on_failed(error)
                return
            if on_done is not None:
                on_done(bool(value))

        submit(work, completed)

    def processing_truth(self) -> dict[str, Any]:
        """Semantic processing truth for presentation (F11 consumes this).

        ``bit_perfect`` is False while any processing revision is EFFECTIVE:
        a transforming path is never presented as bit-perfect.
        """
        effective = self._effective_state is ProcessingEffectiveState.EFFECTIVE
        return {
            "capability_state": self._capability_state.value,
            "requested_revision": self._requested_revision,
            "effective_revision": self._effective_revision,
            "effective_state": self._effective_state.value,
            "effective_plan_id": self._effective_plan_id,
            "bit_perfect": not effective,
            "strategies": sorted(
                strategy.value for strategy in self._capabilities.strategies
            ),
        }

    def bypass_processing(self, *, transport: object | None = None) -> bool:
        """Transactional bypass: EFFECTIVE only after a PROVEN removal."""
        active_transport = transport if transport is not None else self._transport
        if active_transport is None:
            raise ProcessingTransactionError(
                "DSP_TRANSPORT_UNAVAILABLE",
                "no processing transport is composed for this service",
            )
        payload = active_transport.bypass_processing()
        if not isinstance(payload, dict) or not payload.get("bypassed"):
            raise ProcessingTransactionError(
                "DSP_BYPASS_UNPROVEN",
                "the runtime did not prove the processing filter removal",
            )
        self._requested_revision += 1
        self._effective_revision = self._requested_revision
        self._effective_plan_id = None
        self._effective_state = ProcessingEffectiveState.BYPASSED
        return True

    def publish_effective(self, receipt: ProcessingCommitReceipt) -> int:
        """Publish EFFECTIVE — ONLY from a validated commit receipt."""
        self._validate_receipt(receipt)
        candidate = receipt.candidate
        if candidate.processing_generation != self._requested_revision:
            raise ProcessingStaleCommitError(
                "DSP_STALE_COMMIT",
                f"candidate revision {candidate.processing_generation} is "
                f"stale (requested {self._requested_revision})",
            )
        self._effective_revision = candidate.processing_generation
        self._effective_plan_id = candidate.plan_id
        self._effective_state = ProcessingEffectiveState.EFFECTIVE
        return self._effective_revision

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

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


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
