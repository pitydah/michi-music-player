"""AP2-F05 Corrective Seal — queue identity, atomic publish, abort truth,
lifecycle. Every intent must complete EXACTLY once; no stale EFFECTIVE."""

from __future__ import annotations

import threading
import time

import pytest

from michi.application.audio_processing_service import (
    AudioProcessingService,
    ProcessingStaleCommitError,
    ProcessingTransactionError,
)
from michi.infrastructure.audio_processing.native_mapping import (
    NativeProcessingMapping,
)
from tests.audio_phase2.test_processing_capabilities import (
    _BlockingTransport,
    _fake_capability_query,
    _FakeProcessingTransport,
    _InlineExecutor,
    _preamp_graph,
    _signal,
    _transaction_plan,
)


class _CompletionRecorder:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.results: list[dict] = []
        self.failures: list[Exception] = []
        self.completed_counts: dict[int, int] = {}

    def done(self, value) -> None:
        with self.lock:
            self.results.append(value)
            revision = int(value["revision"]) if value else -1
            self.completed_counts[revision] = self.completed_counts.get(revision, 0) + 1

    def failed(self, error: Exception) -> None:
        with self.lock:
            self.failures.append(error)

    @property
    def total(self) -> int:
        with self.lock:
            return len(self.results) + len(self.failures)

    def wait(self, total: int, timeout: float = 8.0) -> None:
        deadline = time.monotonic() + timeout
        while self.total < total and time.monotonic() < deadline:
            time.sleep(0.01)


def _service(transport) -> AudioProcessingService:
    return AudioProcessingService(
        capability_query=_fake_capability_query,
        native_mapping=NativeProcessingMapping(),
        transport=transport,
    )


def _apply(service, recorder) -> None:
    service.apply_processing_async(
        _preamp_graph(),
        _signal(),
        on_done=recorder.done,
        on_failed=recorder.failed,
        async_submit=_InlineExecutor().submit,
    )


def test_queued_intent_drop_completes_the_intent_not_the_work() -> None:
    """Regression for the P0: the dropped tuple carried ``run`` and was
    called as a completion. The queued intent must receive DSP_STALE_INTENT
    exactly once and must never execute natively."""
    transport = _BlockingTransport()
    service = _service(transport)
    recorder = _CompletionRecorder()
    _apply(service, recorder)  # intent 1 starts and blocks
    assert transport.started.wait(3.0)
    _apply(service, recorder)  # intent 2 queues
    _apply(service, recorder)  # intent 3 supersedes intent 2 (queued drop)
    # The dropped queued intent is completed immediately, typed.
    assert recorder.total == 1
    assert len(recorder.failures) == 1
    assert isinstance(recorder.failures[0], ProcessingStaleCommitError)
    assert recorder.failures[0].code == "DSP_STALE_INTENT"
    assert transport.prepared == [] or len(transport.prepared) <= 1

    transport.release.set()
    recorder.wait(3)
    # Exactly one completion per intent: 3 total, no double delivery.
    assert recorder.total == 3, (recorder.results, recorder.failures)
    assert len(recorder.results) + len(recorder.failures) == 3
    assert service.effective_state.value == "effective"
    assert service.effective_revision == service.requested_revision


def test_ten_rapid_presets_complete_exactly_once_and_only_newest_wins() -> None:
    transport = _BlockingTransport()
    service = _service(transport)
    recorder = _CompletionRecorder()
    _apply(service, recorder)
    assert transport.started.wait(3.0)
    for _ in range(9):
        _apply(service, recorder)
    transport.release.set()
    recorder.wait(10)
    assert recorder.total == 10, (recorder.results, recorder.failures)
    # The newest intent is the only one allowed to be effective.
    assert service.effective_state.value == "effective"
    assert service.effective_revision == service.requested_revision
    for revision, count in recorder.completed_counts.items():
        assert count == 1, (revision, count)
    stale_codes = {failure.code for failure in recorder.failures}
    assert stale_codes <= {"DSP_STALE_INTENT", "DSP_STALE_COMMIT"}


def test_apply_then_bypass_and_bypass_then_apply_end_coherent() -> None:
    transport = _FakeProcessingTransport()
    service = _service(transport)
    recorder = _CompletionRecorder()

    class _Bypass(_FakeProcessingTransport):
        def bypass_processing(self) -> dict:
            return {"bypassed": True, "removed": True}

    transport = _Bypass()
    service = _service(transport)
    _apply(service, recorder)
    recorder.wait(1)
    assert recorder.results
    service.disable_processing_async(
        on_done=lambda value: recorder.done({"revision": -2, "value": value}),
        on_failed=recorder.failed,
        async_submit=_InlineExecutor().submit,
    )
    recorder.wait(2)
    assert service.effective_state.value == "bypassed"

    _apply(service, recorder)
    recorder.wait(3)
    assert service.effective_state.value == "effective"
    assert recorder.total == 3


