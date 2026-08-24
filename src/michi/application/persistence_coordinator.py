"""Runtime session persistence — checkpoints + startup restore (M5.C5).

The PersistenceCoordinator owns the durable lifecycle of the playback
session snapshot. It subscribes to queue/playback change notifications and
writes a `PlaybackSessionSnapshot` built from PUBLIC state only — pending
candidates are not committed session state and never leak into the durable
snapshot. Checkpoints are synchronous (no threads/timers) and best-effort;
a position throttle avoids a SQLite write per tiny position tick.

The startup restore is TWO-PHASE (M5-LAST-GATE-2): a coherent restore
requests a non-autoplay resume and holds an explicit resume authority
(WAITING_MEDIA -> WAITING_POSITION) until the backend CONFIRMS the position
through PlaybackService's public ``resume_prepared`` event. While any phase
is open, every checkpoint is a HYBRID: the queue portion is the LIVE runtime
queue (user mutations during startup are never lost) while the playback
portion keeps the restored truth WHILE coherent (queue current identity ==
restored playback path); a broken coherence or a rejection/supersession
releases the authority and the next checkpoint is a coherent session.
"""

import logging
from enum import Enum
from pathlib import Path

from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.ports import SessionRepository
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.playback import PlaybackStatus
from michi.domain.playback_session import PlaybackContextType, PlaybackSequenceEntry
from michi.domain.queue import Track


def _session_key(state) -> tuple:
    """Canonical session identity for change detection (M4-R1).

    Entries are EXCLUDED deliberately: the QUEUE live re-projection updates
    the published entries on every Queue mutation, and the Queue event
    itself already checkpoints — entries-only changes must not double-save.
    """
    return (
        state.context_type,
        state.source_id,
        state.current_index,
        state.repeat_mode,
        state.shuffle_enabled,
    )


_CONTEXT_STRING = {
    PlaybackContextType.NONE: "none",
    PlaybackContextType.SINGLE: "single",
    PlaybackContextType.ALBUM: "album",
    PlaybackContextType.PLAYLIST: "playlist",
    PlaybackContextType.QUEUE: "queue",
}
_CONTEXT_TYPE = {string: ctx for ctx, string in _CONTEXT_STRING.items()}
from michi.domain.session import (  # noqa: E402 — after mapping for clarity
    FORMAT_VERSION,
    PersistedQueueEntry,
    PersistedSessionContext,
    PlaybackSessionSnapshot,
)

logger = logging.getLogger(__name__)


class _ResumePhase(Enum):
    """Explicit two-phase restore window (M5-LAST-GATE-2).

    The restore authority starts at WAITING_MEDIA (the resume was requested,
    the backend acceptance not yet reported), moves to WAITING_POSITION when
    the media identity is committed, and returns to NONE only when a backend
    position update confirms the resume (or a rejection/supersession/queue
    coherence break releases it). While any phase is open, checkpoints are
    hybrids (live queue + restored playback truth).
    """

    NONE = 0
    WAITING_MEDIA = 1
    WAITING_POSITION = 2


