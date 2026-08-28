"""AudioEngineBridge — QML adapter for the M11.3 audio engine runtime.

THIN presentation adapter exposing the canonical engine state
(AudioEngineService), the registered engine set (AudioEngineRegistry) and
the explicit switch intent (AudioEngineSelectionCoordinator) to QML.

The bridge is NOT a runtime authority: it never opens/closes providers,
never binds/unbinds the router, never mutates engine state and never calls
settings persistence. The ONLY switching entry point delegates to
AudioEngineSelectionCoordinator.switch_to(...).

No infrastructure imports (no GStreamer/MPD/Qt backend classes). No polling:
state flows through service notifications; Qt scheduling only defers switch
work for one paint turn and runs isolated availability probes off the UI thread.
"""

import logging
from collections.abc import Callable

from PySide6.QtCore import (
    Property,
    QObject,
    QRunnable,
    QThreadPool,
    QTimer,
    Signal,
    Slot,
)

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.application.audio_engine_selection import EngineSelectionAction
from michi.application.audio_engine_selection_coordinator import (
    AudioEngineSelectionCoordinator,
    AudioEngineSwitchError,
    AudioEngineSwitchInProgressError,
    AudioEngineSwitchNotQuiescentError,
    AudioEngineSwitchUnavailableError,
)
from michi.application.audio_engine_service import AudioEngineService
from michi.domain.audio_engine import (
    AudioEngineCapabilities,
    AudioEngineDescriptor,
    AudioEngineId,
    AudioEngineLifecycle,
)

logger = logging.getLogger(__name__)


class _CallableRunnable(QRunnable):
    def __init__(self, callback: Callable[[], None]) -> None:
        super().__init__()
        self._callback = callback

    def run(self) -> None:
        self._callback()


def submit_audio_engine_probe(callback: Callable[[], None]) -> None:
    """Production probe executor: never performs provider I/O on the UI thread."""
    QThreadPool.globalInstance().start(_CallableRunnable(callback))


def _lifecycle_label(lifecycle: AudioEngineLifecycle) -> str:
    """Human-friendly lifecycle label (canonical state preserved internally)."""
    return {
        AudioEngineLifecycle.UNINITIALIZED: "Preparing",
        AudioEngineLifecycle.UNAVAILABLE: "Not available",
        AudioEngineLifecycle.AVAILABLE: "Available",
        AudioEngineLifecycle.INITIALIZING: "Starting\u2026",
        AudioEngineLifecycle.READY: "Ready",
        AudioEngineLifecycle.FAILED: "Needs attention",
        AudioEngineLifecycle.CLOSING: "Switching\u2026",
    }.get(lifecycle, lifecycle.value)


def _engine_display_name(engine_id: AudioEngineId) -> str:
    return {
        AudioEngineId.QT_MULTIMEDIA: "Qt Multimedia",
        AudioEngineId.GSTREAMER: "GStreamer",
        AudioEngineId.MPD: "MPD",
    }.get(engine_id, engine_id.value)


def _engine_short_identity(engine_id: AudioEngineId) -> str:
    return {
        AudioEngineId.QT_MULTIMEDIA: "Compatibility",
        AudioEngineId.GSTREAMER: "Precision",
        AudioEngineId.MPD: "Dedicated",
    }.get(engine_id, "")


def _engine_description(engine_id: AudioEngineId) -> str:
    return {
        AudioEngineId.QT_MULTIMEDIA: (
            "Uses the desktop's standard multimedia system. "
            "A simple and reliable choice for broad compatibility."
        ),
        AudioEngineId.GSTREAMER: (
            "Uses a flexible in-process audio pipeline with fine control "
            "over playback behavior."
        ),
        AudioEngineId.MPD: (
            "Uses a private playback process managed by Michi, keeping the "
            "audio engine separate from the interface."
        ),
    }.get(engine_id, "")


