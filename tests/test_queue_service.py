"""Tests for QueueService — SOLE authority over QueueState CONTENT (M4-R1).

QueueService owns temporary user-created Queue content ONLY (entries,
ordering, add/remove/move/clear/replace). It NEVER commands playback:
navigation/repeat/shuffle/EOM authority lives in PlaybackSessionService
(see test_playback_session_service.py for the migrated coverage)."""

from pathlib import Path

import pytest


class TestQueueService:
    def test_empty_state(self, queue_service):
        assert queue_service.state.count == 0

    def test_add_track(self, queue_service):
        queue_service.add(Path("/tmp/a.mp3"))
        assert queue_service.state.count == 1

    def test_clear(self, queue_service):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.clear()
        assert queue_service.state.count == 0


class TestQueueMove:
    """M4 Original Closeout: queue reorder (`move`) — exact Track identity,
    committed-current recompute, pending-track preservation, no playback
    side effects, exactly one notification, deterministic invalid moves,
    shuffle navigator integrity.

    Contract under test (NOT yet implemented in production):
    - `QueueService.move(from_index, to_index) -> None` moves the EXACT Track
      object by identity — never recreates, never path-compares;
    - the committed current Track identity is preserved: `current_index` is
      recomputed by identity after the reorder; the pending Track identity is
      preserved: acceptance after the reorder commits at the NEW index;
    - a successful reorder never stops/loads/restarts playback and fires
      EXACTLY ONE notification;
    - invalid moves (out-of-range) and same-index moves are deterministic
      no-ops that fire NO notification;
    - duplicates resolve by exact object identity, never by path;
    - the shuffle navigator pool/history are NOT regenerated or corrupted by
      the physical list reorder (objects are identity-based).
    """

    def _paths(self, service) -> list:
        return [t.file_path for t in service.state.tracks]

    def test_move_forward(self, queue_service):
        a, b, c, d = (
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
            Path("/tmp/d.mp3"),
        )
        for p in (a, b, c, d):
            queue_service.add(p)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.move(0, 2)
        assert self._paths(queue_service) == [b, c, a, d]
        assert queue_service.state.count == 4
        assert calls == [1]  # EXACTLY ONE notification

    def test_move_backward(self, queue_service):
        a, b, c, d = (
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
            Path("/tmp/d.mp3"),
        )
        for p in (a, b, c, d):
            queue_service.add(p)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.move(3, 1)
        assert self._paths(queue_service) == [a, d, b, c]
        assert calls == [1]

    def test_move_first_to_last(self, queue_service):
        a, b, c, d = (
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
            Path("/tmp/d.mp3"),
        )
        for p in (a, b, c, d):
            queue_service.add(p)
        queue_service.move(0, 3)
        assert self._paths(queue_service) == [b, c, d, a]

    def test_move_last_to_first(self, queue_service):
        a, b, c, d = (
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
            Path("/tmp/d.mp3"),
        )
        for p in (a, b, c, d):
            queue_service.add(p)
        queue_service.move(3, 0)
        assert self._paths(queue_service) == [d, a, b, c]

    def test_move_same_index_noop(self, queue_service):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.move(1, 1)
        assert self._paths(queue_service) == [a, b, c]
        assert calls == []  # same-index → no-op, ZERO notify

    def test_move_invalid_negative(self, queue_service):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.move(-1, 2)  # out-of-range source → deterministic no-op
        assert self._paths(queue_service) == [a, b, c]
        assert calls == []

    def test_move_invalid_destination(self, queue_service):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.move(1, 99)  # out-of-range destination → deterministic no-op
        assert self._paths(queue_service) == [a, b, c]
        assert calls == []


