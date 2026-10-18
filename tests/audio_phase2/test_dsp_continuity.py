"""AP2-F06 — transition diagnostics for productive DSP swaps.

The child reports duration, rebuild count and observed position continuation
for every install. This is instrumentation, not a "seamless" claim.
"""

from __future__ import annotations

import importlib.util
import time

import pytest

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="PyGObject/GStreamer unavailable on this host"
)


def _signal(rate: int = 44100):
    from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat

    return PcmSignalFormat(
        rate_hz=rate,
        transport_format="S16LE",
        significant_bits=16,
        layout=ChannelLayout(positions=("FL", "FR")),
    )


def _preamp_graph(gain_db: float, revision: int):
    from michi.domain.audio_processing import PreampNode, ProcessingGraph

    return ProcessingGraph(
        graph_id="graph:continuity",
        revision=revision,
        nodes=(PreampNode(node_id="pre", gain_db=gain_db),),
    )


def _peq_graph(gain_db: float, revision: int):
    from michi.domain.audio_processing import (
        BiquadType,
        ParametricEqNode,
        PeqBand,
        ProcessingGraph,
    )

    return ProcessingGraph(
        graph_id="graph:continuity",
        revision=revision,
        nodes=(
            ParametricEqNode(
                node_id="peq",
                bands=(PeqBand("b", BiquadType.PEAK, 1000.0, 1.4, gain_db, True),),
            ),
        ),
    )


def _geq_graph(gain_db: float, revision: int):
    from michi.domain.audio_processing import (
        GraphicEqLayout,
        GraphicEqNode,
        ProcessingGraph,
    )

    gains = [0.0] * 10
    gains[4] = gain_db
    return ProcessingGraph(
        graph_id="graph:continuity",
        revision=revision,
        nodes=(
            GraphicEqNode(
                "geq", layout_id=GraphicEqLayout.MICHI_10_V1, gains_db=tuple(gains)
            ),
        ),
    )


def _install(service, port, supervisor, graph):
    from michi.application.effective_processing_graph import (
        EffectiveProcessingGraphResolver,
    )
    from michi.application.processing_graph_compiler import (
        ProcessingGraphCompiler,
    )

    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=_signal(), assets=()
    )
    plan = ProcessingGraphCompiler().compile(
        effective, backend=service.capabilities, assets=()
    )
    candidate = service.begin_candidate(
        plan, host_generation=supervisor.host_generation, transport=port
    )
    receipt = service.commit_candidate(candidate, transport=port)
    service.publish_effective(receipt)
    return plan, receipt


def test_each_dsp_swap_reports_transition_diagnostics(tmp_path, monkeypatch) -> None:
    from michi.application.audio_processing_service import AudioProcessingService
    from michi.infrastructure.audio_processing.native_mapping import (
        NativeProcessingMapping,
    )
    from tests.audio_phase2.test_headroom_measurement import _write_sine
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "continuity.wav"
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

        transitions = (
            ("flat->preamp", _preamp_graph(0.0, 1)),
            ("preamp->peq", _peq_graph(6.0, 2)),
            ("peq->geq", _geq_graph(-4.0, 3)),
            ("geq->preamp", _preamp_graph(-6.0, 4)),
        )
        for label, graph in transitions:
            plan, receipt = _install(service, port, supervisor, graph)
            diagnostics = receipt.diagnostics
            assert diagnostics, label
            assert diagnostics["duration_ms"] > 0.0, (label, diagnostics)
            assert diagnostics["rebuilds"] >= 1, (label, diagnostics)
            assert diagnostics["continuity"] in {
                "CONTINUITY_VERIFIED",
                "POSITION_RESET",
                "NOT_MEASURED",
            }, (label, diagnostics)
            assert "silent_gap_ms" in diagnostics
            assert service.effective_state.value == "effective"
            assert plan.plan_id.startswith("dsp:")

        # The last installed graph still produces signal after four swaps.
        port.seek(0)
        metrics = port.capture_processing_output(0.8, probe_hz=[1000.0])
        assert metrics["frames"] > 0
        assert metrics["tones"][0]["magnitude"] > 0.05
    finally:
        port.close()
        supervisor.close()
