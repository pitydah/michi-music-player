"""ApplicationBootstrap — single productive startup for QML application.
Builds all services in dependency order using domain-specific composition builders.
API: build()->start()->create_bridges()->register_context(engine)->load_qml(engine)->shutdown().
"""
from __future__ import annotations

import logging
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


class ApplicationBootstrap:
    """Compose and manage the lifecycle of the QML application services."""

    def __init__(self) -> None:
        self.container = ObservableServiceContainer()
        self._bridges: dict[str, QObject] = {}
        self._has_built = False
        self._has_started = False
        self._session_restore_attempted = False

    def _validate_required(self) -> list[str]:
        return self.container.validate_required_present()

    def build(self) -> Self:
        """Build and register each service once in dependency order."""
        if self._has_built:
            return self
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
        logger.info("Bootstrap: build complete — %d services",
                     len(self.container._services))
        return self

    def start(self) -> Self:
        """Build missing services and start the service container."""
        if not self._has_built:
            self.build()
        logger.info("Bootstrap: starting services")
        self.container.start()
        if self.container.state.value in ("ready", "degraded"):
            self._has_started = True
            self._restore_session_once()
            logger.info("Bootstrap: READY (state=%s)", self.container.state.value)
        else:
            logger.error("Bootstrap: FAILED (state=%s)", self.container.state.value)
        return self

    def create_bridges(self) -> dict[str, QObject]:
        """Create QML bridges backed by the composed service container."""
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
        audit = registrar.audit()
        logger.info("Bootstrap: registered %d context properties", audit["total"])
        if audit["duplicates"]:
            logger.warning("Bootstrap: duplicate context: %s", audit["duplicates"])
        return registrar

    def load_qml(self, engine: QQmlApplicationEngine, qml_path: str | None = None) -> bool:
        """Load the requested QML entry point and report whether it created a root object."""
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
        """Shut down all services and reset bootstrap lifecycle flags."""
        logger.info("Bootstrap: shutting down")
        self.container.shutdown()
        self._has_built = False
        self._has_started = False
        self._session_restore_attempted = False

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
