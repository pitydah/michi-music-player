"""AP2-F08 — PlaybackService + OutputSessionService Native DSD flow."""

from __future__ import annotations

from pathlib import Path

from michi.application.audio_output_planner import OutputPlanner
from michi.application.output_session_service import (
    NativeDsdSessionPrepared,
    OutputRequest,
    OutputSessionService,
)
from michi.application.playback_service import PlaybackService
from michi.domain.audio_output import OutputSessionState
from michi.domain.playback import PlaybackStatus
from tests.audio_phase2.test_native_dsd_output_session import DEVICE, _plan


class _Provider:
    def __init__(self, plan) -> None:
        self.plan = plan

    def __call__(self, path: Path) -> OutputRequest:
        return OutputRequest.native_dsd(self.plan, DEVICE, "profile:direct")


class _NativeCallbacks:
    def __init__(self) -> None:
        self.committed = 0
        self.stopped = 0

    def prepare(self, plan, path, instance_id):
        return NativeDsdSessionPrepared(
            plan=plan,
            execution_id=plan.execution_id,
            stable_device_id=plan.stable_device_id,
            runtime_identity={},
            evidence_refs=plan.evidence_refs,
            handle=object(),
        )

    def commit(self, prepared):
        self.committed += 1

    def abort(self, prepared, reason):
        return {"aborted": True}

    def stop(self, prepared, reason):
        self.stopped += 1
        return {"released": True}


class _FakeAudio:
    def __init__(self) -> None:
        self.accepted = None
        self.rejected = None
        self.state_cb = None
        self.eom = None
        self.loads: list[Path] = []
        self.plays = 0
        self.fail_play = False

    def subscribe_media_accepted(self, callback):
        self.accepted = callback

    def subscribe_media_rejected(self, callback):
        self.rejected = callback

    def subscribe_playback_state_changed(self, callback):
        self.state_cb = callback

    def subscribe_end_of_media(self, callback):
        self.eom = callback

    def load(self, path):
        self.loads.append(Path(path))
        assert self.accepted is not None
        self.accepted(Path(path))

    def play(self):
        self.plays += 1
        if self.fail_play:
            raise RuntimeError("host START failed")

    def pause(self):
        assert self.state_cb is not None
        self.state_cb(PlaybackStatus.PAUSED)

    def resume(self):
        assert self.state_cb is not None
        self.state_cb(PlaybackStatus.PLAYING)

    def stop(self):
        assert self.state_cb is not None
        self.state_cb(PlaybackStatus.STOPPED)

    def seek(self, position_ms):
        raise AssertionError("Native DSD seek must not reach the transport")

    def position(self):
        return 0

    def duration(self):
        return 0


class _FakeVolume:
    def synchronize(self):
        raise AssertionError("Native DSD must skip PCM volume synchronization")


def test_native_dsd_reaches_playing_through_playback_service() -> None:
    plan = _plan()
    callbacks = _NativeCallbacks()
    session = OutputSessionService(
        OutputPlanner(),
        request_provider=_Provider(plan),
        async_submit=None,
        native_dsd_prepare=callbacks.prepare,
        native_dsd_commit=callbacks.commit,
        native_dsd_abort=callbacks.abort,
        native_dsd_stop=callbacks.stop,
        native_dsd_plan_still_current=lambda _plan: True,
    )
    audio = _FakeAudio()
    playback = PlaybackService(
        audio,
        volume_port=_FakeVolume(),
        output_tx=session,
    )
    path = Path("/tmp/native.dsf")
    accepted: list[Path] = []
    playback.load_and_play(path, on_accepted=accepted.append)

    assert accepted == [path]
    assert audio.loads == [path]  # canonical load entry, no PCM pipeline
    assert audio.plays == 1
    assert session.mode == "native_dsd"
    assert session.state is OutputSessionState.RUNNING
    assert session.native_dsd_active is True
    assert callbacks.committed == 1
    assert audio.state_cb is not None
    audio.state_cb(PlaybackStatus.PLAYING)
    assert playback.state.status is PlaybackStatus.PLAYING

    playback.stop()
    assert session.state is OutputSessionState.IDLE
    assert callbacks.stopped == 1


