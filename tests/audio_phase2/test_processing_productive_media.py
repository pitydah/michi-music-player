"""AP2-F05 Part B — REAL productive Shared PCM DSP proof.

The REAL user's media is decoded by the child's playbin3, passes through the
Michi processing filter installed as `audio-filter`, and the child reports
primitive signal metrics proving the DSP changed the audio. Volume is 0 so
nothing is audible; no audio ever crosses IPC.
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import pytest

from michi.application.audio_processing_service import AudioProcessingService
from michi.application.effective_processing_graph import (
    EffectiveProcessingGraphResolver,
)
from michi.application.processing_graph_compiler import (
    ProcessingGraphCompiler,
    ProcessingSamplePolicy,
)
from michi.domain.audio_processing import (
    PreampNode,
    ProcessingGraph,
    ProcessingStrategy,
)
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat
from michi.infrastructure.audio_engines.gstreamer_host_client import (
    GStreamerHostSupervisor,
)
from michi.infrastructure.audio_engines.gstreamer_host_port import (
    GStreamerHostedAudioPort,
)
from michi.infrastructure.audio_processing.native_mapping import (
    NativeProcessingMapping,
)

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="PyGObject/GStreamer not available on this host"
)

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run"
    / "fixtures/pcm16_44100.wav"
)

SLOW = {
    "start_timeout_s": 45.0,
    "command_timeout_s": 30.0,
    "terminate_grace_s": 5.0,
    "term_grace_s": 3.0,
    "kill_grace_s": 3.0,
}


def _real_port():
    supervisor = GStreamerHostSupervisor(**SLOW)
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
    )
    return supervisor, port


def _plan(service, gain_db: float):
    signal = PcmSignalFormat(
        rate_hz=44100,
        transport_format="S16LE",
        significant_bits=16,
        layout=ChannelLayout(positions=("FL", "FR")),
    )
    graph = ProcessingGraph(
        graph_id="graph:f05-media",
        revision=11,
        nodes=(PreampNode(node_id="pre", gain_db=gain_db),),
    )
    effective = EffectiveProcessingGraphResolver().resolve(
        graph, input_signal=signal, assets=()
    )
    return ProcessingGraphCompiler().compile(
        effective,
        backend=service.capabilities,
        assets=(),
        sample_policy=ProcessingSamplePolicy(working_format="F64LE"),
    )


def _install_and_measure(service, port, supervisor, gain_db, *, seconds=0.6):
    plan = _plan(service, gain_db)
    candidate = service.begin_candidate(
        plan,
        host_generation=supervisor.host_generation,
        transport=port,
    )
    receipt = service.commit_candidate(candidate, transport=port)
    service.publish_effective(receipt)
    assert service.effective_state.value == "effective"
    port.seek(0)  # same content window for every measurement
    metrics = port.capture_processing_output(seconds)
    assert metrics["frames"] > 0
    return metrics, receipt


def test_productive_shared_pcm_dsp_really_processes_media() -> None:
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    supervisor, port = _real_port()
    try:
        port.activate()
        port.set_volume(0)  # silent: no audible output
        port.load(FIXTURE)
        deadline = time.monotonic() + 30.0
        while not port.backend_state() and time.monotonic() < deadline:
            port.dispatch_pending()
            time.sleep(0.02)
        port.dispatch_pending()

        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
            transport=port,
        )
        service.refresh_capabilities()
        assert ProcessingStrategy.GAIN in service.capabilities.strategies

        # Flat (unity preamp) baseline through the SAME productive path.
        flat_metrics, flat_receipt = _install_and_measure(
            service, port, supervisor, 0.0
        )
        assert flat_receipt.installed is True
        assert flat_receipt.native_runtime_identity == "playbin3/audio-filter"

        # -6 dB preamp: measurable expected attenuation (~0.5 linear).
        quiet_metrics, quiet_receipt = _install_and_measure(
            service, port, supervisor, -6.0
        )
        assert quiet_metrics["rms"] > 0.0
        assert flat_metrics["samples"] > 0 and quiet_metrics["samples"] > 0
        ratio = quiet_metrics["rms"] / max(flat_metrics["rms"], 1e-12)
        assert 0.35 < ratio < 0.65, (
            f"preamp -6 dB must attenuate near 0.5x: rms {flat_metrics['rms']} "
            f"-> {quiet_metrics['rms']} (ratio {ratio:.3f})"
        )
        # The graph really was replaced in the same productive pipeline.
        assert quiet_receipt.observed_plan_id != flat_receipt.observed_plan_id

        # Transactional bypass: our DSP leaves the chain and the signal
        # RETURNS to the flat baseline (measured, not just claimed).
        bypass_payload = port.bypass_processing()
        assert bypass_payload["bypassed"] is True
        assert bypass_payload["removed"] is True
        port.seek(0)
        bypass_metrics = port.capture_processing_output(0.7)
        assert bypass_metrics["samples"] > 0
        bypass_ratio = bypass_metrics["rms"] / max(flat_metrics["rms"], 1e-12)
        assert 0.7 < bypass_ratio < 1.4, (
            f"bypass must return to baseline: flat {flat_metrics['rms']} -> "
            f"bypass {bypass_metrics['rms']} (ratio {bypass_ratio:.3f})"
        )
    finally:
        port.close()
        supervisor.close()


def test_gain_graph_requires_a_loaded_pipeline_for_effect() -> None:
    """Without media loaded the productive install must fail closed."""
    supervisor, port = _real_port()
    try:
        port.activate()
        service = AudioProcessingService(
            capability_query=port.query_processing_capabilities,
            native_mapping=NativeProcessingMapping(),
            transport=port,
        )
        service.refresh_capabilities()
        plan = _plan(service, -3.0)
        candidate = service.begin_candidate(
            plan, host_generation=supervisor.host_generation, transport=port
        )
        from michi.application.audio_processing_service import (
            ProcessingTransactionError,
        )

        with pytest.raises(Exception) as info:
            service.commit_candidate(candidate, transport=port)
        assert "DSP_COMMIT" in str(info.value) or "DSP_PLAYBACK" in str(info.value)
        assert service.effective_state.value == "preparing"
        _ = ProcessingTransactionError
    finally:
        port.close()
        supervisor.close()
