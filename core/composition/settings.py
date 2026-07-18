"""Settings and accessibility composition — theme, accessibility, background, runtime adapters."""
from __future__ import annotations

from core.service_container import ServiceContainer, ServicePriority


def build(container: ServiceContainer) -> None:
    # Wire settings coordinator with available services
    coordinator = container.get("settings_coordinator")
    if coordinator:
        ps = container.get("playback_service")
        wm = container.get("worker_manager")
        if ps:
            coordinator._player = ps
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
            try:
                coordinator.register_adapter(adapter_cls())
            except Exception:
                pass

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
