"""AP2-F10 — PlaybackService invokes the family transition planner."""

from __future__ import annotations

from pathlib import Path

from michi.application.audio_family_transition import AudioFamily
from michi.application.playback_service import PlaybackService


class _Output:
    def __init__(self, *, evidence: dict | None = None, reject: bool = False) -> None:
        self.current_family = AudioFamily.DOP
        self.last_release_evidence = evidence
        self.reject = reject
        self.aborted: list[str] = []
        self.committed: list[str] = []
        self.dsd_pcm_active = True
        self.native_dsd_active = False
        self.dop_active = False

    def transition_snapshot(self):
        return {
            "family": AudioFamily.DSD_TO_PCM,
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
    assert playback.family_transition_receipts == []
