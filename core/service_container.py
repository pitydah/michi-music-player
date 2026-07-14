from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger("michi.service_container")


class ServicePriority(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    DEFERRED = "deferred"


class ServiceContainer:
    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._priorities: dict[str, ServicePriority] = {}
        self._failures: dict[str, str] = {}
        self._started = False
        self._define_priorities()

    def _define_priorities(self) -> None:
        for name in self._required_names():
            self._priorities[name] = ServicePriority.REQUIRED
        for name in self._optional_names():
            self._priorities[name] = ServicePriority.OPTIONAL
        for name in self._deferred_names():
            self._priorities[name] = ServicePriority.DEFERRED

    @staticmethod
    def _required_names() -> set[str]:
        return {
            "event_bus", "settings_service", "job_service",
            "playback_service", "queue_service", "library_query_service",
            "track_action_service",
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
            "radio_service", "lyrics_service", "metadata_service",
            "assistant_core_service", "assistant_tool_registry",
            "assistant_capability_resolver", "assistant_context_assembler",
            "assistant_conversation_service", "assistant_confirmation_service",
            "assistant_trace_recorder", "assistant_gateways",
            "confirmation_service", "capability_service",
        }

    @staticmethod
    def _deferred_names() -> set[str]:
        return {
            "musicbrainz_provider", "cover_art_provider",
            "lrclib_provider", "assistant_local_model_provider",
        }

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
    def event_bus(self):
        return self._services.get("event_bus")

    @property
    def settings_service(self):
        return self._services.get("settings_service")

    @property
    def job_service(self):
        return self._services.get("job_service")

    @property
    def playback_service(self):
        return self._services.get("playback_service")

    @property
    def queue_service(self):
        return self._services.get("queue_service")

    @property
    def library_query_service(self):
        return self._services.get("library_query_service")

    @property
    def track_action_service(self):
        return self._services.get("track_action_service")

    @property
    def radio_service(self):
        return self._services.get("radio_service")

    @property
    def lyrics_service(self):
        return self._services.get("lyrics_service")

    @property
    def metadata_service(self):
        return self._services.get("metadata_service")

    @property
    def assistant_core_service(self):
        return self._services.get("assistant_core_service")

    @property
    def assistant_tool_registry(self):
        return self._services.get("assistant_tool_registry")

    @property
    def assistant_gateways(self):
        return self._services.get("assistant_gateways")

    @property
    def confirmation_service(self):
        return self._services.get("confirmation_service")

    @property
    def capability_service(self):
        return self._services.get("capability_service")

    @property
    def diagnostics_service(self):
        return self._services.get("diagnostics_service")

    @property
    def action_registry(self):
        return self._services.get("action_registry")

    def ensure_assistant_core(self) -> Any | None:
        if self.has("assistant_core_service"):
            return self._services["assistant_core_service"]
        self._build_assistant_core()
        return self._services.get("assistant_core_service")

    def _build_assistant_core(self) -> None:
        try:
            from core.assistant_initializer import create_assistant_composition

            comp = create_assistant_composition(
                metadata_service=self._services.get("metadata_service"),
                queue_service=self._services.get("queue_service"),
                playlist_service=self._services.get("playlist_service"),
                confirmation_service=self._services.get("confirmation_service"),
                job_service=self._services.get("job_service"),
                settings_service=self._services.get("settings_service"),
                player_service=self._services.get("playback_service"),
                library_db=self._services.get("library_query_service"),
                audio_lab_service=self._services.get("audio_lab_service"),
                sync_manager=self._services.get("device_sync_service"),
                diagnostics_service=self._services.get("diagnostics_service"),
                mix_service=self._services.get("mix_query_service"),
            )

            self.register("assistant_core_service", comp.core_service)
            self.register("assistant_tool_registry", comp.tool_registry)
            self.register("assistant_capability_resolver", comp.capability_resolver)
            self.register("assistant_context_assembler", comp.context_assembler)
            self.register("assistant_conversation_service", comp.conversation_service)
            self.register("assistant_confirmation_service", comp.confirmation_policy)
            self.register("assistant_trace_recorder", comp.trace_recorder)
            self.register("assistant_gateways", comp.gateways)
            logger.info("AssistantCoreService built and registered via composition")
        except Exception as e:
            logger.warning("AssistantCoreService build failed: %s", e)
            import traceback
            logger.debug(traceback.format_exc())

    def start(self) -> None:
        self._started = True
        logger.info("ServiceContainer started")

    def ready(self) -> bool:
        return self._started

    def shutdown(self) -> None:
        order = [
            "assistant_core_service", "radio_service", "lyrics_service",
            "metadata_service", "audio_lab_service",
            "assistant_local_model_provider", "lrclib_provider",
            "cover_art_provider", "musicbrainz_provider",
            "device_sync_service",
        ]
        for name in order:
            svc = self._services.get(name)
            if svc is not None and hasattr(svc, "shutdown"):
                try:
                    svc.shutdown()
                except Exception as e:
                    logger.debug("Shutdown error for '%s': %s", name, e)
        self._started = False
        self._failures.clear()
        logger.info("ServiceContainer shutdown complete")

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
        return True

    def list_services(self) -> dict[str, dict]:
        result: dict[str, dict] = {}
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
