"""ServiceContainer — canonical service registry with full lifecycle management.

States: CREATED -> BUILDING -> BUILT -> STARTING -> READY -> DEGRADED -> FAILED -> STOPPING -> STOPPED.
API: register, get, require, contains, build_order, validate, start, health, cancel_all, shutdown.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger("michi.service_container")


class ContainerState(Enum):
    CREATED = "created"
    BUILDING = "building"
    BUILT = "built"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


class ServicePriority(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    CAPABILITY_GATED = "capability_gated"
    DEFERRED_PHYSICAL = "deferred_physical"
    DEFERRED = "deferred"


BUILTIN_DEPENDENCIES: dict[str, set[str]] = {
    "playlist_service": {"library_query_service", "connection_factory"},
    "history_query_service": {"connection_factory"},
    "global_search_service": {"connection_factory", "library_query_service"},
    "playback_service": {"queue_service", "worker_manager"},
    "queue_service": {"playlist_service", "worker_manager"},
    "track_action_service": {"queue_service", "playback_service"},
    "audio_lab_service": {"worker_manager", "library_query_service", "metadata_service"},
    "metadata_service": {"worker_manager", "library_mutation_service"},
    "library_doctor_service": {"library_query_service", "library_mutation_service", "worker_manager"},
    "device_sync_service": {"worker_manager", "library_query_service"},
    "connection_service": {"worker_manager"},
    "home_audio_service": {"worker_manager", "playback_service"},
    "diagnostics_service": {"worker_manager", "library_query_service", "settings_service"},
    "michi_ai_service": {
        "global_search_service", "playback_service", "playlist_service",
        "diagnostics_service", "settings_service", "action_registry",
    },
    "notification_service": {"action_registry", "job_service"},
    "confirmation_service": {"action_registry"},
    "settings_coordinator": {"settings_service"},
}

SERVICE_ORDER_INDEX: dict[str, int] = {
    name: i for i, name in enumerate([
        "paths", "settings_manager",
        "database", "connection_factory",
        "track_repository", "album_repository", "artist_repository",
        "event_bus", "runtime_persistence", "process_controller",
        "worker_manager", "query_executor", "job_service",
        "confirmation_service",
        "settings_coordinator", "settings_service",
        "playback_service", "queue_service", "track_action_service",
        "library_query_service", "library_sources_service", "library_mutation_service",
        "playlist_service", "history_query_service", "global_search_service",
        "mix_query_service", "mix_service",
        "metadata_service", "smart_tagging_service",
        "library_doctor_service", "audio_lab_service",
        "device_sync_service", "connection_service",
        "home_audio_service", "radio_service", "lyrics_service",
        "diagnostics_service", "notification_service",
        "action_registry",
        "michi_ai_service",
        "theme_service", "accessibility_service",
    ])
}


class ServiceContainer:
    """Typed container holding all backend service references with full lifecycle."""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._priorities: dict[str, ServicePriority] = {}
        self._dependencies: dict[str, set[str]] = {}
        self._failures: dict[str, str] = {}
        self._state = ContainerState.CREATED
        self._define_priorities()

    def _define_priorities(self):
        for name in self._required_names():
            self._priorities[name] = ServicePriority.REQUIRED
        for name in self._optional_names():
            self._priorities[name] = ServicePriority.OPTIONAL
        for name in self._capability_gated_names():
            self._priorities[name] = ServicePriority.CAPABILITY_GATED
        for name in self._deferred_physical_names():
            self._priorities[name] = ServicePriority.DEFERRED_PHYSICAL
        for name in self._deferred_names():
            self._priorities[name] = ServicePriority.DEFERRED

    @staticmethod
    def _required_names() -> set[str]:
        return {
            "database", "connection_factory", "worker_manager",
            "query_executor", "job_service", "event_bus",
            "settings_coordinator", "settings_service",
            "library_query_service", "library_sources_service",
            "library_mutation_service", "playlist_service",
            "history_query_service", "global_search_service",
            "mix_query_service", "mix_service",
            "track_action_service", "playback_service",
            "queue_service", "metadata_service",
        }

    @staticmethod
    def _optional_names() -> set[str]:
        return {
            "theme_service", "accessibility_service",
            "audio_lab_service", "smart_tagging_service",
            "library_doctor_service", "device_sync_service",
            "connection_service", "home_audio_service",
            "radio_service", "lyrics_service",
            "diagnostics_service", "notification_service",
            "action_registry", "confirmation_service",
            "runtime_persistence", "process_controller",
        }

    @staticmethod
    def _capability_gated_names() -> set[str]:
        return {"michi_ai_service"}

    @staticmethod
    def _deferred_physical_names() -> set[str]:
        return set()

    @staticmethod
    def _deferred_names() -> set[str]:
        return set()

    def _all_names(self) -> list[str]:
        return list(
            self._required_names()
            | self._optional_names()
            | self._capability_gated_names()
            | self._deferred_physical_names()
            | self._deferred_names()
        )

    def register(self, name: str, service: Any, priority: ServicePriority | None = None, dependencies: tuple[str, ...] = ()) -> None:
        self._services[name] = service
        if priority is not None:
            self._priorities[name] = priority
        elif name not in self._priorities:
            self._priorities[name] = ServicePriority.OPTIONAL
        if dependencies:
            self._dependencies[name] = set(dependencies)

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

    def build_order(self) -> list[str]:
        deps = {}
        for name in self._all_names():
            deps[name] = set(self._dependencies.get(name, BUILTIN_DEPENDENCIES.get(name, set())))
        for _name, dep_set in deps.items():
            dep_set.intersection_update(self._all_names())
        ordered = []
        seen = set()
        def visit(n: str, path: set):
            if n in seen:
                return
            if n in path:
                raise ValueError(f"Circular dependency: {' -> '.join(path | {n})}")
            for d in deps.get(n, set()):
                visit(d, path | {n})
            seen.add(n)
            ordered.append(n)
        all_sorted = sorted(self._all_names(), key=lambda x: SERVICE_ORDER_INDEX.get(x, 999))
        for svc in all_sorted:
            visit(svc, set())
        remaining = [s for s in all_sorted if s not in ordered]
        ordered.extend(remaining)
        return ordered

    def validate(self) -> list[str]:
        errors = []
        for name in self._required_names():
            svc = self._services.get(name)
            if svc is None:
                errors.append(f"REQUIRED '{name}' is None or missing")
        deps = {}
        for name in self._all_names():
            deps[name] = set(self._dependencies.get(name, BUILTIN_DEPENDENCIES.get(name, set())))
            deps[name].intersection_update(self._all_names())
        for name, dep_set in deps.items():
            if self.priority(name) != ServicePriority.REQUIRED:
                continue
            for dep in dep_set:
                if dep not in self._services or self._services[dep] is None:
                    errors.append(f"'{name}' depends on '{dep}' which is missing")
        for fname in self._failures:
            prio = self.priority(fname)
            if prio == ServicePriority.REQUIRED:
                errors.append(f"REQUIRED '{fname}' has FAILED: {self._failures[fname]}")
        return errors

    @property
    def database(self):
        return self._services.get("database")

    @property
    def connection_factory(self):
        return self._services.get("connection_factory")

    @property
    def worker_manager(self):
        return self._services.get("worker_manager")

    @property
    def query_executor(self):
        return self._services.get("query_executor")

    @property
    def job_service(self):
        return self._services.get("job_service")

    @property
    def event_bus(self):
        return self._services.get("event_bus")

    @property
    def settings_coordinator(self):
        return self._services.get("settings_coordinator")

    @property
    def settings_service(self):
        return self._services.get("settings_service")

    @property
    def theme_service(self):
        return self._services.get("theme_service")

    @property
    def accessibility_service(self):
        return self._services.get("accessibility_service")

    @property
    def library_query_service(self):
        return self._services.get("library_query_service")

    @property
    def library_sources_service(self):
        return self._services.get("library_sources_service")

    @property
    def library_mutation_service(self):
        return self._services.get("library_mutation_service")

    @property
    def playlist_service(self):
        return self._services.get("playlist_service")

    @property
    def history_query_service(self):
        return self._services.get("history_query_service")

    @property
    def global_search_service(self):
        return self._services.get("global_search_service")

    @property
    def mix_query_service(self):
        return self._services.get("mix_query_service")

    @property
    def mix_service(self):
        return self._services.get("mix_service")

    @property
    def track_action_service(self):
        return self._services.get("track_action_service")

    @property
    def playback_service(self):
        return self._services.get("playback_service")

    @property
    def queue_service(self):
        return self._services.get("queue_service")

    @property
    def audio_lab_service(self):
        return self._services.get("audio_lab_service")

    @property
    def metadata_service(self):
        return self._services.get("metadata_service")

    @property
    def smart_tagging_service(self):
        return self._services.get("smart_tagging_service")

    @property
    def library_doctor_service(self):
        return self._services.get("library_doctor_service")

    @property
    def device_sync_service(self) -> Any | None:
        return self._services.get("device_sync_service")

    def ensure_device_sync_service(self) -> Any | None:
        if "device_sync_service" not in self._services or self._services["device_sync_service"] is None:
            try:
                from core.device_sync_service import DeviceSyncService
                svc = DeviceSyncService()
                self.register("device_sync_service", svc)
                logger.info("DeviceSyncService built productively")
                return svc
            except Exception as e:
                logger.warning("DeviceSyncService build failed: %s", e)
                return None
        return self._services["device_sync_service"]

    @property
    def connection_service(self):
        return self._services.get("connection_service")

    @property
    def home_audio_service(self):
        return self._services.get("home_audio_service")

    @property
    def diagnostics_service(self):
        return self._services.get("diagnostics_service")

    @property
    def notification_service(self):
        return self._services.get("notification_service")

    @property
    def action_registry(self):
        return self._services.get("action_registry")

    @property
    def confirmation_service(self):
        return self._services.get("confirmation_service")

    @property
    def runtime_persistence(self):
        return self._services.get("runtime_persistence")

    @property
    def process_controller(self):
        return self._services.get("process_controller")

    @property
    def radio_service(self):
        return self._services.get("radio_service")

    @property
    def lyrics_service(self):
        return self._services.get("lyrics_service")

    @property
    def michi_ai_service(self):
        return self._services.get("michi_ai_service")

    @property
    def state(self) -> ContainerState:
        return self._state

    def start(self):
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
        order = self.build_order()
        started_required = 0
        for name in order:
            if name not in self._services or self._services[name] is None:
                prio = self.priority(name)
                if prio == ServicePriority.REQUIRED:
                    self._failures[name] = "missing"
                continue
            svc = self._services[name]
            if hasattr(svc, 'start') and callable(svc.start):
                try:
                    svc.start()
                except Exception as e:
                    err = str(e)
                    self._failures[name] = err
                    prio = self.priority(name)
                    if prio == ServicePriority.REQUIRED:
                        logger.error("REQUIRED '%s' start failed: %s", name, err)
            else:
                if self.priority(name) == ServicePriority.REQUIRED:
                    started_required += 1
        has_missing_required = any(
            name not in self._services or self._services[name] is None
            for name in self._required_names()
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
        return {
            "state": self._state.value,
            "services": len(self._services),
            "failures": dict(self._failures),
            "required": len(self._required_names()),
            "optional": len(self._optional_names()),
            "capability_gated": len(self._capability_gated_names()),
            "deferred_physical": len(self._deferred_physical_names()),
        }

    def cancel_all(self):
        for name in list(self._services.keys()):
            svc = self._services[name]
            if hasattr(svc, 'cancel'):
                try:
                    svc.cancel()
                except Exception as e:
                    logger.debug("cancel %s: %s", name, e)

    def shutdown(self):
        self._state = ContainerState.STOPPING
        order = self.build_order()
        all_ordered = list(reversed(order))
        for name in self._services:
            if name not in all_ordered:
                all_ordered.append(name)
        for name in all_ordered:
            if name not in self._services:
                continue
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

    def report_failure(self, name: str, error: str):
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
        result = {}
        for name in self._all_names():
            svc = self._services.get(name)
            result[name] = {
                "available": svc is not None,
                "priority": self._priorities.get(name, ServicePriority.OPTIONAL).value,
                "failed": name in self._failures,
                "error": self._failures.get(name, ""),
                "capable": self.is_capable(name),
            }
        return result
