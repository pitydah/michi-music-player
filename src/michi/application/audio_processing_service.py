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
    CompiledProcessingNode,
    CompiledProcessingPlan,
    ProcessingBackendCapabilities,
)
from michi.domain.audio_processing import (
    GRAPHIC_EQ_CENTER_HZ,
    BiquadType,
    GraphicEqLayout,
    ProcessingStrategy,
)

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
    ) -> None:
        self._capability_query = capability_query
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
    @staticmethod
    def _graphic_cascade(
        rate_hz: int, centers: list[float], gains: list[float]
    ) -> list[dict[str, Any]]:
        """Parent-computed RBJ peaking cascade for the active graphic bands."""
        from michi.infrastructure.audio_processing.biquad import (
            biquad_coefficients,
        )

        cascade: list[dict[str, Any]] = []
        for center, gain in zip(centers, gains, strict=True):
            coefficients = biquad_coefficients(
                BiquadType.PEAK,
                rate_hz=float(rate_hz),
                frequency_hz=float(center),
                q=_GRAPHIC_OCTAVE_Q,
                gain_db=float(gain),
            )
            cascade.append(
                {
                    "b": [
                        coefficients.b0,
                        coefficients.b1,
                        coefficients.b2,
                    ],
                    "a": [1.0, coefficients.a1, coefficients.a2],
                }
            )
        return cascade

    @classmethod
    def expected_native_properties(
        cls, node: CompiledProcessingNode, *, rate_hz: int
    ) -> dict[str, Any]:
        """Expected NATIVE readback shape for one compiled node."""
        properties = {str(key): json_normalize(value) for key, value in node.properties}
        if node.strategy is ProcessingStrategy.GAIN:
            return {"gain_db": float(properties["gain_db"])}
        if node.strategy is ProcessingStrategy.GRAPHIC_EQ_NBANDS:
            layout = GraphicEqLayout(str(properties["layout_id"]))
            indices = [int(value) for value in properties["band_indices"]]
            centers = [GRAPHIC_EQ_CENTER_HZ[layout][index] for index in indices]
            gains = [float(value) for value in properties["gains_db"]]
            return {
                "layout_id": layout.value,
                "band_indices": indices,
                "biquad": cls._graphic_cascade(rate_hz, centers, gains),
            }
        raise ValueError(f"no native mapping for strategy {node.strategy.value!r}")

    @staticmethod
    def plan_to_wire(plan: CompiledProcessingPlan) -> dict[str, Any]:
        """Build the bounded native execution DTO for one compiled plan.

        Semantic enrichment stays parent-side: graphic band centers are
        derived from the canonical layout, never from the child.
        """
        nodes: list[dict[str, Any]] = []
        for node in plan.nodes:
            properties = {
                str(key): json_normalize(value) for key, value in node.properties
            }
            if node.strategy is ProcessingStrategy.GRAPHIC_EQ_NBANDS:
                layout = GraphicEqLayout(str(properties["layout_id"]))
                indices = [int(value) for value in properties["band_indices"]]
                properties["band_centers_hz"] = [
                    GRAPHIC_EQ_CENTER_HZ[layout][index] for index in indices
                ]
                properties["biquad_cascade"] = AudioProcessingService._graphic_cascade(
                    plan.sample_contract.input_rate_hz,
                    [float(value) for value in properties["band_centers_hz"]],
                    [float(value) for value in properties["gains_db"]],
                )
            nodes.append(
                {
                    "node_id": node.node_id,
                    "kind": node.kind.value,
                    "strategy": node.strategy.value,
                    "properties": properties,
                }
            )
        contract = plan.sample_contract
        return {
            "plan_id": plan.plan_id,
            "graph_id": plan.graph_id,
            "graph_revision": plan.graph_revision,
            "input_format": contract.input_format,
            "working_format": contract.working_format,
            "input_rate_hz": contract.input_rate_hz,
            "channels": contract.channels_in,
            "nodes": nodes,
        }

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
        self._capability_state = (
            ProcessingCapabilityState.UNAVAILABLE
            if facts.runtime_failure is not None
            else ProcessingCapabilityState.QUERIED
        )
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
            try:
                expected_properties = AudioProcessingService.expected_native_properties(
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

    def publish_effective(
        self, plan_id: str, *, expected_revision: int | None = None
    ) -> int:
        """Publish the effective revision — ONLY after validated readback.

        ``expected_revision`` fences a delayed commit: a candidate prepared
        for revision N can never publish over a newer requested revision N+1
        (newest processing intent wins).
        """
        if (
            expected_revision is not None
            and expected_revision != self._requested_revision
        ):
            raise ProcessingStaleCommitError(
                "DSP_STALE_COMMIT",
                f"candidate revision {expected_revision} is stale "
                f"(requested {self._requested_revision})",
            )
        self._effective_revision = self._requested_revision
        self._effective_plan_id = plan_id
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