class TestQueueCapacity:
    """M4 Original Closeout: configurable queue capacity.

    Contract under test (NOT yet implemented in production):
    - `QueueService(playback_service, rng=None, max_tracks=10000)` — capacity
      configurable with a safe high default;
    - `add()` when count == max_tracks raises `QueueCapacityError`
      (michi.domain.queue) and leaves the queue unchanged — tracks, current,
      pending, and shuffle state untouched; NO silent truncation.
    """

    def _capacity_service(self, playback_service, max_tracks):
        from michi.application.queue_service import QueueService

        return QueueService(max_tracks=max_tracks)

    def test_capacity_exact_boundary(self, playback_service):
        from michi.domain.queue import QueueCapacityError  # RED: undefined

        service = self._capacity_service(playback_service, 3)
        a, b, c, d = (
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
            Path("/tmp/d.mp3"),
        )
        for p in (a, b, c):
            service.add(p)
        assert service.state.count == 3  # boundary fits
        with pytest.raises(QueueCapacityError):
            service.add(d)  # 4th entry exceeds capacity
        assert service.state.count == 3  # no silent truncation

    def test_capacity_default_high(self, playback_service):
        from michi.application.queue_service import QueueService

        service = QueueService()
        assert service.max_tracks == 10000  # public read-only property


class TestInsertAndReplaceAtomicity:
    """KCR-013: content mutations are atomic and capacity-honest."""

    def test_insert_at_inserts_and_notifies_once(self, queue_service):
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))

        queue_service.add(Path("/tmp/a.flac"))
        calls.clear()

        queue_service.insert_at(0, Path("/tmp/b.flac"), title="B")

        assert [t.file_path for t in queue_service.state.tracks] == [
            Path("/tmp/b.flac"),
            Path("/tmp/a.flac"),
        ]
        assert queue_service.state.tracks[0].title == "B"
        assert calls == [1]

    def test_insert_at_clamps_index(self, queue_service):
        queue_service.add(Path("/tmp/a.flac"))
        queue_service.insert_at(999, Path("/tmp/b.flac"))
        assert [t.file_path.name for t in queue_service.state.tracks] == [
            "a.flac",
            "b.flac",
        ]

    def test_insert_at_capacity_failure_is_atomic(self):
        from michi.application.queue_service import (
            QueueCapacityError,
            QueueService,
        )

        service = QueueService(max_tracks=1)
        service.add(Path("/tmp/a.flac"))
        before = tuple(service.state.tracks)
        calls = []
        service.subscribe_changed(lambda: calls.append(1))

        with pytest.raises(QueueCapacityError):
            service.insert_at(0, Path("/tmp/b.flac"))

        assert tuple(service.state.tracks) == before
        assert calls == []

    def test_replace_capacity_failure_is_atomic(self):
        from michi.application.queue_service import (
            QueueCapacityError,
            QueueService,
        )
        from michi.domain.playback_session import (
            PlaybackSequenceEntry as Track,  # queue content entry
        )

        service = QueueService(max_tracks=1)
        service.add(Path("/tmp/a.flac"))
        before = tuple(service.state.tracks)

        with pytest.raises(QueueCapacityError):
            service.replace(
                [
                    Track(Path("/tmp/b.flac")),
                    Track(Path("/tmp/c.flac")),
                ]
            )

        assert tuple(service.state.tracks) == before


class TestCoordinationFailureVisibility:
    """KCR-014: a Queue→Session coordination callback failure is NEVER
    converted into a silent success."""

    def test_queue_notify_propagates_coordination_failure(self, queue_service):
        def failing_observer():
            raise RuntimeError("session sync failed")

        queue_service.subscribe_changed(failing_observer)
        with pytest.raises(RuntimeError, match="session sync failed"):
            queue_service.add(Path("/tmp/a.flac"))
        # state IS committed (commit-first), the failure is observable
        assert queue_service.state.count == 1

    def test_snapshot_iteration_self_unsubscribe_safe(self, queue_service):
        seen = []

        def self_removing():
            queue_service.unsubscribe_changed(self_removing)
            seen.append("self")

        def second():
            seen.append("second")

        queue_service.subscribe_changed(self_removing)
        queue_service.subscribe_changed(second)
        queue_service.add(Path("/tmp/a.flac"))
        assert seen == ["self", "second"]  # self-unsubscribe skipped nothing
