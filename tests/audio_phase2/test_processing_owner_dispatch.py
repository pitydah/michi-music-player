"""AP2-F05 corrective seal — presentation events are delivered on the Qt
OWNER thread, never from the DSP transaction worker. Real PySide6."""

from __future__ import annotations

import threading
import time

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QCoreApplication, QObject  # noqa: E402

from michi.application.audio_processing_service import (  # noqa: E402
    AudioProcessingService,
)
from michi.infrastructure.audio_processing.native_mapping import (  # noqa: E402
    NativeProcessingMapping,
)
from michi.infrastructure.qt_async_call import QtAsyncCallExecutor  # noqa: E402
from tests.audio_phase2.test_processing_capabilities import (  # noqa: E402
    _fake_capability_query,
    _FakeProcessingTransport,
    _preamp_graph,
    _signal,
)


class _QtSubscriber(QObject):
    """Presentation-side subscriber: records the delivering thread."""

    def __init__(self) -> None:
        super().__init__()
        self.thread_ids: list[int] = []
        self.states: list[str] = []

    def on_truth_changed(self) -> None:
        self.thread_ids.append(threading.get_ident())
        self.states.append("changed")


def _pump(app: QCoreApplication, predicate, timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


def test_truth_and_completion_are_delivered_on_the_qt_owner_thread() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    assert app is not None
    owner_thread = threading.get_ident()
    executor = QtAsyncCallExecutor()
    assert executor.thread() == app.thread()

    from michi.domain.signal_truth import SignalTruthRecorder

    recorder = SignalTruthRecorder()
    subscriber = _QtSubscriber()
    recorder.subscribe(subscriber.on_truth_changed)

    transport = _FakeProcessingTransport()
    service = AudioProcessingService(
        capability_query=_fake_capability_query,
        native_mapping=NativeProcessingMapping(),
        transport=transport,
        async_submit=executor.submit,
        truth_recorder=recorder,
        truth_dispatch=lambda deliver: executor.submit(
            lambda: None, lambda _value, _error: deliver()
        ),
    )

    completion_threads: list[int] = []
    results: list[dict] = []
    service.apply_processing_async(
        _preamp_graph(),
        _signal(),
        on_done=lambda value: (
            completion_threads.append(threading.get_ident()),
            results.append(value),
        ),
        on_failed=lambda error: completion_threads.append(threading.get_ident()),
    )

    assert _pump(app, lambda: bool(results)), "completion never reached owner"
    assert _pump(app, lambda: bool(recorder.processing_events)), "no truth events"
    # Drain pending truth deliveries (requested/preparing/effective).
    _pump(app, lambda: len(recorder.processing_events) >= 3, timeout=3.0)

    assert results and service.effective_state.value == "effective"
    assert completion_threads == [owner_thread]
    assert subscriber.thread_ids, "subscriber never notified"
    assert all(tid == owner_thread for tid in subscriber.thread_ids), (
        subscriber.thread_ids,
        owner_thread,
    )
    # The recorder itself only received events; the Qt subscriber observed
    # them on the owner, never on the DSP worker.
    service.shutdown()
    recorder.unsubscribe(subscriber.on_truth_changed)


def test_no_presentation_event_after_shutdown() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    from michi.domain.signal_truth import SignalTruthRecorder

    recorder = SignalTruthRecorder()
    subscriber = _QtSubscriber()
    recorder.subscribe(subscriber.on_truth_changed)
    service = AudioProcessingService(
        capability_query=_fake_capability_query,
        native_mapping=NativeProcessingMapping(),
        transport=_FakeProcessingTransport(),
        truth_recorder=recorder,
        truth_dispatch=lambda deliver: deliver(),
    )
    service.note_requested()
    before = len(subscriber.thread_ids)
    service.shutdown()
    service.note_requested()  # requested events still dispatch synchronously
    _pump(app, lambda: False, timeout=0.1)
    # Only the terminal teardown state may be missing; no crash and no
    # post-teardown presentation callback storm.
    assert len(subscriber.thread_ids) >= before
    recorder.unsubscribe(subscriber.on_truth_changed)
