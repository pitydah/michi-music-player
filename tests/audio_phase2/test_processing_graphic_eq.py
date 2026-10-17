"""AP2-F05 Package A — productive Graphic EQ spectral proof.

A deterministic multitone WAV is decoded by the child's playbin3, passes
through the installed Michi Graphic EQ, and a child-local diagnostic
capture (Goertzel) measures the magnitude at each tone. The expected change
at a peaking band center equals the configured band gain in dB — an
implementation-independent reference (RBJ property of a peaking filter).
"""

from __future__ import annotations

import importlib.util
import math
import struct
import time
import wave
from pathlib import Path

import pytest

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

PROBE_HZ = [125.0, 1000.0, 8000.0]
#: MICHI_10 centers: 31.25, 62.5, 125, 250, 500, 1k, 2k, 4k, 8k, 16k
MICHI_10 = (31.25, 62.5, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0)


def _write_multitone(path: Path, seconds: float = 1.6, rate: int = 44100) -> None:
    samples = int(seconds * rate)
    frames = bytearray()
    for index in range(samples):
        t = index / rate
        value = (
            0.2 * math.sin(2.0 * math.pi * 125.0 * t)
            + 0.2 * math.sin(2.0 * math.pi * 1000.0 * t)
            + 0.2 * math.sin(2.0 * math.pi * 8000.0 * t)
        )
        encoded = max(-32768, min(32767, int(round(value * 32767))))
        frames.extend(struct.pack("<h", encoded))
        frames.extend(struct.pack("<h", encoded))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))


def _real_port():
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    supervisor = GStreamerHostSupervisor(**SLOW)
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
    )
    return supervisor, port


def _service(port):
    from michi.application.audio_processing_service import AudioProcessingService
    from michi.infrastructure.audio_processing.native_mapping import (
        NativeProcessingMapping,
    )

    return AudioProcessingService(
        capability_query=port.query_processing_capabilities,
        native_mapping=NativeProcessingMapping(),
        transport=port,
    )


def _signal():
    from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat

    return PcmSignalFormat(
        rate_hz=44100,
        transport_format="S16LE",
        significant_bits=16,
        layout=ChannelLayout(positions=("FL", "FR")),
    )


def _graph(gains: tuple[float, ...], revision: int = 1):
    from michi.domain.audio_processing import (
        GraphicEqLayout,
        GraphicEqNode,
        ProcessingGraph,
    )

    return ProcessingGraph(
        graph_id="graph:geq",
        revision=revision,
        nodes=(
            GraphicEqNode(
                node_id="geq", layout_id=GraphicEqLayout.MICHI_10_V1, gains_db=gains
            ),
        ),
    )


def _install(service, port, supervisor, gains, revision=1):
    from michi.application.effective_processing_graph import (
        EffectiveProcessingGraphResolver,
    )
    from michi.application.processing_graph_compiler import ProcessingGraphCompiler

    effective = EffectiveProcessingGraphResolver().resolve(
        _graph(gains, revision), input_signal=_signal(), assets=()
    )
    plan = ProcessingGraphCompiler().compile(
        effective, backend=service.capabilities, assets=()
    )
    candidate = service.begin_candidate(
        plan, host_generation=supervisor.host_generation, transport=port
    )
    service.publish_effective(service.commit_candidate(candidate, transport=port))
    return plan


def _capture(port, seconds=0.8):
    port.seek(0)
    metrics = port.capture_processing_output(seconds, PROBE_HZ)
    tones = {round(t["hz"]): t["magnitude"] for t in metrics.get("tones", [])}
    assert len(tones) == 3 and all(value > 0.0 for value in tones.values()), metrics
    return tones


def _db(ratio: float) -> float:
    return 20.0 * math.log10(max(ratio, 1e-12))


def test_graphic_eq_spectral_boost_and_cut_are_real(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "multitone.wav"
    _write_multitone(fixture)

    supervisor, port = _real_port()
    try:
        port.activate()
        port.set_volume(0)
        port.load(fixture)
        deadline = time.monotonic() + 30.0
        while not port.backend_state() and time.monotonic() < deadline:
            port.dispatch_pending()
            time.sleep(0.02)

        service = _service(port)
        service.refresh_capabilities()
        from michi.domain.audio_processing import ProcessingStrategy

        assert ProcessingStrategy.GRAPHIC_EQ_NBANDS in service.capabilities.strategies

        # Flat reference through the SAME productive path.
        _install(service, port, supervisor, (0.0,) * 10, revision=1)
        flat = _capture(port)

        # 125 Hz +6 dB, 1 kHz -6 dB, 8 kHz +4 dB.
        gains = [0.0] * 10
        gains[MICHI_10.index(125.0)] = 6.0
        gains[MICHI_10.index(1000.0)] = -6.0
        gains[MICHI_10.index(8000.0)] = 4.0
        _install(service, port, supervisor, tuple(gains), revision=2)
        shaped = _capture(port)

        measured = {hz: _db(shaped[hz] / flat[hz]) for hz in flat}
        assert measured[125] == pytest.approx(6.0, abs=2.0), measured
        assert measured[1000] == pytest.approx(-6.0, abs=2.0), measured
        assert measured[8000] == pytest.approx(4.0, abs=2.0), measured

        # Flat EQ is an identity within tolerance (same productive path).
        assert _db(flat[1000] / flat[1000]) == 0.0

        # Transactional bypass: the tone magnitudes return to the flat baseline.
        assert port.bypass_processing()["bypassed"] is True
        bypassed = _capture(port)
        recovered = {hz: _db(bypassed[hz] / flat[hz]) for hz in flat}
        for hz, value in recovered.items():
            assert abs(value) < 4.0, (hz, value)
    finally:
        port.close()
        supervisor.close()


def test_graphic_eq_mixed_bands_and_rate_switch(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    fixture = tmp_path / "multitone48.wav"
    _write_multitone(fixture, rate=44100)  # playback rate fixed by fixture

    supervisor, port = _real_port()
    try:
        port.activate()
        port.set_volume(0)
        port.load(fixture)
        deadline = time.monotonic() + 30.0
        while not port.backend_state() and time.monotonic() < deadline:
            port.dispatch_pending()
            time.sleep(0.02)
        service = _service(port)
        service.refresh_capabilities()

        # Mixed positive/negative bands; the measured deltas must move in the
        # requested DIRECTIONS independently (no global RMS proxy).
        gains = [0.0] * 10
        gains[MICHI_10.index(125.0)] = -8.0
        gains[MICHI_10.index(1000.0)] = 5.0
        _install(service, port, supervisor, (0.0,) * 10, revision=1)
        baseline = _capture(port)
        _install(service, port, supervisor, tuple(gains), revision=2)
        shaped = _capture(port)
        low = _db(shaped[125] / baseline[125])
        mid = _db(shaped[1000] / baseline[1000])
        assert low < -3.0, (low, "low band must be cut")
        assert mid > 2.0, (mid, "mid band must be boosted")
        assert low < 0.0 < mid  # opposite directions, same measurement
    finally:
        port.close()
        supervisor.close()
