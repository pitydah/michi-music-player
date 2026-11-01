"""AP2-F10 S13 — release truth and attempt isolation at the Playback boundary.

A dispatched release command is not a confirmed release. While the exact
predecessor identity is still live, Playback must not publish a fictional
STOPPED; and an unconfirmed ownership must block new acquisitions until the
owner reconciles it.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from michi.application.audio_family_transition import (
    AudioFamily,
    AudioFamilyTransitionService,
    FamilyTransitionRequest,
    ReleaseTruth,
    TransitionError,
)
from michi.application.audio_family_transition import (
    PlaybackStatus as TransitionPlaybackStatus,
)
from michi.application.audio_output_planner import OutputPlanner
from michi.application.output_session_service import (
    HandoverState,
    OutputRequest,
    OutputSessionService,
)
from michi.application.playback_service import PlaybackService
from michi.domain.audio_output import OutputSessionState
from michi.domain.playback import PlaybackStatus
from tests.audio_phase2.test_owner_safe_handover import (
    _Deferred,
    _dsd_pcm_plan,
    _session,
    _Tx,
)
from tests.dop.test_dop_planner import _plan as _dop_plan


class _RejectingTx(_Tx):
    """The host refuses the release and keeps the predecessor active."""

    def dop_abort(self, prepared, reason: str) -> dict[str, Any]:
        self.aborted.append(("dop", prepared.execution_id, reason))
        return {"aborted": False, "stale": False}


class _FailingTargetTx(_Tx):
    def dsd_pcm_prepare(self, plan, path: Path, instance: str):
        raise RuntimeError("target failed after a confirmed release")


def _requests() -> dict[str, OutputRequest]:
    dop_one = _dop_plan(execution_id="exec:1")
    dsd_plan = _dsd_pcm_plan()
    return {
        "predecessor.dsf": OutputRequest.dop(dop_one, "profile:dop"),
        "target.dsf": OutputRequest.dsd_to_pcm(
            dsd_plan, dsd_plan.stable_device_id, "profile:dsd"
        ),
    }


def test_rejected_release_keeps_playing_and_never_prepares_the_target(
    tmp_path: Path, fake_audio
) -> None:
    tx = _RejectingTx()
    deferred = _Deferred()
    session = _session(_requests(), tx, deferred)
    session.prepare_for_media(tmp_path / "predecessor.dsf")
    assert session.dop_active is True

    playback = PlaybackService(fake_audio, output_tx=session)
    playback._state.status = PlaybackStatus.PLAYING
    playback._state.file_path = tmp_path / "predecessor.dsf"
    playback._intent = True
    playback._accepted = True
    rejected: list[tuple[Path, str]] = []

    playback.load_and_play(
        tmp_path / "target.dsf",
        on_rejected=lambda path, reason: rejected.append((path, reason)),
    )
    deferred.drive()

    assert tx.aborted == [("dop", "exec:1", "handover_to_dsd_pcm")]
    assert tx.dsd_pcm_prepare_calls == 0
    assert session.handover_release_truth is ReleaseTruth.OWNERSHIP_UNCERTAIN
    assert session.handover_release_confirmed is False
    assert session.handover_ownership_uncertain is True
    assert session.handover_predecessor_active is True
    assert session.dop_active is True
    assert session.handover_state is HandoverState.OWNERSHIP_UNCONFIRMED
    # Playback must not turn a still-live predecessor into a fictional stop.
    assert playback.state.status is PlaybackStatus.PLAYING
    assert playback._accepted is True
    assert playback._intent is True
    assert rejected


def test_uncertain_ownership_blocks_the_next_acquisition(
    tmp_path: Path, fake_audio
) -> None:
    tx = _RejectingTx()
    deferred = _Deferred()
    session = _session(_requests(), tx, deferred)
    session.prepare_for_media(tmp_path / "predecessor.dsf")
    playback = PlaybackService(fake_audio, output_tx=session)
    playback._state.status = PlaybackStatus.PLAYING
    playback.load_and_play(tmp_path / "target.dsf")
    deferred.drive()

    tokens: list[str] = []
    failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "target.dsf", tokens.append, failures.append
    )
    assert deferred.pending == []
    assert tokens == []
    assert [getattr(error, "code", None) for error in failures] == [
        "OUTPUT_OWNERSHIP_UNCONFIRMED"
    ]
    assert session.dop_active is True


def test_confirmed_release_then_target_failure_never_restores(
    tmp_path: Path, fake_audio
) -> None:
    tx = _FailingTargetTx()
    deferred = _Deferred()
    session = _session(_requests(), tx, deferred)
    session.prepare_for_media(tmp_path / "predecessor.dsf")

    playback = PlaybackService(fake_audio, output_tx=session)
    playback._state.status = PlaybackStatus.PLAYING
    playback._state.file_path = tmp_path / "predecessor.dsf"
    playback._intent = True
    playback._accepted = True
    playback.load_and_play(tmp_path / "target.dsf")
    deferred.drive()

    assert session.handover_release_truth is ReleaseTruth.RELEASE_CONFIRMED
    assert session.handover_release_confirmed is True
    assert session.dop_active is False
    assert session.handover_state is HandoverState.FAILED
    assert playback.state.status is PlaybackStatus.STOPPED
    assert playback._intent is False
    assert playback._accepted is False


def test_zero_generations_are_valid_exact_release_identity() -> None:
    service = AudioFamilyTransitionService()
    request = FamilyTransitionRequest(
        media_identity="track:zero",
        source_family=AudioFamily.DOP,
        target_family=AudioFamily.DSD_TO_PCM,
        predecessor_status=TransitionPlaybackStatus.PLAYING,
        request_epoch=2,
        current_epoch=1,
        output_generation=0,
        processing_generation=0,
        binding_generation=0,
        destructive_boundary=True,
        plan_id="plan:zero",
        execution_id="exec:zero",
        stable_device_id="dev:zero",
        host_generation=0,
    )
    receipt = service.plan(request)
    evidence = {
        "confirmed": True,
        "terminal_state": "RELEASED",
        "provenance": "SUPERVISED_HOST",
        "plan_id": "plan:zero",
        "execution_id": "exec:zero",
        "stable_device_id": "dev:zero",
        "binding_generation": 0,
        "host_generation": 0,
    }
    released = service.mark_released(receipt, evidence)
    assert released.predecessor_released is True
    with pytest.raises(TransitionError, match="host_generation"):
        service.mark_released(receipt, {**evidence, "host_generation": "0"})
    with pytest.raises(TransitionError, match="binding_generation"):
        service.mark_released(receipt, {**evidence, "binding_generation": None})


def test_receipt_match_accepts_zero_and_rejects_foreign_generations() -> None:
    session = OutputSessionService(OutputPlanner())
    snapshot = SimpleNamespace(
        plan_id="plan:zero",
        execution_id="exec:zero",
        stable_device_id="dev:zero",
        device="hw:0,0",
        binding_generation=0,
        host_generation=0,
    )
    receipt = {
        "confirmed": True,
        "terminal_state": "RELEASED",
        "provenance": "SUPERVISED_HOST",
        "plan_id": "plan:zero",
        "execution_id": "exec:zero",
        "stable_device_id": "dev:zero",
        "device": "hw:0,0",
        "binding_generation": 0,
        "host_generation": 0,
    }
    assert session._handover_receipt_matches(snapshot, receipt) is True
    assert (
        session._handover_receipt_matches(snapshot, {**receipt, "host_generation": 1})
        is False
    )
    assert (
        session._handover_receipt_matches(snapshot, {**receipt, "host_generation": "0"})
        is False
    )
    assert (
        session._handover_receipt_matches(
            snapshot, {**receipt, "binding_generation": "0"}
        )
        is False
    )


def test_late_stale_release_completion_never_marks_the_new_attempt(
    tmp_path: Path,
) -> None:
    dop_one = _dop_plan(execution_id="exec:1")
    dop_two = _dop_plan(execution_id="exec:2")
    dsd_plan = _dsd_pcm_plan()
    requests = {
        "predecessor.dsf": OutputRequest.dop(dop_one, "profile:dop"),
        "a.dsf": OutputRequest.dsd_to_pcm(
            dsd_plan, dsd_plan.stable_device_id, "profile:dsd"
        ),
        "b.dsf": OutputRequest.dop(dop_two, "profile:dop"),
    }
    tx = _Tx()
    deferred = _Deferred()
    session = _session(requests, tx, deferred)
    session.prepare_for_media(tmp_path / "predecessor.dsf")

    a_tokens: list[str] = []
    a_failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "a.dsf", a_tokens.append, a_failures.append
    )
    deferred.run_one()  # A characterization; submits A release
    a_attempt = session.handover_attempt_id
    assert a_attempt is not None

    b_tokens: list[str] = []
    b_failures: list[Exception] = []
    session.prepare_for_media_async(
        tmp_path / "b.dsf", b_tokens.append, b_failures.append
    )
    deferred.run_one()  # late A release completion
    assert session.handover_state is not HandoverState.SUPERSEDED
    deferred.drive()

    assert b_failures == []
    assert len(b_tokens) == 1
    assert session.handover_state is HandoverState.READY
    assert session.handover_attempt_id != a_attempt
    assert session._dop_prepared is not None
    assert session._dop_prepared.execution_id == "exec:2"
    assert session.state is OutputSessionState.READY
