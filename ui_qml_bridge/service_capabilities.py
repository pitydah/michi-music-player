"""ServiceCapabilities — what each bridge can actually do based on available services."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui_qml_bridge.service_bundle import ServiceBundle


CAPABILITY_STATES = {
    "AVAILABLE": "available",
    "DEGRADED": "degraded",
    "UNAVAILABLE": "unavailable",
    "DEFERRED_PHYSICAL": "deferred_physical",
}


def compute_capabilities(services: "ServiceBundle") -> dict[str, str]:
    """Return dict of capability_name -> state string.

    States: AVAILABLE, DEGRADED, UNAVAILABLE, DEFERRED_PHYSICAL.
    A bridge is available only when all its required services exist.
    DEFERRED_PHYSICAL indicates hardware dependency is deferred vs error.
    """
    return {
        "library": "available" if services.has("db") else "unavailable",
        "playback": "available" if services.has("player_service") else "unavailable",
        "nowplaying": "available" if services.has("player_service") else "unavailable",
        "mix": "available" if services.has("db") else "unavailable",
        "lyrics": "available" if services.has("worker_manager") else "unavailable",
        "connections_michilink": "available" if services.has("michi_link_controller") else "unavailable",
        "home_audio": "available" if services.has("home_audio_controller") else ("deferred_physical" if services.has("snapcast_controller") else "unavailable"),
        "snapcast": "available" if services.has("snapcast_controller") else "unavailable",
        "devices_sync": "available" if services.has("sync_manager") else "unavailable",
        "radio": "available" if services.has("radio_manager") else "unavailable",
        "playlists": "available" if services.has("db") else "unavailable",
        "eq": "available" if services.has("player_service") else "unavailable",
        "settings": "available",
        "audio_lab": "available",
        "metadata": "available",
        "smart_tagging": "available" if services.has("smart_tagging_service") else "unavailable",
        "disc_lab": "available" if services.has("disc_service") else ("deferred_physical" if services.has("db") else "unavailable"),
        "library_doctor": "available" if services.has("db") else "unavailable",
        "diagnostics": "available" if services.has("db") else "unavailable",
        "michi_ai": "available",
        "theme": "available",
        "navigation": "available",
        "route_registry": "available",
        "app_state": "available",
        "command_palette": "available",
        "cover": "available",
        "notifications": "available",
        "global_search": "available" if services.has("search_service") else "unavailable",
    }
