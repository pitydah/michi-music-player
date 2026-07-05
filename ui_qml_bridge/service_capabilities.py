"""ServiceCapabilities — what each bridge can actually do based on available services."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui_qml_bridge.service_bundle import ServiceBundle


def compute_capabilities(services: "ServiceBundle") -> dict[str, bool]:
    """Return dict of capability_name -> available (True/False).

    A bridge is available only when all its required services exist.
    This prevents fake functionality or empty state transitions.
    """
    return {
        "library": services.has("db"),
        "playback": services.has("player_service"),
        "nowplaying": services.has("player_service"),
        "mix": services.has("db"),
        "lyrics": services.has("worker_manager"),
        "connections_michilink": services.has("michi_link_controller"),
        "home_audio": services.has("home_audio_controller"),
        "snapcast": services.has("snapcast_controller"),
        "devices_sync": services.has("sync_manager"),
        "radio": services.has("radio_manager"),
        "playlists": services.has("db"),
        "eq": services.has("player_service"),
        "settings": True,
        "audio_lab": True,
        "metadata": True,
        "smart_tagging": services.has("smart_tagging_service"),
        "disc_lab": services.has("disc_service"),
        "library_doctor": services.has("db"),
        "diagnostics": services.has("db"),
        "michi_ai": True,
        "theme": True,
        "navigation": True,
        "route_registry": True,
        "app_state": True,
        "command_palette": True,
        "cover": True,
    }