class AudioEngineBridge(QObject):
    """QML surface for the canonical audio engine runtime (M11.3-UI)."""

    state_changed = Signal()
    engines_changed = Signal()
    switch_succeeded = Signal(str)
    switch_failed = Signal(str, str)  # (engineId, friendlyMessage)
    technical_error_changed = Signal()
    switch_request_pending_changed = Signal()
    _probe_completed = Signal(int, str, object, str)

    def __init__(
        self,
        engine_service: AudioEngineService,
        registry: AudioEngineRegistry,
        selection_coordinator: AudioEngineSelectionCoordinator,
        playback_quiescent: Callable[[], bool] | None = None,
        playback_subscribe: Callable[[Callable[[], None]], None] | None = None,
        playback_unsubscribe: Callable[[Callable[[], None]], None] | None = None,
        probe_submit: Callable[[Callable[[], None]], None] | None = None,
        switch_submit: Callable[[Callable[[], None]], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = engine_service
        self._registry = registry
        # P1-02: READ-ONLY quiescence query (never an authority — the query
        # reuses PlaybackService.is_engine_switch_quiescent through the
        # composition root; the bridge never duplicates the logic).
        # PLAYBACK-CONTROLS-R1 (P2): engineSwitchReady is a PLAYBACK truth —
        # the projection must re-evaluate when Playback changes, not only
        # when AudioEngineState changes. The bridge subscribes to the
        # playback service notifications when the query is wired.
        self._playback_quiescent = playback_quiescent
        self._playback_subscribe = playback_subscribe
        self._playback_unsubscribe = playback_unsubscribe
        self._playback_changed_cb = None
        self._disposed = False
        if playback_subscribe is not None:
            self._playback_changed_cb = self._on_playback_changed
            playback_subscribe(self._playback_changed_cb)
        self._coordinator = selection_coordinator
        self._probe_submit = probe_submit or (lambda callback: callback())
        self._switch_submit = switch_submit or (
            lambda callback: QTimer.singleShot(0, callback)
        )
        self._probe_generation = 0
        self._switch_request_pending_target = ""
        # Controlled availability snapshot — probed on demand, never on
        # every QML property evaluation. Contains DESCRIPTOR FACTS ONLY
        # (no selected/active/switching — those are composed live from
        # AudioEngineService state so they can never go stale).
        self._engine_facts: list[dict] = [
            self._pending_probe_facts(engine_id)
            for engine_id in self._registry.engine_ids
        ]
        # Presentation-local transient diagnostic (never runtime authority,
        # never persisted): the raw exception text of the last switch
        # failure. Canonical technical truth lives in
        # AudioEngineService.state.error_message for destructive failures.
        self._last_switch_technical_error = ""
        self._service.subscribe_changed(self._on_state_changed)
        self._probe_completed.connect(self._on_probe_completed)
        self.refresh_engines()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def dispose(self) -> None:
        """Deterministic unsubscribe — no leaked callbacks after shutdown."""
        if self._disposed:
            return
        self._disposed = True
        self._service.unsubscribe_changed(self._on_state_changed)
        if (
            self._playback_changed_cb is not None
            and self._playback_unsubscribe is not None
        ):
            self._playback_unsubscribe(self._playback_changed_cb)
            self._playback_changed_cb = None

    def _on_playback_changed(self) -> None:
        """PLAYBACK-CONTROLS-R1: a Playback change can flip
        engineSwitchReady/engineSwitchBlocker — notify the QML projection
        (the coordinator lease remains the real authority)."""
        if not self._disposed:
            self.state_changed.emit()

    def _on_state_changed(self) -> None:
        if not self._disposed:
            self.state_changed.emit()
            # The engines projection composes selected/active/switching from
            # CURRENT service state — a state change may alter the composed
            # rows, so the engines notification must fire too (live model,
            # never stale).
            self.engines_changed.emit()

    # ------------------------------------------------------------------
    # Engine snapshot (controlled refresh — not per-binding probing)
    # ------------------------------------------------------------------

    @Slot()
    def refresh_engines(self) -> None:
        """Refresh each provider independently outside the production UI thread.

        Cached rows stay visible while probes run. One broken provider cannot
        suppress facts from the others, and stale generations are discarded.
        """
        self._probe_generation += 1
        generation = self._probe_generation
        for engine_id in self._registry.engine_ids:
            provider = self._registry.provider(engine_id)

            def probe_one(provider=provider, engine_id=engine_id) -> None:
                try:
                    descriptor = provider.probe()
                    error = ""
                except Exception as exc:  # noqa: BLE001 — provider isolation
                    descriptor = AudioEngineDescriptor(
                        engine_id=engine_id,
                        display_name=_engine_display_name(engine_id),
                        available=False,
                        unavailable_reason=f"Availability check failed: {exc}",
                        capabilities=AudioEngineCapabilities(),
                    )
                    error = str(exc)
                try:
                    self._probe_completed.emit(
                        generation, engine_id.value, descriptor, error
                    )
                except RuntimeError:
                    # The parent QObject may have been destroyed while a
                    # shutdown-time probe was finishing in the thread pool.
                    return

            self._probe_submit(probe_one)

    def _pending_probe_facts(self, engine_id: AudioEngineId) -> dict:
        return {
            "id": engine_id,
            "displayName": _engine_display_name(engine_id),
            "shortIdentity": _engine_short_identity(engine_id),
            "description": _engine_description(engine_id),
            "available": False,
            "implemented": True,
            "canActivate": False,
            "activationBlocker": "Checking availability…",
            "probePending": True,
            "probeError": "",
            "descriptor": None,
            "capabilities": {
                "localFilePlayback": False,
                "seek": False,
                "pause": False,
                "volume": False,
                "mute": False,
            },
        }

    @Slot(int, str, object, str)
    def _on_probe_completed(
        self,
        generation: int,
        raw_engine_id: str,
        descriptor: AudioEngineDescriptor,
        error: str,
    ) -> None:
        if self._disposed or generation != self._probe_generation:
            return
        engine_id = _decode_engine_id(raw_engine_id)
        if engine_id is None:
            return
        facts = {
            "id": engine_id,
            "displayName": _engine_display_name(engine_id),
            "shortIdentity": _engine_short_identity(engine_id),
            "description": _engine_description(engine_id),
            "available": descriptor.available,
            "implemented": descriptor.implemented,
            "canActivate": descriptor.can_activate,
            "activationBlocker": descriptor.activation_blocker,
            "probePending": False,
            "probeError": error,
            "descriptor": descriptor,
            "capabilities": {
                "localFilePlayback": descriptor.capabilities.local_file_playback,
                "seek": descriptor.capabilities.seek,
                "pause": descriptor.capabilities.pause,
                "volume": descriptor.capabilities.volume,
                "mute": descriptor.capabilities.mute,
            },
        }
        for index, current in enumerate(self._engine_facts):
            if current["id"] is engine_id:
                self._engine_facts[index] = facts
                break
        else:
            self._engine_facts.append(facts)
        self.engines_changed.emit()

    # ------------------------------------------------------------------
    # Projections
    # ------------------------------------------------------------------

    def _get_engine_switch_ready(self) -> bool:
        """Compatibility aggregate; row.selectionAllowed is authoritative."""
        if self._switch_request_pending_target:
            return False
        return any(
            row["selectionAllowed"] and row["selectionAction"] != "noop"
            for row in self._get_engines()
        )

    def _get_engine_switch_blocker(self) -> str:
        """Semantic blocker copy for the user — never backend internals."""
        if self._switch_request_pending_target:
            return "Audio engine change is already in progress."
        for row in self._get_engines():
            if row["selectionBlocker"]:
                return row["selectionBlocker"]
        return ""

    def _get_switch_request_pending_target(self) -> str:
        return self._switch_request_pending_target

    def _get_selected_engine_id(self) -> str:
        return self._service.state.selected_engine_id.value

    def _get_active_engine_id(self) -> str:
        active = self._service.state.active_engine_id
        return active.value if active is not None else ""

    def _get_selected_engine_name(self) -> str:
        return _engine_display_name(self._service.state.selected_engine_id)

    def _get_active_engine_name(self) -> str:
        active = self._service.state.active_engine_id
        return _engine_display_name(active) if active is not None else ""

    def _get_lifecycle(self) -> str:
        return self._service.state.lifecycle.value

    def _get_lifecycle_label(self) -> str:
        return _lifecycle_label(self._service.state.lifecycle)

    def _get_switching_to(self) -> str:
        switching = self._service.state.switching_to
        return switching.value if switching is not None else ""

    def _get_fallback_from(self) -> str:
        fallback = self._service.state.fallback_from
        return fallback.value if fallback is not None else ""

    def _get_has_fallback(self) -> bool:
        st = self._service.state
        return (
            st.fallback_from is not None
            and st.active_engine_id == AudioEngineId.QT_MULTIMEDIA
            and st.selected_engine_id != st.active_engine_id
        )

    def _get_error_message(self) -> str:
        return self._service.state.error_message or ""

    def _get_last_switch_technical_error(self) -> str:
        return self._last_switch_technical_error

    def _get_engines(self) -> list[dict]:
        """Live engine rows: cached descriptor facts + CURRENT service state
        overlays (selected/active/switching). No provider re-probe."""
        state = self._service.state
        rows = []
        for facts in self._engine_facts:
            engine_id = facts["id"]
            row = dict(facts)
            descriptor = row.pop("descriptor", None)
            row["id"] = engine_id.value
            row["selected"] = engine_id == state.selected_engine_id
            row["active"] = engine_id == state.active_engine_id
            row["switching"] = (
                engine_id == state.switching_to
                or engine_id.value == self._switch_request_pending_target
            )
            if descriptor is None:
                row["selectionAction"] = EngineSelectionAction.UNAVAILABLE.value
                row["selectionAllowed"] = False
                row["selectionBlocker"] = row["activationBlocker"]
            else:
                plan = self._coordinator.selection_plan(engine_id, descriptor)
                row["selectionAction"] = plan.action.value
                row["selectionAllowed"] = plan.allowed and not bool(
                    self._switch_request_pending_target
                )
                row["selectionBlocker"] = plan.blocker_message
            rows.append(row)
        return rows

    def _get_status_summary(self) -> str:
        """Friendly one-line summary (derived, never persisted)."""
        st = self._service.state
        if st.fallback_from is not None and st.active_engine_id is not None:
            # Runtime-general wording: convergence may follow a failure at
            # startup OR a problem after startup. Technical detail lives in
            # state.error_message (Advanced disclosure only).
            return (
                f"Michi is temporarily using {_engine_display_name(st.active_engine_id)} "
                f"because {_engine_display_name(st.fallback_from)} encountered a problem."
            )
        if (
            st.lifecycle is AudioEngineLifecycle.READY
            and st.active_engine_id is not None
        ):
            return f"{_engine_display_name(st.active_engine_id)} is ready."
        return _lifecycle_label(st.lifecycle)

    # ------------------------------------------------------------------
    # Intent — the ONLY switch path from the presentation layer
    # ------------------------------------------------------------------

    @Slot(str)
    def switch_engine(self, engine_id: str) -> None:
        """Delegate a UI engine switch to the selection coordinator.

        Decodes the canonical id deterministically; invalid strings produce
        a deterministic presentation error. The coordinator remains the
        sole switch authority — this method never stops playback, never
        mutates state, never touches providers/router."""
        target = _decode_engine_id(engine_id)
        # P2-03 lifecycle: every NEW attempt clears the previous transient
        # diagnostic FIRST (it must never look current after a later
        # attempt). Success keeps it empty; failure stores the new one.
        self._set_technical("")
        if target is None:
            self._set_technical(f"unknown engine id: {engine_id!r}")
            logger.warning(
                "audio engine switch rejected: %s", self._last_switch_technical_error
            )
            self.switch_failed.emit(
                engine_id, "Michi could not change the audio engine."
            )
            return
        if self._switch_request_pending_target:
            exc = AudioEngineSwitchInProgressError(
                "engine switch request already pending"
            )
            self._remember_technical(exc)
            self.switch_failed.emit(
                engine_id, "Michi is already changing the audio engine."
            )
            return
        self._set_switch_request_pending(engine_id)
        # Publish pending intent before provider probing/persistence/lifecycle
        # work. The next event-loop turn creates a real paint opportunity;
        # Application remains the sole semantic and transaction authority.
        self._switch_submit(lambda: self._perform_switch(target, engine_id))

    def _perform_switch(self, target: AudioEngineId, engine_id: str) -> None:
        if self._disposed or self._switch_request_pending_target != engine_id:
            return
        failure_message = ""
        refresh_after = False
        try:
            self._coordinator.switch_to(target)
        except AudioEngineSwitchNotQuiescentError as exc:
            self._remember_technical(exc)
            failure_message = str(exc)
        except AudioEngineSwitchUnavailableError as exc:
            self._remember_technical(exc)
            # KCR-023: the coordinator's FRESH probe disproved the cached
            # facts — refresh the availability projection so the row stops
            # showing canActivate=true. Diagnostic only; the primary switch
            # exception is never replaced (a refresh failure keeps it).
            refresh_after = True
            failure_message = "This audio engine is not available on this system."
        except AudioEngineSwitchInProgressError as exc:
            self._remember_technical(exc)
            failure_message = "Michi is already changing the audio engine."
        except AudioEngineSwitchError as exc:
            self._remember_technical(exc)
            failure_message = "Michi could not change the audio engine."
        except Exception as exc:  # defensive boundary — never silent
            self._remember_technical(exc)
            logger.exception("unexpected audio engine switch failure")
            failure_message = "Michi could not change the audio engine."
        else:
            refresh_after = True
        finally:
            self._set_switch_request_pending("")
        if refresh_after:
            try:
                self.refresh_engines()
            except Exception:  # noqa: BLE001 — primary result wins
                logger.warning(
                    "engine availability refresh failed after switch result",
                    exc_info=True,
                )
        if failure_message:
            self.switch_failed.emit(engine_id, failure_message)
        else:
            self.switch_succeeded.emit(engine_id)

    def _set_switch_request_pending(self, engine_id: str) -> None:
        if self._switch_request_pending_target == engine_id:
            return
        self._switch_request_pending_target = engine_id
        if not self._disposed:
            self.switch_request_pending_changed.emit()
            self.state_changed.emit()
            self.engines_changed.emit()

    def _remember_technical(self, exc: Exception) -> None:
        """Presentation-local transient diagnostic evidence (never runtime
        authority, never persisted). Canonical technical truth for
        destructive failures remains AudioEngineService.state.error_message."""
        self._set_technical(str(exc))
        logger.info("audio engine switch failed: %s", exc)

    def _set_technical(self, text: str) -> None:
        """Store the transient diagnostic, notifying ONLY when the value
        actually changed (P2-03 lifecycle: cleared per attempt, replaced by
        failures, kept empty on success)."""
        if self._last_switch_technical_error == text:
            return
        self._last_switch_technical_error = text
        if not self._disposed:
            self.technical_error_changed.emit()

    selectedEngineId = Property(str, _get_selected_engine_id, notify=state_changed)
    activeEngineId = Property(str, _get_active_engine_id, notify=state_changed)
    selectedEngineName = Property(str, _get_selected_engine_name, notify=state_changed)
    activeEngineName = Property(str, _get_active_engine_name, notify=state_changed)
    lifecycle = Property(str, _get_lifecycle, notify=state_changed)
    lifecycleLabel = Property(str, _get_lifecycle_label, notify=state_changed)
    switchingTo = Property(str, _get_switching_to, notify=state_changed)
    fallbackFrom = Property(str, _get_fallback_from, notify=state_changed)
    hasFallback = Property(bool, _get_has_fallback, notify=state_changed)
    errorMessage = Property(str, _get_error_message, notify=state_changed)
    lastSwitchTechnicalError = Property(
        str, _get_last_switch_technical_error, notify=technical_error_changed
    )
    engines = Property(list, _get_engines, notify=engines_changed)
    engineSwitchReady = Property(bool, _get_engine_switch_ready, notify=state_changed)
    engineSwitchBlocker = Property(
        str, _get_engine_switch_blocker, notify=state_changed
    )
    switchRequestPendingTarget = Property(
        str,
        _get_switch_request_pending_target,
        notify=switch_request_pending_changed,
    )
    statusSummary = Property(str, _get_status_summary, notify=state_changed)


def _decode_engine_id(raw: str) -> AudioEngineId | None:
    """Deterministic canonical decode — invalid strings map to None."""
    for engine in AudioEngineId:
        if raw == engine.value:
            return engine
    return None
