"""A26 owner's proposed publication-observability gate (isolated real domain)."""

from __future__ import annotations

from dataclasses import replace
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from michi.application.signal_truth_delivery import (
    DisplayClaim,
    PublicationKey,
    PublicationLedger,
    PublicationStatus,
    project_family_delivery,
    publish_family_fact,
)
from michi.domain.signal_truth import (
    OutputFamilyEvent,
    OutputFamilyState,
    SignalTruthRecorder,
)


def _event(family="managed", execution_id="exec:A", state=OutputFamilyState.RUNNING):
    return OutputFamilyEvent(
        family=family,
        execution_id=execution_id,
        state=state,
        runtime_identity={"host_generation": 10},
    )


def _run(rec, ledger=None, event=None, epoch=1):
    event = event or _event()
    ledger = ledger or PublicationLedger()
    key = PublicationKey(event.family, event.execution_id, epoch)
    return ledger, publish_family_fact(
        ledger=ledger,
        key=key,
        recorder=rec,
        build_event=lambda: event,
    )


def test_acceptance_of_actual_recorder_requires_capture_and_identical_event():
    rec = SignalTruthRecorder()
    ledger, view = _run(rec)
    assert view.status is PublicationStatus.ACCEPTED_IN_RECORDER
    assert view.capture_revision == rec.read_capture_state().revision
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=1
        )
        is DisplayClaim.OBSERVED_RUNNING
    )


def test_missing_recorder_is_not_success():
    rec = None
    ledger, view = _run(None)
    assert view.status is PublicationStatus.FAILED
    assert view.reason == "RECORDER_UNAVAILABLE"
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=1
        )
        is DisplayClaim.UNVERIFIED
    )


def test_invalid_event_recorder_validation_fails_closed():
    ledger, view = PublicationLedger(), None
    view = publish_family_fact(
        ledger=ledger,
        key=PublicationKey("managed", "exec:A", 1),
        recorder=SignalTruthRecorder(),
        build_event=lambda: OutputFamilyEvent(
            family="managed",
            state=OutputFamilyState.RUNNING,
            execution_id="exec:A",
            bit_perfect=True,
        ),
    )
    assert view.status is PublicationStatus.FAILED
    assert view.reason == "RECORDER_REJECTED"


def test_factory_exception_is_sanitized():
    def bad():
        raise RuntimeError("secret path /home/user/music & token")

    ledger = PublicationLedger()
    v = publish_family_fact(
        ledger=ledger,
        key=PublicationKey("managed", "exec:A", 1),
        recorder=SignalTruthRecorder(),
        build_event=bad,
    )
    assert v.reason == "EVENT_BUILD_FAILED"
    assert "/home/" not in repr(v)


class BrokenRecorder(SignalTruthRecorder):
    def record_output_family_event(self, event):
        raise RuntimeError("broken")


class SilentRecorder(SignalTruthRecorder):
    def record_output_family_event(self, event):
        return None


class NoCaptureRecorder(SignalTruthRecorder):
    def read_capture_state(self):
        raise RuntimeError("capture broken")


@pytest.mark.parametrize(
    "recorder,reason",
    [
        (BrokenRecorder, "RECORDER_REJECTED"),
        (SilentRecorder, "APPEND_NOT_PROVEN"),
        (NoCaptureRecorder, "CAPTURE_BEFORE_FAILED"),
    ],
)
def test_no_fabricated_acceptance(recorder, reason):
    rec = recorder()
    ledger, result = _run(rec)
    assert result.status is PublicationStatus.FAILED
    assert result.reason == reason
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=1
        )
        is DisplayClaim.UNVERIFIED
    )


def test_terminal_drop_revokes_stale_running_claim():
    rec, ledger = SilentRecorder(), PublicationLedger()
    accepted = SignalTruthRecorder()
    _, v1 = _run(accepted, ledger=ledger, epoch=1)
    assert v1.status is PublicationStatus.ACCEPTED_IN_RECORDER
    _, v2 = _run(
        rec, ledger=ledger, event=_event(state=OutputFamilyState.UNAVAILABLE), epoch=1
    )
    assert v2.status is PublicationStatus.FAILED
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=1
        )
        is DisplayClaim.UNVERIFIED
    )


