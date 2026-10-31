"""AP2-F10 — PlaybackService invokes the family transition planner."""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.application.audio_family_transition import (
    AudioFamily,
    AudioFamilyTransitionService,
    FamilyTransitionRequest,
    PlaybackStatus,
    TransitionPhase,
)
from michi.application.playback_service import PlaybackService
from michi.domain.playback import PlaybackStatus as DomainPlaybackStatus


class _Output:
    def __init__(
        self,
        *,
        evidence: dict | None = None,
        reject: bool = False,
        source: AudioFamily = AudioFamily.DSD_TO_PCM,
        target: AudioFamily = AudioFamily.DOP,
    ) -> None:
        self.current_family = target
        self.source_family = source
        self.last_release_evidence = evidence
        self.reject = reject
        self.aborted: list[str] = []
        self.committed: list[str] = []
        self.dsd_pcm_active = True
        self.native_dsd_active = False
        self.dop_active = False

    def transition_snapshot(self):
        return {
            "family": self.source_family,
            "state": "running",
            "generation": 7,
            "plan_id": "plan:source",
            "execution_id": "exec:source",
            "stable_device_id": "dev:test",
            "binding_generation": 3,
            "host_generation": 5,
            "processing_generation": 2,
        }

    def prepare_for_media_async(self, path, prepared, failed) -> None:
        if self.reject:
            failed(RuntimeError("target rejected"))
        else:
            prepared("tok:target")

    def abort_media(self, token, reason) -> None:
        self.aborted.append(token)

    def commit_media(self, token, path) -> None:
        self.committed.append(token)


def _receipt() -> dict:
    return {
        "confirmed": True,
        "terminal_state": "RELEASED",
        "provenance": "SUPERVISED_HOST",
        "plan_id": "plan:source",
        "execution_id": "exec:source",
        "stable_device_id": "dev:test",
        "binding_generation": 3,
        "host_generation": 5,
    }


def test_playback_marks_dsd_to_dop_transition_with_exact_receipt():
    from tests.conftest import FakeAudioPort

    output = _Output(evidence=_receipt())
    playback = PlaybackService(FakeAudioPort(), volume_port=object(), output_tx=output)
    accepted: list[Path] = []
    path = Path("/tmp/transition.dsf")
    playback.load_and_play(path, on_accepted=accepted.append)
    assert accepted == [path]
    assert output.committed == ["tok:target"]
    assert len(playback.family_transition_receipts) == 1
    receipt = playback.family_transition_receipts[0]
    assert receipt.predecessor_released is True
    assert receipt.source_family is AudioFamily.DSD_TO_PCM
    assert receipt.target_family is AudioFamily.DOP


def test_playback_rejects_target_when_release_receipt_is_missing():
    from tests.conftest import FakeAudioPort

    output = _Output(evidence=None)
    playback = PlaybackService(FakeAudioPort(), volume_port=object(), output_tx=output)
    accepted: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    playback.load_and_play(
        Path("/tmp/transition.dsf"),
        on_accepted=accepted.append,
        on_rejected=lambda path, reason: rejected.append((path, reason)),
    )
    assert accepted == []
    assert output.aborted == ["tok:target"]
    assert rejected
    # The receipt proves the destructive boundary was NOT crossed with
    # confirmed evidence: ownership is explicitly unconfirmed, never a
    # fabricated complete transition.
    assert [receipt.phase for receipt in playback.family_transition_receipts] == [
        TransitionPhase.OWNERSHIP_UNCONFIRMED
    ]


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (AudioFamily.PCM_DIRECT, AudioFamily.DSD_TO_PCM),
        (AudioFamily.DSD_TO_PCM, AudioFamily.PCM_DIRECT),
        (AudioFamily.PCM_MANAGED, AudioFamily.DSD_TO_PCM),
        (AudioFamily.DSD_TO_PCM, AudioFamily.PCM_MANAGED),
        (AudioFamily.NATIVE_DSD, AudioFamily.DSD_TO_PCM),
        (AudioFamily.DSD_TO_PCM, AudioFamily.NATIVE_DSD),
        (AudioFamily.DOP, AudioFamily.DSD_TO_PCM),
        (AudioFamily.DSD_TO_PCM, AudioFamily.DOP),
    ],
)
def test_playback_marks_all_family_directions_with_receipt(source, target):
    from tests.conftest import FakeAudioPort

    output = _Output(evidence=_receipt(), source=source, target=target)
    playback = PlaybackService(FakeAudioPort(), volume_port=object(), output_tx=output)
    accepted: list[Path] = []
    playback.load_and_play(Path("/tmp/transition.dsf"), on_accepted=accepted.append)
    assert accepted
    assert playback.family_transition_receipts
    receipt = playback.family_transition_receipts[-1]
    assert receipt.source_family is source
    assert receipt.target_family is target
    assert receipt.predecessor_released is True


