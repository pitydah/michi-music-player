"""M11.3F — quiescent engine selection coordinator (application layer).

Transaction/orchestration authority for EXPLICIT engine switching. It does
NOT own engine state (AudioEngineService does), does NOT own the provider
set (AudioEngineRegistry does), does NOT own playback semantics
(PlaybackService does) and does NOT own persistence (SettingsService does).
It composes those authorities into ONE canonical transaction.

Framework-free: no PySide6, no gi, no Gst, no MPD protocol/runtime, no
sqlite3. Providers are obtained ONLY through the registry — never
instantiated here. No background threads, no timers, no polling, no
automatic fallback (M11.3G owns fallback/restart convergence).
"""

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.application.audio_engine_service import AudioEngineService
from michi.application.audio_transport_router import AudioTransportRouter
from michi.application.playback_service import PlaybackService
from michi.application.settings_service import SettingsService
from michi.domain.audio_engine import AudioEngineId, AudioEngineLifecycle


class AudioEngineSwitchError(RuntimeError):
    """Deterministic engine-switch failure (transaction aborted)."""


class AudioEngineSwitchNotQuiescentError(AudioEngineSwitchError):
    """The switch was rejected because playback is not truly quiescent."""


class AudioEngineSwitchUnavailableError(AudioEngineSwitchError):
    """The target cannot activate (available=False / not implemented)."""


class AudioEngineSelectionCoordinator:
    """Explicit quiescent engine selection — the single switch transaction.

    Canonical transaction:

        VERIFY TARGET (registered + freshly probed + can_activate)
        → VERIFY QUIESCENT
        → STOP
        → REVALIDATE QUIESCENT (stop() notifies subscribers; a DIRECT /
          reentrant subscriber may have requested new playback — abort
          before the destructive boundary if so)
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

    # ------------------------------------------------------------------
    # Public transaction
    # ------------------------------------------------------------------

    def switch_to(self, target: AudioEngineId) -> None:
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

        # 3. VERIFY QUIESCENT — before ANY destructive action.
        if not self._playback.is_engine_switch_quiescent():
            raise AudioEngineSwitchNotQuiescentError(
                "engine switch requires quiescent playback (STOPPED, no "
                "pending load, no play intent, no resume in flight)"
            )

        # 4. STOP — transport truth + clean lifecycle residue.
        self._playback.stop()

        # 5. REVALIDATE QUIESCENT — stop() notifies subscribers; a DIRECT /
        #    reentrant subscriber may have requested new playback.
        if not self._playback.is_engine_switch_quiescent():
            raise AudioEngineSwitchNotQuiescentError(
                "quiescence lost after stop (reentrant playback request); "
                "switch aborted before the destructive boundary"
            )

        # 6. PERSIST SELECTION — durable BEFORE the destructive boundary.
        #    On save failure: preference restored, old runtime untouched
        #    (SettingsService.set_audio_engine restores and re-raises).
        self._settings.set_audio_engine(target)

        # 7. SELECTED (old engine may still be active — truthful window).
        self._engine_service.mark_selected(target)
        volume, muted = self._playback.snapshot_volume()

        # 8. DESTRUCTIVE BOUNDARY.
        if active is not None:
            self._engine_service.mark_closing(active)
            # 8a. ROUTER UNBIND — failure: DO NOT close/open, first-error.
            try:
                self._router.unbind()
            except Exception as original:
                self._engine_service.mark_failed(active, str(original))
                raise
            # 8b. CLOSE ACTIVE PROVIDER — after unbind (never close a
            #     provider the router is attached to). Failure: destructive
            #     boundary already crossed; target NOT opened; old-backend
            #     acceptance invalidated (old ownership is gone).
            source_provider = self._registry.provider(active)
            try:
                source_provider.close()
            except Exception as original:
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
            # Target never opened: no ownership to release. FAILED is the
            # honest lifecycle; selected target stays as persisted intent.
            self._engine_service.mark_failed(target, str(original))
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
            # Target bound (or partially bound): release best effort. Never
            # replace the primary error with a cleanup error.
            from contextlib import suppress

            with suppress(Exception):
                self._router.unbind()
            with suppress(Exception):
                provider.close()
            self._engine_service.mark_failed(target, str(original))
            raise

        # 12. READY — only after bind validation + transport restore.
        self._engine_service.mark_ready(target)
