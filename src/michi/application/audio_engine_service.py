"""AudioEngineService — sole owner of AudioEngineState (M11.3A foundation).

State ownership + observation only. Framework-free: no PySide6, no gi, no
subprocess, no socket, no SQLite. Runtime switching belongs to M11.3F."""

import logging
from collections.abc import Callable

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.domain.audio_engine import (
    AudioEngineId,
    AudioEngineLifecycle,
    AudioEngineState,
)

_logger = logging.getLogger(__name__)


class AudioEngineService:
    """Sole authority over AudioEngineState (engine selection/lifecycle).

    SELECTED != ACTIVE: the service establishes the initial state (selected
    QT_MULTIMEDIA, active None until an engine is initialized/bound)."""

    def __init__(self, registry: AudioEngineRegistry | None = None) -> None:
        self._registry = registry
        self._state = AudioEngineState(
            selected_engine_id=AudioEngineId.QT_MULTIMEDIA,
            active_engine_id=None,
            lifecycle=AudioEngineLifecycle.UNINITIALIZED,
        )
        self._subscribers: list[Callable[[], None]] = []

    @property
    def state(self) -> AudioEngineState:
        return self._state

    @property
    def registry(self) -> AudioEngineRegistry | None:
        return self._registry

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    # ------------------------------------------------------------------
    # Lifecycle transitions (M11.3B): semantic methods with invariants.
    # Selection/switching/fallback belong to M11.3F; here we only support
    # the canonical reference-engine initialization transaction.
    # ------------------------------------------------------------------

    def _replace(self, state: AudioEngineState) -> None:
        self._state = state
        # AR-18 (reliability seal): STATE COMMIT happens FIRST; observer
        # publication is isolated — a failing subscriber (e.g. a QML bridge
        # hiccup) must never make the committed state mutation look like a
        # failed engine transaction. Each callback is guarded; the failure
        # is logged as a secondary diagnostic and the remaining observers
        # still run.
        for cb in list(self._subscribers):
            try:
                cb()
            except Exception:  # noqa: BLE001 — observer isolation boundary
                _logger.exception("audio engine state observer failed")

    def mark_initializing(self, engine_id: AudioEngineId) -> None:
        """INITIALIZING: target activation underway."""
        self._replace(
            AudioEngineState(
                selected_engine_id=self._state.selected_engine_id,
                active_engine_id=None,
                lifecycle=AudioEngineLifecycle.INITIALIZING,
                switching_to=engine_id,
            )
        )

    def mark_ready(self, engine_id: AudioEngineId) -> None:
        """READY: transport bound and validated for engine_id."""
        self._replace(
            AudioEngineState(
                selected_engine_id=self._state.selected_engine_id,
                active_engine_id=engine_id,
                lifecycle=AudioEngineLifecycle.READY,
                switching_to=None,
            )
        )

    def mark_failed(self, engine_id: AudioEngineId, message: str) -> None:
        """FAILED: an activatable engine attempted startup but failed.

        Distinct from UNAVAILABLE (dependency/runtime missing)."""
        self._replace(
            AudioEngineState(
                selected_engine_id=self._state.selected_engine_id,
                active_engine_id=None,
                lifecycle=AudioEngineLifecycle.FAILED,
                switching_to=None,
                error_message=message,
            )
        )

    def mark_unavailable(self, engine_id: AudioEngineId, message: str) -> None:
        """UNAVAILABLE: the target cannot activate (dependency missing)."""
        self._replace(
            AudioEngineState(
                selected_engine_id=self._state.selected_engine_id,
                active_engine_id=None,
                lifecycle=AudioEngineLifecycle.UNAVAILABLE,
                switching_to=None,
                error_message=message,
            )
        )

    # ------------------------------------------------------------------
    # M11.3F — selection/switching semantic transitions. All state changes
    # flow through these methods; the coordinator NEVER assigns state.
    # ------------------------------------------------------------------

    def restore_selected(self, engine_id: AudioEngineId) -> None:
        """Restore the persisted SELECTED preference at startup.

        SELECTED != ACTIVE contract: this only re-baselines the user/product
        intent projection. It does NOT converge active to selected (that is
        M11.3G restart convergence, deliberately NOT implemented in F)."""
        self._replace(
            AudioEngineState(
                selected_engine_id=engine_id,
                active_engine_id=self._state.active_engine_id,
                lifecycle=self._state.lifecycle,
                switching_to=self._state.switching_to,
                error_message=self._state.error_message,
            )
        )

    def mark_selected(self, engine_id: AudioEngineId) -> None:
        """Selection committed (persisted). The old engine may STILL be
        active for the switch transaction window: selected != active is
        truthful. Exposes switching_to=engine_id."""
        self._replace(
            AudioEngineState(
                selected_engine_id=engine_id,
                active_engine_id=self._state.active_engine_id,
                lifecycle=self._state.lifecycle,
                switching_to=engine_id,
                error_message=None,
            )
        )

    def mark_closing(self, engine_id: AudioEngineId) -> None:
        """CLOSING: source teardown in progress (still active/bound until
        the router unbind + provider close complete)."""
        self._replace(
            AudioEngineState(
                selected_engine_id=self._state.selected_engine_id,
                active_engine_id=engine_id,
                lifecycle=AudioEngineLifecycle.CLOSING,
                switching_to=self._state.switching_to,
                error_message=None,
            )
        )

    def mark_bound_failed(self, engine_id: AudioEngineId, message: str) -> None:
        """M11.3F P1-04 / F-FINAL-P2-01: an engine remains PHYSICALLY bound to
        the router while the transaction/activation failed.

        Lifecycle is conservatively FAILED: the router's detach is NOT
        failure-atomic, so callback completeness cannot be guaranteed for a
        still-bound engine (READY would overstate it). active=engine_id is
        the PHYSICAL OWNERSHIP truth (router.bound_engine_id ==
        state.active_engine_id invariant). Distinct from mark_failed()
        (which means active=None — M11.3B startup semantics)."""
        self._replace(
            AudioEngineState(
                selected_engine_id=self._state.selected_engine_id,
                active_engine_id=engine_id,
                lifecycle=AudioEngineLifecycle.FAILED,
                switching_to=None,
                error_message=message,
                fallback_from=None,
            )
        )

    # ------------------------------------------------------------------
    # M11.3G — convergence transitions (fallback / startup / runtime loss).
    # State ownership stays HERE; the convergence coordinator NEVER assigns
    # AudioEngineState directly.
    # ------------------------------------------------------------------

    def mark_fallback_ready(
        self,
        active_engine_id: AudioEngineId,
        fallback_from: AudioEngineId,
        message: str,
    ) -> None:
        """READY through AUTOMATIC fallback (M11.3G).

        active=active_engine_id is running as fallback because preferred
        engine fallback_from could not be used. selected (persisted user
        intent) is NEVER overwritten by fallback. error_message carries the
        deterministic reason (e.g. 'MPD runtime failed: ...; using Qt
        Multimedia fallback')."""
        self._replace(
            AudioEngineState(
                selected_engine_id=self._state.selected_engine_id,
                active_engine_id=active_engine_id,
                lifecycle=AudioEngineLifecycle.READY,
                switching_to=None,
                error_message=message,
                fallback_from=fallback_from,
            )
        )

    def mark_convergence_failed(self, message: str) -> None:
        """M11.3G: convergence attempt ended with NO active engine.

        active=None, lifecycle=FAILED, fallback_from=None. error_message
        must carry BOTH facts deterministically (preferred failure + fallback
        failure). Never fabricate READY."""
        self._replace(
            AudioEngineState(
                selected_engine_id=self._state.selected_engine_id,
                active_engine_id=None,
                lifecycle=AudioEngineLifecycle.FAILED,
                switching_to=None,
                error_message=message,
                fallback_from=None,
            )
        )
