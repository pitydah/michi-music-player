"""MichiAISnapshotService — build a unified sanitized snapshot for Michi AI.

Combines data from ContextService, Sync, Michi Link and Audio Lab.
Output is sanitized: no filepaths, tokens, passwords or audio data.
Capabilities come from the RUNTIME (ContextService snapshot + the S4
capability resolver + container health) — never from a static all-True dict
(ADR-005: a missing/unhealthy service reports available=False with a reason).
"""

from __future__ import annotations

from typing import Any


class MichiAISnapshotService:
    def __init__(self, context_service=None, sync_manager=None, michi_link_doctor=None,
                 capability_resolver=None, container=None):
        self._ctx = context_service
        self._sync = sync_manager
        self._doctor = michi_link_doctor
        self._capability_resolver = capability_resolver
        self._container = container

    def build_snapshot(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "route": {},
            "selection": {},
            "playback": {},
            "library_health": {},
            "sync": self._sync_status(),
            "michi_link": self._michi_link_status(),
            "recent_events": [],
            "capabilities": self._capabilities(),
        }

        if self._ctx is not None:
            try:
                snap = self._ctx.get_assistant_snapshot()
                if snap:
                    result["route"] = snap.get("route", {})
                    result["selection"] = snap.get("selection", {})
                    result["playback"] = snap.get("playback", {})
                    result["library_health"] = snap.get("library_health", {})
                    result["recent_events"] = snap.get("recent_events", [])[:20]
                    result["capabilities"] = snap.get("assistant_capabilities", {})
                    result["capability_reasons"] = snap.get("capability_reasons", {})
            except Exception:
                pass

        return result

    def _sync_status(self) -> dict[str, Any]:
        if self._sync is None:
            return {"active": False, "peers": 0}
        try:
            peers = self._sync.get_all_peers() if hasattr(self._sync, "get_all_peers") else []
            active = self._sync.isRunning() if hasattr(self._sync, "isRunning") else False
            return {"active": active, "peers": len(peers), "syncing": hasattr(self._sync, "is_syncing") and self._sync.is_syncing()}
        except Exception:
            return {"active": False, "peers": 0}

    def _michi_link_status(self) -> dict[str, Any]:
        if self._doctor is None:
            return {"available": False}
        try:
            summary = self._doctor.diagnose_home_summary()
            return {"available": True, "summary": summary}
        except Exception:
            return {"available": False}

    def _capabilities(self) -> dict[str, Any]:
        """Runtime capability evidence — never static True values.

        When a ContextService snapshot is available its assistant capabilities
        (runtime-gated) are reused; otherwise the S4 capability resolver and
        the container health are consulted directly.
        """
        resolver = self._capability_resolver
        container = self._container

        def _service_ok(service_key: str) -> bool:
            if container is not None:
                try:
                    return bool(container.contains(service_key)
                                and container.is_capable(service_key))
                except Exception:
                    return False
            return False

        def _evidence(cap_name: str, service_key: str) -> dict[str, Any]:
            if resolver is not None:
                try:
                    resolved = resolver.resolve(cap_name)
                    evidence = resolved.get(cap_name)
                    if evidence is not None:
                        return {
                            "available": bool(evidence.available),
                            "reason": evidence.reason or "",
                        }
                except Exception:
                    pass
            available = _service_ok(service_key)
            return {
                "available": available,
                "reason": "" if available else f"service_missing:{service_key}",
            }

        return {
            "can_search_library": _evidence("library.search", "global_search_service"),
            "can_create_playlist": _evidence("playlist.modify", "playlist_service"),
            "can_analyze_audio": _evidence("audio_lab.analyze", "audio_lab_service"),
            "can_diagnose_ecosystem": _evidence("diagnostics.read", "diagnostics_service"),
            "can_create_plans": _evidence("playlist.modify", "playlist_service"),
        }
