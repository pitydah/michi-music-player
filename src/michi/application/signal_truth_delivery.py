"""Candidate ST-02B publication proof, not a replacement for SignalTruthRecorder.

A recorder's ``record_output_family_event`` returns None. Its successful return
is *not* an acknowledgement. This auxiliary owner-side ledger is a passive
publication-health read model. Integrating it in OutputSession/Qt requires
cross-phase owner approval; do not treat this module alone as that integration.
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from michi.domain.signal_truth import OutputFamilyEvent, OutputFamilyState


class PublicationStatus(StrEnum):
    IN_FLIGHT = "IN_FLIGHT"
    ACCEPTED_IN_RECORDER = "ACCEPTED_IN_RECORDER"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class DisplayClaim(StrEnum):
    OBSERVED_RUNNING = "OBSERVED_RUNNING"
    OBSERVED_READY = "OBSERVED_READY"
    OBSERVED_TERMINAL = "OBSERVED_TERMINAL"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True, slots=True)
class PublicationKey:
    family: str
    execution_id: str | None
    owner_epoch: int

    def __post_init__(self) -> None:
        if self.family not in {
            "managed",
            "native_dsd",
            "dop",
            "dsd_pcm",
            "direct",
            "shared",
        }:
            raise ValueError("unsupported publication family")
        if type(self.owner_epoch) is not int or self.owner_epoch <= 0:
            raise ValueError("positive owner epoch required")
        if self.execution_id is not None and (
            not isinstance(self.execution_id, str) or not self.execution_id.strip()
        ):
            raise ValueError("invalid execution id")


@dataclass(frozen=True, slots=True)
class PublicationView:
    sequence: int
    key: PublicationKey
    status: PublicationStatus
    observed_state: str | None
    reason: str | None
    capture_revision: int | None


class CaptureRecorder(Protocol):
    def read_capture_state(self) -> object: ...
    def record_output_family_event(self, event: OutputFamilyEvent) -> None: ...


class PublicationLedger:
    """Small, bounded passive cache; the recorder remains authoritative.

    A later attempt for the same output family supersedes earlier evidence.
    Owner epochs are monotonic per family. Listeners run outside the ledger
    lock and *must* be wired by OutputSession to a safe UI notification path.
    """

    def __init__(self, *, capacity: int = 64) -> None:
        if type(capacity) is not int or not 1 <= capacity <= 1024:
            raise ValueError("invalid capacity")
        self._lock = threading.RLock()
        self._capacity = capacity
        self._current: dict[str, PublicationView] = {}
        self._history: deque[PublicationView] = deque(maxlen=capacity)
        self._proofs: dict[str, tuple[int, CaptureRecorder, OutputFamilyEvent]] = {}
        self._sequence = 0
        self._listeners: list[Callable[[], None]] = []
        self._notification_failures = 0

    def subscribe(self, callback: Callable[[], None]) -> None:
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    @property
    def notification_failures(self) -> int:
        with self._lock:
            return self._notification_failures

    @property
    def history(self) -> tuple[PublicationView, ...]:
        with self._lock:
            return tuple(self._history)

    def current(self, family: str) -> PublicationView | None:
        with self._lock:
            return self._current.get(family)

    def invalidate_family(self, family: str) -> None:
        """Emergency fail-closed fence if the publisher itself raises.

        This is a NEGATIVE observation only. The ledger never writes the
        recorder or changes an audio session. Even if there is no current
        attempt, any previously accepted proof is invalidated.
        """
        with self._lock:
            prior = self._current.get(family)
            if prior is None:
                return
            view = PublicationView(
                prior.sequence,
                prior.key,
                PublicationStatus.FAILED,
                None,
                "PUBLICATION_INTERNAL_ERROR",
                None,
            )
            self._current[family] = view
            self._proofs.pop(family, None)
            self._history.append(view)
        self._notify()

    def begin(self, key: PublicationKey) -> PublicationView:
        with self._lock:
            previous = self._current.get(key.family)
            if previous is not None and key.owner_epoch < previous.key.owner_epoch:
                raise ValueError("stale output-owner epoch")
            self._sequence += 1
            view = PublicationView(
                self._sequence, key, PublicationStatus.IN_FLIGHT, None, None, None
            )
            self._current[key.family] = view
            self._proofs.pop(key.family, None)
            self._history.append(view)
        self._notify()
        return view

    def resolve(
        self,
        attempt: PublicationView,
        *,
        accepted: bool,
        reason: str | None = None,
        event: OutputFamilyEvent | None = None,
        revision: int | None = None,
        recorder: CaptureRecorder | None = None,
    ) -> PublicationView:
        # The caller must never supply arbitrary exception messages in reason.
        if accepted and (
            event is None or revision is None or revision <= 0 or recorder is None
        ):
            raise ValueError("positive publication requires recorder proof")
        with self._lock:
            current = self._current.get(attempt.key.family)
            if current is None or current.sequence != attempt.sequence:
                return PublicationView(
                    attempt.sequence,
                    attempt.key,
                    PublicationStatus.SUPERSEDED,
                    None,
                    "SUPERSEDED",
                    None,
                )
            view = PublicationView(
                attempt.sequence,
                attempt.key,
                (
                    PublicationStatus.ACCEPTED_IN_RECORDER
                    if accepted
                    else PublicationStatus.FAILED
                ),
                event.state.value if accepted and event is not None else None,
                None if accepted else (reason or "PUBLICATION_UNVERIFIED"),
                revision if accepted else None,
            )
            self._current[attempt.key.family] = view
            if accepted:
                self._proofs[attempt.key.family] = (attempt.sequence, recorder, event)
            else:
                self._proofs.pop(attempt.key.family, None)
            self._history.append(view)
        self._notify()
        return view

    def _notify(self) -> None:
        with self._lock:
            callbacks = tuple(self._listeners)
        for callback in callbacks:
            try:
                callback()
            except Exception:  # observation failure never interrupts output
                with self._lock:
                    self._notification_failures += 1


def publish_family_fact(
    *,
    ledger: PublicationLedger,
    key: PublicationKey,
    recorder: CaptureRecorder | None,
    build_event: Callable[[], OutputFamilyEvent],
) -> PublicationView:
    """Conservatively prove acceptance via the recorder's coherent capture.

    The recorder may publish to subscribers before returning. The ledger first
    notifies IN_FLIGHT and then notifies the final receipt, including on errors.
    A None return from record_output_family_event is NOT an acknowledgement.
    """
    attempt = ledger.begin(key)
    if recorder is None:
        return ledger.resolve(attempt, accepted=False, reason="RECORDER_UNAVAILABLE")
    try:
        before = recorder.read_capture_state()
    except Exception:
        # Compatibility for recorder test doubles / degraded observers: a
        # writer without coherent readback may still accept the output fact,
        # but the UI can NEVER claim delivery has been certified. This also
        # preserves the original production event-write side effect.
        try:
            event = build_event()
        except Exception:
            return ledger.resolve(attempt, accepted=False, reason="EVENT_BUILD_FAILED")
        if not isinstance(event, OutputFamilyEvent) or (
            event.family != key.family or event.execution_id != key.execution_id
        ):
            return ledger.resolve(
                attempt, accepted=False, reason="EVENT_SCOPE_MISMATCH"
            )
        try:
            recorder.record_output_family_event(event)
        except Exception:
            return ledger.resolve(attempt, accepted=False, reason="RECORDER_REJECTED")
        return ledger.resolve(attempt, accepted=False, reason="CAPTURE_BEFORE_FAILED")
    try:
        event = build_event()
    except Exception:
        return ledger.resolve(attempt, accepted=False, reason="EVENT_BUILD_FAILED")
    if not isinstance(event, OutputFamilyEvent) or (
        event.family != key.family or event.execution_id != key.execution_id
    ):
        return ledger.resolve(attempt, accepted=False, reason="EVENT_SCOPE_MISMATCH")
    try:
        recorder.record_output_family_event(event)
    except Exception:
        return ledger.resolve(attempt, accepted=False, reason="RECORDER_REJECTED")
    try:
        after = recorder.read_capture_state()
        accepted = (
            type(after.revision) is int
            and after.revision > before.revision
            and any(item is event for item in after.output_family_events)
        )
    except Exception:
        return ledger.resolve(attempt, accepted=False, reason="CAPTURE_AFTER_FAILED")
    if not accepted:
        return ledger.resolve(attempt, accepted=False, reason="APPEND_NOT_PROVEN")
    return ledger.resolve(
        attempt, accepted=True, event=event, revision=after.revision, recorder=recorder
    )


def project_family_delivery(
    ledger: PublicationLedger,
    *,
    recorder: CaptureRecorder | None,
    family: str,
    execution_id: str | None,
    owner_epoch: int,
) -> DisplayClaim:
    """Positive UI claims need both a delivery ACK and retained recorder fact.

    A dropped ring entry, a newer terminal receipt, or a failure to read the
    recorder causes UNVERIFIED, even if the earlier ledger entry was accepted.
    """
    if recorder is None or execution_id is None:
        return DisplayClaim.UNVERIFIED
    try:
        key = PublicationKey(family, execution_id, owner_epoch)
    except ValueError:
        return DisplayClaim.UNVERIFIED
    view = ledger.current(family)
    if view is None or view.key != key:
        return DisplayClaim.UNVERIFIED
    if view.status is not PublicationStatus.ACCEPTED_IN_RECORDER:
        return DisplayClaim.UNVERIFIED
    with ledger._lock:
        proof = ledger._proofs.get(family)
    if proof is None or proof[0] != view.sequence or proof[1] is not recorder:
        return DisplayClaim.UNVERIFIED
    try:
        capture = recorder.read_capture_state()
        related = tuple(
            event
            for event in capture.output_family_events
            if event.family == family and event.execution_id == execution_id
        )
        if (
            capture.revision < view.capture_revision
            or not related
            or related[-1] is not proof[2]
        ):
            return DisplayClaim.UNVERIFIED
    except Exception:
        return DisplayClaim.UNVERIFIED
    # Avoid accepting an older observed value if the owner began a new attempt
    # while the capture was read.
    if ledger.current(family) != view:
        return DisplayClaim.UNVERIFIED
    if view.observed_state == OutputFamilyState.RUNNING.value:
        return DisplayClaim.OBSERVED_RUNNING
    if view.observed_state == OutputFamilyState.READY.value:
        return DisplayClaim.OBSERVED_READY
    return DisplayClaim.OBSERVED_TERMINAL
