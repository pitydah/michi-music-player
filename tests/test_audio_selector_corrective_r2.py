"""AUDIO ENGINE SELECTOR CORRECTIVE SEAL R2 falsification gates."""

from pathlib import Path

import pytest

from michi.application.audio_engine_selection import (
    EngineSelectionAction,
    EngineSwitchBlocker,
    MediaRequestTerminalStatus,
)
from michi.application.playback_service import EngineSwitchLeaseHeldError
from michi.domain.audio_engine import AudioEngineId
from michi.domain.playback import PlaybackStatus
from tests.test_m11_3f_engine_selection import make_harness


def _accepted_playback(h, status: PlaybackStatus, position_ms: int = 45_000):
    path = Path("/music/current.flac")
    h.playback.load_and_play(path)
    h.router.bound_port.emit_media_accepted(path)
    h.playback.update_position(position_ms)
    h.router.bound_port.emit_playback_state(status)
    assert h.playback.state.status is status
    return path


@pytest.mark.parametrize(
    "status", [PlaybackStatus.STOPPED, PlaybackStatus.PAUSED, PlaybackStatus.PLAYING]
)
def test_preference_only_never_churns_active_runtime(status):
    h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.MPD)
    path = (
        _accepted_playback(h, status) if status is not PlaybackStatus.STOPPED else None
    )
    if status is PlaybackStatus.STOPPED:
        path = _accepted_playback(h, PlaybackStatus.PLAYING)
        h.playback.stop()
        h.playback.update_position(45_000)
    h.settings.set_audio_engine(AudioEngineId.MPD)
    h.service.restore_selected(AudioEngineId.MPD)
    h.service.mark_fallback_ready(
        AudioEngineId.QT_MULTIMEDIA, AudioEngineId.MPD, "fallback"
    )
    qt = h.providers[AudioEngineId.QT_MULTIMEDIA]
    bound = h.router.bound_port
    before = (qt.open_count, qt.close_count, tuple(bound.events))

    plan = h.coordinator.selection_plan(AudioEngineId.QT_MULTIMEDIA)
    assert plan.action is EngineSelectionAction.PREFERENCE_ONLY
    assert plan.allowed is True
    h.coordinator.switch_to(AudioEngineId.QT_MULTIMEDIA)

    assert h.settings.state.audio_engine_id is AudioEngineId.QT_MULTIMEDIA
    assert h.service.state.selected_engine_id is AudioEngineId.QT_MULTIMEDIA
    assert h.service.state.active_engine_id is AudioEngineId.QT_MULTIMEDIA
    assert h.router.bound_port is bound
    assert (qt.open_count, qt.close_count, tuple(bound.events)) == before
    assert h.playback.state.status is status
    assert h.playback.state.position_ms == 45_000
    assert h.playback.state.file_path == path


def test_plan_matrix_distinguishes_noop_runtime_retry_and_unavailable():
    h = make_harness(
        AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER, AudioEngineId.MPD
    )
    assert (
        h.coordinator.selection_plan(AudioEngineId.QT_MULTIMEDIA).action
        is EngineSelectionAction.NOOP
    )
    assert (
        h.coordinator.selection_plan(AudioEngineId.GSTREAMER).action
        is EngineSelectionAction.RUNTIME_SWITCH
    )

    h.settings.set_audio_engine(AudioEngineId.MPD)
    h.service.restore_selected(AudioEngineId.MPD)
    h.service.mark_fallback_ready(
        AudioEngineId.QT_MULTIMEDIA, AudioEngineId.MPD, "fallback"
    )
    assert (
        h.coordinator.selection_plan(AudioEngineId.MPD).action
        is EngineSelectionAction.RETRY_PREFERRED
    )

    h.providers[AudioEngineId.GSTREAMER]._available = False
    unavailable = h.coordinator.selection_plan(AudioEngineId.GSTREAMER)
    assert unavailable.action is EngineSelectionAction.UNAVAILABLE
    assert unavailable.allowed is False
    assert unavailable.blocker is EngineSwitchBlocker.RUNTIME_UNAVAILABLE


@pytest.mark.parametrize("status", [PlaybackStatus.PLAYING, PlaybackStatus.PAUSED])
def test_runtime_switch_preserves_position_and_ends_stopped(status):
    h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.MPD)
    path = _accepted_playback(h, status, 273_000)
    old_port = h.router.bound_port

    h.coordinator.switch_to(AudioEngineId.MPD)

    target = h.router.bound_port
    assert target is not old_port
    assert h.service.state.active_engine_id is AudioEngineId.MPD
    assert h.playback.state.status is PlaybackStatus.STOPPED
    assert h.playback.state.file_path == path
    assert "play" not in target.events
    assert f"load:{path}" in target.events
    target.emit_media_accepted(path)
    assert "seek:273000" in target.events
    assert h.playback.engine_switch_resume_target_ms == 273_000
    assert (
        h.playback.last_engine_switch_rehydration.status
        is MediaRequestTerminalStatus.ACCEPTED
    )


@pytest.mark.parametrize("operation", ["stop", "seek", "play", "load_and_play"])
def test_reentrant_transport_commands_cannot_change_atomic_snapshot(operation):
    h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
    path = _accepted_playback(h, PlaybackStatus.PLAYING, 45_000)
    rejected = []

    def observer():
        if h.service.state.switching_to is not AudioEngineId.GSTREAMER:
            return
        try:
            if operation == "stop":
                h.playback.stop()
            elif operation == "seek":
                h.playback.seek(99_000)
            elif operation == "play":
                h.playback.play()
            else:
                h.playback.load_and_play(Path("/music/sneaky.flac"))
        except EngineSwitchLeaseHeldError:
            rejected.append(operation)

    h.service.subscribe_changed(observer)
    h.coordinator.switch_to(AudioEngineId.GSTREAMER)
    target = h.router.bound_port
    target.emit_media_accepted(path)

    assert rejected
    assert "seek:45000" in target.events
    assert "seek:99000" not in target.events
    assert h.playback.state.file_path == path


