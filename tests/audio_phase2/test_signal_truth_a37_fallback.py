"""A37: degraded readback can preserve recorder writes, but NEVER a display ACK."""

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


class MissingCapture:
    def __init__(self):
        self.events = []

    def record_output_family_event(self, event):
        self.events.append(event)


def test_legacy_writer_preserves_event_but_never_certifies_delivery():
    writer, ledger = MissingCapture(), PublicationLedger()
    seen = OutputFamilyEvent(
        family="managed", state=OutputFamilyState.RUNNING, execution_id="exec:X"
    )
    result = publish_family_fact(
        ledger=ledger,
        key=PublicationKey("managed", "exec:X", 4),
        recorder=writer,
        build_event=lambda: seen,
    )
    assert writer.events == [seen]
    assert result.status is PublicationStatus.FAILED
    assert result.reason == "CAPTURE_BEFORE_FAILED"
    assert (
        project_family_delivery(
            ledger,
            recorder=writer,
            family="managed",
            execution_id="exec:X",
            owner_epoch=4,
        )
        is DisplayClaim.UNVERIFIED
    )


def test_missing_capture_rejects_foreign_family_before_write():
    writer, ledger = MissingCapture(), PublicationLedger()
    event = OutputFamilyEvent(
        family="dop", state=OutputFamilyState.RUNNING, execution_id="exec:X"
    )
    result = publish_family_fact(
        ledger=ledger,
        key=PublicationKey("managed", "exec:X", 4),
        recorder=writer,
        build_event=lambda: event,
    )
    assert writer.events == []
    assert result.reason == "EVENT_SCOPE_MISMATCH"


def test_after_failing_capture_does_not_fabricate_recorder_ack():
    class AbsentAfter(SignalTruthRecorder):
        def __init__(self):
            super().__init__()
            self._read_count = 0

        def read_capture_state(self):
            self._read_count += 1
            if self._read_count > 1:
                raise RuntimeError("readback failed")
            return super().read_capture_state()

    writer, ledger = AbsentAfter(), PublicationLedger()
    ev = OutputFamilyEvent(
        family="native_dsd", state=OutputFamilyState.RUNNING, execution_id="exec:X"
    )
    result = publish_family_fact(
        ledger=ledger,
        key=PublicationKey("native_dsd", "exec:X", 3),
        recorder=writer,
        build_event=lambda: ev,
    )
    assert result.status is PublicationStatus.FAILED
    assert result.reason == "CAPTURE_AFTER_FAILED"
    assert writer.output_family_events[-1] is ev


def test_failed_terminal_readback_revokes_old_running_ack():
    ledger, writer = PublicationLedger(), SignalTruthRecorder()
    key = PublicationKey("managed", "exec:X", 9)
    ev = OutputFamilyEvent(
        family="managed", state=OutputFamilyState.RUNNING, execution_id="exec:X"
    )
    assert (
        publish_family_fact(
            ledger=ledger, key=key, recorder=writer, build_event=lambda: ev
        ).status
        is PublicationStatus.ACCEPTED_IN_RECORDER
    )
    assert (
        project_family_delivery(
            ledger,
            recorder=writer,
            family="managed",
            execution_id="exec:X",
            owner_epoch=9,
        )
        is DisplayClaim.OBSERVED_RUNNING
    )
    broken = MissingCapture()
    terminal = OutputFamilyEvent(
        family="managed", state=OutputFamilyState.UNAVAILABLE, execution_id="exec:X"
    )
    result = publish_family_fact(
        ledger=ledger, key=key, recorder=broken, build_event=lambda: terminal
    )
    assert terminal in broken.events
    assert result.status is PublicationStatus.FAILED
    assert (
        project_family_delivery(
            ledger,
            recorder=writer,
            family="managed",
            execution_id="exec:X",
            owner_epoch=9,
        )
        is DisplayClaim.UNVERIFIED
    )


def test_internal_publisher_failure_invalidates_previous_positive():
    rec, ledger = SignalTruthRecorder(), PublicationLedger()
    key = PublicationKey("managed", "exec:X", 4)
    ev = OutputFamilyEvent(
        family="managed", state=OutputFamilyState.RUNNING, execution_id="exec:X"
    )
    publish_family_fact(ledger=ledger, key=key, recorder=rec, build_event=lambda: ev)
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:X", owner_epoch=4
        )
        is DisplayClaim.OBSERVED_RUNNING
    )
    ledger.invalidate_family("managed")
    assert ledger.current("managed").reason == "PUBLICATION_INTERNAL_ERROR"
    assert (
        project_family_delivery(
            ledger, recorder=rec, family="managed", execution_id="exec:X", owner_epoch=4
        )
        is DisplayClaim.UNVERIFIED
    )