def test_terminal_accepted_clears_running_without_marking_error():
    rec, ledger = SignalTruthRecorder(), PublicationLedger()
    _run(rec, ledger=ledger)
    _, view = _run(rec, ledger=ledger, event=_event(state=OutputFamilyState.RELEASED))
    assert view.status is PublicationStatus.ACCEPTED_IN_RECORDER
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=1
        )
        is DisplayClaim.OBSERVED_TERMINAL
    )


def test_ready_is_distinct_from_running():
    rec, ledger = SignalTruthRecorder(), PublicationLedger()
    _run(rec, ledger=ledger, event=_event(state=OutputFamilyState.READY))
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=1
        )
        is DisplayClaim.OBSERVED_READY
    )


def test_new_output_epoch_invalidates_old_even_if_same_plan_and_id():
    rec, ledger = SignalTruthRecorder(), PublicationLedger()
    _run(rec, ledger=ledger, epoch=1)
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=2
        )
        is DisplayClaim.UNVERIFIED
    )
    _run(rec, ledger=ledger, epoch=2)
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=1
        )
        is DisplayClaim.UNVERIFIED
    )


def test_reject_stale_epoch():
    ledger = PublicationLedger()
    _run(SignalTruthRecorder(), ledger=ledger, epoch=10)
    with pytest.raises(ValueError, match="stale"):
        _run(SignalTruthRecorder(), ledger=ledger, epoch=9)


def test_wrong_family_or_execution_is_refused():
    ledger = PublicationLedger()
    view = publish_family_fact(
        ledger=ledger,
        key=PublicationKey("managed", "exec:A", 1),
        recorder=SignalTruthRecorder(),
        build_event=lambda: _event(family="dop"),
    )
    assert view.reason == "EVENT_SCOPE_MISMATCH"
    assert view.status is PublicationStatus.FAILED


def test_callback_before_recorder_ack_sees_in_flight_and_final_callback():
    ledger, rec = PublicationLedger(), SignalTruthRecorder()
    observed = []
    ledger.subscribe(lambda: observed.append(ledger.current("managed").status))
    rec.subscribe(lambda: observed.append(ledger.current("managed").status))
    _run(rec, ledger=ledger)
    assert observed == [
        PublicationStatus.IN_FLIGHT,
        PublicationStatus.IN_FLIGHT,
        PublicationStatus.ACCEPTED_IN_RECORDER,
    ]


def test_bad_notification_does_not_break_audio_publication():
    ledger, rec = PublicationLedger(), SignalTruthRecorder()
    ledger.subscribe(lambda: 1 / 0)
    _, view = _run(rec, ledger=ledger)
    assert view.status is PublicationStatus.ACCEPTED_IN_RECORDER
    assert ledger.notification_failures == 2


def test_reentrant_listener_does_not_deadlock():
    ledger = PublicationLedger()
    ledger.subscribe(lambda: ledger.current("managed"))
    ledger.subscribe(lambda: ledger.unsubscribe(lambda: None))
    _, v = _run(SignalTruthRecorder(), ledger=ledger)
    assert v.status is PublicationStatus.ACCEPTED_IN_RECORDER


def test_late_resolution_does_not_erase_newer_attempt():
    ledger = PublicationLedger()
    key = PublicationKey("managed", "exec:A", 1)
    a = ledger.begin(key)
    b = ledger.begin(PublicationKey("managed", "exec:B", 2))
    old = ledger.resolve(a, accepted=False, reason="RECORDER_REJECTED")
    assert old.status is PublicationStatus.SUPERSEDED
    assert ledger.current("managed").sequence == b.sequence
    assert ledger.current("managed").status is PublicationStatus.IN_FLIGHT


def test_history_is_bounded_even_after_many_attempts():
    rec, ledger = SignalTruthRecorder(), PublicationLedger(capacity=4)
    for n in range(1, 120):
        _run(rec, ledger=ledger, epoch=n)
    assert len(ledger.history) == 4
    assert ledger.current("managed").key.owner_epoch == 119


def test_capture_without_revision_increment_cannot_ack():
    class Fake:
        def __init__(self):
            self.e = None

        def read_capture_state(self):
            return SimpleNamespace(revision=1, output_family_events=(self.e,))

        def record_output_family_event(self, e):
            self.e = e

    ledger, view = _run(Fake())
    assert view.reason == "APPEND_NOT_PROVEN"


