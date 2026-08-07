"""Capabilities snapshot section — runtime capability evidence.

Every capability is derived from RUNTIME checks: container health
(``contains`` + ``is_capable`` for the backing service key) and, when a
``CapabilityResolver`` is wired, its registered capability evidence
(``library.search``, ``queue.modify``, ...). There is NO static all-True
capability dict here: a missing or unhealthy backing service yields
``available: False`` with a human-readable reason.
"""

from __future__ import annotations

from typing import Any

_CAPABILITY_SERVICE_MAP: dict[str, str] = {
    "can_search_library": "global_search_service",
    "can_create_playlist": "playlist_service",
    "can_queue": "queue_service",
    "can_play": "playback_service",
    "can_edit_metadata": "library_mutation_service",
    "can_analyze_audio": "audio_lab_service",
    "can_diagnose": "diagnostics_service",
    "can_sync": "device_sync_service",
    "can_radio": "radio_service",
    "can_lyrics": "lyrics_service",
    "can_home_audio": "home_audio_service",
    "can_connect": "connection_service",
    "can_ai": "michi_ai_service",
}

# Assistant capabilities whose backing evidence comes from the capability
# resolver (S4), falling back to the container-backed service keys above.
_CAPABILITY_EVIDENCE: dict[str, str] = {
    "library.search": "global_search_service",
    "library.read": "library_query_service",
    "playlist.read": "playlist_service",
    "playlist.modify": "playlist_service",
    "queue.read": "queue_service",
    "queue.modify": "queue_service",
    "playback.control": "playback_service",
    "metadata.read": "library_mutation_service",
    "audio_lab.analyze": "audio_lab_service",
    "devices.sync": "device_sync_service",
    "settings.read": "settings_service",
    "navigation.request": "navigation_service",
}


class CapabilitiesSectionProvider:
    section_key = "capabilities"

    def build(self, context) -> dict[str, Any]:
        container = context.container
        resolver = context.capability_resolver

        def _service_ok(service_key: str) -> bool:
            if container is not None:
                return bool(container.contains(service_key)
                            and container.is_capable(service_key))
            return context.services.get(service_key) is not None

        capabilities: dict[str, dict[str, Any]] = {}

        for name, service_key in _CAPABILITY_SERVICE_MAP.items():
            available = _service_ok(service_key)
            capabilities[name] = {
                "available": available,
                "reason": "" if available else f"service_missing:{service_key}",
            }

        # Capability-resolver evidence (S4 truthfulness: gateway reports
        # operational capabilities — never object existence alone).
        for cap_name, service_key in _CAPABILITY_EVIDENCE.items():
            available = _service_ok(service_key)
            reason = "" if available else f"service_missing:{service_key}"
            if resolver is not None:
                try:
                    resolved = resolver.resolve(cap_name)
                    evidence = resolved.get(cap_name)
                    if evidence is not None:
                        available = bool(evidence.available)
                        reason = evidence.reason or reason
                except Exception:
                    available = False
                    reason = f"capability_resolver_error:{cap_name}"
            capabilities[cap_name] = {"available": available, "reason": reason}

        return {
            "available": True,
            "capabilities": capabilities,
            "resolver_present": resolver is not None,
            "container_present": container is not None,
        }
