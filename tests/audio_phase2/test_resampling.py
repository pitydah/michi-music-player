"""AP2-F06 — explicit resampling vertical (RESAMPLE strategy).

The compiled target rate is enforced natively by audioresample + a rate-pinned
capsfilter, proven by the negotiated sink rate on the real host.
"""

from __future__ import annotations

import importlib.util
import math
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


def _graph(target_rate: int, *, revision: int = 1):
    return ProcessingGraph(
        graph_id="graph:resample",
        revision=revision,
        nodes=(
            PreampNode(node_id="pre", gain_db=0.0),
            ResampleNode(
                node_id="rs",
                target_rate_hz=target_rate,
                quality=ResampleQuality.HIGH,
            ),
        ),
    )


def _compile(graph=None, *, rate: int = 44100, strategies=None):
    effective = EffectiveProcessingGraphResolver().resolve(
        graph or _graph(48000), input_signal=_signal(rate), assets=()
    )
    return ProcessingGraphCompiler().compile(
        effective,
        backend=ProcessingBackendCapabilities(
            backend_id="test",
            strategies=frozenset(strategies or ProcessingStrategy),
        ),
        assets=(),
    )


def test_resample_compiles_with_the_target_rate_contract() -> None:
    plan = _compile()
    strategies = [node.strategy for node in plan.nodes]
    assert strategies == [ProcessingStrategy.GAIN, ProcessingStrategy.RESAMPLE]
    assert plan.changes_rate is True
    assert plan.sample_contract.output_rate_hz == 48000
    node = plan.nodes[1]
    properties = dict(node.properties)
    assert properties["target_rate_hz"] == 48000
    assert NativeProcessingMapping.expected_native_factories(node) == (
        "audioresample",
        "capsfilter",
    )
    assert NativeProcessingMapping.expected_native_properties(node, rate_hz=44100) == {
        "target_rate_hz": 48000,
        "quality": 8,
    }
    wire = NativeProcessingMapping().plan_to_wire(plan)
    assert wire["nodes"][1]["properties"]["target_rate_hz"] == 48000
    assert wire["nodes"][1]["properties"]["native_quality"] == 8


def test_same_rate_resample_is_not_a_rate_change() -> None:
    plan = _compile(_graph(44100))
    assert plan.changes_rate is False
    assert plan.sample_contract.output_rate_hz == 44100


def test_managed_planner_accepts_a_compiled_rate_change() -> None:
    from michi.application.managed_pcm_output_planner import (
        ManagedPcmOutputPlanner,
        ManagedPcmPlannerFacts,
    )
    from michi.domain.audio_device import AudioDeviceBinding, BindingKind
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.managed_pcm_output import ManagedPcmOutputPlan

    plan = _compile()
    facts = ManagedPcmPlannerFacts(
        selected_device_id="dev:dac",
        binding=AudioDeviceBinding(BindingKind.ALSA_PCM, "hw:2,0", 1, True),
        binding_device_id="dev:dac",
        source_pcm=PcmTuple(44100, "", 2, 16),
        compiled_plan=plan,
        terminal_formats=frozenset({"S16LE"}),
        volume_policy="software",
        selection_revision=1,
        current_selection_revision=1,
    )
    result = ManagedPcmOutputPlanner().plan(facts)
    assert isinstance(result, ManagedPcmOutputPlan), result
    assert result.output_rate_hz == 48000
    assert "rate_change" in result.transform_policy


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
@pytest.mark.parametrize("target_rate", [48000, 96000])
def test_resample_runs_natively_and_negotiates_the_target_rate(
    tmp_path, monkeypatch, target_rate
) -> None:
    from michi.application.audio_processing_service import AudioProcessingService
    from tests.audio_phase2.test_headroom_measurement import _write_sine
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "resample-sine.wav"
    _write_sine(fixture, rate=44100, amplitude=0.6)

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
        assert ProcessingStrategy.RESAMPLE in service.capabilities.strategies

        effective = EffectiveProcessingGraphResolver().resolve(
            _graph(target_rate), input_signal=_signal(44100), assets=()
        )
        plan = ProcessingGraphCompiler().compile(
            effective, backend=service.capabilities, assets=()
        )
        candidate = service.begin_candidate(
            plan, host_generation=supervisor.host_generation, transport=port
        )
        receipt = service.commit_candidate(candidate, transport=port)
        service.publish_effective(receipt)
        assert service.processing_truth()["readback_proven"] is True

        port.seek(0)
        metrics = port.capture_processing_output(1.0, probe_hz=[1000.0])
        assert metrics["rate_hz"] == target_rate, metrics
        assert metrics["frames"] > 0
        assert metrics["tones"] and metrics["tones"][0]["magnitude"] > 0.0
    finally:
        port.close()
        supervisor.close()