def test_transition_receipt_phases_never_claim_completion_on_release():
    service = AudioFamilyTransitionService()
    request = FamilyTransitionRequest(
        media_identity="/tmp/track.dsf",
        source_family=AudioFamily.DOP,
        target_family=AudioFamily.DSD_TO_PCM,
        predecessor_status=PlaybackStatus.PLAYING,
        request_epoch=4,
        current_epoch=3,
        output_generation=7,
        processing_generation=2,
        binding_generation=3,
        destructive_boundary=True,
        plan_id="plan:source",
        execution_id="exec:source",
        stable_device_id="dev:test",
        host_generation=5,
    )
    planned = service.plan(request)
    assert planned.phase is TransitionPhase.PLANNED
    assert planned.predecessor_released is False

    released = service.mark_released(planned, _receipt())
    assert released.phase is TransitionPhase.PREDECESSOR_RELEASED
    assert released.predecessor_released is True
    assert released.resume_status is PlaybackStatus.PLAYING

    prepared = service.mark_prepared(released)
    assert prepared.phase is TransitionPhase.TARGET_PREPARED
    assert service.mark_started(prepared).phase is TransitionPhase.TARGET_STARTED
    assert service.mark_failed(prepared).phase is TransitionPhase.TARGET_FAILED


class _BoundaryOutput:
    """Async output transaction that fails AFTER crossing the boundary."""

    def __init__(self, *, boundary_crossed: bool) -> None:
        self.current_family = AudioFamily.DOP
        self.handover_boundary_crossed = boundary_crossed
        self.last_handover_release_evidence = None
        self.aborted: list[str] = []

    def transition_snapshot(self):
        return {
            "family": AudioFamily.DSD_TO_PCM,
            "state": "running",
            "generation": 9,
            "plan_id": "plan:source",
            "execution_id": "exec:source",
            "stable_device_id": "dev:test",
            "binding_generation": 3,
            "host_generation": 5,
            "processing_generation": 2,
        }

    def prepare_for_media_async(self, path, prepared, failed) -> None:
        from michi.application.output_session_service import OutputSessionError

        failed(OutputSessionError("DOP_OUTPUT_PREPARE_FAILED", "target failed"))

    def abort_media(self, token, reason) -> None:
        self.aborted.append(token)


def test_prepare_failure_after_release_never_restores_the_predecessor():
    from tests.conftest import FakeAudioPort

    output = _BoundaryOutput(boundary_crossed=True)
    playback = PlaybackService(FakeAudioPort(), volume_port=object(), output_tx=output)
    playback._intent = True
    playback._accepted = True

    rejected: list[tuple[Path, str]] = []
    playback.load_and_play(
        Path("/tmp/after-release.dsf"),
        on_rejected=lambda path, reason: rejected.append((path, reason)),
    )

    assert rejected
    assert playback._intent is False
    assert playback._accepted is False
    assert playback._state.status is DomainPlaybackStatus.STOPPED


def test_prepare_failure_before_release_restores_the_previous_intent():
    from tests.conftest import FakeAudioPort

    output = _BoundaryOutput(boundary_crossed=False)
    playback = PlaybackService(FakeAudioPort(), volume_port=object(), output_tx=output)
    playback._intent = True
    playback._accepted = True

    rejected: list[tuple[Path, str]] = []
    playback.load_and_play(
        Path("/tmp/before-release.dsf"),
        on_rejected=lambda path, reason: rejected.append((path, reason)),
    )

    assert rejected
    assert playback._intent is True
    assert playback._accepted is True
