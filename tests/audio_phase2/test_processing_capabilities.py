"""AP2-F05 Part B — child processing capabilities + readback gate.

Capability facts are REAL child-native observations; the parent decides
strategy support; readback mismatches fail closed. No Gst object crosses IPC.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from michi.application.audio_processing_service import (
    AudioProcessingService,
    ProcessingCapabilityState,
    ProcessingReadbackMismatchError,
)
from michi.application.effective_processing_graph import (
    EffectiveProcessingGraphResolver,
)
from michi.application.processing_graph_compiler import (
    ProcessingCompilationError,
    ProcessingGraphCompiler,
)
from michi.domain.audio_processing import (
    BiquadType,
    GraphicEqLayout,
    GraphicEqNode,
    ParametricEqNode,
    PeqBand,
    PreampNode,
    ProcessingGraph,
    ProcessingStrategy,
)
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
from michi.infrastructure.audio_engines.gstreamer_host_client import (
    GStreamerHostSupervisor,
)
from michi.infrastructure.audio_engines.gstreamer_host_port import (
    GStreamerHostedAudioPort,
)
from michi.infrastructure.audio_processing.native_mapping import (
    NativeProcessingMapping,
)

FAKE_HOST = Path(__file__).parent / "gst_host_engine_fake.py"
FAST = {
    "start_timeout_s": 1.5,
    "command_timeout_s": 1.0,
    "terminate_grace_s": 0.4,
    "term_grace_s": 0.3,
    "kill_grace_s": 0.5,
}


def _port(behavior: str):
    def factory(fd: int) -> list[str]:
        return [
            sys.executable,
            str(FAKE_HOST),
            "--fd",
            str(fd),
            "--engine-behavior",
            behavior,
        ]

    supervisor = GStreamerHostSupervisor(command_factory=factory, **FAST)
    port = GStreamerHostedAudioPort(
        supervisor,
        command_deadline_s=FAST["command_timeout_s"],
        load_deadline_s=FAST["command_timeout_s"],
    )
    return supervisor, port


def _signal(rate: int = 96000, channels: int = 2):
    return PcmSignalFormat(
        rate_hz=rate,
        transport_format="F32LE",
        significant_bits=None,
        layout=ChannelLayout(
            positions=tuple(f"CH{index}" for index in range(channels))
        ),
    )


def _preamp_graph():
    return ProcessingGraph(
        graph_id="graph:f05",
        revision=1,
        nodes=(PreampNode(node_id="pre", gain_db=-3.0),),
    )


def _graphic_graph():
    return ProcessingGraph(
        graph_id="graph:f05",
        revision=2,
        nodes=(
            GraphicEqNode(
                node_id="geq",
                layout_id=GraphicEqLayout.MICHI_10_V1,
                gains_db=(1.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            ),
        ),
    )


def _peq_graph():
    return ProcessingGraph(
        graph_id="graph:f05",
        revision=3,
        nodes=(
            ParametricEqNode(
                node_id="peq",
                bands=(
                    PeqBand(
                        band_id="b1",
                        filter_type=BiquadType.PEAK,
                        frequency_hz=1000.0,
                        q=0.707,
                        gain_db=2.0,
                    ),
                ),
            ),
        ),
    )


def _compile_with(service: AudioProcessingService, graph):
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=_signal(), assets=()
    )
    return ProcessingGraphCompiler().compile(
        effective, backend=service.capabilities, assets=()
    )


# ── child capability facts (fake host) ────────────────────────────────
def test_child_capability_query_returns_primitive_facts() -> None:
    supervisor, port = _port("normal")
    try:
        port.activate()
        facts = port.query_processing_capabilities()
        assert facts["gstreamer_version"] == "GStreamer fake-1.0"
        assert facts["runtime_failure"] is None
        assert set(facts["factories"]) >= {
            "equalizer-nbands",
            "audioiirfilter",
            "audiofirfilter",
            "audioconvert",
            "audioresample",
            "volume",
        }
    finally:
        port.close()


def test_capability_query_timeout_is_typed_and_bounded() -> None:
    supervisor, port = _port("capabilities_hang")
    port.activate()
    with pytest.raises(Exception) as info:
        port.query_processing_capabilities()
    assert "OUTPUT_HOST_TIMEOUT" in str(info.value) or "OUTPUT_HOST_LOST" in str(
        info.value
    )
    assert not supervisor.pid_alive()
    supervisor.close()


def test_service_decides_support_from_real_facts() -> None:
    supervisor, port = _port("normal")
    try:
        port.activate()
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
        )
        capabilities = service.refresh_capabilities()
        assert service.capability_state is ProcessingCapabilityState.QUERIED
        # Implemented TODAY: GAIN + GRAPHIC_EQ_NBANDS (given the factories).
        assert capabilities.strategies == frozenset(
            {ProcessingStrategy.GAIN, ProcessingStrategy.GRAPHIC_EQ_NBANDS}
        )
        # Compiler integration: the F05 slice compiles; unimplemented
        # strategies refuse with the canonical typed error.
        assert _compile_with(service, _preamp_graph()) is not None
        assert _compile_with(service, _graphic_graph()) is not None
        with pytest.raises(ProcessingCompilationError) as exc:
            _compile_with(service, _peq_graph())
        assert exc.value.code == "DSP_STRATEGY_UNAVAILABLE"
    finally:
        port.close()


def test_missing_equalizer_still_supports_graphic_via_cascade() -> None:
    """equalizer-nbands is diagnostics only: the F05 native mapping is the
    audioiirfilter cascade, so a missing equalizer does NOT disable Graphic
    EQ (this mirrors the real GStreamer 1.28 environment)."""
    supervisor, port = _port("capabilities_missing_eq")
    try:
        port.activate()
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
        )
        capabilities = service.refresh_capabilities()
        assert ProcessingStrategy.GAIN in capabilities.strategies
        assert ProcessingStrategy.GRAPHIC_EQ_NBANDS in capabilities.strategies
        assert _compile_with(service, _graphic_graph()) is not None
    finally:
        port.close()


def test_incompatible_property_excludes_support() -> None:
    supervisor, port = _port("capabilities_incompatible_prop")
    try:
        port.activate()
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
        )
        capabilities = service.refresh_capabilities()
        assert ProcessingStrategy.GRAPHIC_EQ_NBANDS not in capabilities.strategies
        with pytest.raises(ProcessingCompilationError):
            _compile_with(service, _graphic_graph())
    finally:
        port.close()


def test_host_loss_invalidates_capabilities_and_effective_truth() -> None:
    supervisor, port = _port("normal")
    port.activate()
    service = AudioProcessingService(
        capability_query=port.query_processing_capabilities,
        native_mapping=NativeProcessingMapping(),
    )
    service.refresh_capabilities()
    service.note_requested()
    transport = _FakeProcessingTransport()
    plan = _plan()
    candidate = service.begin_candidate(plan, host_generation=1, transport=transport)
    service.publish_effective(service.commit_candidate(candidate, transport=transport))
    assert service.effective_state.value == "effective"

    port.close()  # host boundary gone
    capabilities = service.refresh_capabilities()
    assert service.capability_state is ProcessingCapabilityState.UNAVAILABLE
    assert capabilities.strategies == frozenset()
    # Requested intent survives; effective runtime truth is retired.
    assert service.effective_state.value in {"unavailable", "bypassed"}
    assert service.effective_plan_id is None
    supervisor.close()


# ── readback gate (parent semantic comparison) ────────────────────────
def _observed_for(plan, *, override=None):
    observed = {
        "plan_id": plan.plan_id,
        "graph_revision": plan.graph_revision,
        "nodes": [
            {
                "node_id": node.node_id,
                "strategy": node.strategy.value,
                "factories": list(
                    NativeProcessingMapping().expected_native_factories(node)
                ),
                "observed": NativeProcessingMapping().expected_native_properties(
                    node, rate_hz=plan.sample_contract.input_rate_hz
                ),
            }
            for node in plan.nodes
        ],
        "working_caps": {
            "format": plan.sample_contract.working_format,
            "rate_hz": plan.sample_contract.input_rate_hz,
            "channels": plan.sample_contract.channels_in,
        },
    }
    if override:
        override(observed)
    return observed


class _FakeProcessingTransport:
    """Scripted transport double for transaction-level tests."""

    def __init__(self, *, installed: bool = True, pipeline_generation: int = 3) -> None:
        self.installed = installed
        self.pipeline_generation = pipeline_generation
        self.receipt_pipeline_generation: int | None = None
        self.prepared: list[dict] = []
        self.commits: list[dict] = []
        self.last_wire: dict | None = None

    def prepare_candidate(self, wire: dict, *, processing_generation: int = 0) -> dict:
        self.prepared.append(wire)
        self.last_wire = wire
        self.processing_generation = processing_generation
        plan_id = wire["plan_id"]
        revision = int(wire["graph_revision"])
        # Build the exact observed shape from the wire.
        from michi.application.processing_graph_compiler import (
            CompiledProcessingNode,
        )
        from michi.domain.audio_processing import ProcessingNodeKind, ProcessingStrategy

        nodes = []
        for node in wire["nodes"]:
            strategy = str(node["strategy"])
            properties = node["properties"]
            if strategy == "gain":
                observed = {"gain_db": float(properties["gain_db"])}
            else:
                observed = {
                    "layout_id": str(properties["layout_id"]),
                    "band_indices": [int(v) for v in properties["band_indices"]],
                    "biquad": properties["biquad_cascade"],
                }
            nodes.append(
                {
                    "node_id": node["node_id"],
                    "strategy": strategy,
                    "factories": (
                        ["volume"]
                        if strategy == "gain"
                        else ["audioiirfilter"] * len(properties["gains_db"])
                    ),
                    "observed": observed,
                }
            )
        _ = (CompiledProcessingNode, ProcessingNodeKind, ProcessingStrategy)
        return {
            "plan_id": plan_id,
            "graph_revision": revision,
            "nodes": nodes,
            "working_caps": {
                "format": wire["working_format"],
                "rate_hz": wire["input_rate_hz"],
                "channels": wire["channels"],
            },
            "graph_factories": [
                "audiotestsrc",
                "capsfilter",
                "audioconvert",
                "capsfilter",
                "fakesink",
                *[factory for node in nodes for factory in node["factories"]],
            ],
            "pipeline_generation": self.pipeline_generation,
        }

    def commit_candidate(
        self,
        *,
        plan_id,
        processing_generation,
        pipeline_generation,
        candidate_id: str = "",
    ):
        self.commits.append(
            {
                "plan_id": plan_id,
                "processing_generation": processing_generation,
                "pipeline_generation": pipeline_generation,
            }
        )
        observed = (
            self.prepare_candidate(self.last_wire) if self.last_wire is not None else {}
        )
        # Productive filter mode: exact structural subset + per-node factories.
        observed["graph_factories"] = ["audioconvert", "capsfilter"] + [
            factory
            for node in observed.get("nodes", [])
            for factory in node["factories"]
        ]
        observed["caps_source"] = "negotiated"
        return {
            "installed": self.installed,
            "observed": observed,
            "observed_plan_id": plan_id,
            "observed_graph_revision": 1,
            "pipeline_generation": (
                self.receipt_pipeline_generation
                if self.receipt_pipeline_generation is not None
                else pipeline_generation
            ),
            "processing_generation": processing_generation,
            "host_generation": 1,
            "candidate_id": candidate_id,
            "runtime_identity": "fake:playbin3/audio-filter",
        }


def _plan():
    service = AudioProcessingService(native_mapping=NativeProcessingMapping())
    capabilities = service.refresh_capabilities()
    assert capabilities.strategies == frozenset()
    effective = EffectiveProcessingGraphResolver().resolve(
        _preamp_graph(), input_signal=_signal(), assets=()
    )
    from michi.application.processing_graph_compiler import (
        ProcessingBackendCapabilities,
    )

    return ProcessingGraphCompiler().compile(
        effective,
        backend=ProcessingBackendCapabilities(
            backend_id="test",
            strategies=frozenset(ProcessingStrategy),
        ),
        assets=(),
    )


def _transaction_plan(*, preamp_only: bool = True):
    service = AudioProcessingService(native_mapping=NativeProcessingMapping())
    from michi.application.processing_graph_compiler import (
        ProcessingBackendCapabilities as Backend,
    )

    graph = _preamp_graph() if preamp_only else _graphic_graph()
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=_signal(), assets=()
    )
    plan = ProcessingGraphCompiler().compile(
        effective,
        backend=Backend(backend_id="test", strategies=frozenset(ProcessingStrategy)),
        assets=(),
    )
    return service, plan


def test_full_transaction_publishes_only_from_a_validated_receipt() -> None:
    service, plan = _transaction_plan()
    transport = _FakeProcessingTransport()
    candidate = service.begin_candidate(plan, host_generation=1, transport=transport)
    assert candidate.processing_generation == service.requested_revision
    assert candidate.pipeline_generation == 3
    # EFFECTIVE is untouched by prepare+readback.
    assert service.effective_state.value == "preparing"

    receipt = service.commit_candidate(candidate, transport=transport)
    assert receipt.installed is True
    revision = service.publish_effective(receipt)
    assert revision == candidate.processing_generation
    assert service.effective_state.value == "effective"
    assert service.effective_plan_id == plan.plan_id


def test_commit_without_install_never_publishes() -> None:
    from michi.application.audio_processing_service import ProcessingTransactionError

    service, plan = _transaction_plan()
    transport = _FakeProcessingTransport(installed=False)
    candidate = service.begin_candidate(plan, host_generation=1, transport=transport)
    with pytest.raises(ProcessingTransactionError) as info:
        service.commit_candidate(candidate, transport=transport)
    assert info.value.code == "DSP_COMMIT_NOT_INSTALLED"
    assert service.effective_state.value == "preparing"


def test_commit_with_mismatched_receipt_identity_never_publishes() -> None:
    from michi.application.audio_processing_service import ProcessingTransactionError

    service, plan = _transaction_plan()
    transport = _FakeProcessingTransport(pipeline_generation=5)
    candidate = service.begin_candidate(plan, host_generation=1, transport=transport)
    # The runtime moved underneath the receipt.
    transport.receipt_pipeline_generation = 6
    with pytest.raises(ProcessingTransactionError) as info:
        service.commit_candidate(candidate, transport=transport)
    assert info.value.code == "DSP_COMMIT_RECEIPT_MISMATCH"
    assert service.effective_state.value == "preparing"


@pytest.mark.parametrize(
    "override",
    [
        lambda o: o.update(plan_id="plan:other"),
        lambda o: o.update(graph_revision=99),
        lambda o: o.update(nodes=[]),
        lambda o: o["nodes"][0].update(strategy="resample"),
        lambda o: o["nodes"][0]["observed"].update(gain_db=0.0),
        lambda o: o["working_caps"].update(format="F32LE"),
        lambda o: o.update(
            working_caps={"format": "F64LE", "rate_hz": 44100, "channels": 2}
        ),
    ],
)
def test_readback_mismatch_fails_closed(override) -> None:
    service = AudioProcessingService(native_mapping=NativeProcessingMapping())
    service.note_requested()
    plan = _plan()
    with pytest.raises(ProcessingReadbackMismatchError) as info:
        service.validate_readback(plan, _observed_for(plan, override=override))
    assert info.value.code.startswith("DSP_READBACK_")
    # No effective revision without validated readback.
    assert service.effective_state.value == "preparing"


def test_missing_readback_is_a_typed_mismatch() -> None:
    service = AudioProcessingService(native_mapping=NativeProcessingMapping())
    service.note_requested()
    plan = _plan()
    with pytest.raises(ProcessingReadbackMismatchError) as info:
        service.validate_readback(plan, {})
    assert info.value.code in {"DSP_READBACK_MISSING", "DSP_READBACK_PLAN_MISMATCH"}


def test_stale_processing_commit_cannot_publish_over_newer_intent() -> None:
    from michi.application.audio_processing_service import ProcessingStaleCommitError

    service, plan = _transaction_plan()
    transport = _FakeProcessingTransport()
    candidate = service.begin_candidate(plan, host_generation=1, transport=transport)
    # A newer processing intent supersedes the prepared candidate.
    service.note_requested()
    with pytest.raises(ProcessingStaleCommitError) as info:
        service.commit_candidate(candidate, transport=transport)
    assert info.value.code == "DSP_STALE_COMMIT"
    # Effective truth is NOT published from the stale candidate.
    assert service.effective_state.value == "preparing"


def test_graphic_cascade_matches_the_rbj_golden_mapping() -> None:
    """The compiled graphic plan maps deterministically to native biquads."""
    from michi.application.processing_graph_compiler import (
        ProcessingBackendCapabilities as Backend,
    )
    from michi.domain.audio_processing import BiquadType
    from michi.infrastructure.audio_processing.biquad import biquad_coefficients

    effective = EffectiveProcessingGraphResolver().resolve(
        _graphic_graph(), input_signal=_signal(), assets=()
    )
    plan = ProcessingGraphCompiler().compile(
        effective,
        backend=Backend(backend_id="test", strategies=frozenset(ProcessingStrategy)),
        assets=(),
    )
    node = plan.nodes[0]
    expected = NativeProcessingMapping().expected_native_properties(
        node, rate_hz=plan.sample_contract.input_rate_hz
    )
    from michi.domain.audio_processing import GRAPHIC_EQ_CENTER_HZ, GraphicEqLayout
    from michi.infrastructure.audio_processing.native_mapping import GRAPHIC_OCTAVE_Q

    properties = dict(node.properties)
    gains = properties["gains_db"]
    centers = [
        GRAPHIC_EQ_CENTER_HZ[GraphicEqLayout(properties["layout_id"])][index]
        for index in properties["band_indices"]
    ]
    for band, center, gain in zip(expected["biquad"], centers, gains, strict=True):
        reference = biquad_coefficients(
            BiquadType.PEAK,
            rate_hz=float(plan.sample_contract.input_rate_hz),
            frequency_hz=center,
            q=GRAPHIC_OCTAVE_Q,
            gain_db=float(gain),
        )
        assert band["a"] == [1.0, reference.a1, reference.a2]
        assert band["b"] == [reference.b0, reference.b1, reference.b2]
