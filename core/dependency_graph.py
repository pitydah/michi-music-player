import logging

logger = logging.getLogger(__name__)

SERVICE_ORDER = [
    "configuration", "database_factory", "repository_factory",
    "event_bus", "worker_manager", "query_executor", "job_manager",
    "settings_service", "settings_coordinator", "theme_store",
    "accessibility_service", "library_query_service", "library_mutation_service",
    "playlist_service", "history_query_service", "search_service",
    "playback_service", "queue_service", "audio_lab_service",
    "metadata_service", "library_doctor_service", "device_sync_service",
    "connection_service", "home_audio_service", "diagnostics_service",
    "action_registry", "notification_service", "michi_ai_service",
    "bridges", "models", "qml_context", "root_qml"
]

SERVICE_DEPENDENCIES = {
    "playlist_service": {"library_query_service", "database_factory"},
    "history_query_service": {"database_factory"},
    "search_service": {"database_factory", "library_query_service"},
    "playback_service": {"queue_service", "worker_manager"},
    "queue_service": {"playlist_service", "worker_manager"},
    "audio_lab_service": {"worker_manager", "library_query_service", "metadata_service"},
    "metadata_service": {"worker_manager", "library_mutation_service"},
    "library_doctor_service": {"library_query_service", "library_mutation_service", "worker_manager"},
    "device_sync_service": {"worker_manager", "library_query_service"},
    "connection_service": {"worker_manager"},
    "home_audio_service": {"worker_manager", "playback_service"},
    "diagnostics_service": {"worker_manager", "library_query_service", "settings_service"},
    "michi_ai_service": {"search_service", "playback_service", "playlist_service", "diagnostics_service", "settings_service", "action_registry"},
    "notification_service": {"action_registry", "job_manager"},
}


def resolve_order() -> list[str]:
    seen = set()
    ordered = []

    def visit(name: str, path: set):
        if name in seen:
            return
        if name in path:
            raise ValueError(f"Circular dependency detected: {' -> '.join(path | {name})}")
        for dep in SERVICE_DEPENDENCIES.get(name, set()):
            if dep in SERVICE_ORDER:
                visit(dep, path | {name})
        seen.add(name)
        ordered.append(name)

    for svc in SERVICE_ORDER:
        visit(svc, set())

    remaining = [s for s in SERVICE_ORDER if s not in ordered]
    ordered.extend(remaining)
    return ordered