@pytest.mark.parametrize(
    ("quality", "native"),
    [
        (ResampleQuality.FAST, 2),
        (ResampleQuality.BALANCED, 5),
        (ResampleQuality.HIGH, 8),
        (ResampleQuality.REFERENCE, 10),
    ],
)
def test_resample_quality_has_a_deterministic_native_mapping(quality, native) -> None:
    graph = ProcessingGraph(
        graph_id="graph:resample-q",
        revision=1,
        nodes=(ResampleNode(node_id="rs", target_rate_hz=48000, quality=quality),),
    )
    plan = _compile(graph)
    node = plan.nodes[0]
    assert NativeProcessingMapping.expected_native_properties(node, rate_hz=44100) == {
        "target_rate_hz": 48000,
        "quality": native,
    }
    wire = NativeProcessingMapping().plan_to_wire(plan)
    assert wire["nodes"][0]["properties"]["native_quality"] == native


def _write_tones(path, *, rate: int, components, seconds: float = 2.5) -> None:
    import struct
    import wave

    frames = int(rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        data = bytearray()
        for index in range(frames):
            value = sum(
                amplitude * math.sin(2 * math.pi * frequency * index / rate + phase)
                for frequency, amplitude, phase in components
            )
            sample = int(round(max(-0.999, min(0.999, value)) * 32767))
            data += struct.pack("<hh", sample, sample)
        handle.writeframes(bytes(data))


def _install_resample(service, port, supervisor, *, source_rate, target_rate):
    effective = EffectiveProcessingGraphResolver().resolve(
        _graph(target_rate), input_signal=_signal(source_rate), assets=()
    )
    plan = ProcessingGraphCompiler().compile(
        effective, backend=service.capabilities, assets=()
    )
    candidate = service.begin_candidate(
        plan, host_generation=supervisor.host_generation, transport=port
    )
    receipt = service.commit_candidate(candidate, transport=port)
    service.publish_effective(receipt)
    return plan


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
@pytest.mark.parametrize(
    ("source_rate", "target_rate"),
    [
        (44100, 48000),
        (44100, 96000),
        (48000, 44100),
        (96000, 44100),
        (96000, 48000),
    ],
)
def test_resample_preserves_passband_amplitude(
    tmp_path, monkeypatch, source_rate, target_rate
) -> None:
    from michi.application.audio_processing_service import AudioProcessingService
    from tests.audio_phase2.test_headroom_measurement import _write_sine
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / f"tone-{source_rate}.wav"
    _write_sine(fixture, rate=source_rate, amplitude=0.5, frequency_hz=1000.0)
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
        _install_resample(
            service,
            port,
            supervisor,
            source_rate=source_rate,
            target_rate=target_rate,
        )
        assert service.processing_truth()["readback_proven"] is True
        port.seek(0)
        metrics = port.capture_processing_output(1.0, probe_hz=[1000.0])
        assert metrics["rate_hz"] == target_rate, metrics
        tone = metrics["tones"][0]["magnitude"]
        # Passband amplitude error < 0.04 absolute (~0.7 dB) at 1 kHz.
        assert tone == pytest.approx(0.5, abs=0.04), (tone, source_rate, target_rate)
    finally:
        port.close()
        supervisor.close()


@pytest.mark.skipif(not _HAS_GI, reason="PyGObject/GStreamer unavailable")
def test_resample_suppresses_aliasing_on_downsampling(tmp_path, monkeypatch) -> None:
    """96k tone at 30 kHz must not fold to 18 kHz when downsampled to 48k."""
    from michi.application.audio_processing_service import AudioProcessingService
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "alias-96k.wav"
    _write_tones(
        fixture,
        rate=96000,
        components=((1000.0, 0.4, 0.0), (30000.0, 0.4, 0.0)),
    )
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
        _install_resample(
            service, port, supervisor, source_rate=96000, target_rate=48000
        )
        port.seek(0)
        metrics = port.capture_processing_output(1.0, probe_hz=[1000.0, 18000.0])
        assert metrics["rate_hz"] == 48000
        tones = {tone["hz"]: tone["magnitude"] for tone in metrics["tones"]}
        assert tones[1000.0] == pytest.approx(0.4, abs=0.05)
        # -26 dB or better relative to the passband tone: the alias is
        # suppressed by the HIGH quality sinc filter.
        assert tones[18000.0] < 0.02, tones
    finally:
        port.close()
        supervisor.close()
