"""AP2-F06 — authorized DSP combinations keep a verifiable order/readback.

No new authority: the same compiler/mapping/service/host chain is exercised
with combined graphs (preamp + GEQ + PEQ + resample).
"""

from __future__ import annotations

import importlib.util
import time

import pytest

from michi.application.effective_processing_graph import (
    EffectiveProcessingGraphResolver,
)
from michi.application.processing_graph_compiler import (
    ProcessingBackendCapabilities,
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
    ResampleNode,
    ResampleQuality,
)
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
from michi.infrastructure.audio_processing.native_mapping import (
    NativeProcessingMapping,
)

_HAS_GI = importlib.util.find_spec("gi") is not None


def _signal(rate: int = 44100):
    return PcmSignalFormat(
        rate_hz=rate,
        transport_format="S16LE",
        significant_bits=16,
        layout=ChannelLayout(positions=("FL", "FR")),
    )


def _combined_graph(*, revision: int = 1, target_rate: int = 48000):
    gains = [0.0] * 10
    gains[4] = 3.0
    return ProcessingGraph(
        graph_id="graph:combo",
        revision=revision,
        nodes=(
            PreampNode(node_id="pre", gain_db=-3.0),
            GraphicEqNode(
                "geq", layout_id=GraphicEqLayout.MICHI_10_V1, gains_db=tuple(gains)
            ),
            ParametricEqNode(
                "peq",
                bands=(PeqBand("b1", BiquadType.PEAK, 1000.0, 1.4, 4.0, True),),
            ),
            ResampleNode(
                node_id="rs",
                target_rate_hz=target_rate,
                quality=ResampleQuality.HIGH,
            ),
        ),
    )


def _compile(graph, *, rate: int = 44100):
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=_signal(rate), assets=()
    )
    return ProcessingGraphCompiler().compile(
        effective,
        backend=ProcessingBackendCapabilities(
            backend_id="test", strategies=frozenset(ProcessingStrategy)
        ),
        assets=(),
    )


def test_combined_graph_preserves_order_and_native_readback_shapes() -> None:
    plan = _compile(_combined_graph())
    assert [node.strategy for node in plan.nodes] == [
        ProcessingStrategy.GAIN,
        ProcessingStrategy.GRAPHIC_EQ_NBANDS,
        ProcessingStrategy.BIQUAD_CASCADE,
        ProcessingStrategy.RESAMPLE,
    ]
    wire = NativeProcessingMapping().plan_to_wire(plan)
    assert [node["node_id"] for node in wire["nodes"]] == ["pre", "geq", "peq", "rs"]
    readbacks = [
        NativeProcessingMapping.expected_native_properties(node, rate_hz=44100)
        for node in plan.nodes
    ]
    assert readbacks[0] == {"gain_db": -3.0}
    assert readbacks[1]["layout_id"] == "michi_10_v1"
    assert len(readbacks[1]["biquad"]) == 10
    assert len(readbacks[2]["biquad"]) == 1
    assert readbacks[3] == {"target_rate_hz": 48000, "quality": 8}
    assert plan.sample_contract.output_rate_hz == 48000
    assert plan.changes_rate is True
    assert wire["nodes"][3]["properties"]["native_quality"] == 8


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
def test_combined_graph_installs_and_reads_back_on_the_real_host(
    tmp_path, monkeypatch
) -> None:
    from michi.application.audio_processing_service import AudioProcessingService
    from tests.audio_phase2.test_headroom_measurement import _write_sine
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "combo.wav"
    _write_sine(fixture, rate=44100, amplitude=0.4)
    supervisor, port = _real_port()
    try:
        port.activate()
        port.set_volume(0)
        port.load(fixture)
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            port.dispatch_pending()
            try:
                duration = port.query_duration()
            except Exception:
                duration = None
            if isinstance(duration, int) and duration > 0:
                break
            time.sleep(0.02)
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
            transport=port,
        )
        service.refresh_capabilities()
        assert {
            ProcessingStrategy.GAIN,
            ProcessingStrategy.GRAPHIC_EQ_NBANDS,
            ProcessingStrategy.BIQUAD_CASCADE,
            ProcessingStrategy.RESAMPLE,
        } <= service.capabilities.strategies

        plan = _compile(_combined_graph())
        candidate = service.begin_candidate(
            plan, host_generation=supervisor.host_generation, transport=port
        )
        receipt = service.commit_candidate(candidate, transport=port)
        service.publish_effective(receipt)
        truth = service.processing_truth()
        assert truth["effective_state"] == "effective"
        assert truth["readback_proven"] is True
        assert truth["latency"]["expected_samples"] == plan.total_latency_samples

        port.seek(0)
        metrics = port.capture_processing_output(1.0, probe_hz=[1000.0])
        assert metrics["rate_hz"] == 48000
        assert metrics["frames"] > 0
        assert metrics["tones"][0]["magnitude"] > 0.0
    finally:
        port.close()
        supervisor.close()
