from __future__ import annotations

import pytest

from michi.application.audio_family_transition import (
    AudioFamily,
    AudioFamilyTransitionService,
    FamilyTransitionRequest,
    GaplessClass,
    PlaybackStatus,
    TransitionError,
)


def _request(**kw):
    base = dict(
        media_identity="track:1",
        source_family=AudioFamily.PCM_DIRECT,
        target_family=AudioFamily.DSD_TO_PCM,
        predecessor_status=PlaybackStatus.PLAYING,
        request_epoch=3,
        current_epoch=2,
        output_generation=4,
        processing_generation=5,
        binding_generation=6,
        destructive_boundary=True,
        confirmed_position_ms=1200,
    )
    base.update(kw)
    return FamilyTransitionRequest(**base)


def test_playing_reopen_is_degraded_and_does_not_claim_gapless():
    receipt = AudioFamilyTransitionService().plan(_request())
    assert receipt.gapless is GaplessClass.GAPLESS_DEGRADED_REOPEN
    assert receipt.resume_status is PlaybackStatus.PLAYING
    assert receipt.predecessor_released is False


@pytest.mark.parametrize("status", [PlaybackStatus.PAUSED, PlaybackStatus.STOPPED])
def test_paused_and_stopped_never_autoplay(status):
    receipt = AudioFamilyTransitionService().plan(_request(predecessor_status=status))
    assert receipt.resume_status is status


def test_same_family_and_stale_epoch_rejected():
    service = AudioFamilyTransitionService()
    with pytest.raises(TransitionError, match="TRANSITION_SAME_FAMILY"):
        service.plan(_request(target_family=AudioFamily.PCM_DIRECT))
    with pytest.raises(TransitionError, match="TRANSITION_EPOCH_STALE"):
        service.plan(_request(request_epoch=2))


def test_release_marking_is_explicit():
    service = AudioFamilyTransitionService()
    receipt = service.plan(_request())
    released = service.mark_released(receipt)
    assert released.predecessor_released is True
    assert released.request_epoch == receipt.request_epoch


def test_failed_rollback_converges_stopped():
    service = AudioFamilyTransitionService()
    request = _request(predecessor_status=PlaybackStatus.PAUSED)
    failure = service.on_failure(request, rollback_safe=False, reason="binding_stale")
    assert failure.status is PlaybackStatus.STOPPED
    assert failure.restored is False
