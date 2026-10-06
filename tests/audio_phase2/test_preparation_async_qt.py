"""True async output-preparation tests (AP2-F05 WU0).

These tests use the REAL productive seam:
- blocking request build (characterization/qualification stand-in) on a worker,
- owner completion through the canonical executor delivery,
- every preparation purpose covered,
- supersession/cancellation/no-autoplay semantics preserved.

They deliberately do NOT use the inline test policy: the async scheduling is
the subject under test.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from michi.application.audio_output_planner import OutputPlanner
from michi.application.output_session_service import (
    OutputRequest,
    OutputSessionError,
    OutputSessionService,
)
from michi.application.playback_service import (
    EngineSwitchMediaSnapshot,
    PlaybackService,
)
from michi.domain.playback import PlaybackStatus


class _BlockingProvider:
    """Stands in for the full request build (metadata + characterization)."""

    def __init__(self, blocking_names: set[str] | None = None) -> None:
        self.blocking = blocking_names if blocking_names is not None else {"slow.flac"}
        self.entered = threading.Event()
        self.release = threading.Event()

    def __call__(self, path: Path) -> OutputRequest:
        if Path(path).name in self.blocking:
            self.entered.set()
            self.release.wait(timeout=8.0)
        return OutputRequest.shared()


class _DeferredExecutor:
    """Captures worker/completion pairs; delivery is a separate owner turn."""

    def __init__(self) -> None:
        self._completions: list[tuple] = []
        self._lock = threading.Lock()
        self.owner_ident = threading.get_ident()
        self.worker_idents: list[int] = []

    def submit(self, work, completed) -> None:
        def run() -> None:
            with self._lock:
                self.worker_idents.append(threading.get_ident())
            try:
                value = work()
            except Exception as exc:  # noqa: BLE001 - typed completion
                with self._lock:
                    self._completions.append((completed, None, exc))
            else:
                with self._lock:
                    self._completions.append((completed, value, None))

        threading.Thread(target=run, daemon=True).start()

    def deliver(self) -> int:
        """Owner event-loop turn (runs on the caller thread)."""
        delivered = 0
        while True:
            with self._lock:
                if not self._completions:
                    return delivered
                completed, value, error = self._completions.pop(0)
            completed(value, error)
            delivered += 1

    def wait_completion(self, timeout_s: float = 5.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            with self._lock:
                if self._completions:
                    return
            time.sleep(0.005)
        raise AssertionError("no completion arrived")


def _service(provider: _BlockingProvider, executor, **kwargs) -> OutputSessionService:
    return OutputSessionService(
        OutputPlanner(),
        request_provider=provider,
        executors={},
        async_submit=executor.submit,
        **kwargs,
    )


# ── service level ─────────────────────────────────────────────────────
def test_async_prepare_returns_before_characterization_and_commits_on_owner() -> None:
    provider = _BlockingProvider()
    executor = _DeferredExecutor()
    service = _service(provider, executor)
    tokens: list[str] = []
    failures: list[Exception] = []

    started = time.monotonic()
    service.prepare_for_media_async(
        Path("/tmp/slow.flac"), tokens.append, failures.append
    )
    elapsed = time.monotonic() - started
    assert elapsed < 0.2, "the productive call must not wait for the worker"
    assert provider.entered.wait(timeout=2.0)
    # The build runs on a WORKER thread, never the owner.
    assert executor.worker_idents and executor.worker_idents[0] != executor.owner_ident
    assert tokens == [] and failures == []

    provider.release.set()
    executor.wait_completion()
    completion_threads: list[int] = []

    def owner_turn() -> None:
        completion_threads.append(threading.get_ident())
        executor.deliver()

    owner_turn()
    assert completion_threads == [executor.owner_ident]
    assert len(tokens) == 1 and failures == []


def test_newest_request_wins_and_stale_completion_never_commits() -> None:
    provider = _BlockingProvider(blocking_names={"a.flac"})
    executor = _DeferredExecutor()
    service = _service(provider, executor)
    tokens: list[str] = []
    failures: list[Exception] = []

    service.prepare_for_media_async(Path("/tmp/a.flac"), tokens.append, failures.append)
    assert provider.entered.wait(timeout=2.0)
    service.prepare_for_media_async(Path("/tmp/b.flac"), tokens.append, failures.append)
    executor.wait_completion()
    executor.deliver()  # B commits
    assert len(tokens) == 1 and failures == []

    provider.release.set()  # A finally completes; it is stale
    executor.wait_completion()
    executor.deliver()
    assert len(tokens) == 1, "a stale completion must never commit"
    assert failures and failures[0].code == "OUTPUT_PREPARATION_STALE"


def test_cancel_during_characterization_discards_completion() -> None:
    provider = _BlockingProvider()
    executor = _DeferredExecutor()
    cancelled: list[int] = []
    service = _service(
        provider, executor, cancel_prepare_work=lambda: cancelled.append(1)
    )
    tokens: list[str] = []
    failures: list[Exception] = []

    service.prepare_for_media_async(
        Path("/tmp/slow.flac"), tokens.append, failures.append
    )
    assert provider.entered.wait(timeout=2.0)
    service.cancel_pending_prepare()
    assert cancelled == [1]
    provider.release.set()
    executor.wait_completion()
    executor.deliver()
    assert tokens == []
    assert failures and failures[0].code == "OUTPUT_PREPARATION_STALE"


def test_worker_error_is_delivered_typed_on_the_owner() -> None:
    class _FailingProvider:
        def __call__(self, path: Path):
            raise OutputSessionError("SELECTED_PROFILE_MISSING", "missing profile")

    executor = _DeferredExecutor()
    service = _service(_FailingProvider(), executor)  # type: ignore[arg-type]
    tokens: list[str] = []
    failures: list[Exception] = []
    service.prepare_for_media_async(Path("/tmp/x.flac"), tokens.append, failures.append)
    executor.wait_completion()
    executor.deliver()
    assert tokens == []
    assert failures and failures[0].code == "SELECTED_PROFILE_MISSING"


# ── productive purposes (PlaybackService) ────────────────────────────
def _playback_with_async_service(fake_audio, provider, executor, **kwargs):
    service = _service(provider, executor, **kwargs)
    playback = PlaybackService(fake_audio, output_tx=service)
    return playback, service, executor


def test_user_play_preparation_is_owner_free_and_then_loads_and_plays(
    fake_audio,
) -> None:
    provider = _BlockingProvider()
    playback, _service_obj, executor = _playback_with_async_service(
        fake_audio, provider, _DeferredExecutor()
    )
    started = time.monotonic()
    playback.load_and_play(Path("/tmp/slow.flac"))
    assert time.monotonic() - started < 0.2
    assert provider.entered.wait(timeout=2.0)
    assert fake_audio.loaded is None  # nothing happened before completion
    provider.release.set()
    executor.wait_completion()
    executor.deliver()
    assert fake_audio.loaded == Path("/tmp/slow.flac")
    assert fake_audio.state == "playing"  # USER_PLAY plays explicitly


def test_startup_restore_is_owner_free_and_never_autoplays(fake_audio) -> None:
    provider = _BlockingProvider()
    playback, _service_obj, executor = _playback_with_async_service(
        fake_audio, provider, _DeferredExecutor()
    )
    started = time.monotonic()
    playback.prepare_for_resume(Path("/tmp/slow.flac"), 12_345)
    assert time.monotonic() - started < 0.2
    assert provider.entered.wait(timeout=2.0)
    assert fake_audio.loaded is None
    provider.release.set()
    executor.wait_completion()
    executor.deliver()
    assert fake_audio.loaded == Path("/tmp/slow.flac")
    assert fake_audio.state == "stopped"  # never autoplays
    assert playback.state.status is PlaybackStatus.STOPPED


def test_startup_restore_failure_is_typed_and_never_loads(fake_audio) -> None:
    provider = _BlockingProvider()
    playback, _service_obj, executor = _playback_with_async_service(
        fake_audio, provider, _DeferredExecutor()
    )
    playback.prepare_for_resume(Path("/tmp/slow.flac"), 0)
    assert provider.entered.wait(timeout=2.0)
    # Supersede before the worker finishes: the refusal is STALE and no load
    # may happen after the newer intent.
    playback.stop()
    provider.release.set()
    executor.wait_completion()
    executor.deliver()
    assert fake_audio.loaded is None


def test_engine_switch_rehydration_is_owner_free_and_never_autoplays(
    fake_audio,
) -> None:
    provider = _BlockingProvider()
    playback, _service_obj, executor = _playback_with_async_service(
        fake_audio, provider, _DeferredExecutor()
    )
    snapshot = EngineSwitchMediaSnapshot(
        file_path=Path("/tmp/slow.flac"),
        confirmed_position_ms=5_000,
        deferred_resume_target_ms=None,
        previous_status=PlaybackStatus.STOPPED,
    )
    started = time.monotonic()
    playback.prepare_after_engine_switch(snapshot)
    assert time.monotonic() - started < 0.2
    assert provider.entered.wait(timeout=2.0)
    assert fake_audio.loaded is None
    provider.release.set()
    executor.wait_completion()
    executor.deliver()
    assert fake_audio.loaded == Path("/tmp/slow.flac")
    assert fake_audio.state == "stopped"


def test_output_handover_is_owner_free_and_preserves_resume_rule(fake_audio) -> None:
    provider = _BlockingProvider()
    playback, _service_obj, executor = _playback_with_async_service(
        fake_audio, provider, _DeferredExecutor()
    )
    # Predecessor STOPPED: the handover must NOT start playback.
    started = time.monotonic()
    playback.prepare_for_handover(Path("/tmp/slow.flac"), 9_000)
    assert time.monotonic() - started < 0.2
    assert provider.entered.wait(timeout=2.0)
    assert fake_audio.loaded is None
    provider.release.set()
    executor.wait_completion()
    executor.deliver()
    assert fake_audio.loaded == Path("/tmp/slow.flac")
    assert fake_audio.state == "stopped"


def test_shutdown_during_preparation_discards_the_completion(fake_audio) -> None:
    provider = _BlockingProvider()
    cancelled: list[int] = []
    playback, service_obj, executor = _playback_with_async_service(
        fake_audio,
        provider,
        _DeferredExecutor(),
        cancel_prepare_work=lambda: cancelled.append(1),
    )
    playback.prepare_for_resume(Path("/tmp/slow.flac"), 0)
    assert provider.entered.wait(timeout=2.0)
    # Semantic owner teardown: the pending preparation is superseded and the
    # late completion cannot load or seek.
    playback.stop()
    service_obj.cancel_pending_prepare()
    # stop() itself already propagates cancellation end to end.
    assert cancelled, "cancellation must reach the characterization worker"
    provider.release.set()
    executor.wait_completion()
    executor.deliver()
    assert fake_audio.loaded is None
    assert fake_audio.seek_calls == []


# ── real Qt scheduling ───────────────────────────────────────────────
def test_async_prepare_keeps_the_qt_loop_free_without_nested_pumping(qapp) -> None:
    """Real Qt executor: prompt return, natural QTimer, owner completion."""
    from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot

    class _QtOwnerExecutor(QObject):
        _completed = Signal(object, object, object)

        def __init__(self) -> None:
            super().__init__()
            self.owner_ident = threading.get_ident()
            self._completed.connect(self._deliver, Qt.QueuedConnection)

        def submit(self, work, completed) -> None:
            def run() -> None:
                try:
                    value = work()
                except Exception as exc:  # noqa: BLE001 - typed delivery
                    self._completed.emit(completed, None, exc)
                else:
                    self._completed.emit(completed, value, None)

            threading.Thread(target=run, daemon=True).start()

        @Slot(object, object, object)
        def _deliver(self, completed, value, error) -> None:
            completed(value, error)

    provider = _BlockingProvider()
    executor = _QtOwnerExecutor()
    service = _service(provider, executor)
    received: list[tuple[str, int]] = []
    failures: list[Exception] = []

    def on_prepared(token: str) -> None:
        received.append((token, threading.get_ident()))

    ticks: list[float] = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start()
    try:
        started = time.monotonic()
        service.prepare_for_media_async(
            Path("/tmp/slow.flac"), on_prepared, failures.append
        )
        assert time.monotonic() - started < 0.2
        assert provider.entered.wait(timeout=2.0)

        deadline = time.monotonic() + 0.4
        while time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert len(ticks) >= 5, "the Qt timer froze during the worker"
        assert received == []

        provider.release.set()
        deadline = time.monotonic() + 3.0
        while not received and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert received and received[0][1] == executor.owner_ident
        assert failures == []
    finally:
        timer.stop()
