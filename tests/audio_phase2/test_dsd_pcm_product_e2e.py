from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import pytest

from michi.application.audio_output_planner import OutputPlanner
from michi.application.dsd_policy_service import (
    DsdPolicyDecision,
    OutputFamily,
)
from michi.application.output_session_service import (
    DsdPcmSessionPrepared,
    OutputSessionService,
)
from michi.application.playback_service import PlaybackService
from michi.domain.audio_output import OutputSessionState
from michi.domain.signal_truth import OutputFamilyState, SignalTruthRecorder
from tests.audio_phase2.test_dop_resolver import _resolver
from tests.audio_phase2.test_dsd_source_truth import build_dsf

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="GStreamer Python bindings unavailable"
)


class _Volume:
    def synchronize(self):
        raise AssertionError("DSD→PCM must not synchronize PCM volume")

    def restore(self, volume, muted):
        return None


def test_playback_service_dsd64_to_pcm_eos_release(tmp_path, monkeypatch):
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    source = tmp_path / "product.dsf"
    source.write_bytes(build_dsf(sample_count=88_200, payload=bytes([0x69]) * 176_400))
    decision = DsdPolicyDecision(
        decision=OutputFamily.DSD_TO_PCM,
        reason="DSD_TO_PCM",
        reasons=("DSD_TO_PCM",),
        conversion_consent_required=False,
        quality_profile="FAST",
    )
    resolver = _resolver(
        None,
        dsd_pcm_policy_provider=lambda _source: decision,
        dsd_pcm_planner=__import__(
            "michi.application.dsd_to_pcm_plan",
            fromlist=["DsdToPcmPlanner"],
        ).DsdToPcmPlanner(),
        dsd_pcm_target_rates=lambda _device, _binding: (88_200,),
        dsd_pcm_host_generation=lambda: 1,
        dsd_pcm_decoder_available=True,
    )
    supervisor = GStreamerHostSupervisor(
        start_timeout_s=45.0,
        command_timeout_s=30.0,
        terminate_grace_s=8.0,
        term_grace_s=5.0,
        kill_grace_s=5.0,
    )
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
    )
    session_holder: dict[str, OutputSessionService] = {}

    def prepare(plan_value, path, instance_id):
        identity = port.prepare_dsd_pcm(
            {
                "path": str(path),
                "plan_id": plan_value.plan_id,
                "execution_id": instance_id,
                "binding_generation": plan_value.binding_generation,
                "stable_device_id": plan_value.stable_device_id,
                "locator": plan_value.binding_locator,
                "source_family": "dsf",
                "source_rate_hz": plan_value.source_format.bit_rate_hz,
                "source_bits": plan_value.source_format.bit_rate_hz,
                "bit_order": plan_value.source_format.bit_order.value,
                "channels": plan_value.channels,
                "decoder_factory": plan_value.decoder_factory,
                "target_rate_hz": plan_value.target_rate_hz,
                "output_format": plan_value.output_format,
                "quality_profile": plan_value.quality_profile,
                "resampler_policy": [
                    list(item) for item in plan_value.resampler_policy
                ],
                "sink_factory": "fakesink",
            }
        )
        port.add_dsd_pcm_eos_listener(session_holder["s"].notify_dsd_pcm_eos)
        expected = {
            "plan_id": identity["plan_id"],
            "execution_id": identity["execution_id"],
            "stable_device_id": identity["stable_device_id"],
            "device": identity["device"],
            "binding_generation": identity["binding_generation"],
            "host_generation": identity["host_generation"],
        }
        return DsdPcmSessionPrepared(
            plan=plan_value,
            execution_id=expected["execution_id"],
            stable_device_id=expected["stable_device_id"],
            binding_locator=expected["device"],
            host_generation=expected["host_generation"],
            runtime_identity=dict(identity),
            evidence_refs=(),
            handle=expected,
        )

    def commit(prepared):
        port.commit_dsd_pcm(prepared.handle)

    def abort(prepared, reason):
        return port.abort_dsd_pcm(prepared.handle)

    def stop(prepared, reason):
        return port.stop_dsd_pcm(prepared.handle)

    truth = SignalTruthRecorder()
    session = OutputSessionService(
        OutputPlanner(),
        request_provider=resolver,
        async_submit=None,
        dsd_pcm_prepare=prepare,
        dsd_pcm_commit=commit,
        dsd_pcm_abort=abort,
        dsd_pcm_stop=stop,
        dsd_pcm_plan_still_current=lambda _plan: True,
        truth_recorder=truth,
    )
    session_holder["s"] = session
    playback = PlaybackService(port, volume_port=_Volume(), output_tx=session)
    accepted: list[Path] = []
    try:
        port.activate()
        playback.load_and_play(source, on_accepted=accepted.append)
        assert accepted == [source]
        assert session.mode == "dsd_pcm"
        assert session.state is OutputSessionState.RUNNING
        assert session.topology_loss_applies("dev:dac") is True
        assert session.topology_loss_applies("dev:other") is False
        assert dispatch_eventually(port, session)
        playback.stop()
        assert session.state is OutputSessionState.IDLE
        assert port.dsd_pcm_active is False
        families = [event.family for event in truth.output_family_events]
        states = [event.state for event in truth.output_family_events]
        assert "dsd_pcm" in families
        assert OutputFamilyState.RUNNING in states
        assert OutputFamilyState.RELEASED in states

        accepted.clear()
        playback.load_and_play(source, on_accepted=accepted.append)
        assert accepted == [source]
        assert session.mode == "dsd_pcm"
        assert session.state is OutputSessionState.RUNNING
        assert dispatch_eventually(port, session)
        playback.stop()
        assert session.state is OutputSessionState.IDLE
        assert port.dsd_pcm_active is False
    finally:
        supervisor.close()


def dispatch_eventually(port, session, timeout_s: float = 8.0) -> bool:
    execution = session.active_execution_id
    assert execution
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        port.dispatch_pending()
        if session._dsd_pcm_terminal_execution == execution:
            return True
        time.sleep(0.02)
    return False
