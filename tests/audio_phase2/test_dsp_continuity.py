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
                "PCM_CONTINUITY_VERIFIED",
                "GAP_DETECTED",
                "DISCONTINUITY_DETECTED",
                "POSITION_PRESERVED",
                "NOT_MEASURED",
            }, (label, diagnostics)
            pcm = diagnostics["pcm"]
            assert "position_preserved" in diagnostics
            assert pcm["buffers_observed"] >= 0
            if pcm["classification"] == "PCM_CONTINUITY_VERIFIED":
                # A PCM continuity claim REQUIRES observed PCM buffers.
                assert pcm["buffers_observed"] >= 2, (label, pcm)
                assert pcm["max_gap_ms"] is not None, (label, pcm)
            if pcm["classification"] == "GAP_DETECTED":
                assert pcm["max_gap_ms"] > pcm["gap_tolerance_ms"], (label, pcm)
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


def test_playing_swap_measures_a_real_pcm_timeline(tmp_path, monkeypatch) -> None:
    """With playback active, the sink-pad timeline produces a measured
    classification (and never claims PCM continuity without buffers)."""
    from michi.application.audio_processing_service import AudioProcessingService
    from michi.infrastructure.audio_processing.native_mapping import (
        NativeProcessingMapping,
    )
    from tests.audio_phase2.test_headroom_measurement import _write_sine
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    # Real-time lab sink + EXPLICIT continuity probe (the productive path
    # never pays the diagnostic observation window).
    monkeypatch.setenv("MICHI_GST_LAB_SINK_SYNC", "1")
    monkeypatch.setenv("MICHI_GST_CONTINUITY_PROBE", "1")
    fixture = tmp_path / "playing.wav"
    _write_sine(fixture, rate=44100, amplitude=0.4, seconds=4.0)
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
        port.play()
        time.sleep(0.3)
        plan, receipt = _install(service, port, supervisor, _preamp_graph(0.0, 1))
        diagnostics = receipt.diagnostics
        pcm = diagnostics["pcm"]
        assert diagnostics["continuity"] in {
            "PCM_CONTINUITY_VERIFIED",
            "GAP_DETECTED",
            "DISCONTINUITY_DETECTED",
            "POSITION_PRESERVED",
            "NOT_MEASURED",
        }, diagnostics
        assert diagnostics["duration_ms"] > 0.0
        assert diagnostics["rebuilds"] >= 1
        # The lab rebuild may leave the source at EOS (no PCM observed).
        # Whatever happens, the claim must be internally consistent.
        if pcm["classification"] == "PCM_CONTINUITY_VERIFIED":
            assert pcm["buffers_observed"] >= 2
            assert pcm["max_gap_ms"] is not None
            assert pcm["max_gap_ms"] <= pcm["gap_tolerance_ms"]
        if pcm["classification"] == "GAP_DETECTED":
            assert pcm["buffers_observed"] >= 2
            assert pcm["max_gap_ms"] > pcm["gap_tolerance_ms"]
        if pcm["classification"] == "POSITION_PRESERVED":
            assert pcm["buffers_observed"] < 2
            assert diagnostics["position_preserved"] is True
        if pcm["classification"] == "NOT_MEASURED":
            assert pcm["buffers_observed"] < 2
        assert service.effective_state.value == "effective"
        port.stop()
    finally:
        port.close()
        supervisor.close()


def test_continuity_analyzer_requires_both_sides_of_the_transition() -> None:
    from michi.infrastructure.audio_engines.gstreamer import GStreamerAudioPort

    def buffers(*pts_ms, discont=()):
        return [
            {
                "pts": int(ms * 1e6),
                "duration": 20_000_000,
                "discont": ms in discont,
                "mono_ns": int(ms * 1e6),
            }
            for ms in pts_ms
        ]

    continuous = GStreamerAudioPort._analyze_continuity(
        buffers(0, 20, 40, 60),
        position_preserved=True,
        swap_marker_ns=25_000_000,
        restore_marker_ns=35_000_000,
    )
    assert continuous["classification"] == "PCM_CONTINUITY_VERIFIED"
    assert continuous["buffers_before"] == 2
    assert continuous["buffers_after"] == 2
    assert continuous["max_gap_ms"] == 0.0

    gapped = GStreamerAudioPort._analyze_continuity(
        buffers(0, 20, 320, 340),
        position_preserved=True,
        swap_marker_ns=25_000_000,
        restore_marker_ns=35_000_000,
    )
    assert gapped["classification"] == "GAP_DETECTED"
    assert gapped["max_gap_ms"] >= 250.0

    discont = GStreamerAudioPort._analyze_continuity(
        buffers(0, 20, 40, discont=(40,)),
        position_preserved=True,
        swap_marker_ns=25_000_000,
        restore_marker_ns=35_000_000,
    )
    assert discont["classification"] == "DISCONTINUITY_DETECTED"

    only_before = GStreamerAudioPort._analyze_continuity(
        buffers(0, 20),
        position_preserved=True,
        swap_marker_ns=25_000_000,
        restore_marker_ns=35_000_000,
    )
    assert only_before["classification"] == "POSITION_PRESERVED"
    assert only_before["buffers_after"] == 0

    disabled = GStreamerAudioPort._analyze_continuity(
        buffers(0, 20, 40, 60),
        position_preserved=True,
        swap_marker_ns=25_000_000,
        restore_marker_ns=35_000_000,
        probe_enabled=False,
    )
    assert disabled["classification"] == "POSITION_PRESERVED"
    assert disabled["probe_enabled"] is False

    unavailable = GStreamerAudioPort._analyze_continuity([], position_preserved=False)
    assert unavailable["classification"] == "NOT_MEASURED"


def test_continuity_producer_emits_monotonic_observation_time() -> None:
    from michi.infrastructure.audio_engines.gstreamer import GStreamerAudioPort

    entry = GStreamerAudioPort._continuity_entry(
        pts=123, duration=20_000_000, discont=False, observed_ns=999
    )
    assert entry == {
        "pts": 123,
        "duration": 20_000_000,
        "discont": False,
        "mono_ns": 999,
    }


def test_truncated_timeline_can_never_claim_pcm_continuity() -> None:
    from michi.infrastructure.audio_engines.gstreamer import GStreamerAudioPort

    def buffers(*pts_ms):
        return [
            {
                "pts": int(ms * 1e6),
                "duration": 20_000_000,
                "discont": False,
                "mono_ns": int(ms * 1e6),
            }
            for ms in pts_ms
        ]

    result = GStreamerAudioPort._analyze_continuity(
        buffers(0, 20, 40, 60),
        position_preserved=True,
        swap_marker_ns=25_000_000,
        restore_marker_ns=35_000_000,
        timeline_truncated=True,
    )
    assert result["classification"] != "PCM_CONTINUITY_VERIFIED"
    assert result["timeline_truncated"] is True
    assert result["timestamps_observed"] == 4


def test_timestamps_observed_counts_only_monotonic_entries() -> None:
    from michi.infrastructure.audio_engines.gstreamer import GStreamerAudioPort

    timeline = [
        {"pts": 0, "duration": 20_000_000, "discont": False, "mono_ns": 1},
        {"pts": 20_000_000, "duration": 20_000_000, "discont": False},
        {"pts": 40_000_000, "duration": 20_000_000, "discont": False, "mono_ns": 3},
    ]
    result = GStreamerAudioPort._analyze_continuity(timeline, position_preserved=True)
    assert result["timestamps_observed"] == 2
