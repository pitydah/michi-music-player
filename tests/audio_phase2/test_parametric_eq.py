"""AP2-F06 — productive Parametric EQ (BIQUAD_CASCADE).

Semantic + native coefficients are verified against an INDEPENDENT RBJ
reference; the productive spectral proof measures the real GStreamer graph.
"""

from __future__ import annotations

import importlib.util
import math

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
    ParametricEqNode,
    PeqBand,
    ProcessingGraph,
    ProcessingStrategy,
)
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
from michi.infrastructure.audio_processing.native_mapping import (
    NativeProcessingMapping,
)

_HAS_GI = importlib.util.find_spec("gi") is not None


def _signal(rate=44100, channels=2):
    return PcmSignalFormat(
        rate_hz=rate,
        transport_format="S16LE",
        significant_bits=16,
        layout=ChannelLayout(
            positions=tuple(f"CH{index}" for index in range(channels))
        ),
    )


def _bands():
    return (
        PeqBand("b-low", BiquadType.PEAK, 125.0, 1.4, -6.0, True),
        PeqBand("b-mid", BiquadType.PEAK, 1000.0, 1.4, 6.0, True),
        PeqBand("b-off", BiquadType.PEAK, 4000.0, 1.4, 9.0, False),
    )


def _graph(bands=None, revision=1):
    return ProcessingGraph(
        graph_id="graph:peq",
        revision=revision,
        nodes=(ParametricEqNode(node_id="peq", bands=tuple(bands or _bands())),),
    )


def _compile(graph=None, signal=None, **kwargs):
    effective = EffectiveProcessingGraphResolver().resolve(
        graph or _graph(), input_signal=signal or _signal(), assets=()
    )
    return ProcessingGraphCompiler().compile(
        effective,
        backend=ProcessingBackendCapabilities(
            backend_id="test", strategies=frozenset(ProcessingStrategy)
        ),
        assets=(),
        **kwargs,
    )


def _rbj_peak(rate_hz, frequency_hz, q, gain_db):
    amplitude = 10.0 ** (gain_db / 40.0)
    omega = 2.0 * math.pi * frequency_hz / rate_hz
    alpha = math.sin(omega) / (2.0 * q)
    cos_w = math.cos(omega)
    a0 = 1.0 + alpha / amplitude
    return (
        [
            (1.0 + alpha * amplitude) / a0,
            (-2.0 * cos_w) / a0,
            (1.0 - alpha * amplitude) / a0,
        ],
        [1.0, (-2.0 * cos_w) / a0, (1.0 - alpha / amplitude) / a0],
    )


def test_peq_compiles_to_biquad_cascade_and_preserves_band_identity() -> None:
    plan = _compile()
    node = plan.nodes[0]
    assert node.strategy is ProcessingStrategy.BIQUAD_CASCADE
    properties = dict(node.properties)
    assert properties["rate_hz"] == 44100
    assert [band[0] for band in properties["bands"]] == ["b-low", "b-mid", "b-off"]
    assert plan.changes_sample_values is True


def test_peq_native_coefficients_match_an_independent_rbj_reference() -> None:
    plan = _compile()
    node = plan.nodes[0]
    expected = NativeProcessingMapping.expected_native_properties(node, rate_hz=44100)
    enabled = [band for band in _bands() if band.enabled]
    assert len(expected["biquad"]) == len(enabled)
    for observed, band in zip(expected["biquad"], enabled, strict=True):
        b_reference, a_reference = _rbj_peak(
            44100.0, band.frequency_hz, band.q, band.gain_db
        )
        assert observed["b"] == pytest.approx(b_reference, rel=0, abs=1e-12)
        assert observed["a"] == pytest.approx(a_reference, rel=0, abs=1e-12)

    factories = NativeProcessingMapping.expected_native_factories(node)
    assert factories == ("audioiirfilter",) * len(enabled)

    wire = NativeProcessingMapping().plan_to_wire(plan)
    cascade = wire["nodes"][0]["properties"]["biquad_cascade"]
    assert len(cascade) == len(enabled)
    assert cascade[0]["b"] == pytest.approx(
        expected["biquad"][0]["b"], rel=0, abs=1e-12
    )


