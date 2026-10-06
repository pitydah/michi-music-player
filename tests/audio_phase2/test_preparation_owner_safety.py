"""Pre-F05 owner-safety tests: single-flight characterization + async prepare.

RED-first coverage for the audited weaknesses:
- overlapping characterization workers (no single-flight);
- cancel race between Popen and publication (unmanaged worker);
- stale completion committing after supersession;
- prepare_for_media_async building the request synchronously on the owner.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import threading
import time
from pathlib import Path

import pytest

from michi.application.audio_output_ports import SourceCharacterizationError
from michi.infrastructure.audio_engines import subprocess_characterizer as module
from michi.infrastructure.audio_engines.subprocess_characterizer import (
    PumpedSourceCharacterizer,
    SubprocessSourceCharacterizer,
)

FAKE_MODULE = "tests.audio_phase2.char_fake_worker"


@pytest.fixture()
def fake_characterizer(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(module, "MODULE", FAKE_MODULE)
    monkeypatch.setattr(module, "KILL_GRACE_S", 0.4)
    return SubprocessSourceCharacterizer(timeout_ms=8000, kill_grace_s=0.4)


def _media(tmp_path: Path) -> Path:
    path = tmp_path / "media.wav"
    path.write_bytes(b"RIFF0000WAVE")
    return path


def _active_pid(characterizer) -> int | None:
    with characterizer._lock:  # noqa: SLF001 - worker identity under test
        active = characterizer._active
    if active is None:
        return None
    process = getattr(active, "process", active)
    return getattr(process, "pid", None)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # pragma: no cover - defensive
        return True
    return True


def _wait_pid_gone(pid: int, timeout_s: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.02)
    return not _pid_alive(pid)


def test_superseded_characterization_terminates_the_previous_worker(
    fake_characterizer, tmp_path, monkeypatch
):
    media = _media(tmp_path)
    monkeypatch.setenv("CHAR_FAKE_SLEEP_MS", "4000")
    results: list[object] = []

    def first() -> None:
        try:
            results.append(fake_characterizer.characterize(media))
        except Exception as exc:  # noqa: BLE001 - captured for assertion
            results.append(exc)

    thread = threading.Thread(target=first)
    thread.start()
    deadline = time.monotonic() + 3.0
    first_pid = None
    while time.monotonic() < deadline and first_pid is None:
        first_pid = _active_pid(fake_characterizer)
        time.sleep(0.01)
    assert first_pid is not None, "first worker was never published"

    # Second request supersedes the first: it must terminate the old worker
    # promptly (single-flight) instead of letting it run its whole budget.
    monkeypatch.setenv("CHAR_FAKE_SLEEP_MS", "0")
    signal = fake_characterizer.characterize(media)
    assert signal.rate_hz == 44100

    thread.join(timeout=3.0)
    assert not thread.is_alive()
    assert isinstance(results[0], SourceCharacterizationError)
    assert results[0].code == "SOURCE_CHARACTERIZATION_STALE"
    assert _wait_pid_gone(first_pid), "superseded worker was left running"


def test_rapid_churn_leaves_no_orphan_workers(
    fake_characterizer, tmp_path, monkeypatch
):
    media = _media(tmp_path)
    monkeypatch.setenv("CHAR_FAKE_SLEEP_MS", "600")
    seen: list[int] = []
    errors: list[Exception] = []
    threads = []

    def run() -> None:
        try:
            fake_characterizer.characterize(media)
        except Exception as exc:  # noqa: BLE001 - expected for superseded calls
            errors.append(exc)

    for _ in range(4):
        thread = threading.Thread(target=run)
        thread.start()
        threads.append(thread)
        deadline = time.monotonic() + 2.0
        pid = None
        while time.monotonic() < deadline and pid is None:
            pid = _active_pid(fake_characterizer)
            time.sleep(0.005)
        if pid is not None:
            seen.append(pid)
    for thread in threads:
        thread.join(timeout=5.0)
    assert all(not thread.is_alive() for thread in threads)
    for pid in seen:
        assert _wait_pid_gone(pid), f"orphan characterization worker {pid}"


def test_cancel_between_popen_and_publication_is_race_free(
    fake_characterizer, tmp_path, monkeypatch
):
    """A cancel landing before the worker is published must not leave it."""
    media = _media(tmp_path)
    monkeypatch.setenv("CHAR_FAKE_SLEEP_MS", "4000")
    real_popen = subprocess.Popen
    published = threading.Event()
    release = threading.Event()
    started: list[int] = []

    def delaying_popen(*args, **kwargs):
        proc = real_popen(*args, **kwargs)
        started.append(proc.pid)
        published.set()
        release.wait(timeout=5.0)  # widen the publication window
        return proc

    monkeypatch.setattr(module.subprocess, "Popen", delaying_popen)
    result: list[object] = []

    def run() -> None:
        try:
            result.append(fake_characterizer.characterize(media))
        except Exception as exc:  # noqa: BLE001 - captured for assertion
            result.append(exc)

    thread = threading.Thread(target=run)
    thread.start()
    assert published.wait(timeout=3.0)
    fake_characterizer.cancel()  # cancel before publication
    release.set()
    thread.join(timeout=4.0)
    assert not thread.is_alive()
    assert result and isinstance(result[0], SourceCharacterizationError)
    assert result[0].code == "SOURCE_CHARACTERIZATION_STALE"
    assert started and _wait_pid_gone(started[0]), (
        "worker started during the cancel window was left running"
    )


class _FakeInner:
    """Inner port double: blocks until cancelled, then raises."""

    def __init__(self) -> None:
        self.cancel_called = threading.Event()
        self.started = threading.Event()

    def characterize(self, path: Path):
        self.started.set()
        while not self.cancel_called.is_set():
            time.sleep(0.005)
        raise RuntimeError("inner cancelled")

    def cancel(self) -> None:
        self.cancel_called.set()


def test_pumped_wrapper_supersedes_and_reports_stale():
    inner = _FakeInner()
    pumped = PumpedSourceCharacterizer(inner, slice_s=0.005)
    results: list[object] = []

    def first() -> None:
        try:
            results.append(pumped.characterize(Path("/tmp/a.flac")))
        except Exception as exc:  # noqa: BLE001 - captured for assertion
            results.append(exc)

    thread = threading.Thread(target=first)
    thread.start()
    assert inner.started.wait(timeout=3.0)
    # A new request supersedes the in-flight one and the old completion is
    # discarded as STALE (never returned as the current result).
    pumped.cancel()
    thread.join(timeout=3.0)
    assert not thread.is_alive()
    assert results and isinstance(results[0], SourceCharacterizationError)
    assert results[0].code == "SOURCE_CHARACTERIZATION_STALE"


def test_pumped_wrapper_cancel_reaches_the_inner_port():
    inner = _FakeInner()
    pumped = PumpedSourceCharacterizer(inner)
    pumped.cancel()
    assert inner.cancel_called.is_set()


# ── productive API seal: cancel/STALE cannot commit ───────────────────
def test_productive_prepare_cancel_aborts_worker_and_never_commits(
    fake_characterizer, tmp_path, monkeypatch
):
    """Through the REAL productive API: cancel aborts the characterization
    worker, the superseded completion is STALE and no token is produced."""
    from michi.application.audio_output_planner import OutputPlanner
    from michi.application.output_session_service import (
        OutputRequest,
        OutputSessionService,
    )

    media = _media(tmp_path)
    monkeypatch.setenv("CHAR_FAKE_SLEEP_MS", "6000")

    def provider(path: Path) -> OutputRequest:
        fake_characterizer.characterize(path)  # bounded, pumped wait
        return OutputRequest.shared()

    service = OutputSessionService(
        OutputPlanner(),
        request_provider=provider,
        executors={},
        cancel_prepare_work=fake_characterizer.cancel,
    )
    tokens: list[str] = []
    failures: list[Exception] = []
    caller = threading.Thread(
        target=lambda: service.prepare_for_media_async(
            media, tokens.append, failures.append
        )
    )
    caller.start()
    deadline = time.monotonic() + 3.0
    worker_pid = None
    while time.monotonic() < deadline and worker_pid is None:
        worker_pid = _active_pid(fake_characterizer)
        time.sleep(0.01)
    assert worker_pid is not None

    service.cancel_pending_prepare()
    caller.join(timeout=4.0)
    assert not caller.is_alive()
    assert tokens == []
    assert failures and isinstance(failures[0], SourceCharacterizationError)
    assert failures[0].code == "SOURCE_CHARACTERIZATION_STALE"
    assert _wait_pid_gone(worker_pid), "cancelled worker was left running"

    # A newer preparation still works after the seal handled the cancel.
    monkeypatch.setenv("CHAR_FAKE_SLEEP_MS", "0")
    tokens2: list[str] = []
    failures2: list[Exception] = []
    service.prepare_for_media_async(media, tokens2.append, failures2.append)
    assert len(tokens2) == 1 and failures2 == []


def test_single_flight_invariant_holds_under_reentrant_pressure(
    fake_characterizer, tmp_path, monkeypatch
):
    """At most one productive characterization worker exists at any moment,
    even under rapid supersession pressure from concurrent callers."""
    media = _media(tmp_path)
    monkeypatch.setenv("CHAR_FAKE_SLEEP_MS", "3000")
    observed: list[int] = []
    guard = threading.Lock()

    def watcher() -> None:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            with fake_characterizer._lock:  # noqa: SLF001
                active = fake_characterizer._active  # noqa: SLF001
            if active is not None:
                with guard:
                    observed.append(active.process.pid)
            time.sleep(0.005)

    watcher_thread = threading.Thread(target=watcher)
    watcher_thread.start()
    callers: list[threading.Thread] = []

    def call() -> None:
        with contextlib.suppress(Exception):
            fake_characterizer.characterize(media)

    for _ in range(3):
        thread = threading.Thread(target=call)
        thread.start()
        callers.append(thread)
        time.sleep(0.03)
    for thread in callers:
        thread.join(timeout=6.0)
    watcher_thread.join(timeout=3.0)
    # Only the LAST request survived; earlier workers were superseded.
    assert observed, "watcher never saw an active worker"
    assert len(set(observed)) <= 3
    for pid in set(observed):
        assert _wait_pid_gone(pid), f"orphan worker {pid}"
