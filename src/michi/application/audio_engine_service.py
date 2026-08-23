"""AudioEngineService — sole owner of AudioEngineState (M11.3A foundation).

State ownership + observation only. Framework-free: no PySide6, no gi, no
subprocess, no socket, no SQLite. Runtime switching belongs to M11.3F."""

from collections.abc import Callable

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.domain.audio_engine import (
    AudioEngineId,
    AudioEngineLifecycle,
    AudioEngineState,
)


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
        for cb in list(self._subscribers):
            cb()

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

    def mark_switch_aborted_preserving_active(
        self, engine_id: AudioEngineId, message: str
    ) -> None:
        """M11.3F P1-02: the switch transaction failed BEFORE the source was
        detached — the source runtime is still open, bound, validated and
        usable. Lifecycle describes the ENGINE RUNTIME SLOT: the slot is
        still READY. The active engine is NOT absent; SELECTED != ACTIVE is
        canonical (target preference already durably persisted). This is NOT
        fallback and NOT a failed slot — only the transaction failed."""
        self._replace(
            AudioEngineState(
                selected_engine_id=self._state.selected_engine_id,
                active_engine_id=engine_id,
                lifecycle=AudioEngineLifecycle.READY,
                switching_to=None,
                error_message=message,
                fallback_from=None,
            )
        )

    def mark_bound_failed(self, engine_id: AudioEngineId, message: str) -> None:
        """M11.3F P1-04: target activation failed AFTER the router bound it
        AND the cleanup detach also failed — the target remains PHYSICALLY
        bound. State must reflect physical truth: active=engine_id, lifecycle
        FAILED (the activation transaction failed; it is NOT READY). Never
        close a provider the router still references. Distinct from
        mark_failed() (which means active=None — M11.3B startup semantics)."""
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