def test_host_loss_while_intents_are_pending_never_publishes_effective() -> None:
    transport = _BlockingTransport()
    service = _service(transport)
    recorder = _CompletionRecorder()
    _apply(service, recorder)
    assert transport.started.wait(3.0)
    _apply(service, recorder)
    service.mark_host_lost("SIGKILL")
    transport.dead = True
    transport.release.set()
    recorder.wait(2, timeout=6.0)
    assert service.effective_state.value != "effective"
    assert service.effective_plan_id is None
    assert recorder.total == 2


def test_shutdown_completes_pending_intents_with_dsp_shutdown() -> None:
    transport = _BlockingTransport()
    service = _service(transport)
    recorder = _CompletionRecorder()
    _apply(service, recorder)
    assert transport.started.wait(3.0)
    _apply(service, recorder)  # still queued
    started = time.monotonic()
    service.shutdown(timeout_s=2.0)
    assert time.monotonic() - started < 3.0  # bounded join, never waits on IPC
    assert service.is_accepting is False
    assert len(recorder.failures) == 1
    assert getattr(recorder.failures[0], "code", None) == "DSP_SHUTDOWN"
    # New work after shutdown is refused, typed.
    _apply(service, recorder)
    assert recorder.total == 2
    assert getattr(recorder.failures[-1], "code", None) == "DSP_SHUTDOWN"
    # The worker is still draining the blocked IPC; once released it exits.
    transport.release.set()
    deadline = time.monotonic() + 5.0
    while (
        service._tx_thread is not None
        and service._tx_thread.is_alive()
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)
    assert service._tx_thread is None or not service._tx_thread.is_alive()


def test_receipt_rejected_after_host_loss_never_restores_effective() -> None:
    class _LossAfterCommit(_FakeProcessingTransport):
        on_commit = None

        def commit_candidate(self, **kwargs):
            receipt = super().commit_candidate(**kwargs)
            if self.on_commit is not None:
                self.on_commit()
            return receipt

    transport = _LossAfterCommit()
    service = _service(transport)
    plan = _transaction_plan()[1]
    candidate = service.begin_candidate(plan, host_generation=1, transport=transport)
    transport.on_commit = lambda: service.mark_host_lost("SIGKILL")
    receipt = service.commit_candidate(candidate, transport=transport)
    with pytest.raises(ProcessingStaleCommitError) as info:
        service.publish_effective(receipt)
    assert info.value.code == "DSP_STALE_COMMIT"
    assert service.effective_state.value == "unavailable"
    assert service.effective_plan_id is None


def test_late_receipt_from_an_old_host_generation_cannot_publish() -> None:
    transport = _FakeProcessingTransport()
    service = _service(transport)
    plan = _transaction_plan()[1]
    candidate = service.begin_candidate(plan, host_generation=1, transport=transport)
    receipt = service.commit_candidate(candidate, transport=transport)
    # A different host generation is now current.
    service.refresh_capabilities(host_generation=2)
    with pytest.raises(ProcessingStaleCommitError):
        service.publish_effective(receipt)
    assert service.effective_state.value != "effective"


class _AbortResultTransport(_FakeProcessingTransport):
    def __init__(self, result) -> None:
        super().__init__()
        self._abort_result = result
        self.abort_calls = 0

    def prepare_candidate(self, wire, *, processing_generation=0):
        observed = super().prepare_candidate(
            wire, processing_generation=processing_generation
        )
        observed["nodes"][0]["observed"]["gain_db"] += 1.0
        return observed

    def abort_candidate(self):
        self.abort_calls += 1
        return self._abort_result


@pytest.mark.parametrize(
    ("abort_result", "code"),
    [
        (False, "DSP_CANDIDATE_ABORT_REJECTED"),
        (None, "DSP_CANDIDATE_ABORT_UNPROVEN"),
    ],
)
def test_abort_without_proof_is_a_typed_double_fault(abort_result, code) -> None:
    service, plan = _transaction_plan()
    transport = _AbortResultTransport(abort_result)
    with pytest.raises(ProcessingTransactionError) as info:
        service.begin_candidate(plan, host_generation=1, transport=transport)
    assert info.value.code == code
    assert info.value.payload["candidate_retained"] is True
    assert info.value.payload["abort_error"]
    assert transport.abort_calls == 1


def test_no_completion_is_ever_delivered_twice_under_storm() -> None:
    transport = _BlockingTransport()
    service = _service(transport)
    deliveries: list[object] = []
    lock = threading.Lock()

    def done(value) -> None:
        with lock:
            deliveries.append(value)

    def failed(error) -> None:
        with lock:
            deliveries.append(error)

    def apply() -> None:
        service.apply_processing_async(
            _preamp_graph(),
            _signal(),
            on_done=done,
            on_failed=failed,
            async_submit=_InlineExecutor().submit,
        )

    apply()
    assert transport.started.wait(3.0)
    for _ in range(5):
        apply()
    transport.release.set()
    deadline = time.monotonic() + 8.0
    while len(deliveries) < 6 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(deliveries) == 6, deliveries
    service.shutdown()
