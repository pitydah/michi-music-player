"""AP2-F06 — numeric headroom evidence on the real hosted runtime.

The capture diagnostic reports SAMPLE peak, samples over full scale and the
resulting headroom. It never claims true peak or analog clipping.
"""

from __future__ import annotations

import importlib.util
import math
import struct
import time
import wave

import pytest

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="PyGObject/GStreamer not available on this host"
)


def _write_sine(path, *, rate: int, amplitude: float = 0.9, seconds: float = 2.5):
    frames = int(rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        data = bytearray()
        for index in range(frames):
            value = int(
                round(amplitude * 32767 * math.sin(2 * math.pi * 1000 * index / rate))
            )
            data += struct.pack("<hh", value, value)
        handle.writeframes(bytes(data))


def _signal(rate: int):
    from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat

    return PcmSignalFormat(
        rate_hz=rate,
        transport_format="S16LE",
        significant_bits=16,
        layout=ChannelLayout(positions=("FL", "FR")),
    )


def _graph(*nodes):
    from michi.domain.audio_processing import ProcessingGraph

    return ProcessingGraph(graph_id="graph:headroom", revision=1, nodes=nodes)


def _peq(gain_db: float, *, revision: int):
    from michi.domain.audio_processing import (
        BiquadType,
        ParametricEqNode,
        PeqBand,
    )

    return _graph(
        ParametricEqNode(
            node_id="peq",
            bands=(PeqBand("b1", BiquadType.PEAK, 1000.0, 1.4, gain_db, True),),
        ),
    )


def _install(service, port, supervisor, graph, *, rate: int):
    from michi.application.effective_processing_graph import (
        EffectiveProcessingGraphResolver,
    )
    from michi.application.processing_graph_compiler import (
        ProcessingGraphCompiler,
    )

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


@pytest.mark.parametrize("rate", [44100, 48000, 96000])
def test_headroom_is_numerically_measured_and_auto_headroom_prevents_overflow(
    tmp_path, monkeypatch, rate
) -> None:
    from michi.application.audio_processing_service import AudioProcessingService
    from michi.infrastructure.audio_processing.native_mapping import (
        NativeProcessingMapping,
    )
    from tests.audio_phase2.test_processing_graphic_eq import _real_port

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / f"sine-{rate}.wav"
    _write_sine(fixture, rate=rate, amplitude=0.9)

    supervisor, port = _real_port()
    try:
        port.activate()
        port.set_volume(0)
        port.load(fixture)
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            port.dispatch_pending()
            duration = None
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

        def measure():
            # Restart the fixture at the start of every window. A 1 s window
            # is long enough for playbin3 to preroll the rebuilt filter.
            port.seek(0)
            return port.capture_processing_output(1.0)

        # Flat PEQ baseline (~0.9 sample peak).
        _install(service, port, supervisor, _peq(0.0, revision=1), rate=rate)
        baseline = measure()
        assert 0.8 <= baseline["sample_peak"] <= 1.0, baseline
        assert baseline["exceeds_full_scale"] is False
        assert baseline["samples_over_full_scale"] == 0
        assert baseline["headroom_db"] is not None and baseline["headroom_db"] > 0

        # PEQ +6 dB at the tone frequency pushes the float signal over FS.
        _install(service, port, supervisor, _peq(6.0, revision=2), rate=rate)
        boosted = measure()
        assert boosted["sample_peak"] > 1.4, boosted
        assert boosted["exceeds_full_scale"] is True
        assert boosted["samples_over_full_scale"] > 0
        assert boosted["headroom_db"] is not None and boosted["headroom_db"] < 0

        # Explicit auto-headroom (preamp -6 dB) keeps the same +6 dB shape
        # below full scale: measurable policy, not a hidden level change.
        from michi.domain.audio_processing import PreampNode

        compensated = _graph(
            PreampNode(node_id="auto-headroom", gain_db=-6.0),
            _peq(6.0, revision=3).nodes[0],
        )
        _install(service, port, supervisor, compensated, rate=rate)
        protected = measure()
        assert protected["sample_peak"] < 1.0, protected
        assert protected["exceeds_full_scale"] is False
        assert protected["samples_over_full_scale"] == 0
        # The measured sample peak sits near the original 0.9 amplitude.
        assert 0.75 <= protected["sample_peak"] <= 1.0, protected
    finally:
        port.close()
        supervisor.close()
