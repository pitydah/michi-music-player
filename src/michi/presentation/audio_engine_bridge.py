"""AudioEngineBridge — QML adapter for the M11.3 audio engine runtime.

THIN presentation adapter exposing the canonical engine state
(AudioEngineService), the registered engine set (AudioEngineRegistry) and
the explicit switch intent (AudioEngineSelectionCoordinator) to QML.

The bridge is NOT a runtime authority: it never opens/closes providers,
never binds/unbinds the router, never mutates engine state and never calls
settings persistence. The ONLY switching entry point delegates to
AudioEngineSelectionCoordinator.switch_to(...).

No infrastructure imports (no GStreamer/MPD/Qt backend classes). No
polling, no timers: state flows through AudioEngineService notifications
and explicit refresh_engines() calls.
"""

import logging
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.application.audio_engine_selection_coordinator import (
    AudioEngineSelectionCoordinator,
    AudioEngineSwitchError,
    AudioEngineSwitchInProgressError,
    AudioEngineSwitchNotQuiescentError,
    AudioEngineSwitchUnavailableError,
)
from michi.application.audio_engine_service import AudioEngineService
from michi.domain.audio_engine import AudioEngineId, AudioEngineLifecycle

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        engine_service: AudioEngineService,
        registry: AudioEngineRegistry,
        selection_coordinator: AudioEngineSelectionCoordinator,
        playback_quiescent: Callable[[], bool] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = engine_service
        self._registry = registry
        # P1-02: READ-ONLY quiescence query (never an authority — the query
        # reuses PlaybackService.is_engine_switch_quiescent through the
        # composition root; the bridge never duplicates the logic).
        self._playback_quiescent = playback_quiescent
        self._coordinator = selection_coordinator
        self._disposed = False
        # Controlled availability snapshot — probed on demand, never on
        # every QML property evaluation. Contains DESCRIPTOR FACTS ONLY
        # (no selected/active/switching — those are composed live from
        # AudioEngineService state so they can never go stale).
        self._engine_facts: list[dict] = []
        # Presentation-local transient diagnostic (never runtime authority,
        # never persisted): the raw exception text of the last switch
        # failure. Canonical technical truth lives in
        # AudioEngineService.state.error_message for destructive failures.
        self._last_switch_technical_error = ""
        self._service.subscribe_changed(self._on_state_changed)
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
        """Probe all registered engines (side-effect free) and cache their
        DESCRIPTOR FACTS ONLY. May be called on popup open / settings
        refresh — never on every binding evaluation. Runtime overlays
        (selected/active/switching) are composed live in engines."""
        rows = []
        for descriptor in self._registry.descriptors():
            engine_id = descriptor.engine_id
            rows.append(
                {
                    "id": engine_id,
                    "displayName": _engine_display_name(engine_id),
                    "shortIdentity": _engine_short_identity(engine_id),
                    "description": _engine_description(engine_id),
                    "available": descriptor.available,
                    "implemented": descriptor.implemented,
                    "canActivate": descriptor.can_activate,
                    "activationBlocker": descriptor.activation_blocker,
                    "capabilities": {
                        "localFilePlayback": descriptor.capabilities.local_file_playback,
                        "seek": descriptor.capabilities.seek,
                        "pause": descriptor.capabilities.pause,
                        "volume": descriptor.capabilities.volume,
                        "mute": descriptor.capabilities.mute,
                    },
                }
            )
        self._engine_facts = rows
        if not self._disposed:
            self.engines_changed.emit()

    # ------------------------------------------------------------------
    # Projections
    # ------------------------------------------------------------------

    def _get_engine_switch_ready(self) -> bool:
        """P1-02: truthful selector readiness — the UI must never show a
        selectable row when Playback cannot switch."""
        if self._service.state.switching_to is not None:
            return False
        if self._playback_quiescent is not None:
            return self._playback_quiescent()
        return True  # no query wired (tests/legacy): coordinator gates anyway

    def _get_engine_switch_blocker(self) -> str:
        """Semantic blocker copy for the user — never backend internals."""
        if self._service.state.switching_to is not None:
            return "Audio engine change is already in progress."
        if self._playback_quiescent is not None and not self._playback_quiescent():
            return "Stop playback before changing the audio engine."
        return ""

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
            row["id"] = engine_id.value
            row["selected"] = engine_id == state.selected_engine_id
            row["active"] = engine_id == state.active_engine_id
            row["switching"] = engine_id == state.switching_to
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
        try:
            self._coordinator.switch_to(target)
        except AudioEngineSwitchNotQuiescentError as exc:
            self._remember_technical(exc)
            self.switch_failed.emit(
                engine_id, "Stop playback before changing the audio engine."
            )
        except AudioEngineSwitchUnavailableError as exc:
            self._remember_technical(exc)
            # KCR-023: the coordinator's FRESH probe disproved the cached
            # facts — refresh the availability projection so the row stops
            # showing canActivate=true. Diagnostic only; the primary switch
            # exception is never replaced (a refresh failure keeps it).
            try:
                self.refresh_engines()
            except Exception:  # noqa: BLE001 — primary error wins; the
                # refresh failure is a logged SECONDARY diagnostic
                logger.warning(
                    "engine availability refresh failed after switch "
                    "unavailable (primary error preserved)",
                    exc_info=True,
                )
            self.switch_failed.emit(
                engine_id, "This audio engine is not available on this system."
            )
        except AudioEngineSwitchInProgressError as exc:
            self._remember_technical(exc)
            self.switch_failed.emit(
                engine_id, "Michi is already changing the audio engine."
            )
        except AudioEngineSwitchError as exc:
            self._remember_technical(exc)
            self.switch_failed.emit(
                engine_id, "Michi could not change the audio engine."
            )
        except Exception as exc:  # defensive boundary — never silent
            self._remember_technical(exc)
            logger.exception("unexpected audio engine switch failure")
            self.switch_failed.emit(
                engine_id, "Michi could not change the audio engine."
            )
        else:
            self.refresh_engines()
            self.switch_succeeded.emit(engine_id)

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
    statusSummary = Property(str, _get_status_summary, notify=state_changed)


def _decode_engine_id(raw: str) -> AudioEngineId | None:
    """Deterministic canonical decode — invalid strings map to None."""
    for engine in AudioEngineId:
        if raw == engine.value:
            return engine
    return None
