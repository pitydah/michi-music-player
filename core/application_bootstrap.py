"""ApplicationBootstrap — single productive startup for QML application.
Builds all services in dependency order using domain-specific composition builders.
API: build()->start()->create_bridges()->register_context(engine)->load_qml(engine)->shutdown().
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Self

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
    from ui_qml_bridge.action_registry import ActionRegistry
    from ui_qml_bridge.context_registrar import ContextRegistrar

logger = logging.getLogger("michi.bootstrap")


class ApplicationBootstrap:
    """Compose and manage the lifecycle of the QML application services."""

    def __init__(self) -> None:
        self.container = ObservableServiceContainer()
        self._bridges: dict[str, QObject] = {}
        self._has_built = False
        self._has_started = False

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
        ar = self.container.require("action_registry")

        self._register_actions(ar)
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
        return True

    def shutdown(self) -> None:
        """Shut down all services and reset bootstrap lifecycle flags."""
        logger.info("Bootstrap: shutting down")
        self.container.shutdown()
        self._has_built = False
        self._has_started = False

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

    def _handler(
        self,
        service_name: str,
        method: str,
        *default_args: Any,
    ) -> Callable[..., dict[str, Any]]:
        """Create an action handler that normalizes service calls and failures."""
        svc = self.container.get(service_name)

        def _call(*args: Any) -> dict[str, Any]:
            if not svc:
                return {"ok": False, "error": f"Service not available: {service_name}",
                        "error_code": "SERVICE_UNAVAILABLE"}
            if not hasattr(svc, method):
                return {"ok": False, "error": f"Method not found: {service_name}.{method}",
                        "error_code": "METHOD_NOT_FOUND"}
            try:
                result = getattr(svc, method)(*default_args, *args)
                return result if isinstance(result, dict) else {"ok": True, "result": str(result)}
            except Exception as e:
                return {"ok": False, "error": str(e), "error_code": "EXECUTION_ERROR",
                        "recoverable": True}

        return _call

    def _register_actions(self, ar: ActionRegistry) -> None:
        """Register bootstrap-owned playback actions with their service handlers."""
        from ui_qml_bridge.action_registry import ActionDescriptor
        h = self._handler

        ids = [
            ("play", "playback", "playback_service", "play"),
            ("pause", "playback", "playback_service", "pause"),
            ("next", "playback", "queue_service", "next"),
            ("previous", "playback", "queue_service", "previous"),
            ("stop", "playback", "playback_service", "stop"),
            ("playback.shuffle", "playback", "queue_service", "toggle_shuffle"),
            ("playback.repeat", "playback", "queue_service", "toggle_repeat"),
            ("queue.clear", "playback", "queue_service", "clear"),
            ("playback.volume.up", "playback", "playback_service", "volume_up"),
            ("playback.volume.down", "playback", "playback_service", "volume_down"),
            ("playback.seek", "playback", "playback_service", "seek"),
        ]
        for action_id, category, svc, method in ids:
            ar.register(ActionDescriptor(action_id=action_id, title=action_id, category=category,
                                         handler=h(svc, method)))

    def get_queue_service(self) -> Any | None:
        """Return the queue service when it has been registered."""
        return self.container.get("queue_service")

    def get_worker_manager(self) -> Any | None:
        """Return the worker manager when it has been registered."""
        return self.container.get("worker_manager")

    def get_query_executor(self) -> Any | None:
        """Return the query executor when it has been registered."""
        return self.container.get("query_executor")
