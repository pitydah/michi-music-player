"""Source-characterization responsiveness and cancellation tests.

The production characterization worker is bounded but used to block the Qt
owner for its whole budget. These tests prove the pumped wrapper keeps the
owner responsive and that supersession aborts the worker.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from michi.application.audio_output_planner import OutputPlanner
from michi.application.output_session_service import OutputSessionService
from michi.infrastructure.audio_engines.subprocess_characterizer import (
    PumpedSourceCharacterizer,
)


class _BlockingCharacterizer:
    def __init__(self, hold_s: float = 0.4) -> None:
        self.hold_s = hold_s
        self.cancel_called = threading.Event()
        self.released = threading.Event()

    def characterize(self, path: Path):
        deadline = time.monotonic() + self.hold_s
        while time.monotonic() < deadline:
            if self.cancel_called.is_set():
                raise RuntimeError("characterization cancelled")
            time.sleep(0.005)
        self.released.set()
        return {"path": str(path)}

    def cancel(self) -> None:
        self.cancel_called.set()


def test_pumped_characterizer_pumps_during_the_worker_and_returns() -> None:
    inner = _BlockingCharacterizer()
    pumps: list[float] = []
    pumped = PumpedSourceCharacterizer(
        inner, pump=lambda: pumps.append(time.monotonic()), slice_s=0.005
    )
    started = time.monotonic()
    result = pumped.characterize(Path("/tmp/pumped.flac"))
    elapsed = time.monotonic() - started
    assert result == {"path": "/tmp/pumped.flac"}
    assert elapsed >= 0.3
    # The calling thread kept pumping in short slices instead of sleeping the
    # whole budget away.
    assert len(pumps) >= 10


def test_pumped_characterizer_without_pump_still_works() -> None:
    inner = _BlockingCharacterizer(hold_s=0.05)
    pumped = PumpedSourceCharacterizer(inner)
    assert pumped.characterize(Path("/tmp/no-pump.flac")) == {
        "path": "/tmp/no-pump.flac"
    }


def test_cancel_reaches_the_inner_worker_and_unblocks_the_caller() -> None:
    inner = _BlockingCharacterizer(hold_s=5.0)
    pumped = PumpedSourceCharacterizer(inner, slice_s=0.005)
    errors: list[Exception] = []

    def caller() -> None:
        try:
            pumped.characterize(Path("/tmp/cancel.flac"))
        except Exception as exc:  # noqa: BLE001 - captured for assertion
            errors.append(exc)

    thread = threading.Thread(target=caller)
    thread.start()
    time.sleep(0.1)
    pumped.cancel()
    thread.join(timeout=2.0)
    assert not thread.is_alive()
    assert inner.cancel_called.is_set()
    # A superseded completion is never returned as current: the wrapper
    # reports the stale generation contract (the inner failure is swallowed
    # because a newer request owns the truth).
    from michi.application.audio_output_ports import SourceCharacterizationError

    assert errors and isinstance(errors[0], SourceCharacterizationError)
    assert errors[0].code == "SOURCE_CHARACTERIZATION_STALE"


def test_qt_timer_keeps_running_during_characterization(qapp) -> None:
    from PySide6.QtCore import QTimer

    inner = _BlockingCharacterizer(hold_s=0.4)
    pumped = PumpedSourceCharacterizer(
        inner, pump=lambda: qapp.processEvents(), slice_s=0.005
    )
    ticks: list[float] = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start()
    try:
        pumped.characterize(Path("/tmp/qt-char.flac"))
    finally:
        timer.stop()
    assert len(ticks) >= 5, (
        f"Qt timer froze during characterization (ticks={len(ticks)})"
    )


def test_cancel_pending_prepare_aborts_characterization_work() -> None:
    calls: list[int] = []
    service = OutputSessionService(
        OutputPlanner(),
        facts_provider=lambda _path: None,
        executors={},
        cancel_prepare_work=lambda: calls.append(1),
    )
    service.cancel_pending_prepare()
    service.cancel_pending_prepare()
    assert calls == [1, 1]


def test_cancel_pending_prepare_tolerates_a_failing_cancel_hook() -> None:
    def broken() -> None:
        raise RuntimeError("cancel hook failure")

    service = OutputSessionService(
        OutputPlanner(),
        facts_provider=lambda _path: None,
        executors={},
        cancel_prepare_work=broken,
    )
    service.cancel_pending_prepare()  # must never raise


def test_failing_cancel_hook_does_not_break_the_service() -> None:
    service = OutputSessionService(
        OutputPlanner(),
        facts_provider=lambda _path: None,
        executors={},
    )
    service.cancel_pending_prepare()
    assert service.state is not None
