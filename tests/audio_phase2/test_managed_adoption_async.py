"""S16 — managed adoption must never block the Qt owner."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QTimer

from michi.application.playback_service import PlaybackService
from tests.conftest import FakeAudioPort


class _BlockingAdoptionAudio(FakeAudioPort):
    def __init__(self) -> None:
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()
        self._completion: tuple | None = None

    def adopt_preloaded_media_async(self, claim, *, on_done, on_failed) -> None:
        self.entered.set()

        def run() -> None:
            self.release.wait(timeout=5.0)
            self._completion = (on_done, {"claimed": True})

        threading.Thread(target=run, daemon=True).start()

    def wait_completion(self) -> None:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and self._completion is None:
            time.sleep(0.005)
        assert self._completion is not None

    def deliver(self) -> None:
        assert self._completion is not None
        on_done, value = self._completion
        self._completion = None
        on_done(value)


class _ManagedTx:
    managed_active = True

    def __init__(self) -> None:
        self.committed: Path | None = None
        self.aborted: list[tuple[str, str]] = []
        self.confirm_start = True

    def prepared_transport_claim(self, token: str, path: Path):
        return object()

    def commit_media(self, token: str, path: Path) -> None:
        self.committed = path

    def abort_media(self, token: str, reason: str) -> None:
        self.aborted.append((token, reason))

    @property
    def active_execution_id(self) -> str:
        return "exec:managed:1"

    def notify_managed_playing(self, execution_id: str) -> bool:
        return self.confirm_start and execution_id == "exec:managed:1"

    def release_active(self, reason: str) -> None:
        self.aborted.append(("release", reason))


class _ImmediateAdoptionAudio(FakeAudioPort):
    fail_play = False

    def adopt_preloaded_media_async(self, claim, *, on_done, on_failed) -> None:
        on_done({"claimed": True})

    def play(self) -> None:
        if self.fail_play:
            raise RuntimeError("play rejected")
        super().play()


class _QueuedAdoptionAudio(FakeAudioPort):
    def __init__(self) -> None:
        super().__init__()
        self.pending: list = []

    def adopt_preloaded_media_async(self, claim, *, on_done, on_failed) -> None:
        self.pending.append(on_done)

    def deliver(self, index: int) -> None:
        self.pending[index]({"claimed": True})


class _CommitFailingTx(_ManagedTx):
    def commit_media(self, token: str, path: Path) -> None:
        raise RuntimeError("commit rejected")


class _FailingAdoptionAudio(_ImmediateAdoptionAudio):
    def adopt_preloaded_media_async(self, claim, *, on_done, on_failed) -> None:
        on_failed(RuntimeError("the DAC binding disappeared"))


def test_dac_disappearance_during_managed_adoption_never_falls_back() -> None:
    audio = _FailingAdoptionAudio()
    playback = PlaybackService(audio)
    playback._request_epoch = 1
    tx = _ManagedTx()
    playback._output_tx = tx
    accepted: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    path = Path("/tmp/managed-adoption-dac-lost.wav")

    playback._continue_prepared_load(
        path,
        "output-tx:managed:dac-lost",
        1,
        False,
        False,
        accepted.append,
        lambda rejected_path, message: rejected.append((rejected_path, message)),
        None,
    )

    assert audio.loaded is None
    assert tx.committed is None
    assert accepted == []
    assert rejected and "binding disappeared" in rejected[0][1]
    assert ("output-tx:managed:dac-lost", "managed_adopt_failed") in tx.aborted


def test_a_to_b_to_c_ignores_every_superseded_managed_adoption() -> None:
    audio = _QueuedAdoptionAudio()
    playback = PlaybackService(audio)
    tx = _ManagedTx()
    playback._output_tx = tx
    accepted: list[Path] = []
    paths = [Path(f"/tmp/managed-adoption-{name}.wav") for name in "abc"]

    for index, path in enumerate(paths, start=1):
        playback._request_epoch = index
        playback._continue_prepared_load(
            path,
            f"output-tx:managed:{index}",
            index,
            False,
            False,
            accepted.append,
            None,
            None,
        )

    assert len(audio.pending) == 3
    audio.deliver(0)
    audio.deliver(1)
    assert accepted == []
    assert tx.committed is None

    audio.deliver(2)
    assert accepted == [paths[2]]
    assert tx.committed == paths[2]


def test_managed_commit_failure_never_publishes_acceptance() -> None:
    audio = _ImmediateAdoptionAudio()
    playback = PlaybackService(audio)
    playback._request_epoch = 1
    tx = _CommitFailingTx()
    playback._output_tx = tx
    accepted: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    path = Path("/tmp/managed-adoption-commit-failure.wav")

    playback._continue_prepared_load(
        path,
        "output-tx:managed:commit-failure",
        1,
        False,
        False,
        accepted.append,
        lambda rejected_path, message: rejected.append((rejected_path, message)),
        None,
    )

    assert accepted == []
    assert rejected and rejected[0][0] == path
    assert "commit rejected" in rejected[0][1]
    assert ("output-tx:managed:commit-failure", "output_commit_failed") in tx.aborted


def test_stop_during_managed_adoption_never_accepts_a_late_claim(qapp) -> None:
    audio = _BlockingAdoptionAudio()
    playback = PlaybackService(audio)
    playback._request_epoch = 1
    tx = _ManagedTx()
    playback._output_tx = tx
    accepted: list[Path] = []
    path = Path("/tmp/managed-adoption-stop.wav")

    playback._continue_prepared_load(
        path,
        "output-tx:managed:stop",
        1,
        False,
        False,
        accepted.append,
        None,
        None,
    )
    assert audio.entered.wait(timeout=2.0)

    playback.stop()
    audio.release.set()
    audio.wait_completion()
    audio.deliver()
    qapp.processEvents()

    assert tx.committed is None
    assert accepted == []
    assert tx.aborted == [("release", "stop")]


def test_play_failure_after_managed_commit_never_publishes_acceptance() -> None:
    audio = _ImmediateAdoptionAudio()
    audio.fail_play = True
    playback = PlaybackService(audio)
    playback._request_epoch = 1
    tx = _ManagedTx()
    playback._output_tx = tx
    accepted: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    path = Path("/tmp/managed-adoption-play-failure.wav")

    playback._continue_prepared_load(
        path,
        "output-tx:managed:play-failure",
        1,
        False,
        False,
        accepted.append,
        lambda rejected_path, message: rejected.append((rejected_path, message)),
        None,
    )

    assert tx.committed == path
    assert accepted == []
    assert rejected and rejected[0][0] == path
    assert "play rejected" in rejected[0][1]
    assert ("output-tx:managed:play-failure", "managed_play_failed") in tx.aborted


def test_unconfirmed_managed_start_never_publishes_acceptance() -> None:
    audio = _ImmediateAdoptionAudio()
    playback = PlaybackService(audio)
    playback._request_epoch = 1
    tx = _ManagedTx()
    tx.confirm_start = False
    playback._output_tx = tx
    accepted: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    path = Path("/tmp/managed-adoption-start-unconfirmed.wav")

    playback._continue_prepared_load(
        path,
        "output-tx:managed:start-unconfirmed",
        1,
        False,
        False,
        accepted.append,
        lambda rejected_path, message: rejected.append((rejected_path, message)),
        None,
    )

    assert tx.committed == path
    assert accepted == []
    assert rejected and "not confirmed" in rejected[0][1]
    assert (
        "output-tx:managed:start-unconfirmed",
        "managed_start_unconfirmed",
    ) in tx.aborted


def test_managed_claim_never_blocks_the_qt_owner(qapp) -> None:
    audio = _BlockingAdoptionAudio()
    playback = PlaybackService(audio)
    playback._request_epoch = 1
    tx = _ManagedTx()
    playback._output_tx = tx
    accepted: list[Path] = []
    path = Path("/tmp/managed-adoption.wav")

    ticks = 0
    timer = QTimer()
    timer.setInterval(1)

    def tick() -> None:
        nonlocal ticks
        ticks += 1

    timer.timeout.connect(tick)
    timer.start()

    started = time.monotonic()
    playback._continue_prepared_load(
        path,
        "output-tx:managed:1",
        1,
        False,
        False,
        accepted.append,
        None,
        None,
    )
    elapsed = time.monotonic() - started

    deadline = time.monotonic() + 0.25
    while time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.002)

    timer.stop()

    assert elapsed < 0.2
    assert audio.entered.wait(timeout=2.0)
    assert ticks >= 3
    assert audio.loaded is None
    assert tx.committed is None
    assert accepted == []

    audio.release.set()
    audio.wait_completion()
    audio.deliver()

    assert tx.committed == path
    assert audio.state == "playing"
    assert accepted == [path]
