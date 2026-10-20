"""AP2-F06 — productive FIR/convolution vertical.

Kernel authority: SHA-256 over canonical float32-LE mono coefficients, with
bounds, finiteness and rate/channels checks BEFORE native install. Native
`audiofirfilter` readback must reproduce the installed kernel fingerprint;
EFFECTIVE is published only through that readback.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import struct
import time

import pytest

from michi.application.effective_processing_graph import (
    EffectiveProcessingGraphResolver,
)
from michi.application.processing_graph_compiler import (
    ProcessingBackendCapabilities,
    ProcessingCompilationError,
    ProcessingGraphCompiler,
)
from michi.domain.audio_processing import (
    ConvolutionNode,
    ImpulseResponseMetadata,
    PreampNode,
    ProcessingGraph,
    ProcessingStrategy,
)
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
from michi.infrastructure.audio_processing.native_mapping import (
    NativeProcessingMapping,
)

_HAS_GI = importlib.util.find_spec("gi") is not None


class _IRStore:
    """Deterministic test provider (NOT the durable F13 store)."""

    def __init__(self, kernels: dict[str, tuple[float, ...]], rate_hz: int = 44100):
        self.kernels = dict(kernels)
        self.rate_hz = int(rate_hz)

    def load_float32_mono(self, ir_id: str) -> tuple[float, ...]:
        return self.kernels[ir_id]

    def metadata(self, ir_id: str) -> dict:
        return {"rate_hz": self.rate_hz, "channels": 1}


def _asset(coefficients, rate_hz: int = 44100):
    raw = struct.pack(f"<{len(coefficients)}f", *coefficients)
    sha = hashlib.sha256(raw).hexdigest()
    return ImpulseResponseMetadata(
        asset_id=f"ir:sha256:{sha}", sha256=sha, rate_hz=rate_hz, channels=1
    )


def _signal(rate: int = 44100):
    return PcmSignalFormat(
        rate_hz=rate,
        transport_format="S16LE",
        significant_bits=16,
        layout=ChannelLayout(positions=("FL", "FR")),
    )


def _graph(asset, *, revision: int = 1, gain_db: float = 0.0):
    return ProcessingGraph(
        graph_id="graph:fir",
        revision=revision,
        nodes=(
            PreampNode(node_id="pre", gain_db=0.0),
            ConvolutionNode(
                node_id="fir",
                asset_id=asset.asset_id,
                asset_sha256=asset.sha256,
                gain_db=gain_db,
            ),
        ),
    )


def _compile(graph, asset, store, *, rate: int = 44100):
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=_signal(rate), assets=(asset,)
    )
    return ProcessingGraphCompiler().compile(
        effective,
        backend=ProcessingBackendCapabilities(
            backend_id="test", strategies=frozenset(ProcessingStrategy)
        ),
        assets=(asset,),
        ir_provider=store,
    )


def test_fir_compiles_with_verified_kernel_and_fingerprint() -> None:
    coefficients = (0.25, 0.5, 0.25)
    asset = _asset(coefficients)
    store = _IRStore({asset.asset_id: coefficients})
    plan = _compile(_graph(asset), asset, store)
    node = plan.nodes[1]
    assert node.strategy is ProcessingStrategy.CONVOLUTION_FIR
    properties = dict(node.properties)
    assert properties["taps"] == 3
    assert properties["rate_hz"] == 44100
    assert properties["channels"] == 1
    assert tuple(properties["kernel"]) == pytest.approx(coefficients)
    expected = NativeProcessingMapping.expected_native_properties(node, rate_hz=44100)
    assert expected == {
        "taps": 3,
        "fingerprint": properties["fingerprint"],
    }
    assert NativeProcessingMapping.expected_native_factories(node) == (
        "audiofirfilter",
    )
    wire = NativeProcessingMapping().plan_to_wire(plan)
    assert wire["nodes"][1]["properties"]["kernel"] == list(coefficients)


def test_fir_gain_scales_the_installed_kernel_but_not_the_asset_hash() -> None:
    coefficients = (1.0,)
    asset = _asset(coefficients)
    store = _IRStore({asset.asset_id: coefficients})
    plan = _compile(_graph(asset, gain_db=6.0), asset, store)
    properties = dict(plan.nodes[1].properties)
    assert properties["kernel"][0] == pytest.approx(10 ** (6 / 20), rel=1e-6)
    assert properties["asset_sha256"] == asset.sha256
    assert properties["fingerprint"] != asset.sha256


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        ("no_store", "DSP_FIR_STORE_UNAVAILABLE"),
        ("rate", "DSP_FIR_RATE_MISMATCH"),
    ],
)
def test_fir_refuses_without_store_or_matching_rate(mutate, code) -> None:
    coefficients = (0.5, 0.5)
    asset = _asset(coefficients)
    store = _IRStore({asset.asset_id: coefficients})
    if mutate == "no_store":
        store = None
        expected = code
    else:
        # The effective resolver rejects an IR whose rate differs from the
        # current signal before compilation (defense in depth: the compiler
        # also refuses DSP_FIR_RATE_MISMATCH if reached).
        asset = _asset(coefficients, rate_hz=48000)
        expected = "DSP_ASSET_UNSUPPORTED_SIGNAL"
    with pytest.raises(ProcessingCompilationError) as info:
        _compile(_graph(asset), asset, store)
    assert info.value.code == expected


def test_fir_rejects_metadata_hash_mismatch_and_bad_kernels() -> None:
    coefficients = (0.5, 0.5)
    asset = _asset(coefficients)
    forged = ImpulseResponseMetadata(
        asset_id=asset.asset_id,
        sha256="0" * 64,
        rate_hz=44100,
        channels=1,
    )
    with pytest.raises(ProcessingCompilationError) as info:
        _compile(_graph(asset), forged, _IRStore({asset.asset_id: coefficients}))
    assert info.value.code == "DSP_ASSET_HASH_MISMATCH"

    nan_coefficients = (float("nan"), 0.5)
    nan_asset = _asset(nan_coefficients)
    with pytest.raises(ProcessingCompilationError) as info:
        _compile(
            _graph(nan_asset),
            nan_asset,
            _IRStore({nan_asset.asset_id: nan_coefficients}),
        )
    assert info.value.code == "FIR_KERNEL_NON_FINITE"

    big = tuple(0.0 for _ in range(9000))
    big_asset = _asset(big)
    with pytest.raises(ProcessingCompilationError) as info:
        _compile(_graph(big_asset), big_asset, _IRStore({big_asset.asset_id: big}))
    assert info.value.code == "FIR_KERNEL_TOO_LARGE"


def _install(service, port, supervisor, graph, asset, store, *, rate=44100):
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=_signal(rate), assets=(asset,)
    )
    plan = ProcessingGraphCompiler().compile(
        effective,
        backend=service.capabilities,
        assets=(asset,),
        ir_provider=store,
    )
    candidate = service.begin_candidate(
        plan, host_generation=supervisor.host_generation, transport=port
    )
    receipt = service.commit_candidate(candidate, transport=port)
    service.publish_effective(receipt)
    return plan


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
def test_fir_runs_natively_with_verified_readback(tmp_path, monkeypatch) -> None:
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
    fixture = tmp_path / "fir-multitone.wav"
    _write_multitone(fixture)
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
        assert ProcessingStrategy.CONVOLUTION_FIR in service.capabilities.strategies

        flat_asset = _asset((1.0,))
        flat_store = _IRStore({flat_asset.asset_id: (1.0,)})
        _install(service, port, supervisor, _graph(flat_asset), flat_asset, flat_store)
        assert service.processing_truth()["readback_proven"] is True
        flat = _capture(port)

        coefficients = (0.25, 0.5, 0.25)
        asset = _asset(coefficients)
        store = _IRStore({asset.asset_id: coefficients})
        _install(service, port, supervisor, _graph(asset), asset, store)
        assert service.processing_truth()["readback_proven"] is True
        shaped = _capture(port)

        # Independent analytic reference for the 3-tap moving average:
        # H(f) = 0.5 + 0.5*cos(2*pi*f/fs)
        rate = 44100.0
        for hz, tolerance in ((1000.0, 1.0), (8000.0, 1.5)):
            expected_db = 20 * math.log10(0.5 + 0.5 * math.cos(2 * math.pi * hz / rate))
            measured = _db(shaped[hz] / flat[hz])
            assert measured == pytest.approx(expected_db, abs=tolerance), (
                hz,
                measured,
                expected_db,
            )
    finally:
        port.close()
        supervisor.close()


def test_managed_fir_fails_closed_without_a_store(tmp_path, monkeypatch) -> None:
    from michi.domain.audio_processing import ProcessingProfile
    from tests.audio_phase2.test_managed_productive_flow import (
        FIXTURE,
        _build_graph,
        _close,
        _prepare,
        _select_managed,
    )

    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    coefficients = (0.5, 0.5)
    asset = _asset(coefficients)
    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        graph.set_processing_profile(
            ProcessingProfile(
                profile_id="dsp:fir-nostore",
                display_name="FIR",
                graph=_graph(asset),
            )
        )
        tokens, failures = _prepare(graph)
        assert tokens == []
        assert failures and failures[0].code == "DSP_FIR_STORE_UNAVAILABLE", failures
        assert graph.output_session.state.value != "running"
    finally:
        _close(graph)


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
def test_managed_fir_processes_media_and_reads_back(tmp_path, monkeypatch) -> None:
    from michi.domain.audio_processing import ProcessingProfile
    from tests.audio_phase2.test_managed_productive_flow import (
        _build_graph,
        _close,
        _select_managed,
    )
    from tests.audio_phase2.test_processing_graphic_eq import (
        _capture,
        _db,
        _write_multitone,
    )

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "managed-fir.wav"
    _write_multitone(fixture)
    coefficients = (0.25, 0.5, 0.25)
    asset = _asset(coefficients)
    store = _IRStore({asset.asset_id: coefficients})

    from pathlib import Path

    def capture_for(profile, directory) -> dict:
        Path(directory).mkdir(parents=True, exist_ok=True)
        """ONE session per capture: the lab capture drives PLAYING, so it is
        always the LAST action of its session (never followed by a prepare)."""
        graph, coordinator = _build_graph(directory, ir_provider=store)
        try:
            _select_managed(coordinator)
            graph.set_processing_profile(profile)
            tokens: list[str] = []
            failures: list[Exception] = []
            graph.output_session.prepare_for_media_async(
                fixture, tokens.append, failures.append
            )
            assert failures == [], failures
            graph.output_session.commit_media(tokens[0], fixture)
            assert graph.audio_processing.effective_state.value == "effective"
            assert graph.audio_processing.processing_truth()["readback_proven"] is True
            port = graph.gstreamer_engine_provider.current_port
            identity = port.query_managed_identity()
            assert identity["managed"] is True and identity["loaded"] is True
            return _capture(port)
        finally:
            _close(graph)

    flat = capture_for(
        ProcessingProfile(
            profile_id="dsp:managed-flat",
            display_name="Flat",
            graph=ProcessingGraph(
                graph_id="graph:managed-fir",
                revision=1,
                nodes=(PreampNode(node_id="pre", gain_db=0.0),),
            ),
        ),
        tmp_path / "flat-session",
    )
    shaped = capture_for(
        ProcessingProfile(
            profile_id="dsp:managed-fir",
            display_name="FIR",
            graph=_graph(asset, revision=2),
        ),
        tmp_path / "fir-session",
    )
    rate = 44100.0
    for hz, tolerance in ((1000.0, 1.0), (8000.0, 1.5)):
        expected_db = 20 * math.log10(0.5 + 0.5 * math.cos(2 * math.pi * hz / rate))
        measured = _db(shaped[hz] / flat[hz])
        assert measured == pytest.approx(expected_db, abs=tolerance), (
            hz,
            measured,
            expected_db,
        )