class PersistenceCoordinator:
    """Durable session lifecycle: checkpoints make restart independent of
    graceful shutdown.

    The lifecycle is EXPLICIT: ``__init__`` arms nothing — ``start()``
    subscribes to queue.changed/playback.changed/resume_prepared, ``stop()``
    unsubscribes, and ``shutdown()`` freezes first, writes the final durable
    checkpoint and the volume/mute preferences, then unsubscribes. The final
    checkpoint is ALWAYS written: the two-phase resume (M5-LAST-GATE-2)
    makes it safe during any restore phase — the checkpoint is a HYBRID
    (live queue + restored playback truth while coherent), so neither the
    restored position nor startup queue mutations are lost. Structural/
    current/repeat/shuffle changes are queue-driven (prompt save), lifecycle
    transitions (PAUSED/STOPPED) and track changes checkpoint immediately,
    and position updates checkpoint only when they have moved at least
    ``position_checkpoint_delta_ms`` from the last PERSISTED position.
    Checkpoints are synchronous on notifications — no threads or timers.

    ``restore()`` (startup) rebuilds the queue from the persisted snapshot
    (C3 — atomic, capacity-guarded) and, only when the queue current
    identity matches the backend playback identity (coherence rule,
    §4/§22), prepares a non-autoplay resume (C4 — load + seek after
    acceptance). A mismatched playback path is never used to fabricate a
    PlaybackState. During ``restore()`` the change notifications are
    suppressed by the explicit restoring state (P1-A); once started, the
    two-phase window CONSUMES playback events (no checkpoint while the
    hybrid protects) and checkpoints queue events as hybrids. ``shutdown()``
    freezes the subscriptions FIRST, writes a final checkpoint, persists the
    current volume/mute through the SettingsService public API, and then
    unsubscribes (P2-A); the caller tears the backend down only after
    ``shutdown()`` returns. Volume/mute changes are also persisted DURING
    runtime through a separate settings channel (P1-B) — no graceful-
    shutdown dependency.
    """

    def __init__(
        self,
        session_repository: SessionRepository,
        queue_service: QueueService,
        playback_session: PlaybackSessionService,
        playback_service: PlaybackService,
        settings_service: SettingsService,
        position_checkpoint_delta_ms: int = 5000,
    ) -> None:
        self._repo = session_repository
        self._queue = queue_service
        self._session = playback_session
        self._playback = playback_service
        self._settings = settings_service
        self._position_checkpoint_delta_ms = position_checkpoint_delta_ms
        # Durable position marker: position deltas are measured from the
        # last position the application KNOWS was persisted. Seeded from
        # the current position so a volume-only event (which must never
        # trigger a session rewrite) is not mistaken for an unpersisted
        # baseline.
        self._last_persisted_position_ms: int | None = (
            playback_service.state.position_ms
        )
        # Deterministic change detection: remember the last observed
        # status/file_path so each notification can be classified. Only
        # consulted while started.
        self._last_status = playback_service.state.status
        self._last_file_path = playback_service.state.file_path
        # Explicit lifecycle: subscriptions are armed by start().
        self._started = False
        self._shutdown = False
        self._restoring = False
        # M5-LAST-GATE-2: the explicit two-phase restore window. Set by
        # restore() when a coherent resume was prepared, released only by a
        # backend position confirmation (resume_prepared), a rejection, a
        # supersession/removal, or a queue coherence break. While any phase
        # is open, checkpoints are hybrids — the restored playback truth is
        # preserved AND live queue mutations are never lost.
        self._resume_phase = _ResumePhase.NONE
        # The loaded durable truth while the resume window is open; a
        # shutdown/queue change inside the window must never let the
        # incomplete runtime Playback (still None@0) overwrite it. Cleared
        # when the window closes or the coordinator stops.
        self._restored_snapshot: PlaybackSessionSnapshot | None = None
        # Last-observed volume/mute (P1-B runtime sync baseline).
        self._last_volume, self._last_muted = playback_service.snapshot_volume()
        # M4-R1: session change-detection baseline — only canonical session
        # changes (context/current/repeat/shuffle) checkpoint; a session
        # notification caused by the queue-driven live re-projection must
        # not double-checkpoint (the queue event already saved).
        self._last_session_key = _session_key(playback_session.state)

    def _build_snapshot(self) -> PlaybackSessionSnapshot:
        """Encode the PUBLIC session state (§26).

        Pending candidates are not committed session state (§27) and are
        never persisted. The QUEUE portion is ALWAYS the live runtime queue
        (tracks/current/repeat/shuffle/seed) — user mutations during the
        restore window are never lost (M5-LAST-GATE-2 hybrid). The PLAYBACK
        portion is hybrid while a resume phase is open: the restored
        snapshot's playback_path/position_ms WHILE coherent (queue current
        identity == restored path); a broken coherence writes
        playback_path None / position 0 — the queue mutation wins and no
        identity is fabricated. Outside any phase the runtime Playback is
        encoded ONLY WHILE coherent with the live queue current identity;
        a retained playback file_path (M4: stop() keeps it) that the queue
        does not confirm is never encoded — the durable projection never
        fabricates a playback identity the queue does not confirm.
        """
        queue_state = self._queue.state
        session_state = self._session.state
        if (
            self._resume_phase is not _ResumePhase.NONE
            and self._restored_snapshot is not None
        ):
            if self._hybrid_coherent():
                playback_path = self._restored_snapshot.playback_path
                position_ms = self._restored_snapshot.position_ms
            else:
                playback_path = None
                position_ms = 0
        else:
            playback_state = self._playback.state
            session_entry = session_state.current_entry
            coherent_runtime = (
                playback_state.file_path is not None
                and session_entry is not None
                and str(session_entry.file_path) == str(playback_state.file_path)
            )
            if coherent_runtime:
                playback_path = str(playback_state.file_path)
                position_ms = playback_state.position_ms
            else:
                # PlaybackSession coherence is authoritative (M4-R1 §66): a
                # retained playback file_path that the active session does
                # not confirm is never durable garbage.
                playback_path = None
                position_ms = 0
        context_type = session_state.context_type
        return PlaybackSessionSnapshot(
            format_version=FORMAT_VERSION,
            queue_entries=tuple(
                PersistedQueueEntry(str(track.file_path), track.title)
                for track in queue_state.tracks
            ),
            context=PersistedSessionContext(
                context_type=_CONTEXT_STRING[context_type],
                source_id=session_state.source_id,
                entries=tuple(
                    PersistedQueueEntry(str(e.file_path), e.title)
                    for e in session_state.entries
                ),
                current_index=session_state.current_index,
            ),
            playback_path=playback_path,
            position_ms=position_ms,
            repeat_mode=session_state.repeat_mode,
            shuffle_enabled=session_state.shuffle_enabled,
            shuffle_seed=self._session.shuffle_seed,
        )

    def _hybrid_coherent(self) -> bool:
        """The hybrid's playback portion is only trusted WHILE coherent:
        a resume phase is open, a restored snapshot exists, its playback
        path is present, and the LIVE queue current identity matches the
        restored path (string equality)."""
        restored = self._restored_snapshot
        session_entry = self._session.state.current_entry
        return (
            self._resume_phase is not _ResumePhase.NONE
            and restored is not None
            and restored.playback_path is not None
            and session_entry is not None
            and str(session_entry.file_path) == restored.playback_path
        )

    def _release_resume_authority(self, reason: str = "resume resolved") -> None:
        """Close the restore window: drop the phase and the restored truth.

        The next checkpoint is then a coherent runtime session. The pending
        resume prepare itself is cancelled through the public machinery by
        the CALLER (PlaybackService.stop) where required — releasing here
        only clears the coordinator-side authority.
        """
        self._resume_phase = _ResumePhase.NONE
        self._restored_snapshot = None
        logger.debug("resume authority released: %s", reason)

    def checkpoint(self) -> None:
        """Best-effort synchronous save of the current session state.

        The snapshot is built ONCE and that exact snapshot is saved. The
        repository never raises on sqlite errors (it returns a success
        signal); this also tolerates any unexpected repository failure
        (logged, never propagated). The durable position marker advances to
        the SNAPSHOT's position_ms — not the raw runtime position — ONLY
        when the save actually succeeded, so during the hybrid window it
        matches what was durably written (the restored truth) and a failing
        write does not move the throttle baseline. Runtime continues
        regardless.
        """
        snapshot = self._build_snapshot()
        try:
            saved = self._repo.save(snapshot)
        except Exception as exc:
            logger.warning(
                "session checkpoint failed; durable state remains at previous "
                "checkpoint: %s",
                exc,
            )
            saved = False
        if saved:
            self._last_persisted_position_ms = snapshot.position_ms
        else:
            logger.warning(
                "session checkpoint failed; durable state remains at "
                "previous checkpoint"
            )

    def start(self) -> None:
        """Arm the runtime subscriptions (idempotent).

        ``start()`` is the only place the coordinator subscribes: the
        change notifications below persist session state and the runtime
        volume/mute sync, and the resume_prepared event completes the
        two-phase restore. Snapshotting the last-observed volume/mute here
        means only changes observed AFTER startup are persisted.
        """
        if self._started:
            return
        self._queue.subscribe_changed(self._on_queue_changed)
        self._session.subscribe_changed(self._on_session_changed)
        self._playback.subscribe_changed(self._on_playback_changed)
        self._playback.subscribe_resume_prepared(self._on_resume_prepared)
        self._last_volume, self._last_muted = self._playback.snapshot_volume()
        self._started = True

    def stop(self) -> None:
        """Disarm the runtime subscriptions (idempotent)."""
        if not self._started:
            return
        self._queue.unsubscribe_changed(self._on_queue_changed)
        self._session.unsubscribe_changed(self._on_session_changed)
        self._playback.unsubscribe_changed(self._on_playback_changed)
        self._playback.unsubscribe_resume_prepared(self._on_resume_prepared)
        self._started = False

    def _on_queue_changed(self) -> None:
        # Structural/current/repeat/shuffle changes are all queue-driven:
        # prompt save. Never while restoring or disarmed. During the restore
        # window the checkpoint is a HYBRID (live queue + restored playback
        # truth while coherent), so queue mutations during startup persist
        # instead of being suppressed.
        if self._restoring or not self._started:
            return
        # M4-R1 final seal: Persistence observes Queue for PERSISTENCE only.
        # Queue→Session delivery is owned exclusively by
        # PlaybackSessionService.start() — never redispatch here (one
        # delivery path). Queue changes only invalidate a resume when they
        # change the ACTIVE QUEUE context in a way that breaks session
        # playback identity (SINGLE/ALBUM/PLAYLIST unaffected).
        if self._resume_phase is not _ResumePhase.NONE:
            session_type = self._session.state.context_type
            if (
                session_type is PlaybackContextType.QUEUE
                and not self._hybrid_coherent()
            ):
                self._playback.stop()
                self._release_resume_authority(reason="queue coherence broken")
            # non-QUEUE contexts: Queue mutation does NOT invalidate resume
        self.checkpoint()

    def _on_session_changed(self) -> None:
        # Session context/navigation changes: prompt save. Never while
        # restoring or disarmed. Only CANONICAL session changes checkpoint —
        # a session notification caused by the QUEUE live re-projection
        # (triggered by the same queue event that already checkpoints)
        # must not double-save.
        if self._restoring or not self._started:
            return
        key = _session_key(self._session.state)
        if key == self._last_session_key:
            return  # no canonical change (live re-projection only)
        self._last_session_key = key
        # If the active session current identity supersedes during restore,
        # cancel the pending resume through the public machinery and release
        # the restored authority (same discipline as queue-coherence).
        if (
            self._resume_phase is not _ResumePhase.NONE
            and self._session.state.current_entry is not None
            and (
                self._restored_snapshot is None
                or str(self._session.state.current_entry.file_path)
                != self._restored_snapshot.playback_path
            )
        ):
            self._playback.stop()
            self._release_resume_authority(reason="session superseded")
        self.checkpoint()

    def _on_resume_prepared(self, path: Path, position_ms: int) -> None:
        # M5-PRODUCTION-LIFECYCLE-GATE: the backend CONFIRMED the resume
        # position (media accepted + first post-acceptance position update —
        # the confirmed, clamp-aware value). Received even DURING _restoring:
        # it is the COMPLETION signal of the two-phase restore — the state IS
        # complete at that point (release + marker + checkpoint are safe;
        # restore_session already ran and the confirmed position is the
        # runtime truth) — so it is gated ONLY on _started and never dropped
        # inside the restore window. The restore window closes and the
        # runtime truth (including the confirmed position) becomes durable
        # immediately: no future checkpoint can regress it.
        if not self._started:
            return
        self._release_resume_authority(reason="resume position confirmed")
        self._last_persisted_position_ms = position_ms
        self.checkpoint()

    def _on_playback_changed(self) -> None:
        # Restore's OWN notifications (restore_session/prepare_for_resume)
        # never checkpoint: suppressed while restoring or disarmed. The
        # restore COMPLETION does not flow through here — it arrives via
        # _on_resume_prepared, which is gated ONLY on _started (never
        # dropped inside the restore window).
        if self._restoring or not self._started:
            return
        state = self._playback.state
        # M5-LAST-GATE-2 restore window: while a phase is open, playback
        # events are startup fallout — consumed without a checkpoint (the
        # hybrid protects the durable truth). Media acceptance moves
        # WAITING_MEDIA -> WAITING_POSITION (no release, no checkpoint); a
        # rejection or supersession/removal RELEASES the authority, and the
        # releasing event itself FALLS THROUGH to the normal classification
        # below so it processes normally (the rejection transition
        # checkpoints the coherent session; the supersession's file_path
        # change checkpoints the new runtime).
        if self._resume_phase is _ResumePhase.WAITING_MEDIA:
            if state.file_path is not None:
                # Media accepted: the identity is committed — the window
                # moves to WAITING_POSITION, still protected.
                self._resume_phase = _ResumePhase.WAITING_POSITION
                self._last_status = state.status
                self._last_file_path = state.file_path
                return
            if state.error_message is not None:
                self._release_resume_authority(reason="media rejected")
                # fall through: the rejection's STOPPED transition
                # checkpoints the coherent session
            elif state.status is not PlaybackStatus.STOPPED:
                # Unexpected lifecycle state while waiting for media.
                self._release_resume_authority(
                    reason="unexpected playback state during restore"
                )
                # fall through: process the event normally
            else:
                # Still waiting for the backend acceptance — consume.
                self._last_status = state.status
                self._last_file_path = state.file_path
                return
        elif self._resume_phase is _ResumePhase.WAITING_POSITION:
            if state.error_message is not None:
                # Runtime error on the restored committed track.
                self._release_resume_authority(reason="media rejected")
                # fall through
            elif (
                state.file_path is None
                or self._restored_snapshot is None
                or str(state.file_path) != self._restored_snapshot.playback_path
            ):
                # The committed identity was superseded or removed.
                self._release_resume_authority(reason="superseded or removed")
                # fall through: the file_path change checkpoints the new truth
            else:
                # Still waiting for the backend position confirmation —
                # consume (the resume_prepared event does the release).
                self._last_status = state.status
                self._last_file_path = state.file_path
                return
        status_changed = state.status is not self._last_status
        file_path_changed = state.file_path != self._last_file_path
        if status_changed and state.status in (
            PlaybackStatus.PAUSED,
            PlaybackStatus.STOPPED,
        ):
            # Lifecycle transition: prompt save.
            self.checkpoint()
        elif file_path_changed:
            # Track change: prompt save.
            self.checkpoint()
        else:
            position_ms = state.position_ms
            if (
                self._last_persisted_position_ms is None
                or abs(position_ms - self._last_persisted_position_ms)
                >= self._position_checkpoint_delta_ms
            ):
                # Position throttle: no SQLite write per tiny position tick.
                self.checkpoint()
        self._last_status = state.status
        self._last_file_path = state.file_path
        # P1-B runtime volume/mute sync — a SEPARATE durable channel that
        # never touches the session_snapshot row: persist through the
        # settings public API only when the last-observed values changed.
        volume, muted = self._playback.snapshot_volume()
        if volume != self._last_volume or muted != self._last_muted:
            self._settings.set_playback_preferences(volume, muted)
            self._settings.save()
            self._last_volume = volume
            self._last_muted = muted

    def restore(self, *, engine_available: bool = True) -> None:
        """Startup: rebuild Queue content, restore the PlaybackSession
        logical context, then resume playback only when the SESSION current
        entry matches the persisted playback identity (M4-R1 §66).

        M11.3G (§66): ``engine_available=False`` (no engine could be
        activated at startup) restores QueueState and the logical session
        context but MUST NOT attempt a backend load/seek — the router is
        unbound and no resume may be fabricated. The resume phase stays
        NONE; the next startup (or an explicit engine activation) retries
        normally.

        The coherence rule (§4/§22) guards the resume: ``prepare_for_resume``
        is requested ONLY when the restored session current entry is valid
        and equals ``snapshot.playback_path`` (string equality). A
        mismatched or absent playback path restores content/context only —
        PlaybackState is never fabricated and no load is requested.
        Restore NEVER emits a History event and NEVER autoplays.

        While restoring, the change notifications (restore_session's queue
        notification, prepare_for_resume's playback notification) are
        suppressed so the durable resume snapshot is never degraded by the
        restore itself. Works unstarted (no subscriptions needed). After
        the guard clears (M5-FINAL-TERMINAL-RECONCILIATION): the durable
        marker is set from the restored snapshot ONLY while the resume
        phase is still open (a confirmation that arrived INSIDE restore
        already advanced it to the CONFIRMED value — never regressed by
        the stale snapshot position); the change-detection baseline is
        refreshed from the current playback state so the first post-restore
        position tick classifies by the position delta, never a stale
        file_path change; a terminal backend outcome surfaced inside
        restore while a phase is still open (error_message set — fast
        rejection / seek failure, notifications consumed by the guard)
        releases the resume authority and persists the coherent session —
        the state machine never stays open forever; and the last-observed
        volume/mute is refreshed so a legit post-startup change syncs
        (P1-B).
        """
        if self._restoring:
            return
        self._restoring = True
        try:
            snapshot = self._repo.load()
            # M4-R1: Queue CONTENT restoration (no playback fields).
            self._queue.restore_entries(
                [Track(Path(e.file_path), e.title) for e in snapshot.queue_entries]
            )
            # M4-R1: PlaybackSession logical context restoration — no backend
            # command, no autoplay, no History event.
            context = snapshot.context
            self._session.restore_session(
                context_type=_CONTEXT_TYPE[context.context_type],
                source_id=context.source_id,
                entries=[
                    PlaybackSequenceEntry(Path(e.file_path), e.title)
                    for e in context.entries
                ],
                current_index=context.current_index,
                repeat_mode=snapshot.repeat_mode,
                shuffle_enabled=snapshot.shuffle_enabled,
                shuffle_seed=snapshot.shuffle_seed,
            )
            entries = context.entries
            idx = context.current_index
            coherent = (
                snapshot.playback_path is not None
                and 0 <= idx < len(entries)
                and entries[idx].file_path == snapshot.playback_path
                and engine_available  # M11.3G §66: never resume unbound
            )
            if coherent:
                # M5-LAST-GATE-2: the loaded snapshot is the last valid
                # durable truth while the two-phase resume is unresolved; a
                # shutdown or session change inside the window must never
                # overwrite it with the incomplete runtime Playback.
                self._restored_snapshot = snapshot
                self._resume_phase = _ResumePhase.WAITING_MEDIA
                # C4: load + seek after acceptance; never autoplay.
                self._playback.prepare_for_resume(
                    Path(snapshot.playback_path), snapshot.position_ms
                )
                # The restore window stays open (WAITING_MEDIA) until the
                # backend confirms the position (resume_prepared), rejects
                # it, or the session coherence breaks.
            else:
                # No resume is pending: no restored truth is being held, so a
                # later shutdown must checkpoint normally.
                self._resume_phase = _ResumePhase.NONE
                self._restored_snapshot = None
        finally:
            self._restoring = False
        # The restored position is already persisted; future checkpoints
        # measure position deltas from it. A confirmation that arrived
        # INSIDE restore (fast backend) already advanced the durable marker
        # to the CONFIRMED value — the stale snapshot position must never
        # regress it; only the still-pending case adopts the snapshot
        # position (which is what the hybrid holds).
        if self._resume_phase is not _ResumePhase.NONE:
            self._last_persisted_position_ms = snapshot.position_ms
        # Refresh the change-detection baseline from the CURRENT playback
        # state so the first post-restore position tick classifies by the
        # position delta — never a stale file_path/status change that a
        # suppressed restore notification left behind.
        self._last_status = self._playback.state.status
        self._last_file_path = self._playback.state.file_path
        # Refresh the last-observed volume/mute from the current playback
        # state so a legit post-startup change syncs (P1-B).
        self._last_volume, self._last_muted = self._playback.snapshot_volume()
        # M5-FINAL-TERMINAL-RECONCILIATION: a FAST backend terminal outcome
        # (rejection / seek failure) surfaced synchronously INSIDE restore()
        # and its notifications were consumed by the _restoring guard. The
        # state machine must never stay open forever: release the resume
        # authority and persist the coherent session (queue restored;
        # playback truth per the runtime encode — rejection: None@0; seek
        # failure: the committed path at 0, never the stale hybrid position).
        if (
            self._resume_phase is not _ResumePhase.NONE
            and self._playback.state.error_message is not None
        ):
            self._release_resume_authority(reason="terminal restore outcome")
            self.checkpoint()

    def shutdown(self) -> None:
        """Final durable state: freeze -> checkpoint -> prefs -> unsubscribe.

        Idempotent. Freezes the subscriptions FIRST so backend teardown
        events arriving afterwards are ignored, then writes the final
        checkpoint (the repo save is called directly — checkpoint works
        without subscriptions), persists volume/mute through the settings
        public API, and unsubscribes. The caller tears the backend down
        only after shutdown() returns, so the final durable checkpoint is
        guaranteed to precede runtime teardown.

        M5-LAST-GATE-2: the final checkpoint is ALWAYS written — the hybrid
        makes it safe during ANY restore phase. While a phase is open the
        snapshot keeps the restored playback truth (WHILE coherent) AND the
        live queue mutations; once the resume confirmed, the runtime truth
        (including the confirmed position) is durable. Volume/mute persist
        unchanged in both paths (the settings channel never touches the
        session row).
        """
        if self._shutdown:
            return
        self._shutdown = True
        self._started = False  # freeze FIRST: stop accepting callbacks
        self.checkpoint()
        volume, muted = self._playback.snapshot_volume()
        self._settings.set_playback_preferences(volume, muted)
        self._settings.save()
        self._queue.unsubscribe_changed(self._on_queue_changed)
        self._session.unsubscribe_changed(self._on_session_changed)
        self._playback.unsubscribe_changed(self._on_playback_changed)
        self._playback.unsubscribe_resume_prepared(self._on_resume_prepared)
        self._restoring = False
        self._resume_phase = _ResumePhase.NONE
        self._restored_snapshot = None