def test_disabled_peq_bands_do_not_materialize_or_mutate() -> None:
    bands = (PeqBand("off", BiquadType.PEAK, 1000.0, 1.4, 6.0, False),)
    plan = _compile(_graph(bands))
    assert plan.changes_sample_values is False
    node = plan.nodes[0]
    assert NativeProcessingMapping.expected_native_factories(node) == ()
    assert (
        NativeProcessingMapping.expected_native_properties(node, rate_hz=44100)[
            "biquad"
        ]
        == []
    )


def test_gainless_and_extreme_but_valid_bands_compile() -> None:
    bands = (
        PeqBand("lp", BiquadType.LOW_PASS, 80.0, 0.707, 0.0, True),
        PeqBand("notch", BiquadType.NOTCH, 1000.0, 30.0, 0.0, True),
        PeqBand("shelf", BiquadType.HIGH_SHELF, 8000.0, 0.707, -3.0, True),
    )
    plan = _compile(_graph(bands))
    assert len(dict(plan.nodes[0].properties)["bands"]) == 3


def test_peq_band_at_nyquist_is_never_materialized() -> None:
    bands = (PeqBand("bad", BiquadType.PEAK, 22050.0, 1.0, 3.0, True),)
    plan = _compile(_graph(bands))
    # The resolver marks at/above-Nyquist bands inactive; when every band
    # is inactive the node carries NO native materialization (never a silent
    # filter, never a hidden Nyquist violation).
    assert plan.changes_sample_values is False
    assert plan.nodes == ()
    assert plan.adaptation_reasons == ("inactive_above_nyquist",)


# ── productive spectral proof (real GStreamer, lab sink) ───────────────
@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
@pytest.mark.parametrize("rate", [44100, 48000, 96000])
def test_peq_productively_shapes_real_media(tmp_path, monkeypatch, rate) -> None:
    import time

    from michi.application.audio_processing_service import AudioProcessingService
    from michi.infrastructure.audio_processing.native_mapping import (
        NativeProcessingMapping,
    )
    from tests.audio_phase2.test_processing_graphic_eq import (
        _capture,
        _db,
        _real_port,
        _write_multitone,
    )

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / f"peq-multitone-{rate}.wav"
    _write_multitone(fixture, rate=rate)

    supervisor, port = _real_port()
    try:
        port.activate()
        port.set_volume(0)
        port.load(fixture)
        deadline = time.monotonic() + 30.0
        while not port.backend_state() and time.monotonic() < deadline:
            port.dispatch_pending()
            time.sleep(0.02)
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
            transport=port,
        )
        service.refresh_capabilities()
        assert ProcessingStrategy.BIQUAD_CASCADE in service.capabilities.strategies

        flat_bands = tuple(
            PeqBand(f"f{index}", BiquadType.PEAK, center, 1.4, 0.0, True)
            for index, center in enumerate((125.0, 1000.0))
        )
        _install(service, port, supervisor, _graph(flat_bands, revision=1), rate=rate)
        flat = _capture(port)

        shaped_bands = (
            PeqBand("low", BiquadType.PEAK, 125.0, 1.4, -6.0, True),
            PeqBand("mid", BiquadType.PEAK, 1000.0, 1.4, 6.0, True),
        )
        _install(service, port, supervisor, _graph(shaped_bands, revision=2), rate=rate)
        shaped = _capture(port)

        low = _db(shaped[125] / flat[125])
        mid = _db(shaped[1000] / flat[1000])
        # +-2 dB: Q=1.4 (~1 octave) keeps the octave-separated neighbour's
        # contribution small; the Goertzel window adds < 0.5 dB leakage.
        assert low == pytest.approx(-6.0, abs=2.0), (rate, low, shaped, flat)
        assert mid == pytest.approx(6.0, abs=2.0), (rate, mid, shaped, flat)
        assert low < 0.0 < mid

        assert port.bypass_processing()["bypassed"] is True
        bypassed = _capture(port)
        for hz in flat:
            assert abs(_db(bypassed[hz] / flat[hz])) < 4.0, hz
    finally:
        port.close()
        supervisor.close()


def _install(service, port, supervisor, graph, revision=1, rate=44100):
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=_signal(rate), assets=()
    )
    plan = ProcessingGraphCompiler().compile(
        effective, backend=service.capabilities, assets=()
    )
    candidate = service.begin_candidate(
        plan, host_generation=supervisor.host_generation, transport=port
    )
    service.publish_effective(service.commit_candidate(candidate, transport=port))
    return plan
