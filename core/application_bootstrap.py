"""ApplicationBootstrap — single productive startup for QML application.
Builds all services in dependency order using domain-specific composition builders.
API: build()->start()->create_bridges()->register_context(engine)->load_qml(engine)->shutdown().
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine

from core.service_container import ObservableServiceContainer

from core.composition import infrastructure as infra_builder
from core.composition import playback as playback_builder
from core.composition import library as library_builder
from core.composition import audio_lab as audio_lab_builder
from core.composition import ecosystem as eco_builder
from core.composition import settings as settings_builder
from core.composition import intelligence as intel_builder

if TYPE_CHECKING:
    from ui_qml_bridge.context_registrar import ContextRegistrar

logger = logging.getLogger("michi.bootstrap")

# Presentation preview harness — demo fixtures only load when the app is
# launched with --presentation-preview. Never active in normal runtime.
PRESENTATION_PREVIEW = "--presentation-preview" in sys.argv

# Bootstrap lifecycle states — explicit state machine for startup diagnostics.
# created -> initializing -> ready | degraded | failed -> shutting_down -> stopped
BOOT_CREATED = "created"
BOOT_INITIALIZING = "initializing"
BOOT_READY = "ready"
BOOT_DEGRADED = "degraded"
BOOT_FAILED = "failed"
BOOT_SHUTTING_DOWN = "shutting_down"
BOOT_STOPPED = "stopped"

BOOT_STATES: frozenset[str] = frozenset({
    BOOT_CREATED,
    BOOT_INITIALIZING,
    BOOT_READY,
    BOOT_DEGRADED,
    BOOT_FAILED,
    BOOT_SHUTTING_DOWN,
    BOOT_STOPPED,
})


class ApplicationBootstrap:
    """Compose and manage the lifecycle of the QML application services."""

    def __init__(self) -> None:
        self.container = ObservableServiceContainer()
        self._bridges: dict[str, QObject] = {}
        self._has_built = False
        self._has_started = False
        self._session_restore_attempted = False
        # Explicit bootstrap state machine.
        self._boot_state: str = BOOT_CREATED
        self._failed_services: dict[str, str] = {}
        self._degraded_services: dict[str, str] = {}
        # Demo fixtures loaded only under --presentation-preview (empty otherwise).
        self._presentation_fixtures: dict[str, Any] = {}
        # Read-only demo data adapter — instantiated only under the preview flag.
        self._presentation_provider: Any | None = None

    def _validate_required(self) -> list[str]:
        return self.container.validate_required_present()

    def build(self) -> Self:
        """Build and register each service once in dependency order."""
        if self._has_built:
            return self
        self._boot_state = BOOT_INITIALIZING
        logger.info("Bootstrap: building services")
        infra_builder.build(self.container)
        playback_builder.build(self.container)
        library_builder.build(self.container)
        audio_lab_builder.build(self.container)
        eco_builder.build(self.container)
        settings_builder.build(self.container)
        from core.navigation_service import NavigationService
        self.container.register("navigation_service", NavigationService())

        intel_builder.build(self.container)

        self._has_built = True
        service_count = sum(
            service["available"]
            for service in self.container.list_services().values()
        )
        logger.info("Bootstrap: build complete — %d services", service_count)
        return self

    def start(self) -> Self:
        """Build missing services, start the container, and derive boot state.

        State derivation:
          - container READY and no required failures -> BOOT_READY
          - container DEGRADED or optional failure   -> BOOT_DEGRADED (still runnable)
          - container FAILED or required failure     -> BOOT_FAILED (QML must NOT load)
        """
        if not self._has_built:
            self.build()
        self._boot_state = BOOT_INITIALIZING
        logger.info("Bootstrap: starting services")
        self.container.start()
        self._classify_service_failures()
        container_state = self.container.state.value
        if container_state == "failed" or self._failed_services:
            self._boot_state = BOOT_FAILED
            logger.error(
                "Bootstrap: FAILED (container=%s) — failed required services: %s",
                container_state,
                self._failed_services,
            )
        elif container_state == "degraded" or self._degraded_services:
            self._boot_state = BOOT_DEGRADED
            self._has_started = True
            self._restore_session_once()
            logger.warning(
                "Bootstrap: DEGRADED (container=%s) — degraded services: %s",
                container_state,
                self._degraded_services,
            )
        else:
            self._boot_state = BOOT_READY
            self._has_started = True
            self._restore_session_once()
            logger.info("Bootstrap: READY (state=%s)", container_state)
        if PRESENTATION_PREVIEW:
            self._enable_presentation_preview()
        return self

    def create_bridges(self) -> dict[str, QObject]:
        """Create QML bridges backed by the composed service container.

        Refuses to create bridges when the bootstrap is in the FAILED state: a
        failed required service means the bridges would be backed by missing
        services and present a broken surface to QML. Returns an empty mapping
        so callers can detect the abort without raising.
        """
        if self._boot_state == BOOT_FAILED:
            logger.error(
                "Bootstrap: refusing to create bridges — state is FAILED (%s)",
                self._failed_services,
            )
            return {}
        from ui_qml_bridge.bridge_factory import create_all_bridges
        self._bridges = create_all_bridges(self.container)
        return self._bridges

    def register_context(self, engine: QQmlApplicationEngine) -> ContextRegistrar:
        """Register all available bridges as QML context properties."""
        from ui_qml_bridge.context_registrar import ContextRegistrar
        from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
        registrar = ContextRegistrar(engine)
        for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
            bridge = self._bridges.get(bridge_key)
            if bridge is not None:
                registrar.register(qml_name, bridge)
        theme_bridge = self._bridges.get("theme")
        if theme_bridge is not None:
            registrar.register("visualQuality", theme_bridge)
        audit = registrar.audit()
        logger.info("Bootstrap: registered %d context properties", audit["total"])
        if audit["duplicates"]:
            logger.warning("Bootstrap: duplicate context: %s", audit["duplicates"])
        return registrar

    def load_qml(self, engine: QQmlApplicationEngine, qml_path: str | None = None) -> bool:
        """Load the requested QML entry point and report whether it created a root object.

        Refuses to load QML when the bootstrap is in the FAILED state: a failed
        required service means the application cannot function correctly, so
        loading the UI would only present a broken surface to the user.
        """
        if self._boot_state == BOOT_FAILED:
            logger.error(
                "Bootstrap: refusing to load QML — state is FAILED (%s)",
                self._failed_services,
            )
            return False
        if qml_path is None:
            qml_path = str(Path(__file__).resolve().parent.parent / "ui_qml" / "Main.qml")
        engine.addImportPath(str(Path(qml_path).parent.parent))
        engine.load(qml_path)
        if not engine.rootObjects():
            logger.error("Failed to load QML root objects")
            return False
        app_bridge = self._bridges.get("app")
        if app_bridge and hasattr(app_bridge, 'setReady'):
            app_bridge.setReady()
        self.restore_settings()
        return True

    def shutdown(self) -> None:
        """Shut down all services and reset bootstrap lifecycle flags.

        Idempotent: once SHUTTING_DOWN or STOPPED, subsequent calls are no-ops.
        Transition: SHUTTING_DOWN -> (container.shutdown) -> STOPPED.
        """
        if self._boot_state in (BOOT_SHUTTING_DOWN, BOOT_STOPPED):
            logger.debug("Bootstrap: shutdown already %s — skipping", self._boot_state)
            return
        self._boot_state = BOOT_SHUTTING_DOWN
        logger.info("Bootstrap: shutting down")
        try:
            self.container.shutdown()
        finally:
            self._has_built = False
            self._has_started = False
            self._session_restore_attempted = False
            self._boot_state = BOOT_STOPPED

    def run(
        self,
        engine: QQmlApplicationEngine | None = None,
        qml_path: str | None = None,
    ) -> None:
        """Build and start services, then optionally initialize a QML engine."""
        self.build()
        self.start()
        self.create_bridges()
        if engine is not None:
            self.register_context(engine)
            self.load_qml(engine, qml_path)

    @property
    def boot_state(self) -> str:
        """Current bootstrap lifecycle state (see BOOT_* constants)."""
        return self._boot_state

    @property
    def failed_services(self) -> dict[str, str]:
        """Required services that failed during start (service -> reason)."""
        return dict(self._failed_services)

    @property
    def degraded_services(self) -> dict[str, str]:
        """Optional services that failed during start (service -> reason)."""
        return dict(self._degraded_services)

    def boot_report(self) -> dict[str, Any]:
        """Return a snapshot of the bootstrap state for diagnostics/QML exposure."""
        return {
            "state": self._boot_state,
            "container_state": self.container.state.value,
            "has_built": self._has_built,
            "has_started": self._has_started,
            "failed_services": dict(self._failed_services),
            "degraded_services": dict(self._degraded_services),
        }

    def _classify_service_failures(self) -> None:
        """Populate ``_failed_services`` / ``_degraded_services`` from container state.

        Reads the container's per-service diagnostics and partitions failures by
        priority: required failures are fatal (-> FAILED), optional failures are
        survivable (-> DEGRADED) and disable the corresponding capability.
        """
        self._failed_services.clear()
        self._degraded_services.clear()
        for name, info in self.container.list_services().items():
            if not info.get("failed"):
                continue
            reason = info.get("error") or "failed"
            priority = info.get("priority")
            if priority == "required":
                self._failed_services[name] = reason
                logger.error(
                    "Bootstrap: required service '%s' failed — %s", name, reason
                )
            else:
                self._degraded_services[name] = reason
                logger.warning(
                    "Bootstrap: optional service '%s' degraded — %s", name, reason
                )

    def restore_settings(self) -> None:
        """Apply persisted appearance & accessibility settings to runtime bridges.

        ThemeStore notification requires the QML engine to be ready, so this
        must be called *after* load_qml().  Mono/balance are applied directly
        to the playback service.
        """
        theme = self._bridges.get("theme")
        accessibility = self._bridges.get("accessibility")
        if theme:
            theme._notify_theme_store()
            theme.themeChanged.emit()
        if accessibility:
            accessibility._apply_mono_to_playback()
            accessibility._apply_balance_to_playback()
            accessibility.dataChanged.emit()
        logger.info("Bootstrap: bridge settings restored")

    def _enable_presentation_preview(self) -> bool:
        """Load presentation fixtures into the bootstrap when the flag is set.

        Gated by ``--presentation-preview``: production runtime never imports
        nor activates the fixtures package, and the fixtures never substitute
        real services — they are stored as a read-only snapshot for the
        preview harness only.
        """
        if not PRESENTATION_PREVIEW:
            return False
        # presentation-preview: lazy import keeps fixtures out of normal runtime.
        from tools.presentation_preview.fixtures import (
            DEMO_ALBUMS,
            DEMO_ARTISTS,
            DEMO_PLAYLISTS,
            DEMO_TRACKS,
        )
        from tools.presentation_preview.provider import PresentationPreviewProvider
        self._presentation_fixtures = {
            "albums": list(DEMO_ALBUMS),
            "artists": list(DEMO_ARTISTS),
            "playlists": list(DEMO_PLAYLISTS),
            "tracks": list(DEMO_TRACKS),
        }
        self._presentation_provider = PresentationPreviewProvider(self._presentation_fixtures)
        logger.info(
            "Bootstrap: presentation preview active — demo fixtures loaded "
            "(%d albums, %d artists, %d playlists, %d tracks)",
            len(DEMO_ALBUMS), len(DEMO_ARTISTS), len(DEMO_PLAYLISTS), len(DEMO_TRACKS),
        )
        return True

    def _restore_session_once(self) -> None:
        """Restore the canonical queue once when session memory is enabled."""
        if self._session_restore_attempted:
            return
        self._session_restore_attempted = True
        settings = self.container.get("settings_manager")
        value = settings.value("general/remember_session", True) if settings else True
        enabled = value if isinstance(value, bool) else str(value).lower() in {
            "true", "1", "yes"
        }
        if not enabled:
            return
        queue_service = self.container.get("queue_service")
        if not queue_service:
            return
        try:
            result = queue_service.restore()
            if not result.get("ok") and result.get("error") != "NO_SAVED_STATE":
                logger.warning("Bootstrap: queue session restore skipped: %s", result)
        except Exception:
            logger.exception("Bootstrap: queue session restore failed")

    def _register_actions(self, registry: Any) -> None:
        """Register next/previous actions routed through queue_service, not playback_service."""
        queue_service = self.container.get("queue_service")
        if queue_service is None:
            return
        from ui_qml_bridge.action_registry import ActionDescriptor
        for action_id in ("next", "previous"):
            if registry.get(action_id) is not None:
                continue
            method = getattr(queue_service, action_id, None)
            if method is None:
                continue
            registry.register(ActionDescriptor(
                action_id=action_id,
                title="Siguiente" if action_id == "next" else "Anterior",
                category="playback",
                icon_key="next" if action_id == "next" else "prev",
                handler=lambda m=method: m(),
            ))

    def get_queue_service(self) -> Any | None:
        """Return the queue service when it has been registered."""
        return self.container.get("queue_service")

    def get_worker_manager(self) -> Any | None:
        """Return the worker manager when it has been registered."""
        return self.container.get("worker_manager")

    def get_query_executor(self) -> Any | None:
        """Return the query executor when it has been registered."""
        return self.container.get("query_executor")

    def register_qml(self, alias: str, obj: QObject) -> None:
        """Register a QML object or bridge under the given alias."""
        self._bridges[alias] = obj
