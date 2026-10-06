"""AP2-F05 Part B — REAL hosted Shared PCM processing runtime (readback-first).

The candidate graph is built, prerolled and inspected by REAL GStreamer
inside the supervised output host; the parent validates primitive readback
and aborts on mismatch. No Gst object ever exists in the parent.
"""

from __future__ import annotations

import importlib.util

import pytest

from michi.application.audio_processing_service import AudioProcessingService
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

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="PyGObject/GStreamer not available on this host"
)

SLOW = {
    "start_timeout_s": 45.0,
    "command_timeout_s": 30.0,
    "terminate_grace_s": 5.0,
    "term_grace_s": 3.0,
    "kill_grace_s": 3.0,
}


def _real_port():
    supervisor = GStreamerHostSupervisor(**SLOW)
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
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


def _graph():
    return ProcessingGraph(
        graph_id="graph:f05-shared",
        revision=7,
        nodes=(
            PreampNode(node_id="pre", gain_db=-3.0),
            GraphicEqNode(
                node_id="geq",
                layout_id=GraphicEqLayout.MICHI_10_V1,
                gains_db=(3.0, 0.0, -2.0, 0.0, 1.5, 0.0, 0.0, 0.0, 0.0, 0.0),
            ),
        ),
    )


def _compile(service, graph):
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=_signal(), assets=()
    )
    return ProcessingGraphCompiler().compile(
        effective, backend=service.capabilities, assets=()
    )


def test_real_host_shared_pcm_processing_candidate_readback_first() -> None:
    supervisor, port = _real_port()
    try:
        port.activate()
        facts = port.query_processing_capabilities()
        assert isinstance(facts.get("gstreamer_version"), str)
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities
        )
        capabilities = service.refresh_capabilities()
        # Real environment: the F05 slice strategies are supported.
        assert ProcessingStrategy.GAIN in capabilities.strategies
        assert ProcessingStrategy.GRAPHIC_EQ_NBANDS in capabilities.strategies

        plan = _compile(service, _graph())
        wire = service.plan_to_wire(plan)
        assert wire["working_format"] == "F64LE"
        assert [node["strategy"] for node in wire["nodes"]] == [
            "gain",
            "graphic_eq_nbands",
        ]
        assert wire["nodes"][1]["properties"]["band_centers_hz"][:3] == [
            31.25,
            62.5,
            125.0,
        ]

        # REAL native build + preroll + property/caps readback in the child.
        observed = port.prepare_processing_candidate(wire)
        assert observed["plan_id"] == plan.plan_id
        assert observed["working_caps"] == {
            "format": "F64LE",
            "rate_hz": 96000,
            "channels": 2,
        }
        assert "volume" in observed["graph_factories"]
        # Graphic EQ maps to a parent-computed RBJ biquad cascade executed by
        # real audioiirfilter elements (equalizer-nbands does not expose its
        # band properties in GStreamer 1.28; the probe records that fact).
        graphic_plan_node = next(
            node for node in plan.nodes if node.strategy.value == "graphic_eq_nbands"
        )
        active_bands = len(dict(graphic_plan_node.properties)["band_indices"])
        assert observed["graph_factories"].count("audioiirfilter") == active_bands
        graphic = next(
            node
            for node in observed["nodes"]
            if node["strategy"] == "graphic_eq_nbands"
        )
        assert len(graphic["observed"]["biquad"]) == active_bands
        assert graphic["observed"]["biquad"][0]["a"][0] == 1.0

        # Parent validates expected vs observed (tolerant, fail-closed).
        service.note_requested()
        service.validate_readback(plan, observed)

        assert port.abort_processing_candidate() is True
    finally:
        port.close()
        supervisor.close()


def test_real_host_refuses_unimplemented_peq_strategy() -> None:
    supervisor, port = _real_port()
    try:
        port.activate()
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities
        )
        service.refresh_capabilities()
        with pytest.raises(ProcessingCompilationError) as info:
            _compile(
                service,
                ProcessingGraph(
                    graph_id="graph:peq",
                    revision=1,
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
                ),
            )
        assert info.value.code == "DSP_STRATEGY_UNAVAILABLE"
    finally:
        port.close()
        supervisor.close()


def test_new_candidate_supersedes_previous_native_candidate() -> None:
    supervisor, port = _real_port()
    try:
        port.activate()
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities
        )
        service.refresh_capabilities()
        plan = _compile(service, _graph())
        wire = service.plan_to_wire(plan)

        first = port.prepare_processing_candidate(wire)
        second = port.prepare_processing_candidate(wire)
        # One productive candidate at a time: the second prepare supersedes
        # the first with a bounded native teardown.
        assert first["plan_id"] == second["plan_id"] == plan.plan_id
        assert port.abort_processing_candidate() is True
    finally:
        port.close()
        supervisor.close()
