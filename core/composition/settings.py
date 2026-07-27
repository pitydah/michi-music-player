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
        from core.background_theme_service import BackgroundThemeService
        container.register("theme_service", BackgroundThemeService())
    except Exception:
        logger.error("Failed to create theme_service", exc_info=True)
        container.register("theme_service", None)

    try:
        from core.accessibility_service import AccessibilityService
        container.register("accessibility_service", AccessibilityService())
    except Exception:
        logger.error("Failed to create accessibility_service", exc_info=True)
        container.register("accessibility_service", None)
