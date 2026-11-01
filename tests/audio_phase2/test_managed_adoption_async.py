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
        return execution_id == "exec:managed:1"

    def release_active(self, reason: str) -> None:
        self.aborted.append(("release", reason))


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
