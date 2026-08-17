"""Runtime session persistence — checkpoints + startup restore (M5.C5).

The PersistenceCoordinator owns the durable lifecycle of the playback
session snapshot. It subscribes to queue/playback change notifications and
writes a `PlaybackSessionSnapshot` built from PUBLIC state only — pending
candidates are not committed session state and never leak into the durable
snapshot. Checkpoints are synchronous (no threads/timers) and best-effort;
a position throttle avoids a SQLite write per tiny position tick.
"""

import logging
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


class PersistenceCoordinator:
    """Durable session lifecycle: checkpoints make restart independent of
    graceful shutdown.

    Subscribes to queue.changed and playback.changed; structural/current/
    repeat/shuffle changes are queue-driven (prompt save), lifecycle
    transitions (PAUSED/STOPPED) and track changes checkpoint immediately,
    and position updates checkpoint only when they have moved at least
    ``position_checkpoint_delta_ms`` from the last persisted position.
    Checkpoints are synchronous on notifications — no threads or timers.

    ``restore()`` (startup) rebuilds the queue from the persisted snapshot
    (C3 — atomic, capacity-guarded) and, only when the queue current
    identity matches the backend playback identity (coherence rule,
    §4/§22), prepares a non-autoplay resume (C4 — load + seek after
    acceptance). A mismatched playback path is never used to fabricate a
    PlaybackState. ``shutdown()`` writes a final checkpoint and persists
    the current volume/mute through the SettingsService public API.
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
        self._last_persisted_position_ms: int | None = None
        # Deterministic change detection: remember the last observed
        # status/file_path so each notification can be classified.
        self._last_status = playback_service.state.status
        self._last_file_path = playback_service.state.file_path
        queue_service.subscribe_changed(self._on_queue_changed)
        playback_service.subscribe_changed(self._on_playback_changed)

    def _build_snapshot(self) -> PlaybackSessionSnapshot:
        """Encode the PUBLIC session state (§26).

        Pending candidates are not committed session state (§27) and are
        never persisted; only the committed queue/current/playback identity
        is captured.
        """
        queue_state = self._queue.state
        playback_state = self._playback.state
        return PlaybackSessionSnapshot(
            format_version=FORMAT_VERSION,
            queue_entries=tuple(
                PersistedQueueEntry(str(track.file_path), track.title)
                for track in queue_state.tracks
            ),
            queue_current_index=queue_state.current_index,
            playback_path=(
                str(playback_state.file_path)
                if playback_state.file_path is not None
                else None
            ),
            position_ms=playback_state.position_ms,
            repeat_mode=queue_state.repeat_mode,
            shuffle_enabled=queue_state.shuffle_enabled,
            shuffle_seed=self._queue.shuffle_seed,
        )

    def checkpoint(self) -> None:
        """Best-effort synchronous save of the current session state.

        The repository never raises on sqlite errors; this also tolerates
        any unexpected repository failure (logged, never propagated). The
        last persisted position is always advanced so a failing write does
        not turn into a retry loop.
        """
        try:
            self._repo.save(self._build_snapshot())
        except Exception as exc:
            logger.warning("session checkpoint failed; ignoring: %s", exc)
        self._last_persisted_position_ms = self._playback.state.position_ms

    def _on_queue_changed(self) -> None:
        # Structural/current/repeat/shuffle changes are all queue-driven:
        # prompt save.
        self.checkpoint()

    def _on_playback_changed(self) -> None:
        state = self._playback.state
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

    def restore(self) -> None:
        """Startup: rebuild the queue, then resume playback only when the
        queue current identity matches the persisted playback identity.

        The coherence rule (§4/§22) guards the resume: ``prepare_for_resume``
        is requested ONLY when ``snapshot.queue_current_index`` is valid and
        the entry at that index equals ``snapshot.playback_path`` (string
        equality). A mismatched or absent playback path restores the queue
        only — PlaybackState is never fabricated and no load is requested.
        """
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
            # C4: load + seek after acceptance; never autoplay.
            self._playback.prepare_for_resume(
                Path(snapshot.playback_path), snapshot.position_ms
            )
        # The restored position is already persisted; future checkpoints
        # measure position deltas from it.
        self._last_persisted_position_ms = snapshot.position_ms

    def shutdown(self) -> None:
        """Final checkpoint + volume/mute persistence (graceful stop)."""
        self.checkpoint()
        volume, muted = self._playback.snapshot_volume()
        self._settings.set_playback_preferences(volume, muted)
        self._settings.save()
