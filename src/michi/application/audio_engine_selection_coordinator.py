"""M11.3F — quiescent engine selection coordinator (application layer).

Transaction/orchestration authority for EXPLICIT engine switching. It does
NOT own engine state (AudioEngineService does), does NOT own the provider
set (AudioEngineRegistry does), does NOT own playback semantics
(PlaybackService does) and does NOT own persistence (SettingsService does).
It composes those authorities into ONE canonical transaction.

Framework-free: no PySide6, no gi, no Gst, no MPD protocol/runtime, no
sqlite3. Providers are obtained ONLY through the registry — never
instantiated here. No background threads, no timers, no polling.

M11.3G seam: after a SAFE post-destructive target failure (source already
closed, router safely unbound) the coordinator may notify the convergence
coordinator via ``recover_safe_unbound_failure`` so G can attempt the ONE
automatic Qt fallback. F's thrown-exception semantics never change: the
original target error still propagates after G recovery.
"""

import logging
from collections.abc import Callable
from enum import Enum

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.application.audio_engine_service import AudioEngineService
from michi.application.audio_transport_router import AudioTransportRouter
from michi.application.playback_service import (
    EngineSwitchLeaseHeldError,
    PlaybackNotQuiescentError,
    PlaybackService,
)
from michi.application.settings_service import SettingsService
from michi.domain.audio_engine import AudioEngineId, AudioEngineLifecycle

logger = logging.getLogger(__name__)


class AudioEngineSwitchError(RuntimeError):
    """Deterministic engine-switch failure (transaction aborted)."""


class AudioEngineSwitchNotQuiescentError(AudioEngineSwitchError):
    """The switch was rejected because playback is not truly quiescent."""


class AudioEngineSwitchUnavailableError(AudioEngineSwitchError):
    """The target cannot activate (available=False / not implemented)."""


class AudioEngineSwitchInProgressError(AudioEngineSwitchError):
    """A switch transaction is already in progress; nested switch rejected.

    AudioEngineService publishes state changes synchronously, so a
    subscriber may attempt switch_to(C) while switch_to(B) is mid-flight.
    Exactly ONE explicit engine switch transaction may exist at a time."""


class AudioEngineSwitchFailureStage(Enum):
    """Transaction diagnostics: where an explicit switch failed.

    Orchestration-only — never persisted, never part of AudioEngineState.
    Used by M11.3G to decide whether automatic fallback is SAFE: only
    TARGET_OPEN (no target ownership existed) and
    TARGET_ACTIVATION_DETACHED_RELEASED (detach + provider close both
    succeeded) authorize the recovery callback."""

    SOURCE_UNBIND = "source_unbind"
    SOURCE_CLOSE = "source_close"
    TARGET_OPEN = "target_open"
    TARGET_ACTIVATION_DETACHED_RELEASED = "target_activation_detached_released"
    TARGET_ACTIVATION_DETACHED_CLOSE_FAILED = "target_activation_detached_close_failed"
    TARGET_ACTIVATION_STILL_BOUND = "target_activation_still_bound"


