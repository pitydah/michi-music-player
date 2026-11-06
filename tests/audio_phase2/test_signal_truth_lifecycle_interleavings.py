"""AP2-F11 A09: deterministic lifecycle interleaving regression scenarios.

The tests operate only on the existing Signal Truth recorder. They reproduce
identity and lost-update races without timers, hardware, GStreamer, or Qt.
They do not certify owner-thread delivery to presentation.
"""

from __future__ import annotations

import threading

from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    DecodedRuntimeEvidence,
    OutputPlanEvidence,
    SignalTruthIdentity,
    SignalTruthRecorder,
    SourceFileFactsEvidence,
)


def _identity(number: int) -> SignalTruthIdentity:
    return SignalTruthIdentity(
        plan_id="fixed-plan",
        execution_generation=number,
        port_generation=7,
        binding_generation=3,
        stable_device_id="device-test",
        stable_endpoint_signature="endpoint-test",
    )


def _pcm() -> PcmTuple:
    return PcmTuple(96_000, "S32_LE", 2, 24)


def _plan(identity: SignalTruthIdentity) -> OutputPlanEvidence:
    return OutputPlanEvidence(
        identity=identity,
        requested_pcm=_pcm(),
        sink_factory="alsasink",
        sink_device="hw:TEST,0",
        fixed_gain_required=True,
    )


def _paused_observe(monkeypatch, recorder, event):
    entered = threading.Event()
    resume = threading.Event()
    original = SignalTruthRecorder._with_event
    results: list[bool] = []
    errors: list[BaseException] = []

    def hook(snapshot, current):
        if current is event:
            entered.set()
            if not resume.wait(5):
                raise TimeoutError("test hook timed out waiting for resume")
        return original(snapshot, current)

    monkeypatch.setattr(SignalTruthRecorder, "_with_event", staticmethod(hook))

    def worker() -> None:
        try:
            results.append(recorder.observe(event))
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=worker, name="a09-evidence-worker")
    thread.start()
    assert entered.wait(5), "evidence calculation did not enter the hook"
    return resume, thread, results, errors


def _finish(resume, thread, errors):
    resume.set()
    thread.join(5)
    assert not thread.is_alive(), "worker did not finish"
    assert not errors, errors


def test_superseded_candidate_cannot_be_resurrected(monkeypatch) -> None:
    recorder = SignalTruthRecorder()
    old, newer = _identity(1), _identity(2)
    recorder.begin_candidate(_plan(old))
    late = DecodedRuntimeEvidence(old, _pcm())
    resume, thread, results, errors = _paused_observe(monkeypatch, recorder, late)
    try:
        recorder.begin_candidate(_plan(newer))
    finally:
        _finish(resume, thread, errors)
    assert results == [False]
    assert recorder.candidate_snapshot.identity == newer
    assert recorder.candidate_snapshot.decoded_runtime is None


def test_concurrent_observations_cannot_erase_each_other(monkeypatch) -> None:
    recorder = SignalTruthRecorder()
    current = _identity(1)
    recorder.begin_candidate(_plan(current))
    decoded = DecodedRuntimeEvidence(current, _pcm())
    resume, thread, results, errors = _paused_observe(monkeypatch, recorder, decoded)
    source = SourceFileFactsEvidence(
        identity=current, container="flac", codec="flac", nominal_pcm=_pcm()
    )
    try:
        assert recorder.observe(source)
    finally:
        _finish(resume, thread, errors)
    assert results == [True]
    assert recorder.candidate_snapshot.decoded_runtime == decoded
    assert recorder.candidate_snapshot.source_file_facts == source


def test_commit_during_evidence_calculation_keeps_active_identity(monkeypatch) -> None:
    recorder = SignalTruthRecorder()
    current = _identity(1)
    recorder.begin_candidate(_plan(current))
    decoded = DecodedRuntimeEvidence(current, _pcm())
    resume, thread, results, errors = _paused_observe(monkeypatch, recorder, decoded)
    try:
        assert recorder.commit_candidate(current)
    finally:
        _finish(resume, thread, errors)
    assert results == [True]
    assert recorder.active_snapshot is not None
    assert recorder.active_snapshot.identity == current
    assert recorder.active_snapshot.decoded_runtime == decoded
    # The callback cannot resurrect the already-committed candidate.
    try:
        recorder.candidate_snapshot
    except RuntimeError:
        pass
    else:
        raise AssertionError("candidate resurrected after commit")


def test_retired_active_cannot_be_resurrected(monkeypatch) -> None:
    recorder = SignalTruthRecorder()
    current = _identity(1)
    recorder.begin_candidate(_plan(current))
    assert recorder.commit_candidate(current)
    decoded = DecodedRuntimeEvidence(current, _pcm())
    resume, thread, results, errors = _paused_observe(monkeypatch, recorder, decoded)
    try:
        assert recorder.retire_active(current)
    finally:
        _finish(resume, thread, errors)
    assert results == [False]
    assert recorder.active_snapshot is None
    assert recorder.last_snapshot is not None
    assert recorder.last_snapshot.identity == current
    assert recorder.last_snapshot.decoded_runtime is None


def test_snapshot_calculation_does_not_hold_lifecycle_lock(monkeypatch) -> None:
    recorder = SignalTruthRecorder()
    old, newer = _identity(1), _identity(2)
    recorder.begin_candidate(_plan(old))
    decoded = DecodedRuntimeEvidence(old, _pcm())
    resume, thread, _, errors = _paused_observe(monkeypatch, recorder, decoded)
    advanced = threading.Event()

    def replace_candidate() -> None:
        recorder.begin_candidate(_plan(newer))
        advanced.set()

    replacing = threading.Thread(target=replace_candidate)
    try:
        replacing.start()
        assert advanced.wait(1), "candidate replacement blocked on evidence work"
    finally:
        resume.set()
        replacing.join(5)
        thread.join(5)
    assert not replacing.is_alive()
    assert not thread.is_alive()
    assert not errors, errors
    assert recorder.candidate_snapshot.identity == newer
