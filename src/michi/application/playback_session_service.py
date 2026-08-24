"""Playback session use case — SOLE authority over the active playback
sequence/navigation (M4-R1).

Owns: context (NONE/SINGLE/ALBUM/PLAYLIST/QUEUE), sequence entries, current
index, Next/Previous, Repeat, Shuffle and EndOfMedia navigation policy.
It is the ONLY application service that requests playback through
PlaybackService.load_and_play (with the proven pending/accept/reject/
cancel transaction). QueueService NEVER commands playback.

Dependency direction (essential):
    PlaybackSessionService → PlaybackService
    PlaybackSessionService → QueueService
    NEVER QueueService → PlaybackService/SessionService.

No threads, no timers, no asyncio — owner-thread application logic using
the existing event/callback architecture.
"""

import logging
import random
from collections.abc import Callable
from pathlib import Path

from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.playback_session import (
    PlaybackContextType,
    PlaybackSequenceEntry,
    PlaybackSessionState,
    RepeatMode,
    ShuffleNavigator,
)

logger = logging.getLogger(__name__)


class PlaybackSessionService:
    """Active playback context/navigation authority.

    A session request is a TRANSACTION: a candidate is armed pending; only
    the backend acceptance (on_accepted) may COMMIT the context/entries/
    current_index. Rejection or cancellation never fabricate a new current
    context — the previous committed session remains the last committed
    context. A request epoch guards stale callbacks (request N+1 makes the
    late callback of request N inert).
    """

    def __init__(
        self,
        playback_service: PlaybackService,
        queue_service: QueueService,
        rng=None,
        shuffle_seed: int | None = None,
    ) -> None:
        self._playback = playback_service
        self._queue = queue_service
        self._rng = rng if rng is not None else random.Random()
        self._shuffle_seed = (
            shuffle_seed if shuffle_seed is not None else random.randrange(1, 2**31)
        )
        self._navigator = ShuffleNavigator()
        self._state = PlaybackSessionState()
        self._pending: PlaybackSequenceEntry | None = None
        self._request_epoch = 0
        self._subscribers: list[Callable[[], None]] = []
        self._committed_subscribers: list[Callable[[Path], None]] = []
        self._playback.subscribe_end_of_media(self._on_end_of_media)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    @property
    def state(self) -> PlaybackSessionState:
        return self._state

    @property
    def shuffle_seed(self) -> int:
        return self._shuffle_seed

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def subscribe_track_committed(self, callback: Callable[[Path], None]) -> None:
        """History event: a NEW playback request was ACCEPTED (real backend
        acceptance). Startup restore never emits this."""
        if callback not in self._committed_subscribers:
            self._committed_subscribers.append(callback)

    def unsubscribe_track_committed(self, callback: Callable[[Path], None]) -> None:
        if callback in self._committed_subscribers:
            self._committed_subscribers.remove(callback)

    def _notify(self) -> None:
        for cb in list(self._subscribers):
            cb()

    def _notify_committed(self, path: Path) -> None:
        for cb in list(self._committed_subscribers):
            cb(path)

    # ------------------------------------------------------------------
    # Session request transaction
    # ------------------------------------------------------------------

    def _request(
        self,
        context_type: PlaybackContextType,
        source_id: str | None,
        entries: list[PlaybackSequenceEntry],
        index: int,
    ) -> None:
        """Arm a pending candidate; commit ONLY on acceptance.

        A rejected/cancelled request leaves the previous committed session
        as the last committed context (no fabricated current)."""
        if not entries or not (0 <= index < len(entries)):
            return
        self._request_epoch += 1
        my_epoch = self._request_epoch
        candidate = entries[index]
        self._pending = candidate
        try:
            self._playback.load_and_play(
                candidate.file_path,
                on_accepted=lambda path, c=candidate, e=my_epoch: self._commit(
                    context_type, source_id, entries, index, c, path, e
                ),
                on_rejected=lambda path, message, c=candidate, e=my_epoch: self._reject(
                    c, path, e
                ),
                on_cancelled=lambda path, c=candidate, e=my_epoch: self._cancel(
                    c, path, e
                ),
            )
        except Exception:
            if self._pending is candidate and self._request_epoch == my_epoch:
                self._pending = None
            raise

    def _commit(
        self,
        context_type: PlaybackContextType,
        source_id: str | None,
        entries: list[PlaybackSequenceEntry],
        index: int,
        candidate: PlaybackSequenceEntry,
        path: Path,
        epoch: int,
    ) -> None:
        if epoch != self._request_epoch:
            return  # stale acceptance of an older request
        if self._pending is not candidate:
            return
        if candidate.file_path != path:
            return
        self._pending = None
        self._state.context_type = context_type
        self._state.source_id = source_id
        self._state.entries = tuple(entries)
        self._state.current_index = index
        if self._state.shuffle_enabled:
            self._navigator.record_commit(candidate)
        self._notify()
        self._notify_committed(path)

    def _reject(self, candidate: PlaybackSequenceEntry, path: Path, epoch: int) -> None:
        if epoch != self._request_epoch:
            return
        if self._pending is not candidate:
            return
        if candidate.file_path != path:
            return
        self._pending = None

    def _cancel(self, candidate: PlaybackSequenceEntry, path: Path, epoch: int) -> None:
        if epoch != self._request_epoch:
            return
        if self._pending is not candidate:
            return
        if candidate.file_path != path:
            return
        self._pending = None

    # ------------------------------------------------------------------
    # Context entry points
    # ------------------------------------------------------------------

    def play_single(self, entry: PlaybackSequenceEntry) -> None:
        """SINGLE context. Queue MUST NOT change."""
        self._request(PlaybackContextType.SINGLE, None, [entry], 0)

    def play_context(
        self,
        context_type: PlaybackContextType,
        source_id: str | None,
        entries: list[PlaybackSequenceEntry],
        index: int = 0,
    ) -> None:
        """ALBUM/PLAYLIST snapshot contexts (index = clicked position)."""
        if context_type not in (
            PlaybackContextType.ALBUM,
            PlaybackContextType.PLAYLIST,
        ):
            raise ValueError(f"play_context expects ALBUM/PLAYLIST: {context_type}")
        self._request(context_type, source_id, entries, index)

    def play_queue_index(self, index: int) -> None:
        """QUEUE context: the Queue is the LIVE source sequence. QueueService
        itself never commands playback — the session reads QueueState and
        requests the playback transaction."""
        tracks = self._queue.state.tracks
        if not (0 <= index < len(tracks)):
            return
        entries = [
            PlaybackSequenceEntry(file_path=t.file_path, title=t.title) for t in tracks
        ]
        self._request(PlaybackContextType.QUEUE, None, entries, index)

    # ------------------------------------------------------------------
    # Queue live synchronization (QUEUE context only)
    # ------------------------------------------------------------------

    def on_queue_changed(self) -> None:
        """React to Queue content mutation while the session is QUEUE-context.

        - The currently accepted entry keeps playing when removed (identity
          preserved); the session converges to SINGLE for the accepted path.
        - A pending QUEUE candidate whose exact entry disappeared is
          cancelled through PlaybackService public machinery (this applies
          EVEN BEFORE the context committed: a pending play_queue_index
          request with context NONE still carries a QUEUE candidate).
        - Future entries follow the live Queue ordering for navigation."""
        # Pending QUEUE candidate removed before acceptance (§29): cancel
        # regardless of the committed context (a pre-commit request has
        # context NONE but its pending entry is a QUEUE candidate).
        if self._pending is not None:
            pending_gone = not any(
                t.file_path == self._pending.file_path for t in self._queue.state.tracks
            )
            if pending_gone:
                self._cancel_pending_request(self._pending)
                return
        if self._state.context_type is not PlaybackContextType.QUEUE:
            return
        tracks = self._queue.state.tracks
        current = self._state.current_entry
        if current is not None:
            # Live identity tracking: find the accepted entry by OBJECT
            # identity (duplicates stay distinct).
            live = next(
                (t for t in tracks if t.file_path == current.file_path),
                None,
            )
            if live is None:
                # Current Queue entry removed: playback continues (accepted
                # media remains valid) but the Queue identity is gone — the
                # session converges to SINGLE for the accepted path.
                self._converge_to_single(current)
                return
            # §25: the current entry's identity remains current even when its
            # numeric index moves — re-project the published session to the
            # LIVE ordering (future navigation follows the new order).
            self._state.entries = tuple(
                PlaybackSequenceEntry(file_path=t.file_path, title=t.title)
                for t in tracks
            )
            for i, e in enumerate(self._state.entries):
                if e.file_path == current.file_path:
                    self._state.current_index = i
                    break
            self._notify()

    def _converge_to_single(self, entry: PlaybackSequenceEntry) -> None:
        """Queue current entry removed/cleared while QUEUE plays: the session
        becomes SINGLE for the accepted playback path. No stop, no Queue
        mutation."""
        self._state.context_type = PlaybackContextType.SINGLE
        self._state.source_id = None
        self._state.entries = (entry,)
        self._state.current_index = 0
        if self._state.shuffle_enabled:
            self._navigator.clear()
        self._notify()

    def _cancel_pending_request(self, candidate: PlaybackSequenceEntry) -> None:
        """Cancel a pending QUEUE candidate removed before acceptance. Uses
        the public PlaybackService stop machinery; never fabricates a commit."""
        self._pending = None
        self._request_epoch += 1
        try:
            self._playback.stop()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("pending-queue-candidate cancel stop failed: %s", exc)

    # ------------------------------------------------------------------
    # Navigation (QUEUE-aware next/previous live below — this is the sole
    # navigation implementation; see next()/previous() after the live
    # sequence helpers).
    # ------------------------------------------------------------------

    def set_repeat_mode(self, mode: RepeatMode) -> None:
        if not isinstance(mode, RepeatMode):
            raise ValueError(f"invalid repeat mode: {mode!r}")
        if self._state.repeat_mode is mode:
            return
        self._state.repeat_mode = mode
        self._notify()

    def set_shuffle_enabled(self, enabled: bool) -> None:
        if not isinstance(enabled, bool):
            raise ValueError(f"invalid shuffle flag: {enabled!r}")
        if self._state.shuffle_enabled is enabled:
            return
        self._state.shuffle_enabled = enabled
        if enabled:
            self._navigator.reset(
                list(self._state.entries), self._state.current_entry, self._rng
            )
        else:
            self._navigator.clear()
        self._notify()

    def _play_entry(self, index: int) -> None:
        """Re-request the entry at ``index`` within the CURRENT committed
        context (no Queue mutation)."""
        st = self._state
        if not (0 <= index < len(st.entries)):
            return
        self._request(st.context_type, st.source_id, list(st.entries), index)

    def _live_sequence(self) -> tuple[list[PlaybackSequenceEntry], int]:
        """QUEUE context: the LIVE Queue is the navigation source (§25).

        Future entries follow the current Queue ordering (adds/removes/
        moves reflected); the current entry identity is preserved even when
        its numeric index moved (tracked by path). Returns (entries,
        current_index) reconstructed from QueueState."""
        tracks = self._queue.state.tracks
        entries = [
            PlaybackSequenceEntry(file_path=t.file_path, title=t.title) for t in tracks
        ]
        current = self._state.current_entry
        if current is None:
            return entries, -1
        for i, e in enumerate(entries):
            if e.file_path == current.file_path:
                return entries, i
        return entries, -1

    def _request_live_index(self, index: int) -> None:
        """Request playback of the LIVE Queue entry at ``index`` (the
        pending commit re-snapshots the live sequence at acceptance)."""
        tracks = self._queue.state.tracks
        if not (0 <= index < len(tracks)):
            return
        entries = [
            PlaybackSequenceEntry(file_path=t.file_path, title=t.title) for t in tracks
        ]
        self._request(PlaybackContextType.QUEUE, None, entries, index)

    def next(self) -> None:
        """Manual Next on the active context. Repeat ONE must NOT trap manual
        navigation: at sequence boundaries NONE stops, ALL wraps."""
        st = self._state
        if st.context_type is PlaybackContextType.NONE:
            return
        if st.context_type is PlaybackContextType.QUEUE:
            entries, current = self._live_sequence()
            if current < 0 or not entries:
                return
            if st.shuffle_enabled:
                self._next_shuffled_live()
                return
            if st.repeat_mode is RepeatMode.ALL:
                self._request_live_index((current + 1) % len(entries))
                return
            if current + 1 < len(entries):
                self._request_live_index(current + 1)
            return
        if not st.entries or st.current_index < 0:
            return
        if st.shuffle_enabled:
            self._next_shuffled()
            return
        if st.repeat_mode is RepeatMode.ALL:
            nxt = (st.current_index + 1) % len(st.entries)
            self._play_entry(nxt)
            return
        if st.current_index + 1 < len(st.entries):
            self._play_entry(st.current_index + 1)
        # NONE / ONE at the boundary: no next (manual navigation never traps).

    def previous(self) -> None:
        st = self._state
        if st.context_type is PlaybackContextType.NONE:
            return
        if st.context_type is PlaybackContextType.QUEUE:
            entries, current = self._live_sequence()
            if current < 0 or not entries:
                return
            if st.shuffle_enabled:
                self._previous_shuffled_live()
                return
            if st.repeat_mode is RepeatMode.ALL:
                self._request_live_index((current - 1) % len(entries))
                return
            if current > 0:
                self._request_live_index(current - 1)
            return
        if not st.entries or st.current_index < 0:
            return
        if st.shuffle_enabled:
            self._previous_shuffled()
            return
        if st.repeat_mode is RepeatMode.ALL:
            prev = (st.current_index - 1) % len(st.entries)
            self._play_entry(prev)
            return
        if st.current_index > 0:
            self._play_entry(st.current_index - 1)

    def _next_shuffled_live(self) -> None:
        entries, _ = self._live_sequence()
        target = self._navigator.pop_next(self._rng)
        if target is None:
            if self._state.repeat_mode is RepeatMode.ALL:
                self._navigator.regenerate(
                    entries, self._state.current_entry, self._rng
                )
                target = self._navigator.pop_next(self._rng)
                if target is None:
                    return
            else:
                return
        for i, e in enumerate(entries):
            if e.file_path == target.file_path:
                self._request_live_index(i)
                return

    def _previous_shuffled_live(self) -> None:
        entries, _ = self._live_sequence()
        target = self._navigator.previous_pick()
        if target is None:
            return
        for i, e in enumerate(entries):
            if e.file_path == target.file_path:
                self._request_live_index(i)
                return

    def _next_shuffled(self) -> None:
        st = self._state
        target = self._navigator.pop_next(self._rng)
        if target is None:
            if st.repeat_mode is RepeatMode.ALL:
                self._navigator.regenerate(
                    list(st.entries), st.current_entry, self._rng
                )
                target = self._navigator.pop_next(self._rng)
                if target is None:  # single-entry edge
                    self._play_entry(st.current_index)
                    return
            else:  # NONE / ONE: exhausted pool, nothing more
                return
        self._play_entry(self._index_of(target))

    def _previous_shuffled(self) -> None:
        target = self._navigator.previous_pick()
        if target is None:
            return
        self._play_entry(self._index_of(target))

    def _index_of(self, entry: PlaybackSequenceEntry) -> int:
        for i, e in enumerate(self._state.entries):
            if e is entry:
                return i
        return -1

    # ------------------------------------------------------------------
    # EndOfMedia navigation policy (Session authority)
    # ------------------------------------------------------------------

    def _on_end_of_media(self) -> None:
        """Natural end of the committed track. Canonical decision order:
        1. pending session request → stale EOM, ignore.
        2. Repeat ONE → replay the exact current entry.
        3. Shuffle → next deterministic session entry (regenerate on ALL).
        4. Natural order → advance.
        5. Repeat ALL → wrap/regenerate.
        6. No next → PlaybackService.stop()."""
        if self._pending is not None:
            return  # a new candidate is already in flight: stale EOM
        st = self._state
        if st.context_type is PlaybackContextType.NONE:
            return
        if st.context_type is PlaybackContextType.QUEUE:
            self._eom_queue()
            return
        if not st.entries or st.current_index < 0:
            return
        if st.repeat_mode is RepeatMode.ONE:
            self._play_entry(st.current_index)  # exact current entry replays
            return
        if st.shuffle_enabled:
            self._next_shuffled()
            return
        if st.repeat_mode is RepeatMode.ALL:
            self._play_entry((st.current_index + 1) % len(st.entries))
            return
        if st.current_index + 1 < len(st.entries):
            self._play_entry(st.current_index + 1)
            return
        self._playback.stop()

    def _eom_queue(self) -> None:
        """EOM in QUEUE context: navigate the LIVE Queue sequence."""
        st = self._state
        entries, current = self._live_sequence()
        if current < 0 or not entries:
            return
        if st.repeat_mode is RepeatMode.ONE:
            self._request_live_index(current)  # exact current entry replays
            return
        if st.shuffle_enabled:
            self._next_shuffled_live()
            return
        if st.repeat_mode is RepeatMode.ALL:
            self._request_live_index((current + 1) % len(entries))
            return
        if current + 1 < len(entries):
            self._request_live_index(current + 1)
            return
        self._playback.stop()

    # ------------------------------------------------------------------
    # Restore (logical context only — no backend command, no autoplay,
    # no History event)
    # ------------------------------------------------------------------

    def restore_session(
        self,
        *,
        context_type: PlaybackContextType,
        source_id: str | None,
        entries: list[PlaybackSequenceEntry],
        current_index: int,
        repeat_mode: RepeatMode,
        shuffle_enabled: bool,
        shuffle_seed: int,
    ) -> None:
        self._pending = None
        self._request_epoch += 1
        self._state.context_type = context_type
        self._state.source_id = source_id
        self._state.entries = tuple(entries)
        if not -1 <= current_index < len(entries):
            current_index = -1
        self._state.current_index = current_index
        self._state.repeat_mode = repeat_mode
        self._state.shuffle_enabled = shuffle_enabled
        self._shuffle_seed = shuffle_seed
        self._rng = random.Random(shuffle_seed)
        if shuffle_enabled:
            self._navigator.reset(
                list(self._state.entries), self._state.current_entry, self._rng
            )
        else:
            self._navigator.clear()
        self._notify()
