"""Playback use case — the single mutation authority for PlaybackState."""

from collections.abc import Callable
from pathlib import Path

from michi.application.ports import AudioLoadError, AudioPort
from michi.domain.playback import PlaybackState, PlaybackStatus


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
      for a track whose identity was not committed — stale PlayingState
      events from superseded candidates are ignored.

    `prepare_for_resume` is the startup resume path: it requests a backend
    LOAD and, only after acceptance, seeks the backend to the persisted
    position — it loads and seeks, never autoplays. Intent stays unarmed
    during preparation (the user has not pressed play), so a stray backend
    PLAYING state is ignored; the user's later `play()` resumes from the
    sought position.

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
        self._pending_resume_position_ms: int | None = None
        # M5-LAST-GATE-2 resume confirmation: armed when a prepare_for_resume
        # actually requested a seek (post-acceptance), disarmed by the FIRST
        # position update (which fires `resume_prepared` once) or by any path
        # that clears the resume slot (rejection/stop/supersession).
        self._resume_prepared_subscribers: list[Callable[[Path, int], None]] = []
        self._resume_prepared_pending: bool = False
        self._intent = False
        self._accepted = False
        self._audio.subscribe_media_accepted(self._on_media_accepted)
        self._audio.subscribe_media_rejected(self._on_media_rejected)
        self._audio.subscribe_playback_state_changed(self._on_playback_state_changed)
        self._audio.subscribe_end_of_media(self._on_end_of_media)

    @property
    def state(self) -> PlaybackState:
        return self._state

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        for cb in self._subscribers:
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
        """Request playback of a candidate. Commits nothing synchronously.

        The candidate terminates in exactly one of ACCEPTED / REJECTED /
        CANCELLED / SUPERSEDED. Acceptance, reported by the backend for its
        path, invokes `on_accepted` exactly once with the accepted path.
        Rejection drops the candidate and invokes `on_rejected` exactly once
        with the rejected path and message. A new request supersedes the
        previous pending candidate without invoking any callback for it.
        `stop()` cancels the pending request and invokes `on_cancelled` at
        most once with the pending path. Synchronous backend failures
        propagate, leave no pending candidate behind, and restore the
        previous intent/acceptance flags.
        """
        previous_intent = self._intent
        previous_accepted = self._accepted
        self._pending_path = file_path
        self._pending_on_accepted = on_accepted
        self._pending_on_rejected = on_rejected
        self._pending_on_cancelled = on_cancelled
        self._pending_resume_position_ms = None  # supersedes any prepare
        self._resume_prepared_pending = False  # supersedes any pending confirm
        self._accepted = False
        self._intent = True
        try:
            self._audio.load(file_path)
            self._audio.play()
        except Exception as exc:
            self._pending_path = None
            self._pending_on_accepted = None
            self._pending_on_rejected = None
            self._pending_on_cancelled = None
            self._pending_resume_position_ms = None
            self._resume_prepared_pending = False
            # M11.3C-R6.1: disposición EXPLÍCITA del source previo. Con
            # AudioLoadError(previous_source_preserved=False) el backend
            # cruzó un commit point destructivo y ya no garantiza el source:
            # NO restaurar la aceptación previa (sería autoridad falsa).
            # file_path sigue siendo la identidad lógica del último track
            # commiteado; un play() posterior lo recarga por el camino
            # canónico. Con disposición preservada (o excepción genérica
            # legacy) se restauran la aceptación e intención previas.
            if isinstance(exc, AudioLoadError) and not exc.previous_source_preserved:
                self._intent = False
                self._accepted = False
                self._state.status = PlaybackStatus.STOPPED
                self._notify()
            else:
                self._intent = previous_intent
                self._accepted = previous_accepted
            raise
        self._state.status = PlaybackStatus.STOPPED
        self._state.error_message = None
        self._notify()

    def prepare_for_resume(self, file_path: Path, position_ms: int) -> None:
        """Request a startup resume: LOAD the candidate, never autoplay.

        The startup resume path (M5.C4): requests the backend LOAD of the
        persisted track so acceptance/rejection routing and the pending
        identity guards apply exactly as for any other candidate. Unlike
        ``load_and_play`` it NEVER calls ``play()`` and never arms intent
        — the user has not pressed play, so a stray backend PLAYING state
        is ignored. On acceptance the track identity is committed and the
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
        self._pending_path = file_path
        self._pending_on_accepted = None
        self._pending_on_rejected = None
        self._pending_on_cancelled = None
        self._pending_resume_position_ms = position_ms
        self._accepted = False
        try:
            self._audio.load(file_path)
        except Exception as exc:
            self._pending_path = None
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
            raise
        self._state.status = PlaybackStatus.STOPPED
        self._state.error_message = None
        self._notify()

    def _on_media_accepted(self, file_path: Path) -> None:
        if self._pending_path is None or file_path != self._pending_path:
            return
        on_accepted = self._pending_on_accepted
        self._pending_path = None
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
            # Non-reentrant path: only when the seek left the position
            # UNCHANGED does the backend ALREADY report the requested value
            # (Qt skips positionChanged for an unchanged value) — the
            # confirmation is real (backend truth, never fabricated) and
            # fires now instead of waiting for a signal that never comes. A
            # clamped or changed position stays latched for the async event.
            confirmed = self._audio.position()
            if confirmed == resume_position and confirmed == before:
                self._resume_prepared_pending = False
                for cb in list(self._resume_prepared_subscribers):
                    cb(self._state.file_path, confirmed)

    def _on_media_rejected(self, file_path: Path, message: str) -> None:
        if self._pending_path is not None and file_path == self._pending_path:
            on_rejected = self._pending_on_rejected
            self._pending_path = None
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
        if not self._intent and status != PlaybackStatus.STOPPED:
            return
        if status == PlaybackStatus.PLAYING and not self._accepted:
            return
        if self._state.status == status:
            return
        self._state.status = status
        self._notify()

    def play(self) -> None:
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
        self._audio.pause()

    def resume(self) -> None:
        previous_intent = self._intent
        self._intent = True
        try:
            self._audio.resume()
        except Exception:
            self._intent = previous_intent
            raise

    def stop(self) -> None:
        on_cancelled = self._pending_on_cancelled
        cancelled_path = self._pending_path
        self._pending_path = None
        self._pending_on_accepted = None
        self._pending_on_rejected = None
        self._pending_on_cancelled = None
        self._pending_resume_position_ms = None
        self._resume_prepared_pending = False
        self._intent = False
        self._audio.stop()
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

    def seek(self, position_ms: int) -> None:
        self._audio.seek(position_ms)
        self._state.position_ms = position_ms
        self._notify()

    def set_volume(self, value: int) -> None:
        clamped = max(0, min(100, value))
        self._audio.set_volume(clamped)
        self._state.volume = clamped
        self._notify()

    def set_muted(self, muted: bool) -> None:
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
            if self._state.file_path is not None:
                for cb in list(self._resume_prepared_subscribers):
                    cb(self._state.file_path, position_ms)

    def update_duration(self, duration_ms: int) -> None:
        if self._state.duration_ms != duration_ms:
            self._state.duration_ms = duration_ms
            self._notify()

    def snapshot_volume(self) -> tuple[int, bool]:
        return (self._state.volume, self._state.muted)

    def switch_track(self, file_path: Path) -> None:
        self._audio.stop()
        self._state.status = PlaybackStatus.STOPPED
        self._state.error_message = None
        self.load_and_play(file_path)
