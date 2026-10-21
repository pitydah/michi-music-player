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

    def __init__(
        self,
        kernels: dict[str, tuple[float, ...]],
        rate_hz: int = 44100,
        *,
        sha_override: str | None = None,
        omit_sha: bool = False,
        fail_load: bool = False,
    ):
        self.kernels = dict(kernels)
        self.rate_hz = int(rate_hz)
        self.sha_override = sha_override
        self.omit_sha = omit_sha
        self.fail_load = fail_load

    def load_float32_mono(self, ir_id: str) -> tuple[float, ...]:
        if self.fail_load:
            raise RuntimeError("IR provider failure")
        return self.kernels[ir_id]

    def metadata(self, ir_id: str) -> dict:
        result: dict = {"rate_hz": self.rate_hz, "channels": 1}
        if not self.omit_sha:
            coefficients = self.kernels[ir_id]
            raw = struct.pack(f"<{len(coefficients)}f", *coefficients)
            result["sha256"] = self.sha_override or hashlib.sha256(raw).hexdigest()
        return result


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


def _write_impulse(
    path, *, rate: int = 44100, amplitude: float = 0.5, offset_s: float = 0.25
):
    frames = rate * 2
    data = bytearray(frames * 2 * 2)
    sample = int(round(amplitude * 32767))
    # A DENSE impulse train spans the whole fixture so any capture window
    # contains several impulses regardless of the seek/preroll position.
    step = int(0.02 * rate)
    start = int(offset_s * rate)
    for event in range(start, frames - step, step):
        offset = event * 4
        struct.pack_into("<h", data, offset, sample)
        struct.pack_into("<h", data, offset + 2, sample)
    with open(path, "wb") as handle:
        import wave

        with wave.open(handle, "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(bytes(data))


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
def test_fir_impulse_goldens_match_the_kernel_exactly(tmp_path, monkeypatch) -> None:
    """An impulse convolved with a kernel yields the kernel: absolute peaks."""
    from michi.application.audio_processing_service import AudioProcessingService
    from michi.infrastructure.audio_processing.native_mapping import (
        NativeProcessingMapping,
    )
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "impulse.wav"
    _write_impulse(fixture, amplitude=0.5)
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
        cases = [
            ((1.0,), 0.5),
            ((0.5, 0.5), 0.25),
            ((0.25, 0.5, 0.25), 0.25),
            ((0.0, 0.0, 0.75), 0.375),
            ((-1.0,), 0.5),
        ]
        for index, (coefficients, expected_peak) in enumerate(cases):
            asset = _asset(coefficients)
            store = _IRStore({asset.asset_id: coefficients})
            _install(
                service,
                port,
                supervisor,
                _graph(asset, revision=index + 1),
                asset,
                store,
            )
            assert service.processing_truth()["readback_proven"] is True
            port.seek(0)
            metrics = port.capture_processing_output(0.5)
            assert metrics["sample_peak"] == pytest.approx(expected_peak, abs=1e-3), (
                coefficients,
                metrics["sample_peak"],
            )

        # Explicit gain scales the INSTALLED kernel (asset hash unchanged).
        gain_coefficients = (1.0,)
        gain_asset = _asset(gain_coefficients)
        gain_store = _IRStore({gain_asset.asset_id: gain_coefficients})
        _install(
            service,
            port,
            supervisor,
            _graph(gain_asset, revision=99, gain_db=6.0),
            gain_asset,
            gain_store,
        )
        assert service.processing_truth()["readback_proven"] is True
        port.seek(0)
        gained = port.capture_processing_output(0.5)
        assert gained["sample_peak"] == pytest.approx(
            0.5 * 10 ** (6.0 / 20.0), abs=1e-3
        )
    finally:
        port.close()
        supervisor.close()


def _managed_fir_prepare(tmp_path, store, asset, monkeypatch):
    from michi.domain.audio_processing import ProcessingProfile
    from tests.audio_phase2.test_managed_productive_flow import (
        _build_graph,
        _close,
        _prepare,
        _select_managed,
    )

    if not importlib.util.find_spec("gi"):
        pytest.skip("PyGObject unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    graph, coordinator = _build_graph(tmp_path, ir_provider=store)
    _select_managed(coordinator)
    graph.set_processing_profile(
        ProcessingProfile(
            profile_id="dsp:fir-identity",
            display_name="FIR identity",
            graph=_graph(asset),
        )
    )
    tokens, failures = _prepare(graph)
    _close(graph)
    return tokens, failures


def test_provider_sha_mismatch_is_rejected_before_native(tmp_path, monkeypatch) -> None:
    coefficients = (0.5, 0.5)
    asset = _asset(coefficients)
    bad_sha = _IRStore({asset.asset_id: coefficients}, sha_override="0" * 64)
    tokens, failures = _managed_fir_prepare(tmp_path, bad_sha, asset, monkeypatch)
    assert tokens == []
    assert failures and failures[0].code == "DSP_ASSET_HASH_MISMATCH", failures


def test_provider_without_sha_is_rejected(tmp_path, monkeypatch) -> None:
    coefficients = (0.5, 0.5)
    asset = _asset(coefficients)
    no_sha = _IRStore({asset.asset_id: coefficients}, omit_sha=True)
    tokens, failures = _managed_fir_prepare(tmp_path, no_sha, asset, monkeypatch)
    assert tokens == []
    assert failures and failures[0].code == "DSP_FIR_ASSET_HASH_UNAVAILABLE", failures


def test_provider_coefficients_that_do_not_match_the_declared_sha(
    tmp_path, monkeypatch
) -> None:
    declared = (0.5, 0.5)
    asset = _asset(declared)
    changed = _IRStore({asset.asset_id: (0.25, 0.75)})
    # Metadata declares the sha of the DECLARED kernel, but load returns a
    # different kernel: the computed coefficients hash must fail.
    changed.sha_override = asset.sha256
    tokens, failures = _managed_fir_prepare(tmp_path, changed, asset, monkeypatch)
    assert tokens == []
    assert failures and failures[0].code == "FIR_KERNEL_HASH_MISMATCH", failures


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
def test_fir_gain_can_exceed_full_scale_and_is_measured_per_channel(
    tmp_path, monkeypatch
) -> None:
    """Headroom is measured for FIR boost, not assumed from PEQ only."""
    from michi.application.audio_processing_service import AudioProcessingService
    from michi.infrastructure.audio_processing.native_mapping import (
        NativeProcessingMapping,
    )
    from tests.audio_phase2.test_headroom_measurement import _write_sine
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "fir-headroom.wav"
    _write_sine(fixture, rate=44100, amplitude=0.9)
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

        flat_coefficients = (1.0,)
        flat_asset = _asset(flat_coefficients)
        _install(
            service,
            port,
            supervisor,
            _graph(flat_asset),
            flat_asset,
            _IRStore({flat_asset.asset_id: flat_coefficients}),
        )
        port.seek(0)
        flat = port.capture_processing_output(1.0)
        assert 0.85 <= flat["sample_peak"] <= 1.0, flat

        gain_coefficients = (2.0,)
        gain_asset = _asset(gain_coefficients)
        _install(
            service,
            port,
            supervisor,
            _graph(gain_asset, revision=2),
            gain_asset,
            _IRStore({gain_asset.asset_id: gain_coefficients}),
        )
        assert service.processing_truth()["readback_proven"] is True
        port.seek(0)
        boosted = port.capture_processing_output(1.0)
        # 0.9 * 2 = 1.8 in the float domain: measured, not assumed.
        assert boosted["sample_peak"] > 1.5, boosted
        assert boosted["exceeds_full_scale"] is True
        assert boosted["samples_over_full_scale"] > 0
        assert len(boosted["channels_metrics"]) == 2
        for channel in boosted["channels_metrics"]:
            assert channel["sample_peak"] > 1.5
    finally:
        port.close()
        supervisor.close()
