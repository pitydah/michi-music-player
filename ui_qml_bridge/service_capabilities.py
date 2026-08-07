"""ServiceCapabilities — what each bridge can actually do based on available services."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.service_container import ServiceContainer


CAPABILITY_STATES = {
    "AVAILABLE": "available",
    "DEGRADED": "degraded",
    "UNAVAILABLE": "unavailable",
    "DEFERRED_PHYSICAL": "deferred_physical",
}


def compute_capabilities(container: "ServiceContainer") -> dict[str, str]:
    """Return dict of capability_name -> state string.

    States: AVAILABLE, DEGRADED, UNAVAILABLE, DEFERRED_PHYSICAL.
    A bridge is available only when all its required services exist.
    DEFERRED_PHYSICAL indicates hardware dependency is deferred vs error.
    """
    return {
        "library": "available" if container.contains("connection_factory") else "unavailable",
        "playback": "available" if container.contains("playback_service") else "unavailable",
        "nowplaying": "available" if container.contains("playback_service") else "unavailable",
        "mix": "available" if container.contains("connection_factory") else "unavailable",
        "lyrics": "available" if container.contains("worker_manager") else "unavailable",
        "connections_michilink": "available" if container.contains("connection_service") else "unavailable",
        "home_audio": "available" if container.contains("home_audio_service") else ("deferred_physical" if container.contains("home_audio_service") else "unavailable"),
        "snapcast": "available" if container.contains("home_audio_service") else "unavailable",
        "devices_sync": "available" if container.contains("device_sync_service") else "unavailable",
        "radio": "available" if container.contains("radio_service") else "unavailable",
        "playlists": "available" if container.contains("connection_factory") else "unavailable",
        "eq": "available" if container.contains("playback_service") else "unavailable",
        "settings": "available",
        "audio_lab": "available",
        "metadata": "available",
        "smart_tagging": "available" if container.contains("smart_tagging_service") else "unavailable",
        "disc_lab": "available" if container.contains("cd_ripper_service") else ("deferred_physical" if container.contains("connection_factory") else "unavailable"),
        "library_doctor": "available" if container.contains("connection_factory") else "unavailable",
        "diagnostics": "available" if container.contains("connection_factory") else "unavailable",
        "michi_ai": "available",
        "theme": "available",
        "navigation": "available",
        "route_registry": "available",
        "app_state": "available",
        "command_palette": "available",
        "cover": "available",
        "notifications": "available",
        "global_search": _global_search_state(container),
    }


def _global_search_state(container: "ServiceContainer") -> str:
    """Truthful global search capability (Slice 6).

    ``available`` only when the service exists AND ``search_available()``
    reports the whole chain operative (query executor + worker manager active,
    database readable, at least one provider registered). Falls back to
    presence for legacy service objects without the probe.
    """
    try:
        contains = container.contains("global_search_service")
    except Exception:
        return "unavailable"
    if not contains:
        return "unavailable"
    try:
        service = container.get("global_search_service")
    except Exception:
        return "unavailable"
    checker = getattr(service, "search_available", None)
    if not callable(checker):
        return "available"
    try:
        info = checker()
        return "available" if bool(info.get("ok")) else "unavailable"
    except Exception:
        return "unavailable"
