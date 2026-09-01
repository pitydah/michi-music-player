"""Playback use case — the single mutation authority for PlaybackState."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from michi.application.audio_engine_selection import (
    EngineSwitchBlocker,
    EngineSwitchReadiness,
    MediaRequestPurpose,
    MediaRequestTerminalResult,
    MediaRequestTerminalStatus,
)
from michi.application.ports import AudioLoadError, AudioPort
from michi.domain.playback import PlaybackState, PlaybackStatus

logger = logging.getLogger(__name__)


class EngineSwitchLeaseHeldError(RuntimeError):
    """A playback intent was rejected because an engine switch is holding
    the exclusive quiescence lease (P1-01). Deterministic, explicit."""


class EngineSwitchLease:
    """Exclusive runtime-switch authority plus immutable playback snapshot.

    The coordinator can issue privileged transition commands through this
    object; external PlaybackService commands remain rejected until release
    or terminal engine-switch rehydration.
    """

    __slots__ = ("_service", "_released", "_generation", "snapshot")

    def __init__(
        self,
        service: "PlaybackService",
        snapshot: "EngineSwitchMediaSnapshot",
        generation: int,
    ) -> None:
        self._service = service
        self._released = False
        self._generation = generation
        self.snapshot = snapshot

    def controlled_stop(self) -> None:
        self._service._engine_switch_controlled_stop(self)

    def invalidate_backend_acceptance(self) -> None:
        self._service._engine_switch_invalidate_acceptance(self)

    def prepare_on_target(self) -> bool:
        """Start stopped-media rehydration.

        Returns True when the transition authority was handed to an
        asynchronous request. A terminal callback/timeout then releases it.
        """
        return self._service._engine_switch_prepare_on_target(self)

    def release(self) -> None:
        if not self._released:
            self._released = True
            self._service._release_engine_switch_lease(self)


class PlaybackNotQuiescentError(RuntimeError):
    """The engine-switch lease could not be acquired: playback is not in a
    switchable (quiescent) state."""


@dataclass(frozen=True, slots=True)
class EngineSwitchMediaSnapshot:
    """KCR-021: read-only stopped-media truth captured BEFORE the engine
    destructive boundary. A deferred resume target is a LOGICAL intent,
    never a confirmed backend position."""

    file_path: Path | None
    confirmed_position_ms: int
    deferred_resume_target_ms: int | None
    previous_status: PlaybackStatus = PlaybackStatus.STOPPED
    volume: int = 100
    muted: bool = False


class PlaybackService:
    """Sole canonical authority over PlaybackState. Publishes changes.

    Playback acceptance is asynchronous: `load_and_play` only *requests* a
    candidate. The candidate becomes canonical when the backend reports media
    acceptance (`subscribe_media_accepted`); it is dropped when the backend
    reports rejection or when `stop()` cancels the request. A pending request
    terminates in exactly one of ACCEPTED / REJECTED / CANCELLED /
    SUPERSEDED; `stop()` notifies the requestor via `on_cancelled` at most
    once with the exact pending path. Until a terminal outcome, the service
    owns the pending candidate locally and PlaybackState reflects the last
    committed track as STOPPED.

    Acceptance commits track identity only — never PLAYING. LoadedMedia means
    the media is loaded while the player is in the StoppedState; actual
    playback state follows the backend `playbackStateChanged` signal, which
    this service self-subscribes to and maps truthfully (PlayingState →
    PLAYING, PausedState → PAUSED, StoppedState → STOPPED, idempotently).

    Two minimal guards keep stale lifecycle events honest:
    - `_intent`: True after a successful request (also armed by play()/
      resume()), set False by `stop()` and rejection. Active state events
      (PLAYING, PAUSED) are applied only while intent holds; STOPPED is
      always applied (idempotently), so a late PlayingState cannot
      resurrect playback after stop/rejection.
    - `_accepted`: True only once the current candidate has been accepted,
      reset on each new request and on rejection. PLAYING is never published
      for a track whose identity was not committed.

    INV-AUDIO-NO-GHOST-PLAYBACK (R2/R2.1): a backend reporting non-STOPPED
    (PLAYING/PAUSED) WITHOUT a valid intent is an AUTHORITY VIOLATION — it
    is NEVER silently discarded. The service converges ACTIVELY to STOPPED
    (safety stop + diagnosis; a failed stop surfaces on the model state)
    and never publishes the ghost state. This closes the production
    failure where MPD autoplayed after startup restore (seekid on a stopped
    song starts playback) while the model kept showing STOPPED.

    `prepare_for_resume` is the startup resume path: it requests a backend
    LOAD and, only after acceptance, seeks the backend to the persisted
    position — it loads and seeks, never autoplays. Intent stays unarmed
    during preparation; an unexpected backend PLAYING during preparation is
    an authority violation and converges actively to STOPPED (it is never
    ignored). The user's later `play()` resumes from the sought position.

    `subscribe_resume_prepared` is the public resume-confirmation signal
    (M5-LAST-GATE-2): it fires exactly ONCE — on the first backend position
    update after a prepare_for_resume reached media acceptance and the seek
    was requested — carrying the committed file path and the CONFIRMED
    position (backend clamp tolerated; position 0 is a valid confirmation).
    Status stays STOPPED and nothing autoplays: the signal only completes
    the two-phase restore (media accepted -> position confirmed). It never
    fires for load_and_play (no resume slot).

    Commands express intent only: play()/pause()/resume() never mutate
    PlaybackStatus or notify; PLAYING/PAUSED/STOPPED are published
    exclusively from backend state events. `stop()` is the single
    optimistic exception (safety command: STOPPED immediately).
    """

    def __init__(self, audio_port: AudioPort) -> None:
        self._audio = audio_port
        self._state = PlaybackState()
        self._subscribers: list[Callable[[], None]] = []
        self._eom_subscribers: list[Callable[[], None]] = []
        self._pending_path: Path | None = None
        self._pending_on_accepted: Callable[[Path], None] | None = None
        self._pending_on_rejected: Callable[[Path, str], None] | None = None
        self._pending_on_cancelled: Callable[[Path], None] | None = None
        self._pending_purpose: MediaRequestPurpose | None = None
        self._pending_resume_position_ms: int | None = None
        # M5-LAST-GATE-2 resume confirmation: armed when a prepare_for_resume
        # actually requested a seek (post-acceptance), disarmed by the FIRST
        # position update (which fires `resume_prepared` once) or by any path
        # that clears the resume slot (rejection/stop/supersession).
        self._resume_prepared_subscribers: list[Callable[[Path, int], None]] = []
        self._resume_prepared_pending: bool = False
        # R2.1-02: a registered (not yet confirmed) resume target — distinct
        # from a confirmed backend position; never blocks quiescence.
        self._deferred_resume_target_ms: int | None = None
        self._intent = False
        self._accepted = False
        self._converging_unexpected = False  # R2 ghost-playback guard
        self._engine_switch_lease_active = False  # P1-01 exclusive lease
        self._engine_switch_lease: EngineSwitchLease | None = None
        self._engine_switch_generation = 0
        self._engine_switch_resume_target_ms: int | None = None
        self._last_engine_switch_rehydration: MediaRequestTerminalResult | None = None
        self._engine_switch_timeout_scheduler: (
            Callable[[int, Callable[[], None]], None] | None
        ) = None
        self._engine_switch_timeout_ms = 10_000
        # M11.3C-R6.5.2: token privado de transacción de request — los
        # callbacks públicos son DIRECTOS (pueden rechazar/aceptar/superseder
        # sincrónicamente DENTRO de load()); el epoch permite al request
        # externo detectar que ya no es dueño de la transacción
        self._request_epoch = 0
        self._audio.subscribe_media_accepted(self._on_media_accepted)
        self._audio.subscribe_media_rejected(self._on_media_rejected)
        self._audio.subscribe_playback_state_changed(self._on_playback_state_changed)
        self._audio.subscribe_end_of_media(self._on_end_of_media)

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def engine_switch_resume_target_ms(self) -> int | None:
        return self._engine_switch_resume_target_ms

    @property
    def last_engine_switch_rehydration(
        self,
    ) -> MediaRequestTerminalResult | None:
        return self._last_engine_switch_rehydration

    def set_engine_switch_timeout_scheduler(
        self,
        scheduler: Callable[[int, Callable[[], None]], None],
        *,
        timeout_ms: int = 10_000,
    ) -> None:
        """Inject the runtime scheduler at the composition boundary."""
        self._engine_switch_timeout_scheduler = scheduler
        self._engine_switch_timeout_ms = max(1, timeout_ms)

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        for cb in list(self._subscribers):
            cb()

    def subscribe_end_of_media(self, callback: Callable[[], None]) -> None:
        if callback not in self._eom_subscribers:
            self._eom_subscribers.append(callback)

    def unsubscribe_end_of_media(self, callback: Callable[[], None]) -> None:
        if callback in self._eom_subscribers:
            self._eom_subscribers.remove(callback)

    def subscribe_resume_prepared(self, callback: Callable[[Path, int], None]) -> None:
        if callback not in self._resume_prepared_subscribers:
            self._resume_prepared_subscribers.append(callback)

    def unsubscribe_resume_prepared(
        self, callback: Callable[[Path, int], None]
    ) -> None:
        if callback in self._resume_prepared_subscribers:
            self._resume_prepared_subscribers.remove(callback)

    def _on_end_of_media(self) -> None:
        # Forward only for a committed track: a natural end of the current
        # source. Stale/early EOM signals with nothing committed are ignored,
        # as are EOMs arriving after intent has lapsed (e.g. a rejection that
        # already terminated the request) — those must not re-arm auto-advance.
        if self._state.file_path is None:
            return
        if not self._intent:
            return
        for cb in list(self._eom_subscribers):
            cb()

    def restore_volume(self, volume: int, muted: bool) -> None:
        clamped = max(0, min(100, volume))
        self._audio.set_volume(clamped)
        self._audio.set_muted(muted)
        self._state.volume = clamped
        self._state.muted = muted

    def report_error(self, message: str) -> None:
        self._state.error_message = message
        self._notify()

    def load_and_play(
        self,
        file_path: Path,
        on_accepted: Callable[[Path], None] | None = None,
        on_rejected: Callable[[Path, str], None] | None = None,
        on_cancelled: Callable[[Path], None] | None = None,
    ) -> None:
        self._ensure_no_engine_switch_lease("load_and_play")
        """Request playback of a candidate. Commits nothing synchronously.

        The candidate terminates in exactly one of ACCEPTED / REJECTED /
        CANCELLED / SUPERSEDED. Acceptance, reported by the backend for its
        path, invokes `on_accepted` exactly once with the accepted path.
        Rejection drops the candidate and invokes `on_rejected` exactly once
        with the rejected path and message. A new request supersedes the
        previous pending candidate without invoking any callback for it.
        `stop()` cancels the pending request and invokes `on_cancelled` at
        most once with the pending path.

        Synchronous failure dispositions (M11.3C-R6.2/R6.3):
        A. LOAD failure with previous source preserved
           (AudioLoadError(previous_source_preserved=True) or legacy
           generic exception): restore the previous intent/acceptance.
        B. LOAD failure with previous source NOT preserved
           (AudioLoadError(previous_source_preserved=False)): do NOT
           restore backend acceptance; converge to STOPPED; the previous
           logical identity remains only as a recoverable logical track.
        C. PLAY failure after a successful LOAD: the previous backend
           acceptance is NOT restored (the backend already crossed the
           load commit point); the candidate is terminalized, status
           converges to STOPPED, and a later play() reloads the last
           committed logical track through the canonical path.
        """
        previous_intent = self._intent
        previous_accepted = self._accepted
        self._request_epoch += 1
        my_epoch = self._request_epoch
        self._pending_path = file_path
        self._pending_purpose = MediaRequestPurpose.USER_PLAY
        self._pending_on_accepted = on_accepted
        self._pending_on_rejected = on_rejected
        self._pending_on_cancelled = on_cancelled
        self._pending_resume_position_ms = None  # supersedes any prepare
        self._resume_prepared_pending = False
        self._deferred_resume_target_ms = None  # R2.1-02: supersedes target
        self._accepted = False
        self._intent = True
        # PHASE 1 — LOAD (M11.3C-R6.2): la disposición de AudioLoadError
        # describe exactamente esta fase. El source previo puede estar
        # preservado (True) o ya no garantizado (False). NOTA (R6.5.2):
        # con callbacks DIRECTOS, load() puede REJECT/ACCEPT/SUPERSEDE
        # esta request SÍNCRONICAMENTE dentro de esta llamada.
        try:
            self._audio.load(file_path)
        except Exception as exc:
            if my_epoch != self._request_epoch:
                raise
            if self._pending_path is None and not self._accepted:
                # SAME REQUEST already terminalized synchronously (media_rejected /
                # cancelled callback): preserve terminal rejection/cancellation
                # state and propagate the lifecycle exception.
                raise
            self._clear_pending()
            if isinstance(exc, AudioLoadError) and not exc.previous_source_preserved:
                self._intent = False
                self._accepted = False
                self._state.status = PlaybackStatus.STOPPED
                self._notify()
            else:
                self._intent = previous_intent
                self._accepted = previous_accepted
            raise
        # RECHECK DE DISPOSICIÓN (M11.3C-R6.5.2 BLOCKER B): tras load(),
        # esta request pudo terminar sincrónicamente (REJECTED/ACCEPTED) o
        # ser supersedida por un request reentrante.
        if my_epoch != self._request_epoch:
            return  # supersedida reentrantemente: el nuevo request es dueño
        if self._pending_path is None and not self._accepted:
            # terminal sincrónica (REJECTED/CANCELLED): sin play() ni
            # epílogo de éxito — el error_message de la rejection se
            # preserva y el estado STOPPED queda canónico
            return
        # PHASE 2 — PLAY (M11.3C-R6.2): load(B) ya terminó exitosamente —
        # el source previo YA NO puede asumirse válido (el backend cruzó el
        # commit point y B está armado/pending). Un fallo de play() NO
        # restaura la aceptación/intención de A: converger a STOPPED con
        # identidad lógica A y dejar el candidato B terminalizado; un
        # play() posterior recarga A por el camino canónico. Un
        # media_accepted(B) tardío no puede committear B (pending limpio).
        try:
            self._audio.play()
        except Exception:
            if my_epoch != self._request_epoch:
                raise
            self._clear_pending()
            self._intent = False
            self._accepted = False
            self._state.status = PlaybackStatus.STOPPED
            self._notify()
            raise
        self._state.status = PlaybackStatus.STOPPED
        self._state.error_message = None
        self._notify()

    def _clear_pending(self) -> None:
        """Terminaliza el candidato pendiente sin invocar callbacks."""
        self._pending_path = None
        self._pending_purpose = None
        self._pending_on_accepted = None
        self._pending_on_rejected = None
        self._pending_on_cancelled = None
        self._pending_resume_position_ms = None
        self._resume_prepared_pending = False

    def prepare_for_resume(self, file_path: Path, position_ms: int) -> None:
        """STARTUP RESTORE (P2-01): participates in the M5 two-phase restore
        and may emit resume_prepared. Gated by the engine-switch lease."""
        self._ensure_no_engine_switch_lease("prepare_for_resume")
        self._prepare_stopped_media(
            file_path, position_ms, MediaRequestPurpose.STARTUP_RESTORE
        )

    def prepare_after_engine_switch(self, snapshot: EngineSwitchMediaSnapshot) -> None:
        """ENGINE-SWITCH rehydration (P2-01): LOAD + deferred seek allowed,
        NO autoplay, NO M5 resume_prepared, NOT gated by the lease (the
        coordinator holds it — this is the internal rehydration path)."""
        if snapshot.file_path is None:
            return
        resume_position = snapshot.deferred_resume_target_ms
        if resume_position is None:
            resume_position = snapshot.confirmed_position_ms
        self._prepare_stopped_media(
            snapshot.file_path,
            resume_position,
            MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION,
        )

    def _prepare_stopped_media(
        self,
        file_path: Path,
        position_ms: int,
        purpose: MediaRequestPurpose,
    ) -> None:
        """Shared stopped-media preparation (P2-01). Semantics:
        LOAD (never autoplay) + post-acceptance seek; the deferred resume
        truth of R2.1 is respected. STARTUP_RESTORE emits resume_prepared
        (M5 two-phase); ENGINE_SWITCH does NOT (the PersistenceCoordinator
        state machine must not be opened by an engine switch)."""
        self._prepare_purpose = purpose
        """Request stopped-media preparation: LOAD the candidate, never
        autoplay.

        The startup resume path (M5.C4): requests the backend LOAD of the
        persisted track so acceptance/rejection routing and the pending
        identity guards apply exactly as for any other candidate. Unlike
        ``load_and_play`` it NEVER calls ``play()`` and never arms intent —
        the user has not pressed play; an unexpected backend PLAYING state
        during preparation is an authority violation and converges actively
        to STOPPED (never ignored). On acceptance the track identity is
        committed and the
        backend is then asked to seek to the persisted position (the
        backend clamps; PlaybackState never shows a position the backend
        did not accept — the UI position arrives from the backend's own
        position channel). Status remains STOPPED; the user's later
        ``play()`` starts playback from the sought position. Rejection and
        ``stop()`` use the standard pending semantics; a new request
        supersedes an in-flight prepare without invoking any callback.
        """
        if position_ms < 0:
            position_ms = 0
        previous_accepted = self._accepted
        self._request_epoch += 1  # M11.3C-R6.5.2: request identity
        my_epoch = self._request_epoch
        self._pending_path = file_path
        self._pending_purpose = purpose
        self._pending_on_accepted = None
        self._pending_on_rejected = None
        self._pending_on_cancelled = None
        self._pending_resume_position_ms = position_ms
        self._accepted = False
        try:
            self._audio.load(file_path)
        except AudioLoadError as exc:
            if purpose is MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION:
                # P2-02: a failed load is VISIBLE on the model state (never
                # only in a log). The engine itself stays READY — this is a
                # media domain failure, not an engine failure.
                self._pending_path = None
                self._pending_purpose = None
                self._pending_resume_position_ms = None
                self._state.error_message = (
                    "Audio engine switched, but the current track could not "
                    f"be prepared: {exc}"
                )
                self._notify()
                self._complete_engine_switch_rehydration(
                    MediaRequestTerminalStatus.REJECTED,
                    file_path,
                    str(exc),
                )
                return
            # STARTUP_RESTORE: the original fail-closed disposition —
            # pending cleared, previous acceptance PRESERVED (same as the
            # generic destructive path), then AudioLoadError raises
            self._pending_path = None
            self._pending_purpose = None
            self._pending_on_accepted = None
            self._pending_on_rejected = None
            self._pending_on_cancelled = None
            self._pending_resume_position_ms = None
            self._state.status = PlaybackStatus.STOPPED
            self._notify()
            raise
        except Exception as exc:
            if my_epoch != self._request_epoch:
                raise
            if self._pending_path is None and not self._accepted:
                # SAME REQUEST already terminalized synchronously (media_rejected /
                # cancelled callback): preserve terminal rejection state.
                raise
            self._pending_path = None
            self._pending_purpose = None
            self._pending_on_accepted = None
            self._pending_on_rejected = None
            self._pending_on_cancelled = None
            self._pending_resume_position_ms = None
            self._resume_prepared_pending = False
            # M11.3C-R6.1: misma disposición que load_and_play — un fallo
            # destructivo NO restaura aceptación previa (nunca autoplay,
            # nunca latche de resume armado).
            if isinstance(exc, AudioLoadError) and not exc.previous_source_preserved:
                self._accepted = False
                self._state.status = PlaybackStatus.STOPPED
                self._notify()
            else:
                self._accepted = previous_accepted
            if purpose is MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION:
                self._state.status = PlaybackStatus.STOPPED
                self._state.error_message = (
                    "Audio engine switched, but the current track could not "
                    f"be prepared: {exc}"
                )
                self._notify()
                self._complete_engine_switch_rehydration(
                    MediaRequestTerminalStatus.REJECTED,
                    file_path,
                    str(exc),
                )
            raise
        if my_epoch != self._request_epoch:
            return
        if self._pending_path is None and not self._accepted:
            # GATE 2: Synchronous rejection (terminal)
            # Rejection callback already cleared pending/resume latch,
            # converged status to STOPPED, and preserved error_message.
            return
        if self._accepted:
            # GATE 2: Synchronous acceptance
            # _on_media_accepted already committed state.file_path and
            # executed _apply_prepare_seek(). Status remains STOPPED, no autoplay.
            return
        # GATE 2: Asynchronous pending (pending_path == candidate, accepted == False)
        self._state.status = PlaybackStatus.STOPPED
        self._state.error_message = None
        self._notify()
        if purpose is MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION:
            self._schedule_engine_switch_timeout(file_path, my_epoch)

    def _on_media_accepted(self, file_path: Path) -> None:
        if self._pending_path is None or file_path != self._pending_path:
            return
        on_accepted = self._pending_on_accepted
        purpose = self._pending_purpose
        self._pending_path = None
        self._pending_purpose = None
        self._pending_on_accepted = None
        self._pending_on_rejected = None
        self._pending_on_cancelled = None
        self._state.file_path = file_path
        self._state.error_message = None
        self._accepted = True
        self._notify()
        if on_accepted is not None:
            on_accepted(file_path)
        self._apply_prepare_seek()
        if purpose is MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION:
            self._complete_engine_switch_rehydration(
                MediaRequestTerminalStatus.ACCEPTED, file_path
            )

    def engine_switch_readiness(self) -> EngineSwitchReadiness:
        """Return the typed authority decision for a new explicit switch."""
        if self._engine_switch_lease_active:
            if self._pending_purpose is MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION:
                # A newer explicit selection may supersede only rehydration.
                return EngineSwitchReadiness(True)
            return EngineSwitchReadiness(False, EngineSwitchBlocker.SWITCH_IN_PROGRESS)
        if self._pending_path is not None:
            blocker = (
                EngineSwitchBlocker.STARTUP_RESTORE_PENDING
                if self._pending_purpose is MediaRequestPurpose.STARTUP_RESTORE
                else EngineSwitchBlocker.USER_MEDIA_REQUEST_PENDING
            )
            return EngineSwitchReadiness(False, blocker)
        if self._resume_prepared_pending:
            return EngineSwitchReadiness(
                False, EngineSwitchBlocker.STARTUP_RESTORE_PENDING
            )
        if self._intent and self._state.status is PlaybackStatus.STOPPED:
            return EngineSwitchReadiness(
                False, EngineSwitchBlocker.USER_MEDIA_REQUEST_PENDING
            )
        return EngineSwitchReadiness(True)

    def begin_engine_switch(self) -> EngineSwitchLease:
        """Atomically capture playback truth and acquire switch authority."""
        readiness = self.engine_switch_readiness()
        if not readiness.allowed:
            if readiness.blocker is EngineSwitchBlocker.SWITCH_IN_PROGRESS:
                raise EngineSwitchLeaseHeldError(
                    readiness.detail or readiness.blocker.value
                )
            raise PlaybackNotQuiescentError(
                readiness.detail or readiness.blocker.value  # type: ignore[union-attr]
            )
        if self._engine_switch_lease_active:
            self._cancel_engine_switch_rehydration("superseded by a newer switch")
        snapshot = self.snapshot_engine_switch_media()
        self._engine_switch_generation += 1
        self._engine_switch_lease_active = True
        lease = EngineSwitchLease(self, snapshot, self._engine_switch_generation)
        self._engine_switch_lease = lease
        self._engine_switch_resume_target_ms = (
            snapshot.deferred_resume_target_ms
            if snapshot.deferred_resume_target_ms is not None
            else snapshot.confirmed_position_ms
        )
        return lease

    def acquire_engine_switch_lease(self) -> EngineSwitchLease:
        """Compatibility name for the atomic engine-switch transition."""
        return self.begin_engine_switch()

    def _release_engine_switch_lease(self, lease: EngineSwitchLease) -> None:
        if self._engine_switch_lease is not lease:
            return
        self._engine_switch_lease_active = False
        self._engine_switch_lease = None

    def _require_engine_switch_lease(self, lease: EngineSwitchLease) -> None:
        if self._engine_switch_lease is not lease or lease._released:
            raise EngineSwitchLeaseHeldError("stale engine switch authority")

    def _engine_switch_controlled_stop(self, lease: EngineSwitchLease) -> None:
        self._require_engine_switch_lease(lease)
        if self._state.status is not PlaybackStatus.STOPPED or self._intent:
            self._audio.stop()
        self._intent = False
        self._state.status = PlaybackStatus.STOPPED
        self._state.position_ms = lease.snapshot.confirmed_position_ms
        self._notify()

    def _engine_switch_invalidate_acceptance(self, lease: EngineSwitchLease) -> None:
        self._require_engine_switch_lease(lease)
        self._request_epoch += 1
        self._clear_pending()
        self._intent = False
        self._accepted = False
        self._converging_unexpected = False

    def _engine_switch_prepare_on_target(self, lease: EngineSwitchLease) -> bool:
        self._require_engine_switch_lease(lease)
        if lease.snapshot.file_path is None:
            lease.release()
            return False
        self.prepare_after_engine_switch(lease.snapshot)
        return (
            self._engine_switch_lease is lease
            and self._pending_purpose is MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION
        )

    def _ensure_no_engine_switch_lease(self, operation: str) -> None:
        """P1-01 gate: while the exclusive switch lease is held, playback
        intents that would break quiescence are rejected explicitly."""
        if self._engine_switch_lease_active:
            raise EngineSwitchLeaseHeldError(
                f"{operation} rejected while an engine switch is in progress"
            )

    def snapshot_engine_switch_media(self) -> EngineSwitchMediaSnapshot:
        """KCR-021: read-only capture of the stopped-media truth (the
        logical resume target included). Only reads state — the engine
        switch uses it to rehydrate the new backend without autoplay."""
        return EngineSwitchMediaSnapshot(
            file_path=self._state.file_path,
            confirmed_position_ms=self._state.position_ms,
            deferred_resume_target_ms=self._deferred_resume_target_ms,
            previous_status=self._state.status,
            volume=self._state.volume,
            muted=self._state.muted,
        )

    def _schedule_engine_switch_timeout(self, file_path: Path, epoch: int) -> None:
        if self._engine_switch_timeout_scheduler is None:
            return

        def expire() -> None:
            if (
                self._request_epoch != epoch
                or self._pending_path != file_path
                or self._pending_purpose
                is not MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION
            ):
                return
            self._request_epoch += 1
            self._clear_pending()
            self._accepted = False
            self._intent = False
            self._state.status = PlaybackStatus.STOPPED
            message = (
                "Timed out while preparing the current track on the new audio engine."
            )
            self._state.error_message = message
            self._notify()
            self._complete_engine_switch_rehydration(
                MediaRequestTerminalStatus.TIMEOUT, file_path, message
            )

        self._engine_switch_timeout_scheduler(self._engine_switch_timeout_ms, expire)

    def _complete_engine_switch_rehydration(
        self,
        status: MediaRequestTerminalStatus,
        file_path: Path,
        message: str | None = None,
    ) -> None:
        self._last_engine_switch_rehydration = MediaRequestTerminalResult(
            MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION,
            status,
            str(file_path),
            message,
        )
        lease = self._engine_switch_lease
        if lease is not None:
            lease.release()

    def _cancel_engine_switch_rehydration(self, message: str) -> None:
        path = self._pending_path
        if (
            path is None
            or self._pending_purpose
            is not MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION
        ):
            return
        self._request_epoch += 1
        self._clear_pending()
        self._accepted = False
        self._intent = False
        self._complete_engine_switch_rehydration(
            MediaRequestTerminalStatus.CANCELLED, path, message
        )

    def _apply_prepare_seek(self) -> None:
        """Apply a prepare_for_resume seek, post-acceptance (never autoplay).

        M5-PRODUCTION-LIFECYCLE-GATE: the confirmation latch is armed BEFORE
        the backend seek is issued, so a REENTRANT backend that emits the
        position callback synchronously from within seek() confirms the
        resume — never lost to a latch armed after the fact, never
        double-fired (the latch disarms on the first fire). A seek that
        raises disarms the latch cleanly (no false resume-complete, no
        eternal latch) and surfaces the error on the state. After a
        non-reentrant seek returns, if the backend-reported position is
        UNCHANGED and already equals the requested value (e.g. seek to 0
        from 0 — Qt may not emit a positionChanged for an unchanged value),
        the confirmation fires with that backend-reported position — never
        fabricated. A clamped position (position() != requested) and a
        position that the seek actually CHANGED stay latched: the async
        positionChanged confirms with the backend-reported value.
        """
        resume_position = self._pending_resume_position_ms
        self._pending_resume_position_ms = None
        if resume_position is None:
            return
        self._resume_prepared_pending = True  # armed BEFORE the backend seek
        try:
            before = self._audio.position()
            self._audio.seek(resume_position)
        except Exception as exc:
            self._resume_prepared_pending = False
            self._state.error_message = str(exc)
            self._notify()
            return
        if self._resume_prepared_pending and self._state.file_path is not None:
            # R2.1-02: distinct truth — backend_current_position vs
            # deferred_resume_target. With the MPD deferred seek (daemon
            # stopped) the backend position does NOT move: the seek was
            # REGISTERED on the transport, not applied. The preparation is
            # then SETTLED (latch closed) and the target is tracked
            # explicitly; it is NOT a confirmed backend position and does
            # NOT block engine switching (quiescence). The confirmation
            # fires when the backend reports the position after the
            # explicit Play (positionChanged event).
            confirmed = self._audio.position()
            if confirmed == resume_position and confirmed == before:
                # seek-to-0 / unchanged: backend already reports the value
                self._resume_prepared_pending = False
                if (
                    getattr(self, "_prepare_purpose", None)
                    is not MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION
                ):
                    for cb in list(self._resume_prepared_subscribers):
                        cb(self._state.file_path, confirmed)
            elif confirmed == before and confirmed != resume_position:
                # R2.1-02: deferred target registered (MPD stopped) — the
                # preparation is SETTLED; the target is tracked explicitly
                # and applied by the transport at the explicit play.
                self._resume_prepared_pending = False
                self._deferred_resume_target_ms = resume_position
            # else (position CHANGED): the async positionChanged confirms;
            # the latch stays armed (normal path).

    def _on_media_rejected(self, file_path: Path, message: str) -> None:
        if self._pending_path is not None and file_path == self._pending_path:
            on_rejected = self._pending_on_rejected
            purpose = self._pending_purpose
            self._pending_path = None
            self._pending_purpose = None
            self._pending_on_accepted = None
            self._pending_on_rejected = None
            self._pending_on_cancelled = None
            self._pending_resume_position_ms = None
            self._resume_prepared_pending = False
            self._intent = False
            self._accepted = False
            self._state.status = PlaybackStatus.STOPPED
            self._state.error_message = message
            self._notify()
            if on_rejected is not None:
                on_rejected(file_path, message)
            if purpose is MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION:
                self._complete_engine_switch_rehydration(
                    MediaRequestTerminalStatus.REJECTED, file_path, message
                )
        elif (
            self._state.file_path is not None
            and file_path == self._state.file_path
            and (
                self._state.status != PlaybackStatus.STOPPED
                or self._state.error_message != message
            )
        ):
            self._intent = False
            self._accepted = False
            self._state.status = PlaybackStatus.STOPPED
            self._state.error_message = message
            self._notify()
        # Anything else is a stale, unknown, or duplicate callback: ignored.

    def _on_playback_state_changed(self, status: PlaybackStatus) -> None:
        # INV-AUDIO-NO-GHOST-PLAYBACK (R2 PRODUCTION REALITY): a backend
        # reporting non-STOPPED (PLAYING/PAUSED) WITHOUT a valid playback
        # intent is an observable authority violation — never silently
        # discarded. The model converges actively to STOPPED (safety stop +
        # diagnosis) and NEVER publishes the unexpected state. This closes
        # the production failure where MPD autoplayed after prepare_for_resume
        # (seekid on a stopped song starts playback) while the model kept
        # showing STOPPED and the Play button kept issuing play().
        if not self._intent and status != PlaybackStatus.STOPPED:
            self._converge_unexpected_backend_state(status)
            return
        if status == PlaybackStatus.PLAYING and not self._accepted:
            # acceptance pending: PLAYING before media acceptance is not a
            # legitimate model state either — converge (safety) instead of
            # silently dropping the audio the backend may be producing.
            self._converge_unexpected_backend_state(status)
            return
        if self._state.status == status:
            return
        self._state.status = status
        self._notify()

    def _converge_unexpected_backend_state(self, status: PlaybackStatus) -> None:
        """Safety convergence for an unexpected backend state. Issues a
        backend stop (idempotent), records a diagnostic and, when the stop
        itself fails, surfaces the error on the model state. Re-entrant
        violation events during convergence do not loop (one attempt per
        event; the backend's own STOPPED event converges the model)."""
        if self._converging_unexpected:
            return
        self._converging_unexpected = True
        try:
            self._audio.stop()
        except Exception as exc:  # noqa: BLE001 — safety boundary
            self._state.error_message = (
                f"unexpected backend state {status.value} could not be stopped: {exc}"
            )
            self._notify()
            logger.exception(
                "unexpected backend state %s could not be stopped", status.value
            )
        finally:
            self._converging_unexpected = False

    def play(self) -> None:
        self._ensure_no_engine_switch_lease("play")
        # M11.3C-R6.1: si no hay media aceptada en el backend pero existe un
        # track lógico commiteado y no hay candidato pendiente, recargar el
        # track por el camino canónico. load_and_play() ya invoca
        # _audio.play() directamente — el fallback NUNCA recorre play()
        # recursivamente ni llama _audio.load() a secas.
        if (
            not self._accepted
            and self._pending_path is None
            and self._state.file_path is not None
        ):
            self.load_and_play(self._state.file_path)
            return
        previous_intent = self._intent
        self._intent = True
        try:
            self._audio.play()
        except Exception:
            self._intent = previous_intent
            raise

    def pause(self) -> None:
        self._ensure_no_engine_switch_lease("pause")
        self._audio.pause()

    def resume(self) -> None:
        self._ensure_no_engine_switch_lease("resume")
        previous_intent = self._intent
        self._intent = True
        try:
            self._audio.resume()
        except Exception:
            self._intent = previous_intent
            raise

    def stop(self) -> None:
        self._ensure_no_engine_switch_lease("stop")
        # AR-17 (reliability seal): capture the pending identity FIRST, then
        # attempt the backend safety command; the local intent is cleared
        # ONLY after the backend accepted the stop. A backend stop failure
        # propagates with the pending identity preserved (truthful retry/
        # diagnosis) — STOPPED is never fabricated from a failed stop.
        on_cancelled = self._pending_on_cancelled
        cancelled_path = self._pending_path
        self._audio.stop()
        # SUCCESS COMMIT — backend accepted the safety command
        self._pending_path = None
        self._pending_purpose = None
        self._pending_on_accepted = None
        self._pending_on_rejected = None
        self._pending_on_cancelled = None
        self._pending_resume_position_ms = None
        self._resume_prepared_pending = False
        self._deferred_resume_target_ms = None  # R2.1-02: stop supersedes
        self._intent = False
        self._state.status = PlaybackStatus.STOPPED
        self._state.position_ms = 0
        self._notify()
        # Reentrancy guard: a subscriber may re-request playback during the
        # notify above, re-arming the pending request; the stale cancellation
        # captured before it must not clear that new pending, so fire it only
        # when nothing is pending again.
        if (
            cancelled_path is not None
            and on_cancelled is not None
            and self._pending_path is None
        ):
            on_cancelled(cancelled_path)

    def converge_after_engine_loss(self, reason: str) -> None:
        """M11.3G: converge PlaybackState after a FATAL ENGINE RUNTIME LOSS.

        Owned by PlaybackService — the convergence coordinator never mutates
        private fields directly. Effects:
        - request epoch incremented (stale in-flight requests obsolete)
        - pending candidate terminated EXACTLY ONCE through the existing
          REJECTION semantics (engine loss is failure, NOT user cancellation)
        - pending resume slot + resume confirmation latch cleared
        - intent=False, accepted=False, PlaybackStatus=STOPPED
        - committed file_path, last canonical position, volume and mute
          PRESERVED (informational)
        - error_message=reason, canonical notify
        NO autoplay, NO EOM, NO seek, NO Queue mutation.
        """
        # Capture the pending rejection callback BEFORE clearing, preserving
        # the existing reentrancy discipline (clear pending first, then fire).
        self._request_epoch += 1
        pending_path = self._pending_path
        pending_purpose = self._pending_purpose
        on_rejected = self._pending_on_rejected
        self._pending_path = None
        self._pending_purpose = None
        self._pending_on_accepted = None
        self._pending_on_rejected = None
        self._pending_on_cancelled = None
        self._pending_resume_position_ms = None
        self._resume_prepared_pending = False
        self._deferred_resume_target_ms = None  # R2.1-02: never leaks engines
        self._intent = False
        self._accepted = False
        self._converging_unexpected = False  # R2 ghost-playback guard
        self._state.status = PlaybackStatus.STOPPED
        # file_path / position_ms / volume / muted preserved on purpose.
        self._state.error_message = reason
        self._notify()
        if (
            pending_path is not None
            and pending_purpose is MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION
        ):
            self._complete_engine_switch_rehydration(
                MediaRequestTerminalStatus.REJECTED, pending_path, reason
            )
        if (
            pending_path is not None
            and on_rejected is not None
            and self._pending_path is None
        ):
            # Engine loss is a FAILURE, not user cancellation: reject once.
            on_rejected(pending_path, reason)

    def seek(self, position_ms: int) -> None:
        # AR-16 (reliability seal): seek is INTENT ONLY. A requested position
        # is not a confirmed position — canonical position changes arrive
        # exclusively through backend observation (update_position) or an
        # explicitly confirmed backend truth seam. No fabricated position.
        self._ensure_no_engine_switch_lease("seek")
        self._audio.seek(position_ms)

    def set_volume(self, value: int) -> None:
        self._ensure_no_engine_switch_lease("set_volume")
        clamped = max(0, min(100, value))
        self._audio.set_volume(clamped)
        self._state.volume = clamped
        self._notify()

    def set_muted(self, muted: bool) -> None:
        self._ensure_no_engine_switch_lease("set_muted")
        self._audio.set_muted(muted)
        self._state.muted = muted
        self._notify()

    def update_position(self, position_ms: int) -> None:
        if self._state.position_ms != position_ms:
            self._state.position_ms = position_ms
            self._notify()
        if self._resume_prepared_pending:
            # M5-LAST-GATE-2: the FIRST post-acceptance position update
            # confirms the resume (position 0 included; the backend clamp is
            # tolerated — whatever the backend reports is the CONFIRMED
            # position). Fires ONCE, with the committed path and the
            # confirmed position, then disarms.
            self._resume_prepared_pending = False
            if (
                self._state.file_path is not None
                and getattr(self, "_prepare_purpose", None)
                is not MediaRequestPurpose.ENGINE_SWITCH_REHYDRATION
            ):
                for cb in list(self._resume_prepared_subscribers):
                    cb(self._state.file_path, position_ms)

    def update_duration(self, duration_ms: int) -> None:
        if self._state.duration_ms != duration_ms:
            self._state.duration_ms = duration_ms
            self._notify()

    def snapshot_volume(self) -> tuple[int, bool]:
        return (self._state.volume, self._state.muted)

    def is_engine_switch_quiescent(self) -> bool:
        """TRUE only when an engine switch is safe (M11.3F).

        STOPPED alone is NOT enough: the service may be STOPPED while a load
        request is pending, play intent is armed awaiting backend PLAYING,
        prepare_for_resume is pending, or a resume confirmation latch is
        armed. Quiescent means none of those are in flight. A loaded and
        ACCEPTED but explicitly STOPPED current track IS quiescent. The
        switch coordinator must never inspect the private fields directly —
        this read-only semantic query is the only gate."""
        return (
            self._state.status == PlaybackStatus.STOPPED
            and self._pending_path is None
            and not self._intent
            and self._pending_resume_position_ms is None
            and not self._resume_prepared_pending
        )

    def invalidate_backend_acceptance_for_engine_switch(self) -> None:
        """M11.3F switch-seal: clear OLD-BACKEND acceptance, keep logical state.

        After an engine switch the new backend has never loaded the current
        logical track. Precondition: engine-switch quiescent. Effect:
        state.file_path / STOPPED / canonical volume / canonical mute are
        preserved; backend-specific acceptance and play intent are cleared;
        the request epoch is advanced so any stale in-flight request of the
        old backend is obsolete. NO load, NO play, NO seek, NO Queue mutation.

        After this call the NEXT play() reloads the logical current track on
        the NEW backend through the canonical reload path. This is an engine
        switch boundary — deliberately NOT media rejection."""
        if not self.is_engine_switch_quiescent():
            raise RuntimeError(
                "cannot invalidate backend acceptance: playback is not "
                "engine-switch quiescent"
            )
        self._request_epoch += 1
        self._pending_path = None
        self._pending_purpose = None
        self._pending_on_accepted = None
        self._pending_on_rejected = None
        self._pending_on_cancelled = None
        self._pending_resume_position_ms = None
        self._resume_prepared_pending = False
        self._deferred_resume_target_ms = None  # R2.1-02: never leaks engines
        self._intent = False
        self._accepted = False
        self._converging_unexpected = False  # R2 ghost-playback guard
        # file_path / status / volume / muted / position / duration preserved.
