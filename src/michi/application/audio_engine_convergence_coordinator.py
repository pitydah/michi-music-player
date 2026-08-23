"""M11.3G — lifecycle / failure / convergence coordinator (application layer).

Owns INVOLUNTARY engine convergence ONLY:
- startup selected→active convergence (selected-first, Qt fallback)
- automatic safe Qt fallback (the ONLY automatic fallback engine in 1.0)
- fatal runtime engine loss convergence
- safe recovery after a destructive explicit-switch target failure

Does NOT own: SettingsState, PlaybackState, QueueState, the provider
registry, explicit switching (AudioEngineSelectionCoordinator owns that),
device/output convergence (M11.4), audiophile conformance (M11.5).

Framework-free: no PySide6, no gi, no MPD protocol, no SQLite, no QML.
No timers, no polling, no auto-return to the preferred engine, no retry
loops — one failure event = one convergence attempt, then stop.
"""

import logging

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.application.audio_engine_runtime_failure import (
    AudioEngineRuntimeFailureEvent,
    AudioEngineRuntimeFailureSourcePort,
    RuntimeFailureCallback,
)
from michi.application.audio_engine_service import AudioEngineService
from michi.application.audio_transport_router import AudioTransportRouter
from michi.application.playback_service import PlaybackService
from michi.domain.audio_engine import AudioEngineId

logger = logging.getLogger(__name__)


