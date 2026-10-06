"""AP2-F05 — parent semantic processing authority (PARENT-SAFE).

Owns the SEMANTIC processing state only: capability decisions from child
facts, the requested/effective processing revisions, and the readback-first
commit decisions. It NEVER creates a Gst object and never runs in the child.

Requested != Effective: an effective revision is published only after the
child returns primitive readback that the parent has validated against the
compiled plan.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from michi.application.processing_graph_compiler import (
    CompiledProcessingPlan,
    ProcessingBackendCapabilities,
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
    ) -> None:
        self._capability_query = capability_query
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
        self, plan: CompiledProcessingPlan, observed: dict[str, Any]
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
        global_factories = [
            str(name) for name in (observed.get("graph_factories") or [])
        ]
        if "audioresample" in global_factories:
            raise ProcessingReadbackMismatchError(
                "DSP_READBACK_UNEXPECTED_TRANSFORM",
                "the native graph contains an unexpected resampler",
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
        observed = active_transport.prepare_candidate(wire)
        self.validate_readback(plan, observed)
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
        payload = active_transport.commit_candidate(
            plan_id=candidate.plan_id,
            processing_generation=candidate.processing_generation,
            pipeline_generation=candidate.pipeline_generation,
        )
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
            # readback contract as the validated candidate.
            self.validate_readback(prepared_plan, post_install)
        receipt = ProcessingCommitReceipt(
            candidate=candidate,
            installed=bool(payload.get("installed")),
            observed_plan_id=str(payload.get("observed_plan_id") or ""),
            observed_graph_revision=int(payload.get("observed_graph_revision") or -1),
            observed_pipeline_generation=int(payload.get("pipeline_generation") or -1),
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
        if not receipt.native_runtime_identity:
            raise ProcessingTransactionError(
                "DSP_COMMIT_RECEIPT_MISMATCH",
                "receipt carries no native runtime identity",
            )
        return receipt

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
