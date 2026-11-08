"""AP2-F11 M1: coherent recorder capture without breaking DAC legacy last.

RED-first tests: a committed playback and an aborted preparation are different
facts even where historical DAC tests retain their legacy last_snapshot API.
No audio engine, ALSA, Qt, or hardware is involved in these tests.
"""

from __future__ import annotations

import threading

from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    OutputFamilyEvent,
    OutputFamilyState,
    OutputPlanEvidence,
    ProcessingMeasurement,
    ProcessingTruthEvent,
    ProcessingTruthState,
    SignalTruthIdentity,
    SignalTruthRecorder,
    SourceFileFactsEvidence,
)


def _identity(epoch: int) -> SignalTruthIdentity:
    return SignalTruthIdentity(
        plan_id="plan:A",
        execution_generation=epoch,
        port_generation=epoch,
        binding_generation=2,
        stable_device_id="device:A",
        stable_endpoint_signature="endpoint:A",
    )


def _plan(epoch: int) -> OutputPlanEvidence:
    return OutputPlanEvidence(
        identity=_identity(epoch),
        requested_pcm=PcmTuple(96000, "S32_LE", 2, 24),
        sink_factory="alsasink",
        sink_device="hw:test",
        fixed_gain_required=True,
    )


def test_aborted_candidate_is_not_committed_playback() -> None:
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(_plan(1))
    assert recorder.discard_candidate(_identity(1))
    capture = recorder.read_capture_state()

    assert capture.candidate is None
    assert capture.active is None
    assert capture.last_committed is None
    assert capture.last_aborted_candidate.identity == _identity(1)
    # The existing DAC-facing API is deliberately unchanged until ADR.
    assert recorder.last_snapshot.identity == _identity(1)


def test_committed_history_survives_new_aborted_candidate() -> None:
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(_plan(1))
    assert recorder.commit_candidate(_identity(1))
    assert recorder.retire_active(_identity(1))
    recorder.begin_candidate(_plan(2))
    assert recorder.discard_candidate(_identity(2))
    capture = recorder.read_capture_state()

    assert capture.last_committed.identity == _identity(1)
    assert capture.last_aborted_candidate.identity == _identity(2)
    assert recorder.last_snapshot.identity == _identity(2)


def test_supersession_and_termination_label_aborted_candidates() -> None:
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(_plan(1))
    recorder.begin_candidate(_plan(2))
    a = recorder.read_capture_state()
    assert a.candidate.identity == _identity(2)
    assert a.last_aborted_candidate.identity == _identity(1)
    assert a.last_committed is None

    assert recorder.terminate(_identity(2))
    b = recorder.read_capture_state()
    assert b.last_aborted_candidate.identity == _identity(2)
    assert b.last_committed is None
    assert b.revision > a.revision


def test_capture_revision_advances_for_observation_and_event_streams() -> None:
    recorder = SignalTruthRecorder()
    revisions: list[int] = [recorder.read_capture_state().revision]
    recorder.begin_candidate(_plan(1))
    revisions.append(recorder.read_capture_state().revision)
    assert recorder.observe(
        SourceFileFactsEvidence(
            _identity(1), "flac", "flac", PcmTuple(96000, "S32_LE", 2, 24)
        )
    )
    revisions.append(recorder.read_capture_state().revision)
    recorder.record_processing_event(
        ProcessingTruthEvent(
            state=ProcessingTruthState.REQUESTED,
            processing_generation=1,
        )
    )
    revisions.append(recorder.read_capture_state().revision)
    recorder.record_output_family_event(
        OutputFamilyEvent(
            family="managed",
            state=OutputFamilyState.RUNNING,
            execution_id="exec:A",
        )
    )
    captured = recorder.read_capture_state()
    revisions.append(captured.revision)
    assert all(
        left < right for left, right in zip(revisions, revisions[1:], strict=False)
    )
    assert len(captured.processing_events) == 1
    assert len(captured.output_family_events) == 1
    assert captured.candidate.source_file_facts is not None


def test_capture_bundle_is_immutable_and_detached_from_stream_mutations() -> None:
    from dataclasses import FrozenInstanceError

    import pytest

    recorder = SignalTruthRecorder()
    recorder.begin_candidate(_plan(1))
    old = recorder.read_capture_state()
    recorder.record_processing_event(
        ProcessingTruthEvent(
            state=ProcessingTruthState.REQUESTED,
            processing_generation=1,
        )
    )
    current = recorder.read_capture_state()
    assert old.revision < current.revision
    assert old.processing_events == ()
    assert len(current.processing_events) == 1
    with pytest.raises((FrozenInstanceError, AttributeError)):
        old.revision = 100


def test_capture_reads_remain_consistent_during_writer_bursts() -> None:
    recorder = SignalTruthRecorder()
    stop = threading.Event()
    errors: list[str] = []

    def writer() -> None:
        for epoch in range(1, 301):
            recorder.begin_candidate(_plan(epoch))
            assert recorder.commit_candidate(_identity(epoch))
            assert recorder.retire_active(_identity(epoch))
        stop.set()

    worker = threading.Thread(target=writer)
    worker.start()
    previous_revision = -1
    while not stop.is_set():
        capture = recorder.read_capture_state()
        try:
            assert capture.revision >= previous_revision
            previous_revision = capture.revision
            if capture.active is not None:
                assert capture.last_committed is None or (
                    capture.last_committed.identity != capture.active.identity
                )
            if capture.last_committed is not None:
                assert capture.last_committed.identity.execution_generation <= 300
        except AssertionError as error:
            errors.append(str(error))
            break
    worker.join(timeout=5.0)
    assert not worker.is_alive(), "writer stalled"
    assert not errors, errors
    assert recorder.read_capture_state().last_committed.identity == _identity(300)


def _measured_execution(sequence: int) -> ProcessingMeasurement:
    return ProcessingMeasurement(
        execution_id="exec:A",
        plan_id="plan:A",
        sample_peak=0.5,
        estimated_true_peak=0.6,
        worst_channel=0,
        channels=2,
        sample_rate_hz=96_000,
        window="captured",
        evidence_level="observed",
        sequence=sequence,
    )


def test_measurement_cleanup_invalidates_capture_and_notifies() -> None:
    recorder = SignalTruthRecorder()
    recorder.activate_execution("exec:A", plan_id="plan:A")
    recorder.record_processing_measurement(_measured_execution(1))
    captured_before = recorder.read_capture_state()
    revisions: list[int] = []
    recorder.subscribe(lambda: revisions.append(recorder.read_capture_state().revision))

    assert recorder.discard_processing_measurements("exec:A") == 1
    captured_after = recorder.read_capture_state()
    assert captured_after.revision > captured_before.revision
    assert captured_after.processing_measurements == ()
    assert captured_before.processing_measurements == (_measured_execution(1),)
    assert revisions == [captured_after.revision]
    assert recorder.discard_processing_measurements("exec:A") == 0
    assert revisions == [captured_after.revision]


def test_retiring_execution_clears_measurement_with_capture_notification() -> None:
    recorder = SignalTruthRecorder()
    recorder.activate_execution("exec:A", plan_id="plan:A")
    recorder.record_processing_measurement(_measured_execution(2))
    old = recorder.read_capture_state()
    revisions: list[int] = []
    recorder.subscribe(lambda: revisions.append(recorder.read_capture_state().revision))

    assert recorder.retire_execution("exec:A") == 1
    current = recorder.read_capture_state()
    assert current.revision > old.revision
    assert current.processing_measurements == ()
    assert revisions == [current.revision]
    assert recorder.retire_execution("exec:A") == 0
    assert revisions == [current.revision]
