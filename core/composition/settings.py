"""Settings and accessibility composition — theme, accessibility, background, runtime adapters."""
from __future__ import annotations

import logging

from core.service_container import ServiceContainer

logger = logging.getLogger(__name__)


def build(container: ServiceContainer) -> None:
    """Wire runtime settings adapters and optional presentation services."""
    # Wire settings coordinator with available services
    coordinator = container.get("settings_coordinator")
    if coordinator:
        ps = container.get("playback_service")
        qs = container.get("queue_service")
        wm = container.get("worker_manager")
        if ps:
            coordinator._player = ps
        if qs:
            coordinator._queue = qs
        if wm:
            coordinator._wm = wm

        # Register all settings adapters (bridges not yet available at
        # composition time; adapters fall back to the bridge singleton).
        from core.settings_adapters import register_all_adapters
        try:
            register_all_adapters(coordinator)
        except Exception:
            logger.error("Failed to register settings adapters", exc_info=True)

    try:
        from core.theme_service import ThemeService
        container.register("theme_service", ThemeService())
    except Exception:
        logger.error("Failed to create theme_service", exc_info=True)
        container.register("theme_service", None)

    try:
        from core.accessibility_service import AccessibilityService
        container.register("accessibility_service", AccessibilityService())
    except Exception:
        logger.error("Failed to create accessibility_service", exc_info=True)
        container.register("accessibility_service", None)

    # Canonical contextual truth source (S11) — consumes the REAL services and
    # derives capability evidence from container health + the S4 resolver.
    try:
        from core.context.context_service import ContextService
        container.register(
            "context_service",
            ContextService(
                db=container.get("database"),
                playback=container.get("playback_service"),
                sync=container.get("device_sync_service"),
                snapshot_service=container.get("playback_snapshot_service"),
                services={
                    "queue_service": container.get("queue_service"),
                    "job_service": container.get("job_service"),
                    "radio_service": container.get("radio_service"),
                    "recognition_service": container.get("recognition_service"),
                    "library_query_service": container.get("library_query_service"),
                    "global_search_service": container.get("global_search_service"),
                    "playlist_service": container.get("playlist_service"),
                    "library_mutation_service": container.get("library_mutation_service"),
                    "audio_lab_service": container.get("audio_lab_service"),
                    "diagnostics_service": container.get("diagnostics_service"),
                    "device_sync_service": container.get("device_sync_service"),
                    "connection_service": container.get("connection_service"),
                    "home_audio_service": container.get("home_audio_service"),
                    "lyrics_service": container.get("lyrics_service"),
                    "settings_service": container.get("settings_service"),
                    "navigation_service": container.get("navigation_service"),
                },
                container=container,
            ),
        )
    except Exception:
        logger.error("Failed to create context_service", exc_info=True)
        container.register("context_service", None)