def test_capture_with_different_event_object_cannot_ack():
    class Fake:
        def __init__(self):
            self.revision = 10
            self.e = None

        def read_capture_state(self):
            return SimpleNamespace(
                revision=self.revision, output_family_events=(self.e,)
            )

        def record_output_family_event(self, e):
            self.e = replace(e)
            self.revision += 1

    ledger, view = _run(Fake())
    assert view.reason == "APPEND_NOT_PROVEN"


def test_bad_after_capture_fails_closed():
    class Fake(SignalTruthRecorder):
        def __init__(self):
            super().__init__()
            self.n = 0

        def read_capture_state(self):
            self.n += 1
            if self.n > 1:
                raise RuntimeError("postcapture broken")
            return super().read_capture_state()

    _, v = _run(Fake())
    assert v.reason == "CAPTURE_AFTER_FAILED"


def test_event_chain_receives_none_return_but_still_can_be_accepted():
    rec = SignalTruthRecorder()
    assert rec.record_output_family_event(_event()) is None
    _, v = _run(rec)
    assert v.status is PublicationStatus.ACCEPTED_IN_RECORDER


@pytest.mark.parametrize("bad", [0, -1, True, "1"])
def test_invalid_owner_epoch_refused(bad):
    with pytest.raises(ValueError):
        PublicationKey("managed", "exec:A", bad)


def test_concurrent_worker_inflight_never_claims_running():
    entered, resume = Event(), Event()

    class Delayed(SignalTruthRecorder):
        def record_output_family_event(self, event):
            entered.set()
            assert resume.wait(5)
            super().record_output_family_event(event)

    ledger, rec = PublicationLedger(), Delayed()
    result = []
    worker = Thread(target=lambda: result.append(_run(rec, ledger=ledger)[1]))
    worker.start()
    assert entered.wait(2)
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=1
        )
        is DisplayClaim.UNVERIFIED
    )
    resume.set()
    worker.join(4)
    assert not worker.is_alive()
    assert result[0].status is PublicationStatus.ACCEPTED_IN_RECORDER


def test_ring_eviction_removes_positive_even_after_accepted_write():
    rec, ledger = SignalTruthRecorder(), PublicationLedger()
    _run(rec, ledger=ledger)
    for i in range(65):
        rec.record_output_family_event(_event(family="other", execution_id=f"x:{i}"))
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=1
        )
        is DisplayClaim.UNVERIFIED
    )


def test_external_terminal_without_ledger_invalidates_old_positive():
    rec, ledger = SignalTruthRecorder(), PublicationLedger()
    _run(rec, ledger=ledger)
    rec.record_output_family_event(_event(state=OutputFamilyState.UNAVAILABLE))
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:A", owner_epoch=1
        )
        is DisplayClaim.UNVERIFIED
    )


def test_wrong_recorder_cannot_reuse_acceptance_token():
    rec, ledger = SignalTruthRecorder(), PublicationLedger()
    _run(rec, ledger=ledger)
    other = SignalTruthRecorder()
    other.record_output_family_event(_event())
    assert (
        project_family_delivery(
            ledger,
            recorder=other,
            family="managed",
            execution_id="exec:A",
            owner_epoch=1,
        )
        is DisplayClaim.UNVERIFIED
    )


def test_repeated_family_switch_requires_explicit_current_scope():
    rec, ledger = SignalTruthRecorder(), PublicationLedger()
    _run(rec, ledger=ledger)
    _run(rec, ledger=ledger, event=_event(family="dop", execution_id="exec:B"), epoch=2)
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="dop", execution_id="exec:B", owner_epoch=2
        )
        is DisplayClaim.OBSERVED_RUNNING
    )
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:B", owner_epoch=2
        )
        is DisplayClaim.UNVERIFIED
    )


def test_wrong_exec_identity_refused_even_when_family_matches():
    ledger = PublicationLedger()
    view = publish_family_fact(
        ledger=ledger,
        key=PublicationKey("managed", "exec:B", 1),
        recorder=SignalTruthRecorder(),
        build_event=_event,
    )
    assert view.reason == "EVENT_SCOPE_MISMATCH"


def test_boolean_epoch_is_not_a_valid_generation():
    assert (
        project_family_delivery(
            PublicationLedger(),
            recorder=SignalTruthRecorder(),
            family="managed",
            execution_id="exec:A",
            owner_epoch=True,
        )
        is DisplayClaim.UNVERIFIED
    )
