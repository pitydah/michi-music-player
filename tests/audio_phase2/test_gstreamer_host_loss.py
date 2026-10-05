"""Host-loss convergence tests: Direct truth, termination honesty, restart.

A dead host is an infrastructure loss: playback must converge honestly, the
Direct executor must not keep stale runtime truth, closure must be bounded
and retryable, and a fresh host must start on the NEXT explicit open — never
an automatic audio resume.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

import pytest

from michi.application.ports import AudioTransportUnavailableError
from michi.domain.signal_truth import SignalTruthRecorder
from michi.infrastructure.audio_engines.gstreamer_host_client import (
    EXITED_BEFORE,
    GRACEFUL,
    GStreamerHostSupervisor,
)
from michi.infrastructure.audio_engines.gstreamer_host_port import (
    GStreamerHostedAudioPort,
)
from michi.infrastructure.audio_engines.providers import (
    GStreamerHostedEngineProvider,
)
from michi.infrastructure.audio_output.direct_output_executor import (
    DirectExecutionState,
    GStreamerDirectOutputExecutor,
)


def _plan(plan_id: str = "plan:direct", rate: int = 96000):
    from michi.domain.audio_device import AudioDeviceBinding, BindingKind
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.audio_output import (
        FallbackKind,
        GstSinkSpec,
        OutputPlan,
        PathSemantics,
        VolumePolicy,
    )

    binding = AudioDeviceBinding(
        kind=BindingKind.ALSA_PCM,
        locator="hw:CARD=DX5,DEV=0",
        generation=1,
        currently_available=True,
        card_index=1,
        pcm_device=0,
    )
    return OutputPlan(
        plan_id=plan_id,
        stable_device_id="usb:test",
        binding=binding,
        path_semantics=PathSemantics.HARDWARE_RAW,
        requested_pcm=PcmTuple(rate, "S32_LE", 2, 24),
        engine_id="gstreamer",
        volume_policy=VolumePolicy.FIXED,
        allow_resample=False,
        allow_remix=False,
        allow_processing=False,
        fallback=FallbackKind.STOP,
        sink=GstSinkSpec(factory="alsasink", device="hw:CARD=DX5,DEV=0"),
        resync_delay_ms=0,
        preconditions=("engine_gstreamer_direct",),
        evidence_refs=("probe:1",),
        decision_codes=("ENGINE_GSTREAMER_DIRECT",),
    )


FAKE_HOST = Path(__file__).parent / "gst_host_engine_fake.py"
FAST = {
    "start_timeout_s": 1.5,
    "command_timeout_s": 1.0,
    "terminate_grace_s": 0.4,
    "term_grace_s": 0.3,
    "kill_grace_s": 0.5,
}


def _command_factory(behavior: str):
    def factory(fd: int) -> list[str]:
        return [
            sys.executable,
            str(FAKE_HOST),
            "--fd",
            str(fd),
            "--engine-behavior",
            behavior,
        ]

    return factory


def _supervisor(behavior: str) -> GStreamerHostSupervisor:
    return GStreamerHostSupervisor(command_factory=_command_factory(behavior), **FAST)


def test_host_loss_after_commit_invalidates_direct_truth_on_close() -> None:
    supervisor = _supervisor("crash_on_stop")
    recorder = SignalTruthRecorder()
    executor = GStreamerDirectOutputExecutor(signal_truth=recorder)
    port = GStreamerHostedAudioPort(
        supervisor,
        command_deadline_s=FAST["command_timeout_s"],
        load_deadline_s=FAST["command_timeout_s"],
        direct_executor=executor,
    )
    executor.bind_port_provider(lambda: port)
    try:
        port.activate()
        receipt = executor.prepare(_plan())
        port.play()  # real Direct verification through the host
        executor.commit(receipt)
        assert executor.state is DirectExecutionState.COMMITTED
        assert recorder.active_snapshot is not None

        with pytest.raises(AudioTransportUnavailableError):
            port.stop()  # the child process dies mid-command
        # The reader thread observes the process death; bounded wait for the
        # owner-thread loss commit.
        deadline = time.monotonic() + 3.0
        active = None
        while time.monotonic() < deadline:
            port.dispatch_pending()
            active = recorder.active_snapshot
            if active is not None and any(
                "host lost" in anomaly.detail for anomaly in active.anomalies
            ):
                break
            time.sleep(0.02)
        assert active is not None
        assert any("host lost" in anomaly.detail for anomaly in active.anomalies), (
            "host loss must be recorded as a runtime anomaly"
        )
    finally:
        port.close()
    # Exactly the in-process semantics: loss is an anomaly; close terminates
    # the execution and retires the active truth. Nothing stays COMPLETE.
    assert executor.state is DirectExecutionState.IDLE
    assert recorder.active_snapshot is None
    assert recorder.last_snapshot is not None
    assert supervisor.termination_kind == EXITED_BEFORE  # never called graceful


def test_crash_during_shutdown_is_not_reported_as_graceful() -> None:
    supervisor = _supervisor("crash_on_close")
    port = GStreamerHostedAudioPort(supervisor, command_deadline_s=0.5)
    try:
        port.activate()
        port.close()
    finally:
        supervisor.close()
    assert port.termination_kind == EXITED_BEFORE
    assert not supervisor.pid_alive()


def test_close_after_external_kill_is_bounded_and_retryable() -> None:
    supervisor = _supervisor("normal")
    port = GStreamerHostedAudioPort(supervisor, command_deadline_s=1.0)
    try:
        port.activate()
        pid = supervisor.pid
        assert pid is not None
        os.kill(pid, signal.SIGKILL)
        deadline = time.monotonic() + 3.0
        while supervisor.pid_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        port.close()
        port.close()  # idempotent after loss
    finally:
        supervisor.close()
    assert not supervisor.pid_alive()


def test_restart_after_loss_is_a_fresh_host_and_never_autoplays() -> None:
    provider = GStreamerHostedEngineProvider(
        supervisor_factory=lambda: _supervisor("normal")
    )
    try:
        provider.open()
        first_supervisor = provider.current_supervisor
        assert first_supervisor is not None
        first_pid = first_supervisor.pid
        assert first_pid is not None
        os.kill(first_pid, signal.SIGKILL)
        deadline = time.monotonic() + 3.0
        while first_supervisor.pid_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        provider.close()

        # Recovery is explicit: a NEW open creates a fresh supervised host.
        second_port = provider.open()
        try:
            assert isinstance(second_port, GStreamerHostedAudioPort)
            second_supervisor = provider.current_supervisor
            assert second_supervisor is not None
            assert second_supervisor.pid != first_pid
            assert second_supervisor.pid_alive()
            # The port issues no playback command by itself: recovery never
            # resumes audio. A fresh load + play is an explicit caller action.
            assert second_port.backend_state() is None
        finally:
            provider.close()
        assert provider.current_port is None
    finally:
        provider.close()
    assert first_supervisor.termination_kind in (EXITED_BEFORE, GRACEFUL)


def test_direct_without_signal_truth_still_closes_cleanly() -> None:
    supervisor = _supervisor("normal")
    executor = GStreamerDirectOutputExecutor()
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=1.0, direct_executor=executor
    )
    executor.bind_port_provider(lambda: port)
    try:
        port.activate()
        executor.prepare(_plan())
        port.play()
    finally:
        port.close()
    assert executor.state is DirectExecutionState.IDLE
