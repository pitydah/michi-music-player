"""M6.9-PRESENTATION — owner-thread contract.

The coordinator callbacks arrive from executor worker threads. The
relay must deliver them to the bridge owner thread (GUI thread):
worker callback thread != bridge thread, but projection mutation
thread == bridge thread. Deterministic (Events, Qt event delivery;
no sleeps).
"""

import threading

import pytest
from enrichment_presentation_fakes import (
    ARTIST_A_KEY,
    make_bridge,
    process_events,
)

from michi.application.enrichment_executor import ThreadPoolEnrichmentExecutor


@pytest.fixture(autouse=True, scope="module")
def _app():
    from enrichment_presentation_fakes import ensure_app

    return ensure_app()


def _thread_id():
    # Python thread identity — stable across QThread wrappers.
    return threading.get_ident()


class TestOwnerThreadContract:
    def test_worker_callback_thread_differs_from_bridge_thread(self):
        """State callbacks from a REAL thread pool are marshaled: the
        emit happens on a worker thread, the slot (and therefore the
        projection mutation) runs on the bridge owner thread."""
        from PySide6.QtCore import Qt

        bridge, service, _, _, _, coordinator, library = make_bridge(
            online=True, executor=ThreadPoolEnrichmentExecutor(max_workers=2)
        )
        owner_thread = _thread_id()
        emit_threads: list = []
        delivery_threads: list = []

        # Direct spy: runs on the EMITTING thread (the worker).
        bridge._relay.event_received.connect(
            lambda ev, intent: emit_threads.append(_thread_id()),
            Qt.DirectConnection,
        )
        # Queued spy: delivered like the bridge slot — on the owner thread.
        bridge._relay.event_received.connect(
            lambda ev, intent: delivery_threads.append(_thread_id()),
            Qt.QueuedConnection,
        )

        bridge.activate_artist(ARTIST_A_KEY)
        import time

        end = time.monotonic() + 10
        while bridge.property("state") != "READY" and time.monotonic() < end:
            process_events(8)
        assert bridge.property("state") == "READY"

        coordinator.shutdown()
        assert emit_threads, "no worker emitted any event"
        assert any(t != owner_thread for t in emit_threads), (
            "callbacks never came from a worker thread"
        )
        assert delivery_threads, "queued delivery never ran"
        assert all(t == owner_thread for t in delivery_threads), (
            "projection mutated off the owner thread"
        )

    def test_manual_candidate_callback_marshaled(self):
        """search_artist_candidates_async callbacks are marshaled too."""
        from PySide6.QtCore import Qt

        bridge, _, _, _, _, coordinator, _ = make_bridge(
            online=True, executor=ThreadPoolEnrichmentExecutor(max_workers=2)
        )
        owner_thread = _thread_id()
        emit_threads: list = []
        delivery_threads: list = []

        bridge._relay.candidates_received.connect(
            lambda kind, cands, epoch: emit_threads.append(_thread_id()),
            Qt.DirectConnection,
        )
        bridge._relay.candidates_received.connect(
            lambda kind, cands, epoch: delivery_threads.append(_thread_id()),
            Qt.QueuedConnection,
        )

        bridge.open_review("artist")
        bridge.search_artist("Artist A")
        import time

        end = time.monotonic() + 10
        while not bridge.property("artistCandidates") and time.monotonic() < end:
            process_events(8)
        assert len(bridge.property("artistCandidates")) == 1
        assert any(t != owner_thread for t in emit_threads)
        assert delivery_threads and all(t == owner_thread for t in delivery_threads)
        coordinator.shutdown()