class AudioEngineConvergenceCoordinator:
    """Involuntary engine convergence — the G authority.

    fallback policy (fixed): preferred non-Qt engine fails → try Qt once.
    Qt is the canonical REFERENCE / SAFE engine; there is NO fallback chain
    and GStreamer/MPD are NEVER automatic alternates. If Qt itself is the
    failed engine: NO automatic alternate engine.
    """

    def __init__(
        self,
        *,
        engine_service: AudioEngineService,
        registry: AudioEngineRegistry,
        router: AudioTransportRouter,
        playback: PlaybackService,
    ) -> None:
        self._engine_service = engine_service
        self._registry = registry
        self._router = router
        self._playback = playback
        self._recovery_in_progress = False
        self._shutdown = False
        self._failure_subscriptions: dict[AudioEngineId, RuntimeFailureCallback] = {}

    # ------------------------------------------------------------------
    # Startup convergence (selected-first)
    # ------------------------------------------------------------------

    def converge_startup(self) -> None:
        """Activate the persisted SELECTED engine; safe Qt fallback.

        Precondition: SettingsService.load() already restored
        selected_engine_id into AudioEngineService (bootstrap order).

        selected == Qt:
            activate Qt; if unavailable → UNAVAILABLE (active None) with NO
            alternate (Qt is the fallback floor; no GStreamer/MPD fallback).
        selected != Qt:
            activate selected; only if that fails → attempt Qt exactly once.
        The router may remain unbound when nothing can activate — the graph
        keeps existing honestly (Library/Settings/UI without playback).
        """
        if self._shutdown:
            return
        state = self._engine_service.state
        selected = state.selected_engine_id
        if selected == AudioEngineId.QT_MULTIMEDIA:
            self._activate_preferred(selected, allow_qt_fallback=False)
        else:
            if not self._activate_preferred(selected, allow_qt_fallback=True):
                # selected != Qt and activation failed AND Qt fallback also
                # failed/unavailable → convergence_failed already projected.
                pass

    def _activate_preferred(
        self, engine_id: AudioEngineId, *, allow_qt_fallback: bool
    ) -> bool:
        """Activate ``engine_id``; on failure optionally attempt Qt once.

        Returns True when an engine is READY (preferred or fallback)."""
        descriptor = self._registry.descriptor(engine_id)
        if not descriptor.can_activate:
            blocker = descriptor.activation_blocker or "unavailable"
            self._engine_service.mark_unavailable(engine_id, blocker)
            if allow_qt_fallback:
                return self._try_qt_fallback(
                    fallback_from=engine_id,
                    primary_reason=f"{engine_id.value} unavailable: {blocker}",
                )
            return False

        if not self._activate_and_bind(engine_id, fallback_from=None, message=None):
            if allow_qt_fallback:
                # Preserve the ORIGINAL activation failure reason (primary
                # error truth) in the fallback message.
                original = self._engine_service.state.error_message
                return self._try_qt_fallback(
                    fallback_from=engine_id,
                    primary_reason=(
                        f"{engine_id.value} activation failed: "
                        f"{original or 'unknown error'}"
                    ),
                )
            return False
        return True

    def _activate_and_bind(
        self,
        engine_id: AudioEngineId,
        *,
        fallback_from: AudioEngineId | None,
        message: str | None,
    ) -> bool:
        """PROBE→INITIALIZING→OPEN→BIND→VALIDATE→READY (or fallback_ready).

        Returns True on READY. On failure: cleans up safely (router unbound
        + provider closed best effort when detach succeeded; never closes a
        still-bound provider) and returns False with honest state."""
        provider = self._registry.provider(engine_id)
        volume, muted = self._playback.snapshot_volume()
        self._engine_service.mark_initializing(engine_id)
        try:
            port = provider.open()
        except Exception as exc:
            self._engine_service.mark_failed(engine_id, str(exc))
            return False
        try:
            self._router.bind(engine_id, port)
            if self._router.bound_engine_id != engine_id:
                raise RuntimeError(
                    f"router bind validation failed: bound="
                    f"{self._router.bound_engine_id}, expected={engine_id.value}"
                )
            # Restore canonical transport preferences on the active transport
            # only (never through an unbound router).
            self._playback.restore_volume(volume, muted)
        except Exception as exc:
            from contextlib import suppress

            with suppress(Exception):
                self._router.unbind()
            if self._router.bound_engine_id is None:
                with suppress(Exception):
                    provider.close()
                self._engine_service.mark_failed(engine_id, str(exc))
            else:
                self._engine_service.mark_bound_failed(
                    self._router.bound_engine_id, str(exc)
                )
            return False
        if fallback_from is not None:
            self._engine_service.mark_fallback_ready(
                engine_id, fallback_from, message or "engine convergence"
            )
        else:
            self._engine_service.mark_ready(engine_id)
        return True

    def _try_qt_fallback(
        self, *, fallback_from: AudioEngineId, primary_reason: str
    ) -> bool:
        """Attempt the ONE automatic fallback: Qt Multimedia, exactly once.

        Never mutates persisted selection. Never loops. If Qt cannot
        activate, projects convergence_failed carrying BOTH facts."""
        qt_descriptor = self._registry.descriptor(AudioEngineId.QT_MULTIMEDIA)
        if not qt_descriptor.can_activate:
            blocker = qt_descriptor.activation_blocker or "unavailable"
            self._engine_service.mark_convergence_failed(
                f"{primary_reason}; Qt Multimedia fallback unavailable: {blocker}"
            )
            return False
        if not self._activate_and_bind(
            AudioEngineId.QT_MULTIMEDIA,
            fallback_from=fallback_from,
            message=(f"{primary_reason}; using Qt Multimedia fallback"),
        ):
            self._engine_service.mark_convergence_failed(
                f"{primary_reason}; Qt Multimedia fallback failed"
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Explicit-switch safe recovery (F→G seam)
    # ------------------------------------------------------------------

    def recover_safe_unbound_failure(
        self, failed_target: AudioEngineId, reason: str
    ) -> None:
        """M11.3G seam invoked by AudioEngineSelectionCoordinator ONLY in
        SAFE post-destructive states (TARGET_OPEN / TARGET_ACTIVATION_DETACHED:
        source closed, router safely unbound). Attempts the Qt fallback once.

        Never replaces the original exception (F still raises it); never
        mutates the persisted selected preference (target stays the user
        intent: SELECTED != ACTIVE canonical)."""
        if self._shutdown or self._recovery_in_progress:
            return
        self._recovery_in_progress = True
        try:
            if failed_target == AudioEngineId.QT_MULTIMEDIA:
                # Qt was the failed target: no automatic alternate engine.
                return
            self._try_qt_fallback(
                fallback_from=failed_target,
                primary_reason=f"{failed_target.value} failed: {reason}",
            )
        finally:
            self._recovery_in_progress = False

    # ------------------------------------------------------------------
    # Fatal runtime engine loss
    # ------------------------------------------------------------------

    def subscribe_provider(self, provider: AudioEngineRuntimeFailureSourcePort) -> None:
        """Wire ONE provider's runtime-failure source (idempotent).

        The failure-observation protocol is OPT-IN: providers/fakes that do
        not implement AudioEngineRuntimeFailureSourcePort are skipped (they
        simply cannot report runtime loss)."""
        engine_id = provider.engine_id
        if engine_id in self._failure_subscriptions:
            return
        subscribe = getattr(provider, "subscribe_runtime_failed", None)
        if subscribe is None:
            return  # provider without the optional G seam
        callback = self._on_runtime_failure
        subscribe(callback)
        self._failure_subscriptions[engine_id] = callback

    def handle_runtime_failure(self, event: AudioEngineRuntimeFailureEvent) -> None:
        """Typed fatal engine-loss entry point (also usable directly)."""
        if self._shutdown:
            return  # G disabled: never fallback during shutdown
        if self._recovery_in_progress:
            return  # coalesce duplicate/reentrant fatal events
        state = self._engine_service.state
        if event.engine_id != state.active_engine_id:
            return  # failure from an inactive engine: ignored
        provider = self._registry.provider(event.engine_id)
        current_generation = getattr(provider, "current_runtime_generation", None)
        if (
            current_generation is not None
            and event.runtime_generation != current_generation
        ):
            return  # stale generation: must never kill the new runtime
        self._recovery_in_progress = True
        try:
            self._converge_runtime_loss(event)
        finally:
            self._recovery_in_progress = False

    def _on_runtime_failure(self, event: AudioEngineRuntimeFailureEvent) -> None:
        self.handle_runtime_failure(event)

    def _converge_runtime_loss(self, event: AudioEngineRuntimeFailureEvent) -> None:
        """STEP1 Playback converge STOPPED → STEP2 router detach → STEP3
        close failed provider → Qt fallback ONLY when fully safe."""
        active = self._engine_service.state.active_engine_id
        # STEP 1: Playback convergence (owned by PlaybackService).
        self._playback.converge_after_engine_loss(event.reason)
        # STEP 2: router detach.
        try:
            self._router.unbind()
        except Exception as exc:
            if self._router.bound_engine_id is not None:
                # Detach failed: NEVER close the provider, NEVER fallback
                # (ownership uncertain; two concurrently owned engines would
                # be forbidden).
                self._engine_service.mark_bound_failed(active, str(exc))
                return
            logger.warning("engine runtime loss unbind raised after detach: %s", exc)
        # STEP 3: close the failed provider (only when router detached).
        provider = self._registry.provider(event.engine_id)
        try:
            provider.close()
        except Exception as exc:
            # Provider ownership uncertain: NO fallback.
            self._engine_service.mark_failed(event.engine_id, str(exc))
            return
        # SAFE: router detached + provider closed → Qt fallback exactly once.
        if active == AudioEngineId.QT_MULTIMEDIA:
            # Qt is the fallback floor: no automatic alternate engine.
            self._engine_service.mark_convergence_failed(
                f"Qt Multimedia runtime failed: {event.reason}; "
                "no automatic alternate engine"
            )
            return
        self._try_qt_fallback(
            fallback_from=event.engine_id,
            primary_reason=f"{event.engine_id.value} runtime failed: {event.reason}",
        )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Disable convergence BEFORE the audio teardown begins.

        Unsubscribes provider runtime-failure events and rejects subsequent
        events — an MPD close-time transport error must NEVER open Qt during
        application shutdown."""
        self._shutdown = True
        for engine_id, callback in list(self._failure_subscriptions.items()):
            try:
                provider = self._registry.provider(engine_id)
                provider.unsubscribe_runtime_failed(callback)
            except Exception:
                logger.warning(
                    "failed to unsubscribe runtime-failure for %s", engine_id
                )
        self._failure_subscriptions.clear()
