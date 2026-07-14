"""ServiceContainer — typed service registry with lifecycle management.

All services are registered with a classification:
  - REQUIRED: domain-critical; failure blocks domain, capability=False, logs error
  - OPTIONAL: nice-to-have; failure tolerated, capability may degrade
  - DEFERRED: created on first access, not at startup

Lifecycle: CREATED -> STARTING -> READY | DEGRADED | FAILED -> STOPPING -> STOPPED
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger("michi.service_container")


class ContainerState(Enum):
    CREATED = "created"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


class ServicePriority(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    DEFERRED = "deferred"


SERVICES_REQUIRED = {
    "database", "connection_factory", "worker_manager", "query_executor",
    "job_service", "settings_service", "queue_service",
}


class ServiceContainer:
    """Typed container holding all backend service references with full lifecycle."""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._priorities: dict[str, ServicePriority] = {}
        self._failures: dict[str, str] = {}
        self._state = ContainerState.CREATED
        self._start_order: list[str] = []

        self._define_priorities()

    def _define_priorities(self):
        for name in self._required_names():
            self._priorities[name] = ServicePriority.REQUIRED
        for name in self._optional_names():
            self._priorities[name] = ServicePriority.OPTIONAL
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
            "mix_query_service", "track_action_service",
            "playback_service", "queue_service", "metadata_service",
        }

    @staticmethod
    def _optional_names() -> set[str]:
        return {
            "theme_service", "accessibility_service",
            "audio_lab_service", "smart_tagging_service",
            "library_doctor_service", "device_sync_service",
            "connection_service", "home_audio_service",
            "diagnostics_service", "notification_service",
            "action_registry",
        }

    @staticmethod
    def _deferred_names() -> set[str]:
        return set()

    def _all_names(self) -> list[str]:
        return list(self._required_names() | self._optional_names() | self._deferred_names())

    def register(self, name: str, service: Any) -> None:
        self._services[name] = service

    def get(self, name: str) -> Any:
        return self._services.get(name)

    def has(self, name: str) -> bool:
        return name in self._services and self._services[name] is not None

    def priority(self, name: str) -> ServicePriority | None:
        return self._priorities.get(name)

    @property
    def state(self) -> ContainerState:
        return self._state

    @state.setter
    def state(self, value: ContainerState):
        self._state = value

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

    def start(self):
        self._state = ContainerState.STARTING
        required_failures = {n for n, e in self._failures.items() if self.priority(n) == ServicePriority.REQUIRED}
        self._state = ContainerState.DEGRADED if required_failures else ContainerState.READY

    def ready(self) -> bool:
        return self._state in (ContainerState.READY, ContainerState.DEGRADED)

    def health(self) -> dict:
        return {"state": self._state.value, "services": len(self._services), "failures": dict(self._failures)}

    def shutdown(self):
        self._state = ContainerState.STOPPING
        self._failures.clear()
        self._state = ContainerState.STOPPED

    def report_failure(self, name: str, error: str):
        self._failures[name] = error
        priority = self.priority(name)
        if priority == ServicePriority.REQUIRED:
            logger.error("REQUIRED service '%s' FAILED: %s — domain blocked, capability=False", name, error)

    def is_capable(self, name: str) -> bool:
        prio = self.priority(name)
        if prio == ServicePriority.REQUIRED:
            return name in self._services and self._services[name] is not None and name not in self._failures
        if prio == ServicePriority.OPTIONAL:
            return name in self._services and self._services[name] is not None
        return True

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


ServiceRegistry = ServiceContainer
