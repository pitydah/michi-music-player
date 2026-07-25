"""Settings and accessibility composition — theme, accessibility, background, runtime adapters."""
from __future__ import annotations

import contextlib

from core.service_container import ServiceContainer


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

        # Register all settings adapters
        from core.settings_adapters import (
            AccessibilitySettingsAdapter, ThemeSettingsAdapter,
            PlaybackSettingsAdapter, AudioSettingsAdapter, EqSettingsAdapter,
            LibrarySettingsAdapter, CacheSettingsAdapter, HistorySettingsAdapter,
            RadioSettingsAdapter, LyricsSettingsAdapter, DeviceSettingsAdapter,
            ConnectionSettingsAdapter, HomeAudioSettingsAdapter, LoggingSettingsAdapter,
        )
        for adapter_cls in (AccessibilitySettingsAdapter, ThemeSettingsAdapter,
                            PlaybackSettingsAdapter, AudioSettingsAdapter,
                            EqSettingsAdapter, LibrarySettingsAdapter,
                            CacheSettingsAdapter, HistorySettingsAdapter,
                            RadioSettingsAdapter, LyricsSettingsAdapter,
                            DeviceSettingsAdapter, ConnectionSettingsAdapter,
                            HomeAudioSettingsAdapter, LoggingSettingsAdapter):
            with contextlib.suppress(Exception):
                coordinator.register_adapter(adapter_cls())

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