class AudioEngineSelectionCoordinator:
    """Explicit quiescent engine selection — the single switch transaction.

    Canonical transaction:

        VERIFY TARGET (registered + freshly probed + can_activate)
        → [STOP when explicitly requested by stop_and_switch_to]
        → VERIFY / REVALIDATE QUIESCENT
        → PERSIST SELECTION (durable save BEFORE any destructive work)
        → mark SELECTED (switching_to exposed truthfully)
        → mark CLOSING
        → ROUTER UNBIND
        → CLOSE ACTIVE PROVIDER
        → INVALIDATE OLD BACKEND ACCEPTANCE
        → mark INITIALIZING
        → OPEN TARGET PROVIDER
        → ROUTER BIND + VALIDATE
        → RESTORE VOLUME/MUTE
        → mark READY

    Rules enforced here:
    - NEVER close a provider while the router is still attached to it.
    - NEVER open the target before the source is closed (max 1 open engine).
    - No fallback: on failure the transaction reports honestly (FAILED) and
      re-raises the FIRST error; cleanup errors are secondary (suppressed).
    - No automatic alternate engine, no reopen of the previous engine,
      no auto-select Qt (M11.3G owns all recovery policy).
    """

    def __init__(
        self,
        *,
        engine_service: AudioEngineService,
        registry: AudioEngineRegistry,
        router: AudioTransportRouter,
        playback: PlaybackService,
        settings: SettingsService,
    ) -> None:
        self._engine_service = engine_service
        self._registry = registry
        self._router = router
        self._playback = playback
        self._settings = settings
        # M11.3F P1-03: synchronous reentrancy guard — exactly ONE explicit
        # switch transaction at a time (owner-thread model, boolean only).
        self._switch_in_progress = False
        # M11.3G seam: safe-fallback recovery callback (never replaces the
        # original exception; may be None when G is not wired).
        self._recover_callback: Callable[[AudioEngineId, str], None] | None = None
        # Transaction diagnostics: stage of the LAST failed transaction.
        self.last_failure_stage: AudioEngineSwitchFailureStage | None = None

    def set_recovery_callback(
        self, callback: Callable[[AudioEngineId, str], None] | None
    ) -> None:
        """M11.3G seam: register the safe-unbound-failure recovery handler.

        Called ONLY after TARGET_OPEN or TARGET_ACTIVATION_DETACHED
        failures (source ownership released, router safely unbound). The
        callback must never replace the original exception."""
        self._recover_callback = callback

    # ------------------------------------------------------------------
    # Public transaction
    # ------------------------------------------------------------------

    def switch_to(self, target: AudioEngineId) -> None:
        """Explicit quiescent switch to ``target``. Deterministic failure.

        Target validation always precedes optional stop. The strict switch
        path leaves a non-quiescent runtime untouched; Stop & Switch may stop
        first, then revalidates quiescence before persistence or provider
        destruction. Same-engine READY selection is a no-op."""
        # M11.3F P1-03: reentrancy guard — a subscriber of AudioEngineService
        # state changes may attempt a nested switch while this transaction is
        # mid-flight; reject it deterministically.
        if self._switch_in_progress:
            raise AudioEngineSwitchInProgressError(
                "engine switch already in progress; nested switch rejected"
            )
        self._switch_in_progress = True
        self.last_failure_stage = None  # reset at the start of every transaction
        try:
            self._switch_to_transaction(target, stop_playback=False)
        finally:
            self._switch_in_progress = False

    def stop_and_switch_to(self, target: AudioEngineId) -> None:
        """Stop active/pending playback and switch in one application use case.

        Target validation and same-engine idempotence happen before stop, so
        an unavailable or already-current target never disrupts playback.
        Stop failure and reentrant playback both abort before persistence and
        before the provider/router destructive boundary.
        """
        if self._switch_in_progress:
            raise AudioEngineSwitchInProgressError(
                "engine switch already in progress; nested switch rejected"
            )
        self._switch_in_progress = True
        self.last_failure_stage = None
        try:
            self._switch_to_transaction(target, stop_playback=True)
        finally:
            self._switch_in_progress = False

    def _switch_to_transaction(
        self, target: AudioEngineId, *, stop_playback: bool
    ) -> None:
        """Explicit quiescent switch to ``target``. Deterministic failure.

        Pre-destructive checks (registered / can_activate / quiescent) fail
        with the OLD runtime untouched: no stop, no persistence mutation, no
        unbind, no close, no target open. Same-engine idempotence: when
        selected == active == target and READY, this is a no-op."""
        # 1. VERIFY TARGET — fresh probe, can_activate gate.
        provider = self._registry.provider(target)
        descriptor = provider.probe()
        if not descriptor.can_activate:
            raise AudioEngineSwitchUnavailableError(
                f"target engine {target.value} no activable: "
                f"{descriptor.activation_blocker}"
            )

        state = self._engine_service.state
        active = state.active_engine_id

        # 2. SAME-ENGINE IDEMPOTENCE — no churn, no duplicate callbacks.
        if (
            target == state.selected_engine_id
            and target == active
            and state.lifecycle == AudioEngineLifecycle.READY
        ):
            return

        # Dedicated Stop & Switch path. PlaybackService owns all stop
        # semantics; this coordinator only composes the use case. The later
        # lease acquisition is the mandatory revalidation after synchronous
        # playback observers have run.
        if stop_playback and not self._playback.is_engine_switch_quiescent():
            self._playback.stop()

        # 3. ACQUIRE THE EXCLUSIVE QUIESCENCE LEASE (P1-01). This is the
        #    atomic check-then-act guard: from now on Playback REJECTS new
        #    playback intents (play/resume/load_and_play/prepare_for_resume)
        #    with EngineSwitchLeaseHeldError, so a synchronous observer
        #    firing inside mark_selected() can never re-arm playback under
        #    an in-flight switch. No redundant stop() (KCR-021) — the
        #    provider is released at the destructive boundary.
        try:
            lease = self._playback.acquire_engine_switch_lease()
        except PlaybackNotQuiescentError as exc:
            raise AudioEngineSwitchNotQuiescentError(str(exc)) from exc
        except EngineSwitchLeaseHeldError as exc:
            raise AudioEngineSwitchInProgressError(str(exc)) from exc

        try:  # P1-01: lease held across the WHOLE transaction, released in
            # finally on every outcome (success, persistence failure, source
            # unbind/close failure, target open/bind/restore failure).
            # 6. PERSIST SELECTION — durable BEFORE the destructive boundary.
            #    On save failure: preference restored, old runtime untouched
            #    (SettingsService.set_audio_engine restores and re-raises).
            self._settings.set_audio_engine(target)

            # 7. SELECTED (old engine may still be active — truthful window).
            self._engine_service.mark_selected(target)
            volume, muted = self._playback.snapshot_volume()
            # 7.5 (KCR-021): capture the stopped-media truth (logical resume
            #     target included) BEFORE the destructive boundary — the old
            #     backend invalidation must never erase what the user restored.
            media_snapshot = self._playback.snapshot_engine_switch_media()

            # 8. DESTRUCTIVE BOUNDARY.
            if active is not None:
                self._engine_service.mark_closing(active)
                # 8a. ROUTER UNBIND — failure: DO NOT close/open, first-error.
                #     F-FINAL-P2-01: AudioTransportRouter._detach() is NOT
                #     failure-atomic — an exception may occur after SOME
                #     callbacks were detached while bound_engine_id still equals
                #     the source. Physical ownership truth (active=source) is
                #     preserved, but READY is NOT guaranteed: the projection is
                #     conservatively FAILED via mark_bound_failed (callback
                #     completeness cannot be assumed). If the detach DID happen
                #     despite the exception (bound None), no source remains.
                try:
                    self._router.unbind()
                except Exception as original:
                    self.last_failure_stage = (
                        AudioEngineSwitchFailureStage.SOURCE_UNBIND
                    )
                    bound = self._router.bound_engine_id
                    if bound == active:
                        self._engine_service.mark_bound_failed(active, str(original))
                    elif bound is None:
                        self._engine_service.mark_failed(active, str(original))
                    else:
                        # Unexpected physical identity: preserve observable truth
                        # without fabricating (bound engine is what the router
                        # actually references).
                        self._engine_service.mark_bound_failed(bound, str(original))
                    raise
                # 8b. CLOSE ACTIVE PROVIDER — after unbind (never close a
                #     provider the router is attached to). Failure: destructive
                #     boundary already crossed; target NOT opened; old-backend
                #     acceptance invalidated (old ownership is gone).
                source_provider = self._registry.provider(active)
                try:
                    source_provider.close()
                except Exception as original:
                    self.last_failure_stage = AudioEngineSwitchFailureStage.SOURCE_CLOSE
                    self._playback.invalidate_backend_acceptance_for_engine_switch()
                    self._engine_service.mark_failed(active, str(original))
                    raise
                # 8c. INVALIDATE OLD BACKEND ACCEPTANCE — the new backend has
                #     never loaded the logical track; next play() reloads it.
                self._playback.invalidate_backend_acceptance_for_engine_switch()

            # 9. TARGET ACTIVATION.
            self._engine_service.mark_initializing(target)
            try:
                target_port = provider.open()
            except Exception as original:
                self.last_failure_stage = AudioEngineSwitchFailureStage.TARGET_OPEN
                # Target never opened: no ownership to release. FAILED is the
                # honest lifecycle; selected target stays as persisted intent.
                self._engine_service.mark_failed(target, str(original))
                # M11.3G seam: SAFE for fallback (source closed, router unbound).
                if self._recover_callback is not None:
                    self._recover_callback(target, str(original))
                raise
            try:
                self._router.bind(target, target_port)
                # 10. VALIDATE — never READY before router truth.
                if self._router.bound_engine_id != target:
                    raise AudioEngineSwitchError(
                        f"router bind validation failed: bound="
                        f"{self._router.bound_engine_id}, expected={target.value}"
                    )
                # 11. RESTORE VOLUME/MUTE — canonical preferences on the new
                #     transport BEFORE READY.
                self._playback.restore_volume(volume, muted)
            except Exception as original:
                # Target bound (or partially bound): release best effort. P1-04:
                # NEVER close the target provider while the router still reports
                # itself bound to it — that would create router → closed backend.
                # If the cleanup detach failed, the state must reflect the
                # PHYSICAL truth (active=target, lifecycle=FAILED, primary error).
                from contextlib import suppress

                with suppress(Exception):
                    self._router.unbind()
                if self._router.bound_engine_id is None:
                    # Detach succeeded: release target ownership. The recovery
                    # callback is invoked ONLY when the provider close ALSO
                    # succeeds (P1-02: detach alone does not prove the runtime
                    # is fully released — a failed close makes fallback UNSAFE).
                    try:
                        provider.close()
                    except Exception as close_exc:
                        self.last_failure_stage = AudioEngineSwitchFailureStage(
                            "target_activation_detached_close_failed"
                        )
                        self._engine_service.mark_failed(
                            target,
                            f"{original}; provider release failed: {close_exc}",
                        )
                        # FIRST ERROR WINS: the ORIGINAL activation error is the
                        # primary exception; the close failure is secondary
                        # diagnostic truth (recorded in state, never the raise).
                        raise original from close_exc
                    self._engine_service.mark_failed(target, str(original))
                    # M11.3G seam: SAFE for fallback ONLY because detach AND
                    # release both succeeded. The original error still
                    # propagates afterwards.
                    # noqa: E501 — canonical long stage enum on one line
                    self.last_failure_stage = AudioEngineSwitchFailureStage.TARGET_ACTIVATION_DETACHED_RELEASED  # noqa: E501
                    if self._recover_callback is not None:
                        self._recover_callback(target, str(original))
                else:
                    # Detach failed: target remains physically bound. Do NOT
                    # close it. State reflects physical truth, primary error
                    # preserved (cleanup unbind error stays secondary). NOT SAFE
                    # for fallback (two concurrently owned engines forbidden).
                    self.last_failure_stage = (
                        AudioEngineSwitchFailureStage.TARGET_ACTIVATION_STILL_BOUND
                    )
                    self._engine_service.mark_bound_failed(
                        self._router.bound_engine_id, str(original)
                    )
                raise

            # 12. READY — only after bind validation + transport restore.
            self._engine_service.mark_ready(target)

            # 13. (KCR-021) stopped-media rehydration on the NEW backend —
            #     LOAD + deferred seek allowed, NO autoplay, NO optimistic
            #     position (visible position reconfirms through backend truth).
            #     A media rehydration failure is a SEPARATE domain from the
            #     engine switch: the target stays READY; the model surfaces the
            #     rejection/load error through its canonical path.
            try:
                self._playback.prepare_after_engine_switch(media_snapshot)
            except Exception:
                # engine already READY — the model state carries the media
                # failure (first-error-wins preserved for the switch itself)
                logger.warning(
                    "stopped-media rehydration failed after engine switch to %s",
                    target.value,
                    exc_info=True,
                )
        finally:  # P1-01: lease ALWAYS released
            lease.release()