def test_start_failure_compensates_the_committed_native_execution() -> None:
    plan = _plan()
    callbacks = _NativeCallbacks()
    session = OutputSessionService(
        OutputPlanner(),
        request_provider=_Provider(plan),
        async_submit=None,
        native_dsd_prepare=callbacks.prepare,
        native_dsd_commit=callbacks.commit,
        native_dsd_abort=callbacks.abort,
        native_dsd_stop=callbacks.stop,
        native_dsd_plan_still_current=lambda _plan: True,
    )
    audio = _FakeAudio()
    audio.fail_play = True
    playback = PlaybackService(audio, volume_port=_FakeVolume(), output_tx=session)
    path = Path("/tmp/native.dsf")
    import pytest

    with pytest.raises(RuntimeError):
        playback.load_and_play(path)
    assert session.native_dsd_active is False
    assert session.state is OutputSessionState.IDLE
    assert playback.state.status is PlaybackStatus.STOPPED


def test_native_device_loss_converges_without_autoplay() -> None:
    from michi.application.audio_device_registry import AudioDeviceTopologyChange
    from michi.application.direct_output_lifecycle_coordinator import (
        DirectOutputLifecycleCoordinator,
    )
    from michi.domain.playback import PlaybackStatus

    class _Registry:
        def generation_for(self, stable_device_id):
            return 1

        def available_ids(self):
            return set()

        def subscribe_topology_changed(self, callback):
            return None

        def unsubscribe_topology_changed(self, callback):
            return None

    plan = _plan()
    callbacks = _NativeCallbacks()
    session = OutputSessionService(
        OutputPlanner(),
        request_provider=_Provider(plan),
        async_submit=None,
        native_dsd_prepare=callbacks.prepare,
        native_dsd_commit=callbacks.commit,
        native_dsd_abort=callbacks.abort,
        native_dsd_stop=callbacks.stop,
        native_dsd_plan_still_current=lambda _plan: True,
    )
    audio = _FakeAudio()
    playback = PlaybackService(audio, volume_port=_FakeVolume(), output_tx=session)
    coordinator = DirectOutputLifecycleCoordinator(_Registry(), playback, session)
    coordinator.start()
    path = Path("/tmp/native-lost.dsf")
    playback.load_and_play(path)
    audio.state_cb(PlaybackStatus.PLAYING)
    assert session.native_dsd_active is True

    coordinator.handle_topology_changed(
        AudioDeviceTopologyChange(
            stable_device_id=plan.stable_device_id,
            previous_available=True,
            current_available=False,
            previous_generation=1,
            current_generation=1,
            previous_bindings=(),
            current_bindings=(),
        )
    )
    assert playback.state.status is PlaybackStatus.STOPPED
    assert session.native_dsd_active is False
    assert session.state in (OutputSessionState.LOST, OutputSessionState.IDLE)
    assert callbacks.stopped == 0  # loss, not a forged confirmed release
    assert callbacks.stopped == 0


def test_cleanup_failure_does_not_block_playback_convergence() -> None:
    plan = _plan()
    callbacks = _NativeCallbacks()
    session = OutputSessionService(
        OutputPlanner(),
        request_provider=_Provider(plan),
        async_submit=None,
        native_dsd_prepare=callbacks.prepare,
        native_dsd_commit=callbacks.commit,
        native_dsd_abort=callbacks.abort,
        native_dsd_stop=callbacks.stop,
        native_dsd_plan_still_current=lambda _plan: True,
    )
    audio = _FakeAudio()
    audio.fail_play = True
    playback = PlaybackService(audio, volume_port=_FakeVolume(), output_tx=session)

    def _fail_abort(_prepared, _reason):
        raise RuntimeError("abort transport down")

    session._native_dsd_abort = _fail_abort
    path = Path("/tmp/native-cleanup-fail.dsf")
    import pytest

    with pytest.raises(RuntimeError, match="host START failed"):
        playback.load_and_play(path)
    assert playback.state.status is PlaybackStatus.STOPPED
    assert session.native_dsd_active is False
    assert session._native_dsd_prepared is not None  # cleanup is not faked
    assert session.state is OutputSessionState.RELEASING
