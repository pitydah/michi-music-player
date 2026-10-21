"""AP2-F06 — explicit terminal dither on a proven Managed terminal format.

Authority: dither is compiled ONLY with `terminal_format_verified=True`
(Managed: the sink is pinned to the compiled output_format). Shared has no
terminal authority and is refused. Internal converters keep dither disabled.
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
    ProcessingCompilationError,
    ProcessingGraphCompiler,
    ProcessingSamplePolicy,
)
from michi.domain.audio_processing import (
    DitherMode,
    DitherNode,
    PreampNode,
    ProcessingGraph,
    ProcessingStrategy,
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


def _graph(*, mode: DitherMode = DitherMode.TPDF, bits: int = 16, revision: int = 1):
    return ProcessingGraph(
        graph_id="graph:dither",
        revision=revision,
        nodes=(
            PreampNode(node_id="pre", gain_db=0.0),
            DitherNode(node_id="dither", mode=mode, target_bits=bits),
        ),
    )


def _compile(graph=None, *, verified: bool = True, policy=None):
    effective = EffectiveProcessingGraphResolver().resolve(
        graph or _graph(), input_signal=_signal(), assets=()
    )
    return ProcessingGraphCompiler().compile(
        effective,
        backend=ProcessingBackendCapabilities(
            backend_id="test", strategies=frozenset(ProcessingStrategy)
        ),
        sample_policy=policy
        or ProcessingSamplePolicy(terminal_format_verified=verified),
    )


def test_dither_requires_a_proven_terminal_format() -> None:
    with pytest.raises(ProcessingCompilationError) as info:
        _compile(verified=False)
    assert info.value.code == "DSP_DITHER_TERMINAL_UNPROVEN"


def test_dither_compiles_with_explicit_native_properties() -> None:
    plan = _compile()
    node = plan.nodes[1]
    assert node.strategy is ProcessingStrategy.DITHER_TERMINAL
    assert plan.sample_contract.output_format == "S16LE"
    assert NativeProcessingMapping.expected_native_factories(node) == (
        "audioconvert",
        "capsfilter",
    )
    assert NativeProcessingMapping.expected_native_properties(node, rate_hz=44100) == {
        "dithering": 2,
        "noise_shaping": 0,
        "dithering_threshold": 16,
        "output_format": "S16LE",
    }
    wire = NativeProcessingMapping().plan_to_wire(plan)
    assert wire["nodes"][1]["properties"]["dithering"] == 2
    assert wire["nodes"][1]["properties"]["output_format"] == "S16LE"

    none_plan = _compile(_graph(mode=DitherMode.NONE))
    none_props = NativeProcessingMapping.expected_native_properties(
        none_plan.nodes[1], rate_hz=44100
    )
    assert none_props["dithering"] == 0

    plan24 = _compile(_graph(bits=24))
    assert plan24.sample_contract.output_format == "S24LE"


def test_dither_rejects_unsupported_targets_and_noise_shaping() -> None:
    effective = EffectiveProcessingGraphResolver().resolve(
        _graph(bits=16), input_signal=_signal(), assets=()
    )
    with pytest.raises(ProcessingCompilationError) as info:
        ProcessingGraphCompiler().compile(
            effective,
            backend=ProcessingBackendCapabilities(
                backend_id="test", strategies=frozenset(ProcessingStrategy)
            ),
            sample_policy=ProcessingSamplePolicy(
                terminal_format_verified=True, noise_shaping_mode="shaped"
            ),
        )
    assert info.value.code == "DSP_DITHER_NOISE_SHAPING_UNSUPPORTED"

    effective = EffectiveProcessingGraphResolver().resolve(
        _graph(bits=20), input_signal=_signal(), assets=()
    )
    with pytest.raises(ProcessingCompilationError) as info:
        ProcessingGraphCompiler().compile(
            effective,
            backend=ProcessingBackendCapabilities(
                backend_id="test", strategies=frozenset(ProcessingStrategy)
            ),
            sample_policy=ProcessingSamplePolicy(terminal_format_verified=True),
        )
    assert info.value.code == "DSP_DITHER_TARGET_UNSUPPORTED"


def _install(service, port, supervisor, graph, *, verified: bool = True):
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=_signal(), assets=()
    )
    plan = ProcessingGraphCompiler().compile(
        effective,
        backend=service.capabilities,
        sample_policy=ProcessingSamplePolicy(terminal_format_verified=verified),
    )
    candidate = service.begin_candidate(
        plan, host_generation=supervisor.host_generation, transport=port
    )
    receipt = service.commit_candidate(candidate, transport=port)
    service.publish_effective(receipt)
    return plan


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
def test_terminal_dither_is_installed_and_read_back(tmp_path, monkeypatch) -> None:
    from michi.application.audio_processing_service import AudioProcessingService
    from tests.audio_phase2.test_headroom_measurement import _write_sine
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "dither.wav"
    _write_sine(fixture, rate=44100, amplitude=1.5e-5)
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
        assert ProcessingStrategy.DITHER_TERMINAL in service.capabilities.strategies

        _install(service, port, supervisor, _graph(mode=DitherMode.TPDF))
        assert service.processing_truth()["readback_proven"] is True
        port.seek(0)
        dithered = port.capture_processing_output(1.0)
        assert dithered["format"] == "S16LE"
        assert dithered["rate_hz"] == 44100
        assert dithered["sample_peak"] <= 1.0

        _install(service, port, supervisor, _graph(mode=DitherMode.NONE, revision=2))
        assert service.processing_truth()["readback_proven"] is True
        port.seek(0)
        truncated = port.capture_processing_output(1.0)
        assert truncated["format"] == "S16LE"
        # TPDF adds a ~1 LSB noise floor; explicit no-dither quantization of a
        # sub-LSB sine stays near zero. Both are reproducible statistics.
        assert dithered["rms"] > truncated["rms"] + 2e-6
        assert dithered["rms"] > 4e-6
    finally:
        port.close()
        supervisor.close()


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
def test_managed_dither_executes_on_the_selected_binding(tmp_path, monkeypatch) -> None:
    from michi.domain.audio_processing import ProcessingProfile
    from tests.audio_phase2.test_managed_productive_flow import (
        FIXTURE,
        _build_graph,
        _close,
        _select_managed,
    )

    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    graph, coordinator = _build_graph(tmp_path)
    try:
        _select_managed(coordinator)
        graph.set_processing_profile(
            ProcessingProfile(
                profile_id="dsp:managed-dither",
                display_name="Dither",
                graph=_graph(),
            )
        )
        tokens: list[str] = []
        failures: list[Exception] = []
        graph.output_session.prepare_for_media_async(
            FIXTURE, tokens.append, failures.append
        )
        assert failures == [], failures
        graph.output_session.commit_media(tokens[0], FIXTURE)
        assert graph.audio_processing.effective_state.value == "effective"
        assert graph.audio_processing.processing_truth()["readback_proven"] is True
        port = graph.gstreamer_engine_provider.current_port
        identity = port.query_managed_identity()
        assert identity["managed"] is True and identity["loaded"] is True
        # Terminal authority chain: compiled output == DSP terminal == sink.
        assert identity["negotiated"]["format"] == "S16LE"
        assert identity["negotiated"]["rate_hz"] == 44100
        metrics = port.capture_processing_output(0.8)
        assert metrics["format"] == "S16LE"
    finally:
        _close(graph)


def _write_sine24(
    path,
    *,
    rate: int = 44100,
    amplitude: float = 5e-8,
    seconds: float = 2.5,
    frequency_hz: float = 1000.0,
) -> None:
    import math
    import wave

    frames = int(rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(3)
        handle.setframerate(rate)
        data = bytearray()
        for index in range(frames):
            value = int(
                round(
                    amplitude
                    * (1 << 23)
                    * math.sin(2 * math.pi * frequency_hz * index / rate)
                )
            )
            packed = (value & 0xFFFFFF).to_bytes(3, "little")
            data += packed + packed
        handle.writeframes(bytes(data))


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
def test_s24_terminal_dither_raises_the_noise_floor(tmp_path, monkeypatch) -> None:
    """24-bit target: a sub-24-bit-LSB input truncates to silence; TPDF adds
    ~1 LSB of shaped noise (reproducible RMS statistics, not sample equality)."""
    from michi.application.audio_processing_service import AudioProcessingService
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "dither24.wav"
    _write_sine24(fixture)
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

        _install(service, port, supervisor, _graph(bits=24))
        assert service.processing_truth()["readback_proven"] is True
        port.seek(0)
        dithered = port.capture_processing_output(1.0)
        assert dithered["format"] == "S24LE"
        assert dithered["rate_hz"] == 44100

        _install(
            service,
            port,
            supervisor,
            _graph(mode=DitherMode.NONE, bits=24, revision=2),
        )
        port.seek(0)
        truncated = port.capture_processing_output(1.0)
        assert truncated["format"] == "S24LE"
        # TPDF at 24 bits: ~1 LSB RMS/sqrt(12) ~= 3.4e-8; truncation of a
        # sub-LSB input is silence.
        assert dithered["rms"] > truncated["rms"] + 1e-8
        assert dithered["rms"] > 2e-8
    finally:
        port.close()
        supervisor.close()


def test_dither_mode_mapping_is_fail_closed() -> None:
    from michi.infrastructure.audio_processing.native_mapping import (
        dither_mode_to_native,
    )

    assert dither_mode_to_native("tpdf") == 2
    assert dither_mode_to_native("none") == 0
    for bad in ("auto", "tpdf_hf", "", None, 2, True):
        with pytest.raises(ValueError):
            dither_mode_to_native(bad)


def test_forged_dither_wire_is_rejected_before_native() -> None:
    import dataclasses

    plan = _compile()
    node = plan.nodes[1]
    properties = dict(node.properties)
    properties["mode"] = "auto"
    forged = dataclasses.replace(
        plan,
        nodes=(
            plan.nodes[0],
            dataclasses.replace(node, properties=tuple(properties.items())),
        ),
    )
    with pytest.raises(ValueError):
        NativeProcessingMapping().plan_to_wire(forged)
