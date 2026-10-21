"""AP2-F06 — Signal Truth measurement fence under concurrency.

The validation + append must be atomic wrt activation/retirement, and a late
measurement of a retired execution must never reappear (A -> B -> A).
"""

from __future__ import annotations

import threading
import time

import pytest

from michi.domain.signal_truth import (
    ProcessingMeasurement,
    SignalTruthRecorder,
)


def _measurement(
    execution_id: str, plan_id: str, sequence: int
) -> ProcessingMeasurement:
    return ProcessingMeasurement(
        execution_id=execution_id,
        plan_id=plan_id,
        sample_peak=0.5,
        estimated_true_peak=0.6,
        worst_channel=0,
        channels=2,
        sample_rate_hz=44100,
        window="0.4s",
        evidence_level="UNIT",
        sequence=sequence,
    )


def test_a_b_a_uses_distinct_instances_and_rejects_late_a() -> None:
    recorder = SignalTruthRecorder()
    recorder.activate_execution("exec:A", plan_id="plan:P")
    late = _measurement("exec:A", "plan:P", 1)
    recorder.retire_execution("exec:A")
    recorder.activate_execution("exec:B", plan_id="plan:P")
    with pytest.raises(ValueError):
        recorder.record_processing_measurement(late)
    recorder.record_processing_measurement(_measurement("exec:B", "plan:P", 2))
    assert [m.execution_id for m in recorder.processing_measurements] == ["exec:B"]
    # A third execution with the SAME plan never accepts A's result either.
    recorder.retire_execution("exec:B")
    recorder.activate_execution("exec:A2", plan_id="plan:P")
    with pytest.raises(ValueError):
        recorder.record_processing_measurement(late)
    assert recorder.processing_measurements == ()


def test_retirement_and_publication_are_atomic_under_races() -> None:
    recorder = SignalTruthRecorder()
    accepted = 0
    rejected = 0
    lock = threading.Lock()

    for _ in range(120):
        execution_id = f"exec:{accepted + rejected}"
        recorder.activate_execution(execution_id, plan_id="plan:P")
        barrier = threading.Barrier(2)

        def publish(execution_id=execution_id, barrier=barrier) -> None:
            nonlocal accepted, rejected
            barrier.wait()
            try:
                recorder.record_processing_measurement(
                    _measurement(execution_id, "plan:P", accepted + rejected)
                )
            except ValueError:
                with lock:
                    rejected += 1
            else:
                with lock:
                    accepted += 1

        def retire(execution_id=execution_id, barrier=barrier) -> None:
            barrier.wait()
            recorder.retire_execution(execution_id)

        workers = [threading.Thread(target=publish), threading.Thread(target=retire)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        # Whatever the interleaving: no measurement of a retired execution
        # remains.
        assert all(
            measurement.execution_id != execution_id
            for measurement in recorder.processing_measurements
        )
    assert accepted + rejected == 120


def test_history_is_bounded_and_notification_does_not_hold_the_lock() -> None:
    recorder = SignalTruthRecorder()
    recorder.activate_execution("exec:B", plan_id="plan:P")
    notifications: list[int] = []
    slow_entered = threading.Event()
    release = threading.Event()

    calls = {"count": 0}

    def slow() -> None:
        if calls["count"] == 0:
            slow_entered.set()
            release.wait(2.0)
        calls["count"] += 1
        notifications.append(1)

    recorder.subscribe(slow)
    for sequence in range(40):
        recorder.record_processing_measurement(
            _measurement("exec:B", "plan:P", sequence)
        )
    assert len(recorder.processing_measurements) == 16
    assert slow_entered.is_set()
    # Activation/retirement never waits on the slow subscriber.
    started = time.monotonic()
    recorder.activate_execution("exec:C", plan_id="plan:P")
    recorder.retire_execution("exec:C")
    assert time.monotonic() - started < 0.5
    release.set()


def test_event_lists_are_safe_for_owner_reads_during_worker_writes() -> None:
    from michi.domain.signal_truth import (
        OutputFamilyEvent,
        OutputFamilyState,
        ProcessingTruthEvent,
        ProcessingTruthState,
    )

    recorder = SignalTruthRecorder()
    stop = threading.Event()
    errors: list[str] = []

    def writer() -> None:
        for index in range(300):
            recorder.record_output_family_event(
                OutputFamilyEvent(
                    family="managed",
                    state=OutputFamilyState.RUNNING,
                    execution_id=f"exec:{index}",
                )
            )
            recorder.record_processing_event(
                ProcessingTruthEvent(
                    state=ProcessingTruthState.EFFECTIVE,
                    processing_generation=index,
                )
            )

    def reader() -> None:
        while not stop.is_set():
            try:
                events = recorder.output_family_events
                assert isinstance(events, tuple)
                assert all(event.family == "managed" for event in events)
                processing = recorder.processing_events
                assert isinstance(processing, tuple)
            except Exception as exc:  # noqa: BLE001 - collected for assertion
                errors.append(repr(exc))

    writer_thread = threading.Thread(target=writer)
    reader_thread = threading.Thread(target=reader)
    reader_thread.start()
    writer_thread.start()
    writer_thread.join()
    stop.set()
    reader_thread.join()
    assert not errors, errors
    assert len(recorder.output_family_events) == 64
    assert len(recorder.processing_events) == 64