def test_user_request_pending_has_typed_blocker_but_playing_does_not():
    h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
    h.playback.load_and_play(Path("/music/pending.flac"))
    readiness = h.playback.engine_switch_readiness()
    assert readiness.allowed is False
    assert readiness.blocker is EngineSwitchBlocker.USER_MEDIA_REQUEST_PENDING

    h.router.bound_port.emit_media_accepted(Path("/music/pending.flac"))
    h.router.bound_port.emit_playback_state(PlaybackStatus.PLAYING)
    assert h.playback.engine_switch_readiness().allowed is True


def test_rehydration_rejection_is_terminal_and_releases_transport_commands():
    h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
    path = _accepted_playback(h, PlaybackStatus.PLAYING)

    h.coordinator.switch_to(AudioEngineId.GSTREAMER)
    with pytest.raises(EngineSwitchLeaseHeldError):
        h.playback.play()

    h.router.bound_port.emit_media_rejected(path, "decoder rejected media")

    assert (
        h.playback.last_engine_switch_rehydration.status
        is MediaRequestTerminalStatus.REJECTED
    )
    assert h.playback.engine_switch_readiness().allowed is True
    h.playback.play()  # authority was released; canonical reload may proceed


def test_rehydration_timeout_is_terminal_without_polling_or_sleep():
    h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
    path = _accepted_playback(h, PlaybackStatus.PAUSED)
    scheduled = []
    h.playback.set_engine_switch_timeout_scheduler(
        lambda _timeout_ms, callback: scheduled.append(callback), timeout_ms=25
    )

    h.coordinator.switch_to(AudioEngineId.GSTREAMER)
    assert len(scheduled) == 1
    with pytest.raises(EngineSwitchLeaseHeldError):
        h.playback.seek(99_000)

    scheduled.pop()()

    terminal = h.playback.last_engine_switch_rehydration
    assert terminal.status is MediaRequestTerminalStatus.TIMEOUT
    assert terminal.file_path == str(path)
    assert h.playback.state.status is PlaybackStatus.STOPPED
    assert "Timed out" in h.playback.state.error_message
    assert h.playback.engine_switch_readiness().allowed is True


def test_new_switch_supersedes_only_old_engine_rehydration():
    h = make_harness(
        AudioEngineId.QT_MULTIMEDIA,
        AudioEngineId.GSTREAMER,
        AudioEngineId.MPD,
    )
    path = _accepted_playback(h, PlaybackStatus.PLAYING, 78_000)

    h.coordinator.switch_to(AudioEngineId.GSTREAMER)
    stale_port = h.router.bound_port
    h.coordinator.switch_to(AudioEngineId.MPD)

    assert h.playback.last_engine_switch_rehydration.status is (
        MediaRequestTerminalStatus.CANCELLED
    )
    stale_port.emit_media_accepted(path)
    assert h.playback.last_engine_switch_rehydration.status is (
        MediaRequestTerminalStatus.CANCELLED
    )
    h.router.bound_port.emit_media_accepted(path)
    assert h.playback.last_engine_switch_rehydration.status is (
        MediaRequestTerminalStatus.ACCEPTED
    )
    assert h.playback.state.position_ms == 78_000


def test_controlled_stop_failure_aborts_before_detach_and_clears_switch_intent():
    h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
    _accepted_playback(h, PlaybackStatus.PLAYING)
    source = h.router.bound_port

    def fail_stop():
        raise RuntimeError("stop refused")

    source.stop = fail_stop
    with pytest.raises(RuntimeError, match="stop refused"):
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)

    assert h.router.bound_port is source
    assert h.providers[AudioEngineId.QT_MULTIMEDIA].close_count == 0
    assert h.providers[AudioEngineId.GSTREAMER].open_count == 0
    assert h.settings.state.audio_engine_id is AudioEngineId.QT_MULTIMEDIA
    assert h.service.state.selected_engine_id is AudioEngineId.QT_MULTIMEDIA
    assert h.service.state.switching_to is None


def test_runtime_loss_terminalizes_pending_rehydration_and_releases_lease():
    h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
    _accepted_playback(h, PlaybackStatus.PLAYING)
    h.coordinator.switch_to(AudioEngineId.GSTREAMER)

    h.playback.converge_after_engine_loss("engine disappeared")

    terminal = h.playback.last_engine_switch_rehydration
    assert terminal.status is MediaRequestTerminalStatus.REJECTED
    assert terminal.message == "engine disappeared"
    assert h.playback.engine_switch_readiness().allowed is True


def test_probe_exception_maps_to_typed_unavailable_plan():
    h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)

    def fail_probe():
        raise RuntimeError("probe crashed")

    h.providers[AudioEngineId.GSTREAMER].probe = fail_probe
    plan = h.coordinator.selection_plan(AudioEngineId.GSTREAMER)

    assert plan.action is EngineSelectionAction.UNAVAILABLE
    assert plan.blocker is EngineSwitchBlocker.RUNTIME_UNAVAILABLE
    assert "probe crashed" in plan.blocker_detail
