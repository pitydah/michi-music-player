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
from michi.application.ports import SessionRepository
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.playback import PlaybackStatus
from michi.domain.session import (
    FORMAT_VERSION,
    PersistedQueueEntry,
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
        playback_service: PlaybackService,
        settings_service: SettingsService,
        position_checkpoint_delta_ms: int = 5000,
    ) -> None:
        self._repo = session_repository
        self._queue = queue_service
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
        encoded.
        """
        queue_state = self._queue.state
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
            playback_path = (
                str(playback_state.file_path)
                if playback_state.file_path is not None
                else None
            )
            position_ms = playback_state.position_ms
        return PlaybackSessionSnapshot(
            format_version=FORMAT_VERSION,
            queue_entries=tuple(
                PersistedQueueEntry(str(track.file_path), track.title)
                for track in queue_state.tracks
            ),
            queue_current_index=queue_state.current_index,
            playback_path=playback_path,
            position_ms=position_ms,
            repeat_mode=queue_state.repeat_mode,
            shuffle_enabled=queue_state.shuffle_enabled,
            shuffle_seed=self._queue.shuffle_seed,
        )

    def _hybrid_coherent(self) -> bool:
        """The hybrid's playback portion is only trusted WHILE coherent:
        a resume phase is open, a restored snapshot exists, its playback
        path is present, and the LIVE queue current identity matches the
        restored path (string equality)."""
        restored = self._restored_snapshot
        return (
            self._resume_phase is not _ResumePhase.NONE
            and restored is not None
            and restored.playback_path is not None
            and 0 <= self._queue.state.current_index < len(self._queue.state.tracks)
            and str(self._queue.state.tracks[self._queue.state.current_index].file_path)
            == restored.playback_path
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
        self._playback.subscribe_changed(self._on_playback_changed)
        self._playback.subscribe_resume_prepared(self._on_resume_prepared)
        self._last_volume, self._last_muted = self._playback.snapshot_volume()
        self._started = True

    def stop(self) -> None:
        """Disarm the runtime subscriptions (idempotent)."""
        if not self._started:
            return
        self._queue.unsubscribe_changed(self._on_queue_changed)
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
        self.checkpoint()
        # A queue mutation that broke the hybrid coherence (e.g. removing
        # the restored current) invalidates the restored playback truth: the
        # pending resume is cancelled through the PUBLIC machinery (safe
        # during the window — nothing is playing; stop clears the pending
        # prepare), THEN the authority is released.
        if self._resume_phase is not _ResumePhase.NONE and not self._hybrid_coherent():
            self._playback.stop()
            self._release_resume_authority(reason="queue coherence broken")

    def _on_resume_prepared(self, path: Path, position_ms: int) -> None:
        # M5-LAST-GATE-2: the backend CONFIRMED the resume position (media
        # accepted + first post-acceptance position update — the confirmed,
        # clamp-aware value). The restore window closes and the runtime truth
        # (including the confirmed position) becomes durable immediately:
        # no future checkpoint can regress it.
        if self._resume_phase in (
            _ResumePhase.WAITING_MEDIA,
            _ResumePhase.WAITING_POSITION,
        ):
            self._release_resume_authority(reason="resume position confirmed")
            self._last_persisted_position_ms = position_ms
            self.checkpoint()

    def _on_playback_changed(self) -> None:
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

    def restore(self) -> None:
        """Startup: rebuild the queue, then resume playback only when the
        queue current identity matches the persisted playback identity.

        The coherence rule (§4/§22) guards the resume: ``prepare_for_resume``
        is requested ONLY when ``snapshot.queue_current_index`` is valid and
        the entry at that index equals ``snapshot.playback_path`` (string
        equality). A mismatched or absent playback path restores the queue
        only — PlaybackState is never fabricated and no load is requested.

        While restoring, the change notifications (restore_session's queue
        notification, prepare_for_resume's playback notification) are
        suppressed so the durable resume snapshot is never degraded by the
        restore itself. Works unstarted (no subscriptions needed). After
        the guard clears, the durable marker is set from the restored
        snapshot and the last-observed volume/mute is refreshed from the
        current playback state, so a legit post-startup change syncs.
        """
        if self._restoring:
            return
        self._restoring = True
        try:
            snapshot = self._repo.load()
            self._queue.restore_session(snapshot)
            entries = snapshot.queue_entries
            idx = snapshot.queue_current_index
            coherent = (
                snapshot.playback_path is not None
                and 0 <= idx < len(entries)
                and entries[idx].file_path == snapshot.playback_path
            )
            if coherent:
                # M5-LAST-GATE-2: the loaded snapshot is the last valid
                # durable truth while the two-phase resume is unresolved; a
                # shutdown or queue change inside the window must never
                # overwrite it with the incomplete runtime Playback.
                self._restored_snapshot = snapshot
                self._resume_phase = _ResumePhase.WAITING_MEDIA
                # C4: load + seek after acceptance; never autoplay.
                self._playback.prepare_for_resume(
                    Path(snapshot.playback_path), snapshot.position_ms
                )
                # The restore window stays open (WAITING_MEDIA) until the
                # backend confirms the position (resume_prepared), rejects
                # it, or the queue coherence breaks.
            else:
                # No resume is pending: no restored truth is being held, so a
                # later shutdown must checkpoint normally.
                self._resume_phase = _ResumePhase.NONE
                self._restored_snapshot = None
        finally:
            self._restoring = False
        # The restored position is already persisted; future checkpoints
        # measure position deltas from it.
        self._last_persisted_position_ms = snapshot.position_ms
        # Refresh the last-observed volume/mute from the current playback
        # state so a legit post-startup change syncs (P1-B).
        self._last_volume, self._last_muted = self._playback.snapshot_volume()

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
        self._playback.unsubscribe_changed(self._on_playback_changed)
        self._playback.unsubscribe_resume_prepared(self._on_resume_prepared)
        self._restoring = False
        self._resume_phase = _ResumePhase.NONE
        self._restored_snapshot = None
