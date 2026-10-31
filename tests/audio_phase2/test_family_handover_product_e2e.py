"""AP2-F10 C4 — bidirectional family handover through the real output host.

E2E-A: DSD→PCM RUNNING → DoP RUNNING.
E2E-B: DoP RUNNING → DSD→PCM RUNNING.

The chain is the productive one: PlaybackService → OutputSessionService →
GStreamerHostedAudioPort → GStreamerHostSupervisor. ``fakesink`` is only a
laboratory terminal; this is not physical DAC certification.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from michi.application.audio_family_transition import TransitionPhase
from michi.application.audio_output_planner import OutputPlanner
from michi.application.dsd_policy_service import DsdPolicyDecision, OutputFamily
from michi.application.dsd_to_pcm_plan import DsdToPcmPlanner
from michi.application.output_session_service import (
    DopSessionPrepared,
    DsdPcmSessionPrepared,
    HandoverState,
    OutputSessionService,
)
from michi.application.playback_service import PlaybackService
from michi.domain.audio_output import OutputSessionState
from michi.domain.dop import DopInterpretationState, DopPolicyDecision
from michi.domain.signal_truth import OutputFamilyState, SignalTruthRecorder
from tests.audio_phase2.test_dop_resolver import _resolver
from tests.audio_phase2.test_dsd_source_truth import build_dsf

_HAS_GI = importlib.util.find_spec("gi") is not None


def _resolved_prefix():
    from michi.infrastructure.audio_output.dop_plugin import resolve_dop_prefix

    try:
        return resolve_dop_prefix()
    except RuntimeError:
        return None


_PREFIX = _resolved_prefix()

pytestmark = pytest.mark.skipif(
    not _HAS_GI or _PREFIX is None,
    reason="GStreamer or Gate A michidop prefix unavailable",
)


class _Volume:
    def synchronize(self):
        raise AssertionError("DSD families must not synchronize PCM volume")

    def restore(self, volume, muted):
        return None


def _dop_resolver():
    return _resolver(
        DopPolicyDecision(
            explicit_requested=True,
            auto_allowed=False,
            minimum_interpretation_state=DopInterpretationState.USER_CONFIRMED,
        )
    )


def _dsd_pcm_resolver():
    decision = DsdPolicyDecision(
        decision=OutputFamily.DSD_TO_PCM,
        reason="DSD_TO_PCM",
        reasons=("DSD_TO_PCM",),
        conversion_consent_required=False,
        quality_profile="FAST",
    )
    return _resolver(
        None,
        dsd_pcm_policy_provider=lambda _source: decision,
        dsd_pcm_planner=DsdToPcmPlanner(),
        dsd_pcm_target_rates=lambda _device, _binding, _channels: (88_200,),
        dsd_pcm_host_generation=lambda: 1,
        dsd_pcm_decoder_available=True,
    )


class _Rig:
    def __init__(self, port, session, resolver):
        self.port = port
        self.session = session
        self.resolver = resolver

    def request_for(self, path: Path):
        return self.resolver(path)


def _build(tmp_path, monkeypatch, *, dsd_source: Path):
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    dsd_source.write_bytes(
        build_dsf(sample_count=352_800, payload=bytes([0x69]) * 705_600)
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
    truth = SignalTruthRecorder()
    session_holder: dict[str, OutputSessionService] = {}
    dop_resolver = _dop_resolver()
    dsd_resolver = _dsd_pcm_resolver()

    def request_for(path: Path):
        # The same canonical resolver authority resolves both families; the
        # selected media intent (not a fabricated plan) chooses the family.
        if path.name == "dop.dsf":
            return dop_resolver(path)
        return dsd_resolver(path)

    def dop_prepare(plan_value, path, _instance):
        from michi.infrastructure.audio_output.dop_runtime import DopOutputExecutor

        prepared = DopOutputExecutor(port, sink_factory="fakesink").prepare(
            plan_value, path
        )
        port.add_dop_eos_listener(session_holder["s"].notify_dop_eos)
        return DopSessionPrepared(
            plan=plan_value,
            execution_id=plan_value.execution_id,
            stable_device_id=plan_value.stable_device_id,
            runtime_identity=dict(prepared.identity),
            evidence_refs=(),
            handle=prepared,
        )

    def dop_commit(prepared):
        from michi.infrastructure.audio_output.dop_runtime import DopOutputExecutor

        DopOutputExecutor(port, sink_factory="fakesink").commit(prepared.handle)

    def dop_abort(prepared, reason):
        from michi.infrastructure.audio_output.dop_runtime import DopOutputExecutor

        return DopOutputExecutor(port, sink_factory="fakesink").abort(
            prepared.handle, reason
        )

    def dop_stop(prepared, reason):
        from michi.infrastructure.audio_output.dop_runtime import DopOutputExecutor

        return DopOutputExecutor(port, sink_factory="fakesink").stop(
            prepared.handle, reason
        )

    def dsd_prepare(plan_value, path, instance_id):
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

    def dsd_commit(prepared):
        port.commit_dsd_pcm(prepared.handle)

    def dsd_abort(prepared, reason):
        return port.abort_dsd_pcm(prepared.handle)

    def dsd_stop(prepared, reason):
        return port.stop_dsd_pcm(prepared.handle)

    session = OutputSessionService(
        OutputPlanner(),
        request_provider=request_for,
        async_submit=None,
        dop_prepare=dop_prepare,
        dop_commit=dop_commit,
        dop_abort=dop_abort,
        dop_stop=dop_stop,
        dop_plan_still_current=lambda _plan: True,
        dsd_pcm_prepare=dsd_prepare,
        dsd_pcm_commit=dsd_commit,
        dsd_pcm_abort=dsd_abort,
        dsd_pcm_stop=dsd_stop,
        dsd_pcm_plan_still_current=lambda _plan: True,
        truth_recorder=truth,
    )
    session_holder["s"] = session
    playback = PlaybackService(port, volume_port=_Volume(), output_tx=session)
    return supervisor, port, session, playback, truth


def _assert_handover_started(
    session: OutputSessionService,
    playback: PlaybackService,
    *,
    predecessor_execution: str,
    predecessor_plan: str,
    target_family: str,
) -> None:
    evidence = session.last_handover_release_evidence
    assert evidence is not None
    assert evidence["confirmed"] is True
    assert evidence["terminal_state"] == "RELEASED"
    assert evidence["provenance"] == "SUPERVISED_HOST"
    assert evidence["execution_id"] == predecessor_execution
    assert evidence["plan_id"] == predecessor_plan
    assert evidence["target_family"] == target_family
    assert session.handover_state is HandoverState.READY
    assert playback.family_transition_receipts
    receipt = playback.family_transition_receipts[-1]
    assert receipt.phase is TransitionPhase.TARGET_STARTED
    assert receipt.predecessor_released is True


def test_e2e_a_dsd_pcm_running_to_dop_running(tmp_path, monkeypatch) -> None:
    source_dsd = tmp_path / "dsd_pcm.dsf"
    source_dop = tmp_path / "dop.dsf"
    supervisor, port, session, playback, truth = _build(
        tmp_path, monkeypatch, dsd_source=source_dsd
    )
    source_dop.write_bytes(source_dsd.read_bytes())
    accepted: list[Path] = []
    try:
        port.activate()
        playback.load_and_play(source_dsd, on_accepted=accepted.append)
        assert accepted == [source_dsd]
        assert session.mode == "dsd_pcm"
        assert session.state is OutputSessionState.RUNNING
        assert port.dsd_pcm_active is True
        predecessor_execution = session.active_execution_id
        predecessor_plan = session.transition_snapshot()["plan_id"]
        assert predecessor_execution and predecessor_plan

        playback.load_and_play(source_dop, on_accepted=accepted.append)
        assert accepted == [source_dsd, source_dop]
        assert session.mode == "dop"
        assert session.state is OutputSessionState.RUNNING
        assert session.dop_active is True
        assert port.dsd_pcm_active is False
        assert port.dop_active is True
        _assert_handover_started(
            session,
            playback,
            predecessor_execution=predecessor_execution,
            predecessor_plan=predecessor_plan,
            target_family="dop",
        )

        families = [event.family for event in truth.output_family_events]
        states = [event.state for event in truth.output_family_events]
        assert "dsd_pcm" in families
        assert ("dsd_pcm", OutputFamilyState.RUNNING) in list(
            (event.family, event.state) for event in truth.output_family_events
        )
        assert ("dsd_pcm", OutputFamilyState.RELEASED) in list(
            (event.family, event.state) for event in truth.output_family_events
        )
        assert OutputFamilyState.RUNNING in states

        playback.stop()
        assert session.state is OutputSessionState.IDLE
        assert port.dop_active is False
    finally:
        supervisor.close()


def test_e2e_b_dop_running_to_dsd_pcm_running(tmp_path, monkeypatch) -> None:
    source_dsd = tmp_path / "target.dsf"
    source_dop = tmp_path / "dop.dsf"
    supervisor, port, session, playback, truth = _build(
        tmp_path, monkeypatch, dsd_source=source_dsd
    )
    source_dop.write_bytes(source_dsd.read_bytes())
    accepted: list[Path] = []
    try:
        port.activate()
        playback.load_and_play(source_dop, on_accepted=accepted.append)
        assert accepted == [source_dop]
        assert session.mode == "dop"
        assert session.state is OutputSessionState.RUNNING
        assert port.dop_active is True
        predecessor_execution = session.active_execution_id
        predecessor_plan = session.transition_snapshot()["plan_id"]
        assert predecessor_execution and predecessor_plan

        playback.load_and_play(source_dsd, on_accepted=accepted.append)
        assert accepted == [source_dop, source_dsd]
        assert session.mode == "dsd_pcm"
        assert session.state is OutputSessionState.RUNNING
        assert session.dsd_pcm_active is True
        assert port.dop_active is False
        _assert_handover_started(
            session,
            playback,
            predecessor_execution=predecessor_execution,
            predecessor_plan=predecessor_plan,
            target_family="dsd_pcm",
        )

        events = [(event.family, event.state) for event in truth.output_family_events]
        assert ("dop", OutputFamilyState.RUNNING) in events
        assert ("dop", OutputFamilyState.RELEASED) in events

        playback.stop()
        assert session.state is OutputSessionState.IDLE
        assert port.dsd_pcm_active is False
    finally:
        supervisor.close()
