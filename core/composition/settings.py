"""Settings and accessibility composition — theme, accessibility, background."""
from __future__ import annotations

from core.service_container import ServiceContainer, ServicePriority


def build(container: ServiceContainer) -> None:
    try:
        from core.background_theme_service import BackgroundThemeService
        container.register("theme_service", BackgroundThemeService())
    except Exception:
        container.register("theme_service", None)

    try:
        from core.accessibility_service import AccessibilityService
        container.register("accessibility_service", AccessibilityService())
    except Exception:
        container.register("accessibility_service", None)
