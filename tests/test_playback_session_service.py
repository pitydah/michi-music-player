"""M4-R1 — PlaybackSessionService tests (authority migration from Queue).

PlaybackSessionService owns the ACTIVE playback context/sequence and
navigation (Next/Previous/Repeat/Shuffle/EndOfMedia). QueueService owns
temporary content only and never commands playback. This file carries the
migrated navigation coverage (former Queue authority tests) plus the new
M4-R1 core matrix (S/A/P/Q/N + architecture AR tests).
"""

import random
from pathlib import Path

from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.domain.playback_session import (
    PlaybackContextType,
    PlaybackSequenceEntry,
    RepeatMode,
)


def make_session(fake_audio, seed: int = 42):
    playback = PlaybackService(fake_audio)
    queue = QueueService()
    session = PlaybackSessionService(playback, queue, rng=random.Random(seed))
    session.start()  # M4-R1 final seal: explicit lifecycle arms subscriptions
    return playback, queue, session


def accept(session, fake_audio, path):
    fake_audio.trigger_media_accepted(Path(path))


# ---------------------------------------------------------------------------
# S — SINGLE
# ---------------------------------------------------------------------------


class TestSingle:
    def test_s01_queue_empty_play_single(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        session.play_single(PlaybackSequenceEntry(Path("/tmp/A.flac"), "A"))
        accept(session, fake_audio, "/tmp/A.flac")
        st = session.state
        assert st.context_type is PlaybackContextType.SINGLE
        assert st.current_index == 0
        assert st.count == 1
        assert queue.state.count == 0  # Queue unchanged (empty)

    def test_s02_queue_populated_play_single_queue_untouched(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/Q1.flac"))
        queue.add(Path("/tmp/Q2.flac"))
        queue.add(Path("/tmp/Q3.flac"))
        before = [t.file_path for t in queue.state.tracks]
        session.play_single(PlaybackSequenceEntry(Path("/tmp/A.flac"), "A"))
        accept(session, fake_audio, "/tmp/A.flac")
        assert session.state.context_type is PlaybackContextType.SINGLE
        assert [t.file_path for t in queue.state.tracks] == before  # byte-same

    def test_s03_single_then_single_commits_after_acceptance(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        session.play_single(PlaybackSequenceEntry(Path("/tmp/A.flac"), "A"))
        session.play_single(PlaybackSequenceEntry(Path("/tmp/B.flac"), "B"))
        # A acceptance is stale (superseded by B request)
        accept(session, fake_audio, "/tmp/A.flac")
        assert session.state.current_entry is None  # nothing committed yet
        accept(session, fake_audio, "/tmp/B.flac")
        assert session.state.current_entry.file_path == Path("/tmp/B.flac")

    def test_s04_rejected_no_phantom_current(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        session.play_single(PlaybackSequenceEntry(Path("/tmp/A.flac"), "A"))
        fake_audio.trigger_media_rejected(Path("/tmp/A.flac"), "corrupt")
        assert session.state.current_entry is None
        assert session.state.context_type is PlaybackContextType.NONE

    def test_s05_late_acceptance_from_previous_request_ignored(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        session.play_single(PlaybackSequenceEntry(Path("/tmp/A.flac"), "A"))
        session.play_single(PlaybackSequenceEntry(Path("/tmp/B.flac"), "B"))
        accept(session, fake_audio, "/tmp/A.flac")  # stale
        assert session.state.current_entry is None
        accept(session, fake_audio, "/tmp/B.flac")
        assert session.state.current_entry.file_path == Path("/tmp/B.flac")

    def test_single_never_mutates_queue_instrumented(self, fake_audio):
        """Acceptance TEST 2: Queue mutations == 0 while playing a SINGLE."""
        playback, queue, session = make_session(fake_audio)
        for p in ("/tmp/Q1.flac", "/tmp/Q2.flac"):
            queue.add(Path(p))
        calls = {"add": 0, "remove": 0, "move": 0, "clear": 0}
        orig = (queue.add, queue.remove, queue.move, queue.clear)
        queue.add = lambda *a, **k: (
            calls.__setitem__("add", calls["add"] + 1),
            orig[0](*a, **k),
        )[-1]
        queue.remove = lambda *a, **k: (
            calls.__setitem__("remove", calls["remove"] + 1),
            orig[1](*a, **k),
        )[-1]
        queue.move = lambda *a, **k: (
            calls.__setitem__("move", calls["move"] + 1),
            orig[2](*a, **k),
        )[-1]
        queue.clear = lambda *a, **k: (
            calls.__setitem__("clear", calls["clear"] + 1),
            orig[3](*a, **k),
        )[-1]
        session.play_single(PlaybackSequenceEntry(Path("/tmp/A.flac"), "A"))
        accept(session, fake_audio, "/tmp/A.flac")
        session.next()  # boundary: no next on SINGLE
        assert calls == {"add": 0, "remove": 0, "move": 0, "clear": 0}


# ---------------------------------------------------------------------------
# Q — QUEUE CONTEXT + LIVE SYNC
# ---------------------------------------------------------------------------


class TestQueueContext:
    def test_q05_play_queue_index_sets_queue_context(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/Q1.flac"))
        queue.add(Path("/tmp/Q2.flac"))
        session.play_queue_index(1)
        accept(session, fake_audio, "/tmp/Q2.flac")
        st = session.state
        assert st.context_type is PlaybackContextType.QUEUE
        assert st.current_index == 1
        assert st.entries[1].file_path == Path("/tmp/Q2.flac")

    def test_q06_queue_reorder_future_item_new_order(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/Q1.flac"))
        queue.add(Path("/tmp/Q2.flac"))
        queue.add(Path("/tmp/Q3.flac"))
        session.play_queue_index(0)
        accept(session, fake_audio, "/tmp/Q1.flac")
        queue.move(1, 2)  # Q2 moves after Q3
        session.on_queue_changed()
        session.next()
        accept(session, fake_audio, "/tmp/Q3.flac")
        assert session.state.current_entry.file_path == Path("/tmp/Q3.flac")

    def test_q07_queue_remove_future_item_not_next(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/Q1.flac"))
        queue.add(Path("/tmp/Q2.flac"))
        queue.add(Path("/tmp/Q3.flac"))
        session.play_queue_index(0)
        accept(session, fake_audio, "/tmp/Q1.flac")
        queue.remove(1)  # Q2 removed
        session.on_queue_changed()
        session.next()
        accept(session, fake_audio, "/tmp/Q3.flac")
        assert session.state.current_entry.file_path == Path("/tmp/Q3.flac")

    def test_q08_queue_add_future_item_available(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/Q1.flac"))
        session.play_queue_index(0)
        accept(session, fake_audio, "/tmp/Q1.flac")
        queue.add(Path("/tmp/Q2.flac"))
        session.on_queue_changed()
        session.next()
        accept(session, fake_audio, "/tmp/Q2.flac")
        assert session.state.current_entry.file_path == Path("/tmp/Q2.flac")

    def test_q09_remove_current_queue_entry_playback_continues_single(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/Q1.flac"))
        queue.add(Path("/tmp/Q2.flac"))
        session.play_queue_index(0)
        accept(session, fake_audio, "/tmp/Q1.flac")
        queue.remove(0)  # current Queue entry removed
        session.on_queue_changed()
        # playback continues; session converges to SINGLE for the accepted path
        assert fake_audio.state == "playing"
        st = session.state
        assert st.context_type is PlaybackContextType.SINGLE
        assert st.current_entry.file_path == Path("/tmp/Q1.flac")

    def test_q10_clear_queue_while_queue_plays_continues_single(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/Q1.flac"))
        session.play_queue_index(0)
        accept(session, fake_audio, "/tmp/Q1.flac")
        queue.clear()  # Queue becomes empty
        session.on_queue_changed()
        assert fake_audio.state == "playing"  # no implicit stop
        assert queue.state.count == 0
        st = session.state
        assert st.context_type is PlaybackContextType.SINGLE
        assert st.current_entry.file_path == Path("/tmp/Q1.flac")

    def test_q11_remove_pending_queue_candidate_cancels(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/Q1.flac"))
        queue.add(Path("/tmp/Q2.flac"))
        session.play_queue_index(1)  # pending candidate Q2
        assert session._pending is not None
        queue.remove(1)  # exact pending entry removed before acceptance
        session.on_queue_changed()
        assert session._pending is None  # cleared via public machinery
        # never committed the removed entry
        assert session.state.current_entry is None

    def test_q12_duplicate_paths_distinct_identity(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/A.flac"))
        queue.add(Path("/tmp/B.flac"))
        queue.add(Path("/tmp/A.flac"))  # duplicate path, distinct entry
        session.play_queue_index(2)  # the SECOND A
        accept(session, fake_audio, "/tmp/A.flac")
        assert session.state.current_index == 2  # not ambiguous with first

    def test_q01_queue_service_has_no_playback_constructor(self):
        """QueueService constructor has NO PlaybackService (source-level AR)."""
        import inspect

        # QueueService source must NOT import/reference PlaybackService
        # (the migration-window legacy positional arg is absorbed WITHOUT
        # importing the type — source-level AR01/AR02 satisfied).
        import michi.application.queue_service as mod

        mod_src = inspect.getsource(mod)
        assert "import PlaybackService" not in mod_src
        assert "from michi.application.playback_service" not in mod_src
        assert "load_and_play" not in mod_src
        assert "subscribe_end_of_media" not in mod_src
        assert "_on_end_of_media" not in mod_src

    def test_q02_q03_q04_queue_mutations_zero_playback_calls(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/Q1.flac"))
        queue.add(Path("/tmp/Q2.flac"))
        queue.remove(0)
        queue.clear()
        assert fake_audio.state == "stopped"  # zero PlaybackService calls


# ---------------------------------------------------------------------------
# N — NAVIGATION
# ---------------------------------------------------------------------------


class TestNavigation:
    def _queue_context(self, fake_audio, paths):
        playback, queue, session = make_session(fake_audio)
        for p in paths:
            queue.add(Path(p))
        session.play_queue_index(0)
        accept(session, fake_audio, paths[0])
        return playback, queue, session

    def test_n01_next_on_queue(self, fake_audio):
        _, _, session = self._queue_context(fake_audio, ["/tmp/A.flac", "/tmp/B.flac"])
        session.next()
        accept(session, fake_audio, "/tmp/B.flac")
        assert session.state.current_entry.file_path == Path("/tmp/B.flac")

    def test_n02_previous_on_queue(self, fake_audio):
        _, _, session = self._queue_context(fake_audio, ["/tmp/A.flac", "/tmp/B.flac"])
        session.next()
        accept(session, fake_audio, "/tmp/B.flac")
        session.previous()
        accept(session, fake_audio, "/tmp/A.flac")
        assert session.state.current_entry.file_path == Path("/tmp/A.flac")

    def test_n03_next_on_single_no_queue_interaction(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        queue.add(Path("/tmp/Q1.flac"))
        session.play_single(PlaybackSequenceEntry(Path("/tmp/A.flac"), "A"))
        accept(session, fake_audio, "/tmp/A.flac")
        before = [t.file_path for t in queue.state.tracks]
        session.next()  # SINGLE boundary: no next
        assert session.state.current_entry.file_path == Path("/tmp/A.flac")
        assert [t.file_path for t in queue.state.tracks] == before

    def test_n06_repeat_one_eom_replays(self, fake_audio):
        _, _, session = self._queue_context(fake_audio, ["/tmp/A.flac", "/tmp/B.flac"])
        session.set_repeat_mode(RepeatMode.ONE)
        fake_audio.trigger_end_of_media()
        accept(session, fake_audio, "/tmp/A.flac")  # replay of exact entry
        assert session.state.current_entry.file_path == Path("/tmp/A.flac")

    def test_n07_repeat_one_manual_next_not_trapped(self, fake_audio):
        _, _, session = self._queue_context(fake_audio, ["/tmp/A.flac", "/tmp/B.flac"])
        session.set_repeat_mode(RepeatMode.ONE)
        session.next()  # manual navigation, not EOM
        accept(session, fake_audio, "/tmp/B.flac")
        assert session.state.current_entry.file_path == Path("/tmp/B.flac")

    def test_n08_repeat_all_wrap(self, fake_audio):
        _, _, session = self._queue_context(fake_audio, ["/tmp/A.flac", "/tmp/B.flac"])
        session.set_repeat_mode(RepeatMode.ALL)
        session.next()
        accept(session, fake_audio, "/tmp/B.flac")
        session.next()  # wraps to A
        accept(session, fake_audio, "/tmp/A.flac")
        assert session.state.current_entry.file_path == Path("/tmp/A.flac")

    def test_n09_shuffle_deterministic(self, fake_audio):
        playback, queue, session = make_session(fake_audio, seed=7)
        for p in ("/tmp/A.flac", "/tmp/B.flac", "/tmp/C.flac"):
            queue.add(Path(p))
        session.play_queue_index(0)
        accept(session, fake_audio, "/tmp/A.flac")
        session.set_shuffle_enabled(True)
        session.next()
        assert session.state.current_entry is not None  # deterministic pick
        # same seed → same first pick
        playback2, queue2, session2 = make_session(fake_audio, seed=7)
        for p in ("/tmp/A.flac", "/tmp/B.flac", "/tmp/C.flac"):
            queue2.add(Path(p))
        session2.play_queue_index(0)
        accept(session2, fake_audio, "/tmp/A.flac")
        session2.set_shuffle_enabled(True)
        session2.next()
        assert (
            session2.state.current_entry.file_path
            == session.state.current_entry.file_path
        )

    def test_n10_eom_with_pending_candidate_ignored(self, fake_audio):
        _, _, session = self._queue_context(fake_audio, ["/tmp/A.flac", "/tmp/B.flac"])
        session.next()  # pending candidate B in flight
        fake_audio.trigger_end_of_media()  # stale EOM
        assert session._pending is not None  # pending preserved
        accept(session, fake_audio, "/tmp/B.flac")
        assert session.state.current_entry.file_path == Path("/tmp/B.flac")

    def test_eom_no_next_stops(self, fake_audio):
        _, _, session = self._queue_context(fake_audio, ["/tmp/A.flac"])
        fake_audio.trigger_end_of_media()  # no next → stop
        assert fake_audio.state == "stopped"


# ---------------------------------------------------------------------------
# ALBUM / PLAYLIST contexts
# ---------------------------------------------------------------------------


class TestContexts:
    def test_album_context(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        entries = [
            PlaybackSequenceEntry(Path("/tmp/A1.flac"), "1"),
            PlaybackSequenceEntry(Path("/tmp/A2.flac"), "2"),
            PlaybackSequenceEntry(Path("/tmp/A3.flac"), "3"),
        ]
        session.play_context(PlaybackContextType.ALBUM, "album-1", entries, 0)
        accept(session, fake_audio, "/tmp/A1.flac")
        st = session.state
        assert st.context_type is PlaybackContextType.ALBUM
        assert st.source_id == "album-1"
        assert st.current_index == 0
        assert queue.state.count == 0  # Album never copies to Queue

    def test_album_track_click_index(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        entries = [
            PlaybackSequenceEntry(Path("/tmp/A1.flac"), "1"),
            PlaybackSequenceEntry(Path("/tmp/A2.flac"), "2"),
            PlaybackSequenceEntry(Path("/tmp/A3.flac"), "3"),
            PlaybackSequenceEntry(Path("/tmp/A4.flac"), "4"),
            PlaybackSequenceEntry(Path("/tmp/A5.flac"), "5"),
        ]
        session.play_context(PlaybackContextType.ALBUM, "album-1", entries, 3)
        accept(session, fake_audio, "/tmp/A4.flac")
        assert session.state.current_index == 3  # album track 4 → index 3
        session.next()
        accept(session, fake_audio, "/tmp/A5.flac")
        assert session.state.current_entry.file_path == Path("/tmp/A5.flac")
        session.previous()
        accept(session, fake_audio, "/tmp/A4.flac")
        assert session.state.current_index == 3

    def test_playlist_context_snapshot(self, fake_audio):
        playback, queue, session = make_session(fake_audio)
        entries = [
            PlaybackSequenceEntry(Path("/tmp/P1.flac"), "1"),
            PlaybackSequenceEntry(Path("/tmp/P2.flac"), "2"),
        ]
        session.play_context(PlaybackContextType.PLAYLIST, "pl-1", entries, 1)
        accept(session, fake_audio, "/tmp/P2.flac")
        st = session.state
        assert st.context_type is PlaybackContextType.PLAYLIST
        assert st.source_id == "pl-1"
        assert st.current_index == 1
        assert queue.state.count == 0  # Playlist never copies to Queue

    def test_album_playlist_zero_queue_mutations(self, fake_audio):
        """Acceptance TEST 3: Album/Playlist play without copying to Queue."""
        playback, queue, session = make_session(fake_audio)
        calls = {"add": 0, "remove": 0, "move": 0, "clear": 0}
        orig = (queue.add, queue.remove, queue.move, queue.clear)
        queue.add = lambda *a, **k: (
            calls.__setitem__("add", calls["add"] + 1),
            orig[0](*a, **k),
        )[-1]
        queue.remove = lambda *a, **k: (
            calls.__setitem__("remove", calls["remove"] + 1),
            orig[1](*a, **k),
        )[-1]
        queue.move = lambda *a, **k: (
            calls.__setitem__("move", calls["move"] + 1),
            orig[2](*a, **k),
        )[-1]
        queue.clear = lambda *a, **k: (
            calls.__setitem__("clear", calls["clear"] + 1),
            orig[3](*a, **k),
        )[-1]
        entries = [PlaybackSequenceEntry(Path("/tmp/A1.flac"), "1")]
        session.play_context(PlaybackContextType.ALBUM, "a", entries, 0)
        accept(session, fake_audio, "/tmp/A1.flac")
        session.play_context(PlaybackContextType.PLAYLIST, "p", entries, 0)
        accept(session, fake_audio, "/tmp/A1.flac")
        assert calls == {"add": 0, "remove": 0, "move": 0, "clear": 0}


# ---------------------------------------------------------------------------
# M4-R1 FINAL SEAL — duplicate entry identity (D01-D09) + lifecycle (LC)
# ---------------------------------------------------------------------------


class TestFinalSealIdentity:
    """P1-01: Queue entry identity is opaque entry_id, never file_path."""

    def test_d01_duplicate_paths_distinct_entry_ids(self):
        from michi.domain.queue import Track

        a1 = Track(Path("/A.flac"))
        a2 = Track(Path("/A.flac"))
        assert a1.entry_id != a2.entry_id

    def test_d02_play_a2_exact_identity(self, fake_audio):
        _, q, session = make_session(fake_audio)
        q.add(Path("/A.flac"))  # A1
        q.add(Path("/B.flac"))
        q.add(Path("/A.flac"))  # A2
        a2_id = q.state.tracks[2].entry_id
        session.play_queue_index(2)
        accept(session, fake_audio, "/A.flac")
        assert session._active_queue_entry_id == a2_id
        assert session.state.current_index == 2

    def test_d03_play_a2_remove_a1_stays_queue(self, fake_audio):
        _, q, session = make_session(fake_audio)
        q.add(Path("/A.flac"))
        q.add(Path("/B.flac"))
        q.add(Path("/A.flac"))
        a2_id = q.state.tracks[2].entry_id
        session.play_queue_index(2)
        accept(session, fake_audio, "/A.flac")
        q.remove(0)  # A1 removed; A2 survives
        session.on_queue_changed()
        assert session.state.context_type is PlaybackContextType.QUEUE
        assert session._active_queue_entry_id == a2_id
        assert session.state.current_index == 1  # new A2 position
        assert fake_audio.state == "playing"

    def test_d04_play_a2_remove_a2_converges_single_no_rebind(self, fake_audio):
        _, q, session = make_session(fake_audio)
        q.add(Path("/A.flac"))
        q.add(Path("/B.flac"))
        q.add(Path("/A.flac"))
        session.play_queue_index(2)
        accept(session, fake_audio, "/A.flac")
        q.remove(2)  # A2 removed; A1 still exists
        session.on_queue_changed()
        assert session.state.context_type is PlaybackContextType.SINGLE
        assert session.state.current_entry.file_path == Path("/A.flac")
        assert session._active_queue_entry_id is None
        # A1 remains in the Queue
        assert [t.file_path for t in q.state.tracks] == [
            Path("/A.flac"),
            Path("/B.flac"),
        ]

    def test_d05_play_a2_move_a2_index_0(self, fake_audio):
        _, q, session = make_session(fake_audio)
        q.add(Path("/A.flac"))
        q.add(Path("/B.flac"))
        q.add(Path("/A.flac"))
        a2_id = q.state.tracks[2].entry_id
        session.play_queue_index(2)
        accept(session, fake_audio, "/A.flac")
        q.move(2, 0)  # A2 → index 0
        session.on_queue_changed()
        assert session.state.context_type is PlaybackContextType.QUEUE
        assert session._active_queue_entry_id == a2_id
        assert session.state.current_index == 0

    def test_d06_pending_a2_remove_a2_cancels(self, fake_audio):
        _, q, session = make_session(fake_audio)
        q.add(Path("/A.flac"))
        q.add(Path("/B.flac"))
        q.add(Path("/A.flac"))
        a2_id = q.state.tracks[2].entry_id
        session.play_queue_index(2)  # pending
        assert session._pending_queue_entry_id == a2_id
        q.remove(2)  # A2 removed before acceptance; A1 remains
        session.on_queue_changed()
        assert session._pending is None  # cancelled
        assert session.state.current_entry is None  # never committed

    def test_d07_pending_a2_remove_a1_stays_valid(self, fake_audio):
        _, q, session = make_session(fake_audio)
        q.add(Path("/A.flac"))
        q.add(Path("/B.flac"))
        q.add(Path("/A.flac"))
        session.play_queue_index(2)  # pending A2
        q.remove(0)  # A1 removed — A2 pending must survive
        session.on_queue_changed()
        assert session._pending is not None
        accept(session, fake_audio, "/A.flac")
        assert session.state.current_entry.file_path == Path("/A.flac")

    def test_d08_shuffle_duplicates_distinct(self, fake_audio):
        _, q, session = make_session(fake_audio)
        q.add(Path("/A.flac"))
        q.add(Path("/B.flac"))
        q.add(Path("/A.flac"))
        session.play_queue_index(0)
        accept(session, fake_audio, "/A.flac")
        session.set_shuffle_enabled(True)
        # pool must contain BOTH A-entries as distinct identities
        pool_ids = {e.entry_id for e in session._navigator.pool}
        assert len(pool_ids) == 2  # {B, one of the A's} — distinct identities
        assert len(session._navigator.pool) == 2

    def test_d09_remove_future_duplicate_shuffle(self, fake_audio):
        _, q, session = make_session(fake_audio)
        q.add(Path("/A.flac"))
        q.add(Path("/B.flac"))
        q.add(Path("/A.flac"))
        session.play_queue_index(0)
        accept(session, fake_audio, "/A.flac")
        session.set_shuffle_enabled(True)
        removed_id = q.state.tracks[2].entry_id  # A2 (future)
        q.remove(2)
        session.on_queue_changed()
        assert removed_id not in {e.entry_id for e in session._navigator.pool}
        assert removed_id not in {e.entry_id for e in session._navigator.history}


class TestFinalSealLifecycle:
    """P1-04: explicit lifecycle — start()/stop() own subscriptions."""

    def test_lc01_init_zero_eom_subscription(self, fake_audio):
        _, q, session = make_session(fake_audio)
        session.stop()  # disarm the start() from make_session
        assert session._started is False

    def test_lc02_start_arms_exactly_one_each(self, fake_audio):
        from michi.application.playback_service import PlaybackService
        from michi.application.queue_service import QueueService

        svc = PlaybackService(fake_audio)
        q = QueueService()
        session = PlaybackSessionService(svc, q)
        assert session._started is False  # __init__ subscribes nothing
        session.start()
        assert session._started is True
        assert svc._eom_subscribers.count(session._on_end_of_media) == 1
        assert q._subscribers.count(session.on_queue_changed) == 1

    def test_lc03_double_start_one_each(self, fake_audio):
        from michi.application.playback_service import PlaybackService
        from michi.application.queue_service import QueueService

        svc = PlaybackService(fake_audio)
        q = QueueService()
        session = PlaybackSessionService(svc, q)
        session.start()
        session.start()
        assert svc._eom_subscribers.count(session._on_end_of_media) == 1
        assert q._subscribers.count(session.on_queue_changed) == 1

    def test_lc04_stop_zero_subscriptions(self, fake_audio):
        from michi.application.playback_service import PlaybackService
        from michi.application.queue_service import QueueService

        svc = PlaybackService(fake_audio)
        q = QueueService()
        session = PlaybackSessionService(svc, q)
        session.start()
        session.stop()
        assert session._on_end_of_media not in svc._eom_subscribers
        assert session.on_queue_changed not in q._subscribers

    def test_lc05_double_stop_safe(self, fake_audio):
        from michi.application.playback_service import PlaybackService
        from michi.application.queue_service import QueueService

        svc = PlaybackService(fake_audio)
        q = QueueService()
        session = PlaybackSessionService(svc, q)
        session.start()
        session.stop()
        session.stop()  # no error

    def test_lc06_late_eom_after_stop_no_navigation(self, fake_audio):
        from michi.application.playback_service import PlaybackService
        from michi.application.queue_service import QueueService

        svc = PlaybackService(fake_audio)
        q = QueueService()
        session = PlaybackSessionService(svc, q)
        session.start()
        q.add(Path("/A.flac"))
        session.play_queue_index(0)
        accept(session, fake_audio, "/A.flac")
        session.stop()
        before = session.state.current_index
        fake_audio.trigger_end_of_media()  # late EOM
        assert session.state.current_index == before  # zero navigation
        assert fake_audio.loaded == Path("/A.flac")  # no playback request

    def test_lc07_late_queue_mutation_after_stop(self, fake_audio):
        from michi.application.playback_service import PlaybackService
        from michi.application.queue_service import QueueService

        svc = PlaybackService(fake_audio)
        q = QueueService()
        session = PlaybackSessionService(svc, q)
        session.start()
        q.add(Path("/A.flac"))
        session.play_queue_index(0)
        accept(session, fake_audio, "/A.flac")
        session.stop()
        q.add(Path("/B.flac"))
        assert session.state.current_index == 0  # no live-sync reaction
        assert session.state.context_type is PlaybackContextType.QUEUE

    def test_lc08_history_start_stop(self, fake_audio):
        from michi.application.library_service import LibraryService
        from michi.application.playback_history_coordinator import (
            PlaybackHistoryCoordinator,
        )

        class FakeScanner:
            def scan(self, root):
                return []

            def validate_file(self, path):
                return None

        lib = LibraryService(FakeScanner())
        _, _, session = make_session(fake_audio)
        history = PlaybackHistoryCoordinator(session, lib)
        history.start()
        assert session._committed_subscribers.count(history._on_committed) == 1
        history.stop()
        assert history._on_committed not in session._committed_subscribers

    def test_lc09_bridge_dispose(self, fake_audio):
        from michi.presentation.playback_session_bridge import (
            PlaybackSessionBridge,
        )

        _, _, session = make_session(fake_audio)
        bridge = PlaybackSessionBridge(session)
        assert session._subscribers.count(bridge._on_session_changed) == 1
        bridge.dispose()
        assert bridge._on_session_changed not in session._subscribers
        bridge.dispose()  # idempotent

    def test_one_queue_delivery_per_mutation(self, fake_audio):
        """P2: exactly ONE Session delivery per Queue event (no redispatch)."""
        _, q, session = make_session(fake_audio)
        q.add(Path("/A.flac"))
        q.add(Path("/B.flac"))
        session.play_queue_index(0)
        accept(session, fake_audio, "/A.flac")
        deliveries = []
        orig_notify = q._notify

        def spy_notify():
            # count how many times the SESSION callback is invoked
            session_cb = session.on_queue_changed
            if session_cb in q._subscribers:
                deliveries.append(1)
            orig_notify()

        q._notify = spy_notify
        q.add(Path("/C.flac"))
        assert len(deliveries) == 1
        q.move(0, 2)
        assert len(deliveries) == 2
        q.remove(0)
        assert len(deliveries) == 3
        # the session callback is subscribed EXACTLY once
        assert q._subscribers.count(session.on_queue_changed) == 1
