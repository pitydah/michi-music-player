"""ServiceContainer — canonical service registry with full lifecycle management.

States: CREATED -> BUILDING -> BUILT -> STARTING -> READY -> DEGRADED -> FAILED -> STOPPING -> STOPPED.
API: register, get, require, contains, build_order, validate, start, health, cancel_all, shutdown.

Lifecycle is derived EXCLUSIVELY from the declarative manifest
(``core.service_manifest``, ADR-001, FASE 1 P0 stabilization): SERVICE_MANIFEST
is the single source of truth for priority, lifecycle kind, dependencies,
start/stop methods, required/optional, health, start order and shutdown order.
There is no second inventory and no second dependency graph.

Aliases (descriptors with ``alias_of``) share the registered instance and
lifecycle of their target: alias instances are never started or shut down
separately (exactly-once per instance, tracked by object identity).

The ``_required_names``/``_optional_names``/``_capability_gated_names``/
``_deferred_physical_names``/``_deferred_names``/``_all_names`` helpers below
are DEPRECATED compatibility views computed FROM the manifest. They exist only
for legacy test assertions; no execution path calls them.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.service_manifest import (
    SERVICE_MANIFEST,
    LifecycleKind,
    ServiceDescriptor,
    ServicePriority,
)

logger = logging.getLogger("michi.service_container")


class ContainerState(Enum):
    """Lifecycle states for the service container."""

    CREATED = "created"
    BUILDING = "building"
    BUILT = "built"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


class ManifestCycleError(ValueError):
    """Raised when the manifest dependency graph contains a cycle.

    Carries the detected cycle path so bootstrap can report it explicitly.
    """


class ServiceContainer:
    """Typed container holding all backend service references with full lifecycle."""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._priorities: dict[str, ServicePriority] = {}
        self._failures: dict[str, str] = {}
        self._state = ContainerState.CREATED
        self._started_order: list[str] = []
        self._started_ids: set[int] = set()
        self._define_priorities()

    def _define_priorities(self):
        # Manifest-driven: every manifest descriptor declares its own priority.
        for name, desc in SERVICE_MANIFEST.items():
            self._priorities[name] = desc.priority

    # ── DEPRECATED compatibility views (manifest-derived; never used in
    # ── execution paths — kept for legacy test assertions). ───────────────
    @staticmethod
    def _required_names() -> set[str]:
        """DEPRECATED — manifest-derived view: keys with REQUIRED priority."""
        return {
            name for name, desc in SERVICE_MANIFEST.items()
            if desc.priority == ServicePriority.REQUIRED
        }

    @staticmethod
    def _optional_names() -> set[str]:
        """DEPRECATED — manifest-derived view: keys with OPTIONAL priority."""
        return {
            name for name, desc in SERVICE_MANIFEST.items()
            if desc.priority == ServicePriority.OPTIONAL
        }

    @staticmethod
    def _capability_gated_names() -> set[str]:
        """DEPRECATED — manifest-derived view: keys with CAPABILITY_GATED priority."""
        return {
            name for name, desc in SERVICE_MANIFEST.items()
            if desc.priority == ServicePriority.CAPABILITY_GATED
        }

    @staticmethod
    def _deferred_physical_names() -> set[str]:
        """DEPRECATED — manifest-derived view: keys with DEFERRED_PHYSICAL priority."""
        return {
            name for name, desc in SERVICE_MANIFEST.items()
            if desc.priority == ServicePriority.DEFERRED_PHYSICAL
        }

    @staticmethod
    def _deferred_names() -> set[str]:
        """DEPRECATED — manifest-derived view: keys with DEFERRED priority."""
        return {
            name for name, desc in SERVICE_MANIFEST.items()
            if desc.priority == ServicePriority.DEFERRED
        }

    def _all_names(self) -> list[str]:
        """DEPRECATED — manifest-derived view: every manifest key."""
        return list(SERVICE_MANIFEST)

    # ── Manifest graph (single source of truth) ───────────────────────────

    def _alias_target(self, name: str) -> str | None:
        """Return the canonical key *name* resolves to (None when not an alias)."""
        desc = SERVICE_MANIFEST.get(name)
        if desc is None or desc.alias_of is None:
            return None
        return desc.alias_of

    def _resolved_dependencies(self, name: str) -> set[str]:
        """Return the declared dependencies of *name* with aliases resolved."""
        desc = SERVICE_MANIFEST.get(name)
        if desc is None:
            return set()
        resolved = set()
        for dep in desc.dependencies:
            resolved.add(self._alias_target(dep) or dep)
        return resolved

    def _manifest_graph(self) -> dict[str, set[str]]:
        """Dependency graph derived ONLY from manifest descriptors.

        Alias descriptors are not graph nodes (they are not lifecycle owners);
        dependencies pointing at aliases resolve to the alias target.
        """
        graph: dict[str, set[str]] = {}
        for name, desc in SERVICE_MANIFEST.items():
            if desc.alias_of is not None:
                continue
            graph[name] = set()
            for dep in desc.dependencies:
                graph[name].add(self._alias_target(dep) or dep)
        return graph

    @staticmethod
    def _topological_sort(graph: dict[str, set[str]]) -> list[str]:
        """Deterministic Kahn topological sort over *graph* (insertion order).

        Raises ManifestCycleError with the detected cycle path when the graph
        contains a cycle — there is no silent fallback.
        """
        nodes = list(graph)
        emitted: set[str] = set()
        order: list[str] = []

        def _ready(name: str) -> bool:
            return name not in emitted and all(
                dep in emitted or dep not in graph for dep in graph[name]
            )

        while True:
            progress = False
            for name in nodes:
                if _ready(name):
                    emitted.add(name)
                    order.append(name)
                    progress = True
            if not progress:
                break

        remaining = [n for n in nodes if n not in emitted]
        if remaining:
            cycle = ServiceContainer._find_cycle(graph, remaining[0])
            raise ManifestCycleError(" -> ".join(cycle))
        return order

    @staticmethod
    def _find_cycle(graph: dict[str, set[str]], start: str) -> list[str]:
        """Return a cycle path in *graph* reachable from *start*."""
        path: list[str] = []
        seen: dict[str, int] = {}

        def visit(name: str) -> list[str] | None:
            if name in seen:
                return path[seen[name]:] + [name]
            if name not in graph:
                return None
            seen[name] = len(path)
            path.append(name)
            for dep in graph[name]:
                result = visit(dep)
                if result is not None:
                    return result
            path.pop()
            del seen[name]
            return None

        return visit(start) or [start]

    # ── Public API ────────────────────────────────────────────────────────

    def register(self, name: str, service: Any, priority: ServicePriority | None = None, dependencies: tuple[str, ...] = ()) -> None:
        self._services[name] = service
        if priority is not None:
            self._priorities[name] = priority
        elif name not in self._priorities:
            desc = SERVICE_MANIFEST.get(name)
            self._priorities[name] = desc.priority if desc else ServicePriority.OPTIONAL

    def get(self, name: str) -> Any:
        return self._services.get(name)

    def require(self, name: str) -> Any:
        svc = self._services.get(name)
        if svc is None:
            raise KeyError(f"Required service '{name}' not registered")
        return svc

    def contains(self, name: str) -> bool:
        return name in self._services and self._services[name] is not None

    def has(self, name: str) -> bool:
        return self.contains(name)

    def priority(self, name: str) -> ServicePriority | None:
        return self._priorities.get(name)

    def descriptor(self, name: str) -> ServiceDescriptor | None:
        """Return the manifest descriptor for *name* (or None when absent)."""
        return SERVICE_MANIFEST.get(name)

    def lifecycle_of(self, name: str) -> str:
        """Return the manifest lifecycle kind for *name* (or 'unknown')."""
        desc = SERVICE_MANIFEST.get(name)
        return desc.lifecycle.value if desc else "unknown"

    def build_order(self) -> list[str]:
        """Return manifest names in dependency-safe startup order.

        Manifest-only: aliases are excluded (not lifecycle owners) and
        registered keys without a manifest descriptor are appended. Raises
        ManifestCycleError when the manifest graph contains a cycle.
        """
        order = self._topological_sort(self._manifest_graph())
        for name in self._services:
            if name not in SERVICE_MANIFEST:
                order.append(name)
        return order

    def build_start_order(self) -> list[str]:
        return self.build_order()

    def validate_acyclic_graph(self) -> list[str]:
        """Return the manifest dependency order; raise on cycles."""
        return self.build_order()

    def validate_required_present(self) -> list[str]:
        """Return list of REQUIRED manifest names that are missing or None."""
        return [
            name for name, desc in SERVICE_MANIFEST.items()
            if desc.priority == ServicePriority.REQUIRED
            and (name not in self._services or self._services[name] is None)
        ]

    def validate_no_none_required(self) -> list[str]:
        """Return list of REQUIRED manifest names whose value is None or missing."""
        return self.validate_required_present()

    def validate_dependencies_present(self) -> list[str]:
        """Return manifest dependency violations (missing or None targets)."""
        errors = []
        for name, desc in SERVICE_MANIFEST.items():
            if desc.alias_of is not None:
                continue
            for dep in self._resolved_dependencies(name):
                if dep not in self._services or self._services[dep] is None:
                    errors.append(f"'{name}' depends on '{dep}' which is missing")
        return errors

    def validate(self) -> list[str]:
        """Return registration, dependency, and required-service failures.

        REQUIRED descriptors with missing dependencies, REQUIRED aliases whose
        target is missing, and manifest cycles are all fatal errors.
        """

        errors = []
        for name in self.validate_required_present():
            errors.append(f"REQUIRED '{name}' is None or missing")
        for name, desc in SERVICE_MANIFEST.items():
            if desc.priority != ServicePriority.REQUIRED:
                continue
            if desc.alias_of is not None:
                if self._services.get(desc.alias_of) is None:
                    errors.append(
                        f"REQUIRED alias '{name}' -> '{desc.alias_of}' is None or missing"
                    )
                continue
            for dep in self._resolved_dependencies(name):
                if dep not in self._services or self._services[dep] is None:
                    errors.append(f"'{name}' depends on '{dep}' which is missing")
        try:
            self._topological_sort(self._manifest_graph())
        except ManifestCycleError as exc:
            errors.append(f"Circular dependency: {exc}")
        for fname in self._failures:
            prio = self.priority(fname)
            if prio == ServicePriority.REQUIRED:
                errors.append(f"REQUIRED '{fname}' has FAILED: {self._failures[fname]}")
        for warning in self.manifest_diagnostics():
            logger.warning("Manifest: %s", warning)
        return errors

    def manifest_diagnostics(self) -> list[str]:
        """Return manifest/composition consistency warnings (never fatal).

        Warnings cover: registered keys without a manifest descriptor,
        MANAGED manifest descriptors that were never registered, declared
        manifest dependencies that were never injected, and aliases that
        point at unknown keys.
        """
        warnings = []
        registered_without = sorted(
            key for key in self._services if key not in SERVICE_MANIFEST
        )
        if registered_without:
            warnings.append(
                f"registered without manifest descriptor: {registered_without}"
            )
        manifest_unregistered = sorted(
            name for name, desc in SERVICE_MANIFEST.items()
            if desc.lifecycle == LifecycleKind.MANAGED
            and desc.alias_of is None
            and name not in self._services
        )
        if manifest_unregistered:
            warnings.append(
                f"MANAGED manifest descriptors without registration: {manifest_unregistered}"
            )
        for name, desc in SERVICE_MANIFEST.items():
            if desc.alias_of is not None:
                continue
            missing = [
                dep for dep in self._resolved_dependencies(name)
                if dep not in self._services
            ]
            if missing:
                warnings.append(
                    f"'{name}' declares dependencies never registered: {missing}"
                )
        broken_aliases = sorted(
            f"{name} -> {desc.alias_of}"
            for name, desc in SERVICE_MANIFEST.items()
            if desc.alias_of is not None and desc.alias_of not in SERVICE_MANIFEST
        )
        if broken_aliases:
            warnings.append(f"aliases without target descriptor: {broken_aliases}")
        return warnings

    @property
    def database(self) -> Any | None:
        return self._services.get("database")

    @property
    def connection_factory(self) -> Any | None:
        return self._services.get("connection_factory")

    @property
    def worker_manager(self) -> Any | None:
        return self._services.get("worker_manager")

    @property
    def query_executor(self) -> Any | None:
        return self._services.get("query_executor")

    @property
    def job_service(self) -> Any | None:
        return self._services.get("job_service")

    @property
    def event_bus(self) -> Any | None:
        return self._services.get("event_bus")

    @property
    def settings_coordinator(self) -> Any | None:
        return self._services.get("settings_coordinator")

    @property
    def settings_service(self) -> Any | None:
        return self._services.get("settings_service")

    @property
    def theme_service(self) -> Any | None:
        return self._services.get("theme_service")

    @property
    def accessibility_service(self) -> Any | None:
        return self._services.get("accessibility_service")

    @property
    def library_query_service(self) -> Any | None:
        return self._services.get("library_query_service")

    @property
    def library_sources_service(self) -> Any | None:
        return self._services.get("library_sources_service")

    @property
    def library_mutation_service(self) -> Any | None:
        return self._services.get("library_mutation_service")

    @property
    def playlist_service(self) -> Any | None:
        return self._services.get("playlist_service")

    @property
    def history_query_service(self) -> Any | None:
        return self._services.get("history_query_service")

    @property
    def global_search_service(self) -> Any | None:
        return self._services.get("global_search_service")

    @property
    def mix_query_service(self) -> Any | None:
        return self._services.get("mix_query_service")

    @property
    def mix_service(self) -> Any | None:
        return self._services.get("mix_service")

    @property
    def track_action_service(self) -> Any | None:
        return self._services.get("track_action_service")

    @property
    def playback_service(self) -> Any | None:
        return self._services.get("playback_service")

    @property
    def queue_service(self) -> Any | None:
        return self._services.get("queue_service")

    @property
    def audio_lab_service(self) -> Any | None:
        return self._services.get("audio_lab_service")

    @property
    def metadata_service(self) -> Any | None:
        return self._services.get("metadata_service")

    @property
    def smart_tagging_service(self) -> Any | None:
        return self._services.get("smart_tagging_service")

    @property
    def library_doctor_service(self) -> Any | None:
        return self._services.get("library_doctor_service")

    @property
    def device_sync_service(self) -> Any | None:
        return self._services.get("device_sync_service")

    @property
    def connection_service(self) -> Any | None:
        return self._services.get("connection_service")

    @property
    def home_audio_service(self) -> Any | None:
        return self._services.get("home_audio_service")

    @property
    def diagnostics_service(self) -> Any | None:
        return self._services.get("diagnostics_service")

    @property
    def notification_service(self) -> Any | None:
        return self._services.get("notification_service")

    @property
    def action_registry(self) -> Any | None:
        return self._services.get("action_registry")

    @property
    def confirmation_service(self) -> Any | None:
        return self._services.get("confirmation_service")

    @property
    def runtime_persistence(self) -> Any | None:
        return self._services.get("runtime_persistence")

    @property
    def process_controller(self) -> Any | None:
        return self._services.get("process_controller")

    @property
    def radio_service(self) -> Any | None:
        return self._services.get("radio_service")

    @property
    def lyrics_service(self) -> Any | None:
        return self._services.get("lyrics_service")

    @property
    def michi_ai_service(self) -> Any | None:
        return self._services.get("michi_ai_service")

    @property
    def state(self) -> ContainerState:
        return self._state

    @staticmethod
    def _start_method_for(name: str, svc: Any):
        """Return the callable start method for *svc*, or None when absent.

        MANAGED descriptors without their declared start method are skipped
        with a debug log — a missing start method is not an error.
        """
        desc = SERVICE_MANIFEST.get(name)
        method_name = desc.start_method if desc else "start"
        method = getattr(svc, method_name, None)
        if not callable(method):
            if desc is not None and desc.lifecycle == LifecycleKind.MANAGED:
                logger.debug(
                    "MANAGED service '%s' has no '%s' method — start skipped",
                    name, method_name,
                )
            return None
        return method

    def _lifecycle_start_order(self) -> list[str]:
        """Return MANAGED manifest names in dependency-safe start order.

        Aliases are excluded (they are not lifecycle owners); the order is
        the manifest topological order, so every declared dependency is
        started before its dependents.
        """
        order = self._topological_sort(self._manifest_graph())
        return [
            name for name in order
            if name in SERVICE_MANIFEST
            and SERVICE_MANIFEST[name].lifecycle == LifecycleKind.MANAGED
        ]

    def _record_start_failure(self, name: str, err: str) -> None:
        self._failures[name] = err
        prio = self.priority(name)
        if prio == ServicePriority.REQUIRED:
            logger.error("REQUIRED '%s' start failed: %s", name, err)
        else:
            logger.warning("OPTIONAL '%s' start degraded: %s", name, err)

    def start(self) -> ServiceContainer | None:
        """Validate and start registered services in manifest dependency order.

        Only MANAGED manifest descriptors are started (aliases never start
        separately; each instance starts exactly once). OPTIONAL descriptors
        whose declared dependencies are missing degrade honestly through
        report_failure instead of being silently skipped. Cycles and missing
        REQUIRED dependencies drive the container to FAILED.
        """

        errors = self.validate()
        if errors:
            logger.error("Container start blocked by %d validation error(s)", len(errors))
            for e in errors:
                logger.error("  %s", e)
            self._state = ContainerState.FAILED
            return self
        if self._state == ContainerState.CREATED:
            self._state = ContainerState.BUILDING
        self._state = ContainerState.STARTING
        self._started_order = []
        self._started_ids = set()

        degraded_by_deps: set[str] = set()
        for name, desc in SERVICE_MANIFEST.items():
            if desc.priority != ServicePriority.OPTIONAL or desc.alias_of is not None:
                continue
            svc = self._services.get(name)
            if svc is None:
                continue
            missing = [
                dep for dep in self._resolved_dependencies(name)
                if dep not in self._services or self._services[dep] is None
            ]
            if missing:
                degraded_by_deps.add(name)
                self.report_failure(
                    name, f"missing dependency: {', '.join(sorted(missing))}"
                )

        order = self._lifecycle_start_order()
        for name in order:
            if name not in self._services or self._services[name] is None:
                prio = self.priority(name)
                if prio == ServicePriority.REQUIRED:
                    self._failures[name] = "missing"
                continue
            svc = self._services[name]
            if name in degraded_by_deps:
                continue
            if id(svc) in self._started_ids:
                continue
            if (hasattr(self, '_service_states')
                    and self._service_states.get(name) in ('ready', 'starting')):
                continue
            start_method = self._start_method_for(name, svc)
            if start_method is None:
                continue
            if hasattr(self, '_service_states'):
                self._service_states[name] = "starting"
                self.service_state_changed.emit(name, "starting")
            self._started_order.append(name)
            self._started_ids.add(id(svc))
            try:
                result = start_method()
                if isinstance(result, dict) and result.get("ok") is False:
                    err = str(result.get("error") or "start returned ok=False")
                    self._record_start_failure(name, err)
                    if hasattr(self, '_service_states'):
                        self._service_states[name] = "failed"
                        self.service_state_changed.emit(name, "failed")
                    continue
                if hasattr(self, '_service_states'):
                    self._service_states[name] = "ready"
                    self.service_state_changed.emit(name, "ready")
            except Exception as e:
                self._record_start_failure(name, str(e))
                if hasattr(self, '_service_states'):
                    self._service_states[name] = "failed"
                    self.service_state_changed.emit(name, "failed")
        required_names = {
            name for name, desc in SERVICE_MANIFEST.items()
            if desc.priority == ServicePriority.REQUIRED
        }
        has_missing_required = any(
            name not in self._services or self._services[name] is None
            for name in required_names
        )
        has_required_failure = any(
            self.priority(n) == ServicePriority.REQUIRED
            for n in self._failures
        )
        if has_missing_required or has_required_failure:
            self._state = ContainerState.FAILED
        else:
            has_optional_failure = any(
                self.priority(n) == ServicePriority.OPTIONAL
                for n in self._failures
            )
            self._state = ContainerState.DEGRADED if has_optional_failure else ContainerState.READY

    def ready(self) -> bool:
        return self._state in (ContainerState.READY, ContainerState.DEGRADED)

    def health(self) -> dict:
        managed = sum(
            1 for desc in SERVICE_MANIFEST.values()
            if desc.lifecycle == LifecycleKind.MANAGED
        )
        required = sum(
            1 for desc in SERVICE_MANIFEST.values()
            if desc.priority == ServicePriority.REQUIRED
        )
        optional = sum(
            1 for desc in SERVICE_MANIFEST.values()
            if desc.priority == ServicePriority.OPTIONAL
        )
        capability_gated = sum(
            1 for desc in SERVICE_MANIFEST.values()
            if desc.priority == ServicePriority.CAPABILITY_GATED
        )
        deferred_physical = sum(
            1 for desc in SERVICE_MANIFEST.values()
            if desc.priority == ServicePriority.DEFERRED_PHYSICAL
        )
        deferred = sum(
            1 for desc in SERVICE_MANIFEST.values()
            if desc.priority == ServicePriority.DEFERRED
        )
        return {
            "state": self._state.value,
            "services": len(self._services),
            "failures": dict(self._failures),
            "required": required,
            "optional": optional,
            "capability_gated": capability_gated,
            "deferred_physical": deferred_physical,
            "deferred": deferred,
            "manifest_entries": len(SERVICE_MANIFEST),
            "manifest_managed": managed,
            "started": len(self._started_order),
        }

    def cancel_all(self) -> None:
        for name in list(self._services.keys()):
            svc = self._services[name]
            if hasattr(svc, 'cancel'):
                try:
                    svc.cancel()
                except Exception as e:
                    logger.debug("cancel %s: %s", name, e)

    def shutdown(self) -> None:
        """Stop registered services in reverse manifest dependency order.

        Order: MANAGED descriptors in reverse start order, then EXTERNAL
        descriptors, then any remaining registered key. Each instance is
        processed exactly once (aliases and duplicate keys share the
        instance identity and are deduplicated).
        """

        self._state = ContainerState.STOPPING
        shutdown_order: list[str] = []
        processed: set[str] = set()
        seen_ids: set[int] = set()

        def _append(name: str) -> None:
            if name not in self._services or name in processed:
                return
            svc = self._services[name]
            if id(svc) in seen_ids:
                return
            processed.add(name)
            seen_ids.add(id(svc))
            shutdown_order.append(name)

        start_order = self._lifecycle_start_order()
        for name in reversed(start_order):
            _append(name)
        for name, desc in SERVICE_MANIFEST.items():
            if desc.lifecycle == LifecycleKind.EXTERNAL:
                _append(name)
        for name in self._services:
            _append(name)

        for name in shutdown_order:
            svc = self._services[name]
            if hasattr(svc, 'shutdown') and callable(svc.shutdown):
                try:
                    svc.shutdown()
                except Exception as e:
                    logger.debug("shutdown %s: %s", name, e)
            elif hasattr(svc, 'stop') and callable(svc.stop):
                try:
                    svc.stop()
                except Exception as e:
                    logger.debug("stop %s: %s", name, e)
        self.cancel_all()
        self._failures.clear()
        self._state = ContainerState.STOPPED

    def report_failure(self, name: str, error: str) -> None:
        self._failures[name] = error
        priority = self.priority(name)
        if priority == ServicePriority.REQUIRED:
            logger.error("REQUIRED service '%s' FAILED: %s", name, error)

    def is_capable(self, name: str) -> bool:
        prio = self.priority(name)
        if prio == ServicePriority.REQUIRED:
            return name in self._services and self._services[name] is not None and name not in self._failures
        if prio == ServicePriority.OPTIONAL:
            return name in self._services and self._services[name] is not None
        if prio == ServicePriority.CAPABILITY_GATED:
            return name in self._services and self._services[name] is not None and name not in self._failures
        return prio != ServicePriority.DEFERRED_PHYSICAL

    def list_services(self) -> dict[str, dict]:
        """List every registered key plus every manifest name.

        Each entry reports availability, priority, failure state and
        capability. Manifest lifecycle state is exposed via ``lifecycle_of``.
        """
        result = {}
        for name in sorted(set(self._services.keys()) | set(SERVICE_MANIFEST)):
            svc = self._services.get(name)
            result[name] = {
                "available": svc is not None,
                "priority": self._priorities.get(name, ServicePriority.OPTIONAL).value,
                "failed": name in self._failures,
                "error": self._failures.get(name, ""),
                "capable": self.is_capable(name),
            }
        return result


class ObservableServiceContainer(ServiceContainer, QObject):
    """Service container that emits Qt signals for service state changes."""

    service_state_changed = Signal(str, str)

    VALID_STATES = {"registered", "starting", "ready", "degraded", "unavailable", "failed", "stopping", "stopped"}

    def __init__(self):
        ServiceContainer.__init__(self)
        QObject.__init__(self)
        self._service_states: dict[str, str] = {}

    def _can_auto_start(self, service) -> bool:
        """Check if service.start() can be called without arguments."""
        if not hasattr(service, 'start') or not callable(service.start):
            return False
        import inspect
        try:
            sig = inspect.signature(service.start)
            params = list(sig.parameters.keys())
            # Allow self + optional params with defaults
            required = [p for p in params
                       if p != 'self'
                       and sig.parameters[p].default is inspect.Parameter.empty]
            return len(required) == 0
        except (ValueError, TypeError):
            return False

    def register(
        self,
        name: str,
        service: Any,
        priority: ServicePriority | None = None,
        dependencies: tuple[str, ...] | None = None,
    ) -> None:
        """Register a service — does NOT auto-start. Use start() for topological startup."""

        self._service_states[name] = "registered"
        ServiceContainer.register(self, name, service, priority, dependencies or ())
        self.service_state_changed.emit(name, self._service_states[name])

    def get_service_state(self, name: str) -> str:
        return self._service_states.get(name, "unavailable")

    def get_service_states(self) -> dict[str, str]:
        return dict(self._service_states)

    def get_service_diagnostics(self, name: str) -> dict:
        return {
            "name": name,
            "state": self._service_states.get(name, "unavailable"),
            "available": self.contains(name),
            "priority": self.priority(name).value if self.priority(name) else "unknown",
            "failed": name in self._failures,
            "error": self._failures.get(name, ""),
            "lifecycle": self.lifecycle_of(name),
        }
