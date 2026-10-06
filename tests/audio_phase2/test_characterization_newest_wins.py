"""Deterministic newest-wins tests for the pumped characterization wrapper.

The B/C race (an older call cancelling a newer call's inner worker) is forced
with event-driven barriers, not probabilistic thread churn.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from michi.application.audio_output_ports import SourceCharacterizationError
from michi.infrastructure.audio_engines.subprocess_characterizer import (
    PumpedSourceCharacterizer,
)


class _InstrumentedInner:
    """Mirrors the real inner: one active run, cancel kills the ACTIVE run."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: dict | None = None
        self._run_count = 0
        self._concurrent = 0
        self.max_concurrent = 0
        self.first_run_entered = threading.Event()
        self.run_release = threading.Event()
        self.first_cancel_entered = threading.Event()
        self.first_cancel_release = threading.Event()
        self.cancel_calls = 0

    def characterize(self, path: Path):
        with self._lock:
            self._run_count += 1
            token = {
                "id": self._run_count,
                "dead": False,
                "dead_event": threading.Event(),
                "finished_event": threading.Event(),
                "path": str(path),
            }
            self._active = token
            self._concurrent += 1
            self.max_concurrent = max(self.max_concurrent, self._concurrent)
        self.first_run_entered.set()
        # A run completes on harness release OR on being killed (dead), which
        # mirrors the real inner terminate+reap behavior.
        deadline = time.monotonic() + 8.0
        while (
            not self.run_release.is_set()
            and not token["dead_event"].is_set()
            and time.monotonic() < deadline
        ):
            time.sleep(0.002)
        with self._lock:
            self._concurrent -= 1
            dead = token["dead"]
            token["finished_event"].set()
            if self._active is token:
                self._active = None
        if dead:
            raise RuntimeError(f"inner cancelled run {token['id']}")
        return {"ok": True, "path": token["path"]}

    def cancel(self) -> None:
        self.cancel_calls += 1
        if self.cancel_calls == 1:
            # First cancel (B superseding A) blocks: the deterministic pause
            # point inside the supersession transition.
            self.first_cancel_entered.set()
            self.first_cancel_release.wait(timeout=8.0)
        with self._lock:
            token = self._active
        if token is not None:
            token["dead_event"].set()
            # terminate + bounded reap: the killed run must be GONE before a
            # new worker may start (single-flight).
            token["finished_event"].wait(timeout=2.0)


def _run_characterization(
    pumped, path: str, results: list, index: int
) -> threading.Thread:
    def call() -> None:
        try:
            value = pumped.characterize(Path(path))
        except Exception as exc:  # noqa: BLE001 - captured for assertion
            results[index] = exc
        else:
            results[index] = value

    thread = threading.Thread(target=call)
    return thread


def test_b_never_cancels_c_and_newest_request_wins() -> None:
    inner = _InstrumentedInner()
    pumped = PumpedSourceCharacterizer(inner, slice_s=0.005)
    results: list[object] = [None, None, None]

    a = _run_characterization(pumped, "/tmp/a.flac", results, 0)
    a.start()
    assert inner.first_run_entered.wait(timeout=3.0)

    # B enters supersession and pauses INSIDE the transition (blocked in the
    # first inner cancel, before publishing/starting its own worker).
    b = _run_characterization(pumped, "/tmp/b.flac", results, 1)
    b.start()
    assert inner.first_cancel_entered.wait(timeout=3.0)
    time.sleep(0.05)

    # C is the NEWEST request.
    c = _run_characterization(pumped, "/tmp/c.flac", results, 2)
    c.start()
    time.sleep(0.05)

    # Release B's pause, then let every inner run complete.
    inner.first_cancel_release.set()
    time.sleep(0.2)
    inner.run_release.set()

    for thread in (a, b, c):
        thread.join(timeout=8.0)
        assert not thread.is_alive()

    # NEWEST WINS: C must succeed; older A/B must be STALE, never an inner
    # failure produced by an older call cancelling C's worker.
    assert results[2] == {"ok": True, "path": "/tmp/c.flac"}, results
    for stale in (results[0], results[1]):
        assert isinstance(stale, SourceCharacterizationError), results
        assert stale.code == "SOURCE_CHARACTERIZATION_STALE"
    # At most ONE productive inner worker existed at any instant.
    assert inner.max_concurrent == 1


def test_cancel_never_leaves_a_live_worker_or_a_lost_newest() -> None:
    inner = _InstrumentedInner()
    pumped = PumpedSourceCharacterizer(inner, slice_s=0.005)
    results: list[object] = [None]

    a = _run_characterization(pumped, "/tmp/a.flac", results, 0)
    a.start()
    assert inner.first_run_entered.wait(timeout=3.0)

    # Cancel participates in the same startup fence: after it returns, no
    # worker may still be productive and the pending call is STALE.
    inner.first_cancel_release.set()  # this test does not pause the cancel
    pumped.cancel()
    inner.run_release.set()
    a.join(timeout=8.0)
    assert not a.is_alive()
    assert isinstance(results[0], SourceCharacterizationError)
    assert results[0].code == "SOURCE_CHARACTERIZATION_STALE"
    assert inner.max_concurrent == 1
